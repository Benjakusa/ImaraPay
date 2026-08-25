"""
conversation/tasks.py
=====================
Celery tasks for conversation engine.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='conversation.process_whatsapp_message', bind=True, max_retries=3)
def process_whatsapp_message(self, inbound_event_id: str):
    """
    The central async task for processing an inbound WhatsApp message (§17).
    Delegates to _process_whatsapp_message_sync for the actual logic.
    """
    try:
        _process_whatsapp_message_sync(inbound_event_id)
    except Exception as exc:
        logger.exception(f"Error processing WhatsApp message event {inbound_event_id}: {exc}")
        raise self.retry(exc=exc, countdown=10)


def _process_whatsapp_message_sync(inbound_event_id: str):
    """
    Core processing logic — plain function (no Celery dependency).
    Called by the Celery task AND by the thread-based sync fallback.
    Resolves PhoneIdentity → parses command → dispatches handler → sends reply.
    Safe to run twice with the same input (wamid dedup ensures idempotency).
    """
    from apps.whatsapp.models import InboundWhatsAppEvent
    from apps.conversation.models import ProcessedWhatsAppMessage
    from apps.conversation.parser import parse_command, parse_interactive_reply
    from apps.conversation.handlers import dispatch
    from apps.identity.models import PhoneIdentity
    from apps.conversation.reply_composer import unrecognized_sender_reply
    from apps.whatsapp.adapter import WhatsAppBusinessAdapter

    try:
        event = InboundWhatsAppEvent.objects.get(id=inbound_event_id)
    except InboundWhatsAppEvent.DoesNotExist:
        logger.error(f"InboundWhatsAppEvent {inbound_event_id} not found.")
        return

    wamid = event.wamid
    phone_number = event.from_number

    # ── wamid idempotency check (§15.1) ──────────────────────────────────────
    if ProcessedWhatsAppMessage.objects.filter(wamid=wamid).exists():
        logger.info(f"Duplicate wamid {wamid} — skipping.")
        return

    # Mark as processed BEFORE doing work — prevents duplicate on crash-restart
    ProcessedWhatsAppMessage.objects.create(wamid=wamid, phone_number=phone_number)

    # ── Resolve PhoneIdentity ─────────────────────────────────────────────────
    phone_identity = PhoneIdentity.resolve(phone_number)
    if not phone_identity:
        logger.info(f"Unrecognized sender {phone_number} — sending onboarding reply.")
        wa = WhatsAppBusinessAdapter()
        wa.send_raw_message(phone_number, unrecognized_sender_reply())
        event.mark_processed()
        return

    # ── Parse the message ─────────────────────────────────────────────────────
    payload = event.payload
    message = payload.get('message', {})
    msg_type = message.get('type', 'text')

    if msg_type == 'text':
        raw_text = message.get('text', {}).get('body', '')
        parsed = parse_command(raw_text)
    elif msg_type == 'interactive':
        parsed = parse_interactive_reply(message.get('interactive', {}))
    else:
        from apps.conversation.reply_composer import unknown_command_reply
        parsed_text = f"[{msg_type} message]"
        parsed = type('PC', (), {'command': 'unknown', 'raw': parsed_text})()

    # ── Dispatch to handler ────────────────────────────────────────────────────
    reply_payload = dispatch(phone_identity, parsed)

    # ── Send reply ────────────────────────────────────────────────────────────
    wa = WhatsAppBusinessAdapter()
    wa.send_raw_message(phone_number, reply_payload)

    event.mark_processed()


@shared_task(name='conversation.expire_sessions')
def expire_conversation_sessions():
    """Expire stale multi-turn sessions (§17 beat task)."""
    from apps.conversation.models import ConversationSession
    stale = ConversationSession.objects.filter(
        expires_at__lt=timezone.now()
    ).exclude(flow='NONE')
    count = stale.update(flow='NONE', state={})
    if count:
        logger.info(f"Expired {count} conversation session(s).")
    return count


@shared_task(name='conversation.send_merchant_notification')
def send_merchant_notification(tenant_id: str, message_payload: dict):
    """
    Send a proactive WhatsApp notification to all active OWNER/ADMIN phone identities
    of a tenant (e.g. payment confirmed). Uses template messaging when session window
    is not open (§11.2).
    """
    from apps.identity.models import PhoneIdentity
    from apps.whatsapp.adapter import WhatsAppBusinessAdapter
    from apps.tenants.models import Tenant

    try:
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        logger.error(f"Tenant {tenant_id} not found for notification.")
        return

    recipients = PhoneIdentity.objects.filter(
        tenant=tenant,
        status='ACTIVE',
        role__in=['OWNER', 'ADMIN'],
    )
    wa = WhatsAppBusinessAdapter()
    for pi in recipients:
        wa.send_raw_message(pi.phone_number, message_payload)
