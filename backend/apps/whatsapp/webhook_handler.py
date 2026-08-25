"""
whatsapp/webhook_handler.py
===========================
Main inbound webhook dispatcher (§11.3).
1. Verifies Meta signature
2. Durably stores the raw event before any processing
3. Returns 200 immediately
4. Queues Celery task for async processing
"""
import logging
from apps.whatsapp.models import InboundWhatsAppEvent

logger = logging.getLogger(__name__)


def handle_inbound_webhook(raw_body: bytes, signature_header: str, payload: dict) -> dict:
    """
    Entry point called from the Django view.
    Verifies signature, persists event, queues processing.
    Returns {'ok': True} on success.
    Raises ValueError on signature failure.
    """
    from apps.whatsapp.adapter import WhatsAppBusinessAdapter

    adapter = WhatsAppBusinessAdapter()

    # ── 1. Verify signature before any parsing ─────────────────────────────────
    if not adapter.verify_webhook_signature(raw_body, signature_header):
        logger.warning("WhatsApp webhook signature verification FAILED.")
        raise ValueError("Invalid webhook signature.")

    # ── 2. Extract messages from Meta's nested payload ─────────────────────────
    messages = _extract_messages(payload)
    if not messages:
        # Could be a status update or other non-message event — acknowledge silently
        return {'ok': True, 'events': 0}

    processed = 0
    for msg_data in messages:
        wamid = msg_data.get('wamid')
        from_number = msg_data.get('from_number')

        if not wamid or not from_number:
            logger.warning(f"Skipping malformed message entry: {msg_data}")
            continue

        # ── 3. Durably store before processing (§11.3 step 3) ─────────────────
        if InboundWhatsAppEvent.objects.filter(wamid=wamid).exists():
            logger.info(f"Duplicate wamid {wamid} at ingestion — skipping.")
            continue

        event = InboundWhatsAppEvent.objects.create(
            wamid=wamid,
            from_number=from_number,
            payload=msg_data,
        )

        # ── 4. Queue async processing ──────────────────────────────────────────
        _queue_processing(str(event.id))
        processed += 1

    return {'ok': True, 'events': processed}


def _extract_messages(payload: dict) -> list:
    """
    Extract individual message entries from Meta's nested webhook payload.
    Returns a list of flat dicts: {wamid, from_number, type, message, ...}
    """
    results = []
    try:
        entries = payload.get('entry', [])
        for entry in entries:
            for change in entry.get('changes', []):
                value = change.get('value', {})
                messages = value.get('messages', [])
                for msg in messages:
                    results.append({
                        'wamid': msg.get('id'),
                        'from_number': _normalise_phone(msg.get('from', '')),
                        'type': msg.get('type', 'text'),
                        'message': msg,
                        'metadata': value.get('metadata', {}),
                        'raw_entry': entry,
                    })
    except Exception as e:
        logger.error(f"Error extracting messages from webhook payload: {e}")
    return results


def _normalise_phone(phone: str) -> str:
    """Normalise to E.164 with leading +."""
    p = phone.strip().replace(' ', '').replace('-', '').replace('+', '')
    if p.startswith('0') and len(p) == 10:
        p = '254' + p[1:]
    return '+' + p if not p.startswith('+') else p


def _queue_processing(event_id: str):
    """
    Queue the Celery task for async processing.
    In dev (no Redis), CELERY_TASK_ALWAYS_EAGER=True makes .delay() run inline.
    In production (Redis configured), runs truly async via worker.
    """
    try:
        from apps.conversation.tasks import process_whatsapp_message
        process_whatsapp_message.delay(event_id)
    except Exception as e:
        logger.error(f"Failed to queue processing for event {event_id}: {e}")
