from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
import datetime

from apps.tenants.models import Tenant
from apps.identity.models import PhoneIdentity
from apps.payments.models import PaymentRequest, Transaction
from apps.conversation.parser import parse_command, ParsedCommand
from apps.conversation.handlers import dispatch
from apps.conversation.session import get_session, set_session_flow, clear_session
from apps.conversation.models import ProcessedWhatsAppMessage
from apps.conversation.tasks import process_whatsapp_message
from apps.whatsapp.models import InboundWhatsAppEvent

User = get_user_model()


class CommandParserTest(TestCase):
    def test_parse_commands(self):
        # 1. request
        pc = parse_command("request 2500 for INV-1002")
        self.assertEqual(pc.command, 'request')
        self.assertEqual(pc.amount, 2500)
        self.assertEqual(pc.reference, 'INV-1002')

        # 2. request with auto-ref
        pc = parse_command("request 500")
        self.assertEqual(pc.command, 'request')
        self.assertEqual(pc.amount, 500)
        self.assertIsNone(pc.reference)

        # 3. today
        pc = parse_command("today")
        self.assertEqual(pc.command, 'today')

        # 4. status
        pc = parse_command("status INV-1002")
        self.assertEqual(pc.command, 'status')
        self.assertEqual(pc.reference, 'INV-1002')

        # 5. last
        pc = parse_command("last 5")
        self.assertEqual(pc.command, 'last')
        self.assertEqual(pc.n, 5)

        # 6. cancel
        pc = parse_command("cancel INV-1002")
        self.assertEqual(pc.command, 'cancel')
        self.assertEqual(pc.reference, 'INV-1002')

        # 7. help
        pc = parse_command("help")
        self.assertEqual(pc.command, 'help')

        # 8. unknown
        pc = parse_command("random message body")
        self.assertEqual(pc.command, 'unknown')


class ConversationFlowTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Imara Tech", slug="imara-tech")
        self.user = User.objects.create_user(username="owner", email="owner@imara.example", password="password")
        self.phone = "+254712345678"

        # Active phone identity bound to tenant
        self.pi = PhoneIdentity.objects.create(
            tenant=self.tenant,
            phone_number=self.phone,
            role='OWNER',
            status='ACTIVE'
        )

    def test_dispatch_today(self):
        # Create a succeeded payment request to check total
        pr = PaymentRequest.objects.create(
            tenant=self.tenant,
            amount_minor=3000,
            currency="KES",
            reference="TX-1",
            status="SUCCEEDED",
            expires_at=timezone.now() + datetime.timedelta(hours=1)
        )
        # Create transaction
        Transaction.objects.create(
            tenant=self.tenant,
            payment_request=pr,
            amount_minor=3000,
            currency="KES",
            mpesa_receipt_number="QE123456",
            customer_phone="254711223344"
        )

        parsed = parse_command("today")
        reply = dispatch(self.pi, parsed)
        body = reply.get('text', {}).get('body', '')
        self.assertIn("Total Collected Today: KES 3,000", body)

    def test_dispatch_request_below_threshold(self):
        # Threshold is KES 1,000. Let's request 500 (below threshold)
        parsed = parse_command("request 500 for INV-500")
        reply = dispatch(self.pi, parsed)

        body = reply.get('text', {}).get('body', '')
        self.assertIn("Payment Request Created", body)
        self.assertIn("INV-500", body)

        # Check DB
        pr = PaymentRequest.objects.get(reference="INV-500", tenant=self.tenant)
        self.assertEqual(pr.amount_minor, 500)
        self.assertEqual(pr.status, 'CREATED')

    def test_dispatch_request_above_threshold_requires_confirmation(self):
        # Request 2500 (above default threshold of KES 1,000)
        parsed = parse_command("request 2500 for INV-2500")
        reply = dispatch(self.pi, parsed)

        # Should prompt with interactive buttons
        self.assertEqual(reply.get('type'), 'interactive')
        interactive = reply.get('interactive', {})
        self.assertEqual(interactive.get('type'), 'button')
        self.assertIn("Confirm Payment Request", interactive.get('header', {}).get('text', ''))

        # Session flow should be set to CREATE_REQUEST
        session = get_session(self.pi)
        self.assertEqual(session.flow, 'CREATE_REQUEST')
        self.assertEqual(session.state.get('amount'), 2500)
        self.assertEqual(session.state.get('reference'), 'INV-2500')

        # Now send "confirm" to activate it
        confirm_parsed = parse_command("confirm")
        reply2 = dispatch(self.pi, confirm_parsed)

        body = reply2.get('text', {}).get('body', '')
        self.assertIn("Payment Request Created", body)
        self.assertIn("INV-2500", body)

        # Session should be cleared
        session.refresh_from_db()
        self.assertEqual(session.flow, 'NONE')

        # Check DB
        pr = PaymentRequest.objects.get(reference="INV-2500", tenant=self.tenant)
        self.assertEqual(pr.amount_minor, 2500)
        self.assertEqual(pr.status, 'CREATED')

    def test_whatsapp_wamid_deduplication(self):
        # Ingest a WhatsApp event
        wamid = "wamid.test_dedup_123"
        event = InboundWhatsAppEvent.objects.create(
            wamid=wamid,
            from_number=self.phone,
            payload={
                "message": {
                    "id": wamid,
                    "type": "text",
                    "text": {"body": "today"}
                }
            }
        )

        # Run process_whatsapp_message task first time
        process_whatsapp_message(str(event.id))
        self.assertTrue(ProcessedWhatsAppMessage.objects.filter(wamid=wamid).exists())

        # Reset count of total processed messages
        first_count = ProcessedWhatsAppMessage.objects.filter(wamid=wamid).count()
        self.assertEqual(first_count, 1)

        # Running process again with the same event (or duplicate event with same wamid) should be a no-op
        process_whatsapp_message(str(event.id))
        self.assertEqual(ProcessedWhatsAppMessage.objects.filter(wamid=wamid).count(), 1)
