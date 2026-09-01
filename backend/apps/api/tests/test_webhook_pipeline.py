"""
apps/api/tests/test_webhook_pipeline.py
========================================
Proper Django TestCase port of e2e_pipeline_test.py.
Uses RequestFactory — no live server, no manual DB setup needed.
Run with: python manage.py test apps.api.tests --verbosity=2
"""
import json
import uuid
import time

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.identity.models import PhoneIdentity
from apps.whatsapp.models import InboundWhatsAppEvent
from apps.conversation.models import ProcessedWhatsAppMessage
from apps.api.whatsapp_views import WhatsAppWebhookView

User = get_user_model()

PHONE = '+254799000001'


def _build_whatsapp_payload(from_phone: str, body: str, wamid: str) -> dict:
    """Build a minimal WhatsApp Cloud API inbound message payload."""
    return {
        'object': 'whatsapp_business_account',
        'entry': [{
            'id': 'test-waba',
            'changes': [{
                'value': {
                    'messaging_product': 'whatsapp',
                    'metadata': {
                        'display_phone_number': from_phone,
                        'phone_number_id': 'sim',
                    },
                    'messages': [{
                        'from': from_phone.lstrip('+'),
                        'id': wamid,
                        'timestamp': str(int(time.time())),
                        'text': {'body': body},
                        'type': 'text',
                    }],
                },
                'field': 'messages',
            }],
        }],
    }


class WhatsAppWebhookPipelineTest(TestCase):
    """
    Integration tests for the WhatsApp inbound webhook pipeline.
    Exercises the full stack from HTTP request → storage → task
    (sync via CELERY_TASK_ALWAYS_EAGER=True in test settings).
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.tenant = Tenant.objects.create(name='Pipeline Test Tenant', slug='pipeline-test')
        self.user = User.objects.create_user(
            username='pipeline_owner',
            email='owner@pipeline.example',
            password='test-pass',
        )
        # Active PhoneIdentity so commands are processed
        self.pi = PhoneIdentity.objects.create(
            tenant=self.tenant,
            phone_number=PHONE,
            role='OWNER',
            status='ACTIVE',
        )

    def _post_webhook(self, command: str):
        """Send a simulated WhatsApp message through the webhook view."""
        wamid = f'wamid.test_{uuid.uuid4().hex[:12]}'
        payload = _build_whatsapp_payload(PHONE, command, wamid)
        body = json.dumps(payload).encode()
        request = self.factory.post(
            '/api/v1/whatsapp/webhook/',
            data=body,
            content_type='application/json',
        )
        view = WhatsAppWebhookView.as_view()
        response = view(request)
        return response, wamid

    def test_webhook_returns_200(self):
        response, _ = self._post_webhook('help')
        self.assertEqual(response.status_code, 200)

    def test_webhook_creates_inbound_event(self):
        response, wamid = self._post_webhook('today')
        event = InboundWhatsAppEvent.objects.filter(wamid=wamid).first()
        self.assertIsNotNone(event, 'InboundWhatsAppEvent should be created for every inbound message')

    def test_webhook_creates_processed_message(self):
        """With CELERY_TASK_ALWAYS_EAGER=True tasks run synchronously, so ProcessedWhatsAppMessage exists."""
        response, wamid = self._post_webhook('help')
        processed = ProcessedWhatsAppMessage.objects.filter(wamid=wamid).first()
        self.assertIsNotNone(processed, 'ProcessedWhatsAppMessage should be created after processing')

    def test_webhook_idempotency(self):
        """Sending the same wamid twice must NOT create two ProcessedWhatsAppMessage records."""
        _, wamid = self._post_webhook('today')

        # Re-post same wamid (duplicate delivery)
        payload = _build_whatsapp_payload(PHONE, 'today', wamid)
        body = json.dumps(payload).encode()
        request = self.factory.post(
            '/api/v1/whatsapp/webhook/',
            data=body,
            content_type='application/json',
        )
        WhatsAppWebhookView.as_view()(request)

        count = ProcessedWhatsAppMessage.objects.filter(wamid=wamid).count()
        self.assertLessEqual(count, 1, 'Duplicate wamid must not produce multiple ProcessedWhatsAppMessage records')

    def test_webhook_non_json_body_returns_200(self):
        """Meta must always receive 200 — even for malformed bodies."""
        request = self.factory.post(
            '/api/v1/whatsapp/webhook/',
            data=b'not-json',
            content_type='application/json',
        )
        self.assertEqual(WhatsAppWebhookView.as_view()(request).status_code, 200)

    def test_verification_challenge_valid_token(self):
        """GET with correct verify_token returns the hub.challenge value."""
        request = self.factory.get(
            '/api/v1/whatsapp/webhook/',
            {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'imara-dev-verify',
                'hub.challenge': 'abc123',
            },
        )
        response = WhatsAppWebhookView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'abc123', response.content)

    def test_verification_challenge_invalid_token(self):
        """GET with wrong verify_token returns 403."""
        request = self.factory.get(
            '/api/v1/whatsapp/webhook/',
            {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'wrong-token',
                'hub.challenge': 'abc123',
            },
        )
        self.assertEqual(WhatsAppWebhookView.as_view()(request).status_code, 403)
