"""
api/whatsapp_views.py
=====================
Django view for the WhatsApp Cloud API webhook (§14.1, §11.3).
GET  — Meta verification challenge (must respond with hub.challenge)
POST — Primary merchant entrypoint. Responds 200 immediately;
       all processing is async via Celery so Meta never times out.
"""
import logging
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from apps.whatsapp.webhook_handler import handle_inbound_webhook
from apps.whatsapp.adapter import WhatsAppBusinessAdapter

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    """
    The primary inbound endpoint for WhatsApp Cloud API messages.
    Must always return 200 to Meta — even on errors — to prevent infinite retries.
    CSRF is exempt because Meta POSTs raw JSON with no Django CSRF token.
    Security is provided by X-Hub-Signature-256 verification instead.
    """

    def get(self, request):
        """Meta webhook verification challenge."""
        mode = request.GET.get('hub.mode', '')
        token = request.GET.get('hub.verify_token', '')
        challenge = request.GET.get('hub.challenge', '')

        adapter = WhatsAppBusinessAdapter()
        if adapter.verify_challenge_token(mode, token):
            logger.info("WhatsApp webhook verification successful.")
            return HttpResponse(challenge, content_type='text/plain', status=200)

        logger.warning(f"WhatsApp webhook verification failed. mode={mode!r}, token={token!r}")
        return HttpResponse('Verification failed', status=403)

    def post(self, request):
        """
        Receive inbound WhatsApp messages.
        Verifies signature, stores event durably, queues Celery task.
        ALWAYS returns 200 so Meta doesn't retry indefinitely (§11.3).
        """
        import json

        raw_body = request.body
        signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            logger.warning("WhatsApp webhook received non-JSON body.")
            return HttpResponse(status=200)  # still return 200

        try:
            result = handle_inbound_webhook(raw_body, signature, payload)
            logger.info(f"Webhook processed: {result}")
        except ValueError as e:
            # Signature failure — log but still return 200 (avoid Meta retries leaking info)
            logger.error(f"WhatsApp webhook signature error: {e}")

        return HttpResponse(status=200)
