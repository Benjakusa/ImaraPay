"""
whatsapp/adapter.py
===================
WhatsApp Business Cloud API adapter (§11).
Handles:
  - Webhook signature verification (X-Hub-Signature-256)
  - Sending plain text, interactive button, interactive list, CTA URL messages
  - Session-window-aware message dispatch (template vs free-form)
  - Simulation mode when credentials are absent (same pattern as M-Pesa sandbox)
"""
import hashlib
import hmac
import json
import logging
import requests
from django.conf import settings
from apps.audit.services import log_action

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


def _get_config():
    """Return WhatsApp Cloud API config from settings, with safe defaults."""
    cfg = getattr(settings, 'IMARA_PAY', {})
    return {
        'phone_number_id': cfg.get('WHATSAPP_PHONE_NUMBER_ID', ''),
        'access_token': cfg.get('WHATSAPP_ACCESS_TOKEN', ''),
        'verify_token': cfg.get('WHATSAPP_VERIFY_TOKEN', 'imara-dev-verify'),
        'app_secret': cfg.get('WHATSAPP_APP_SECRET', ''),
        'simulation_mode': not cfg.get('WHATSAPP_ACCESS_TOKEN'),
    }


class WhatsAppBusinessAdapter:
    """
    Official Meta WhatsApp Business Cloud API adapter.
    Falls back to simulation mode when credentials are not configured.
    """

    def __init__(self):
        self._cfg = _get_config()
        self._sim = self._cfg['simulation_mode']
        if self._sim:
            logger.info("WhatsApp adapter running in SIMULATION mode (no credentials set).")

    # ─── Webhook Verification ─────────────────────────────────────────────────

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verify X-Hub-Signature-256 from Meta (§11.3).
        Returns True if valid. Always returns True in simulation mode (dev only).
        """
        if self._sim:
            return True

        app_secret = self._cfg['app_secret']
        if not app_secret or not signature_header:
            logger.warning("WhatsApp signature verification skipped — no app secret configured.")
            return False

        expected = "sha256=" + hmac.new(
            app_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)

    def verify_challenge_token(self, mode: str, token: str) -> bool:
        """Verify the hub.verify_token in Meta's webhook challenge."""
        return mode == 'subscribe' and token == self._cfg['verify_token']

    # ─── Message Sending ──────────────────────────────────────────────────────

    def send_raw_message(self, to: str, message_payload: dict, tenant=None) -> dict:
        """
        Send any WhatsApp message payload to a recipient.
        Selects template vs free-form based on session window (§11.2).
        In simulation mode, logs the message instead of calling the API.
        """
        to_clean = to.lstrip('+')  # Meta expects E.164 without leading +

        payload = {
            "messaging_product": "whatsapp",
            "to": to_clean,
            **message_payload,
        }

        # Resolve credentials dynamically if tenant is provided
        phone_number_id = self._cfg['phone_number_id']
        access_token = self._cfg['access_token']
        sim_mode = self._sim

        if tenant:
            from apps.merchants.models import WhatsAppAccount
            wa = WhatsAppAccount.objects.filter(tenant=tenant).first()
            if wa and wa.access_token and wa.phone_number_id:
                phone_number_id = wa.phone_number_id
                access_token = wa.access_token
                sim_mode = False

        if sim_mode:
            logger.info(f"[SIM] WhatsApp → {to}: {json.dumps(message_payload, ensure_ascii=False)[:200]}")
            return {'success': True, 'simulated': True, 'to': to, 'payload': message_payload}

        return self._call_send_api_direct(payload, phone_number_id, access_token)

    def _call_send_api_direct(self, payload: dict, phone_number_id: str, access_token: str) -> dict:
        url = f"{GRAPH_API_BASE}/{phone_number_id}/messages"

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    'Authorization': f"Bearer {access_token}",
                    'Content-Type': 'application/json',
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"WhatsApp send OK: {data.get('messages', [{}])[0].get('id', '?')}")
            return {'success': True, 'response': data}
        except requests.RequestException as e:
            logger.error(f"WhatsApp send error: {e}")
            return {'success': False, 'error': str(e)}

    def _call_send_api(self, payload: dict, tenant=None) -> dict:
        phone_number_id = self._cfg['phone_number_id']
        access_token = self._cfg['access_token']

        if tenant:
            from apps.merchants.models import WhatsAppAccount
            wa = WhatsAppAccount.objects.filter(tenant=tenant).first()
            if wa and wa.access_token and wa.phone_number_id:
                phone_number_id = wa.phone_number_id
                access_token = wa.access_token

        return self._call_send_api_direct(payload, phone_number_id, access_token)

    # ─── High-level helpers (kept from v2 for compatibility) ──────────────────

    def send_payment_link(self, payment_request, customer_phone=None, tenant=None):
        """Send a checkout link to a customer (or merchant)."""
        from apps.conversation.reply_composer import payment_link_reply_text
        phone = customer_phone or payment_request.customer_phone
        if not phone:
            return {'success': False, 'error': 'No phone number'}
        msg = payment_link_reply_text(payment_request)
        result = self.send_raw_message(phone, msg, tenant=tenant)

        log_action(
            'WHATSAPP_SEND_PAYMENT_LINK',
            tenant=payment_request.tenant,
            details={
                'payment_request_id': str(payment_request.id),
                'recipient_phone': phone,
            }
        )
        return result

    def send_payment_receipt_notification(self, payment_request, mpesa_receipt: str):
        """Notify merchant(s) of a successful payment (§10.2)."""
        from apps.conversation.reply_composer import payment_confirmed_notification
        from apps.identity.models import PhoneIdentity

        msg = payment_confirmed_notification(payment_request, mpesa_receipt)

        # Send to all active OWNER/ADMIN phone identities for this tenant
        recipients = PhoneIdentity.objects.filter(
            tenant=payment_request.tenant,
            status='ACTIVE',
            role__in=['OWNER', 'ADMIN'],
        )
        results = []
        for pi in recipients:
            results.append(self.send_raw_message(pi.phone_number, msg))

        log_action(
            'WHATSAPP_SEND_RECEIPT',
            tenant=payment_request.tenant,
            details={
                'payment_request_id': str(payment_request.id),
                'mpesa_receipt': mpesa_receipt,
                'recipients': [pi.phone_number for pi in recipients],
            }
        )
        return results or [{'success': True, 'simulated': True}]

    def handle_incoming_merchant_command(self, tenant, raw_text: str) -> dict:
        """
        Legacy simulation-mode entry point (used by the web WhatsApp simulator UI).
        Now delegates to the conversation engine for consistent behaviour.
        """
        from apps.conversation.parser import parse_command
        from apps.conversation.handlers import dispatch
        from apps.identity.models import PhoneIdentity

        # For simulation, use the first active OWNER PhoneIdentity or a fake one
        pi = PhoneIdentity.objects.filter(
            tenant=tenant, status='ACTIVE', role='OWNER'
        ).first()

        if not pi:
            # Simulation mode: create an ephemeral fake identity object (not saved)
            class FakePI:
                phone_number = '+254700000000'
                role = 'OWNER'
                status = 'ACTIVE'
                tenant_id = tenant.id
                id = 'sim'
                def __init__(self, t):
                    self.tenant = t
            pi = FakePI(tenant)

        parsed = parse_command(raw_text)
        reply_payload = dispatch(pi, parsed)

        # Return in the legacy format the UI expects
        return {
            'success': True,
            'reply': reply_payload.get('text', {}).get('body', '') or
                     reply_payload.get('interactive', {}).get('body', {}).get('text', 'Done.'),
            'payload': reply_payload,
        }
