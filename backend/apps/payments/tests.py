from django.test import TestCase
from django.utils import timezone
import datetime
from apps.tenants.models import Tenant
from apps.merchants.models import MerchantProfile
from apps.payments.models import PaymentRequest, PaymentAttempt, Transaction
from apps.providers.mpesa_sandbox import MPesaSandboxAdapter
from apps.webhooks.models import WebhookEvent

class PaymentStateMachineTest(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Merchant A Tech", slug="merchant-a")
        self.tenant_b = Tenant.objects.create(name="Merchant B Foods", slug="merchant-b")

        self.expires = timezone.now() + datetime.timedelta(hours=1)
        self.req_a = PaymentRequest.objects.create(
            tenant=self.tenant_a,
            amount_minor=2500,
            currency="KES",
            reference="INV-001",
            expires_at=self.expires
        )

    def test_payment_creation(self):
        self.assertEqual(self.req_a.status, 'CREATED')
        self.assertIsNotNone(self.req_a.public_token)
        self.assertEqual(self.req_a.amount_minor, 2500)

    def test_payment_stk_initiation_and_success_flow(self):
        attempt = PaymentAttempt.objects.create(
            payment_request=self.req_a,
            tenant=self.tenant_a,
            customer_phone="254712345678"
        )
        adapter = MPesaSandboxAdapter()
        init_res = adapter.initiate_payment(attempt)

        self.assertTrue(init_res['success'])
        self.assertEqual(attempt.status, 'PENDING')
        self.req_a.refresh_from_db()
        self.assertEqual(self.req_a.status, 'PENDING')

        # Process successful STK push callback
        cb_res = adapter.process_callback(
            checkout_request_id=attempt.external_reference,
            result_code=0,
            result_desc="Success"
        )

        self.assertTrue(cb_res['success'])
        self.assertEqual(cb_res['status'], 'SUCCEEDED')
        self.req_a.refresh_from_db()
        self.assertEqual(self.req_a.status, 'SUCCEEDED')
        self.assertIsNotNone(self.req_a.paid_at)

        # Check Transaction created
        tx = Transaction.objects.filter(payment_request=self.req_a).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount_minor, 2500)
        self.assertEqual(tx.tenant, self.tenant_a)

    def test_tenant_isolation(self):
        req_b = PaymentRequest.objects.create(
            tenant=self.tenant_b,
            amount_minor=5000,
            currency="KES",
            reference="INV-002",
            expires_at=self.expires
        )

        a_requests = PaymentRequest.objects.filter(tenant=self.tenant_a)
        b_requests = PaymentRequest.objects.filter(tenant=self.tenant_b)

        self.assertIn(self.req_a, a_requests)
        self.assertNotIn(req_b, a_requests)
        self.assertIn(req_b, b_requests)
        self.assertNotIn(self.req_a, b_requests)

    def test_webhook_idempotency(self):
        attempt = PaymentAttempt.objects.create(
            payment_request=self.req_a,
            tenant=self.tenant_a,
            customer_phone="254712345678"
        )
        adapter = MPesaSandboxAdapter()
        adapter.initiate_payment(attempt)

        # First callback
        cb_1 = adapter.process_callback(
            checkout_request_id=attempt.external_reference,
            result_code=0,
            result_desc="Success"
        )
        self.assertEqual(cb_1['status'], 'SUCCEEDED')

        # Duplicate callback with same event ID
        cb_2 = adapter.process_callback(
            checkout_request_id=attempt.external_reference,
            result_code=0,
            result_desc="Success"
        )
        self.assertTrue(cb_2['already_processed'])

        # Confirm only 1 transaction exists
        tx_count = Transaction.objects.filter(payment_request=self.req_a).count()
        self.assertEqual(tx_count, 1)
