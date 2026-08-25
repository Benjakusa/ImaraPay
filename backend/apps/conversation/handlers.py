"""
conversation/handlers.py
========================
Per-command handlers. Each handler:
  1. Calls into the payments internal service layer (never PSP/provider directly)
  2. Returns a reply payload dict (from reply_composer)
  3. May update ConversationSession state for multi-turn flows

Security contract (§7.2/§7.3):
  - Read-only and low-blast-radius creation: no step-up needed
  - PENDING→CANCELLED (in-flight) and any sensitive mutation: step-up required
"""
import logging
import secrets
import datetime
from django.conf import settings
from django.utils import timezone

from apps.conversation.parser import (
    ParsedCommand, COMMAND_REQUEST, COMMAND_TODAY, COMMAND_STATUS,
    COMMAND_LAST, COMMAND_CANCEL, COMMAND_HELP, COMMAND_UNKNOWN,
    COMMAND_CONFIRM, COMMAND_EDIT,
)
from apps.conversation import reply_composer as rc
from apps.conversation.session import get_session, set_session_flow, clear_session
from apps.identity.models import PhoneIdentity

logger = logging.getLogger(__name__)

# Confirmation threshold: amounts at or above this require an interactive confirm step (§8.2)
CONFIRMATION_THRESHOLD = getattr(settings, 'IMARA_PAY', {}).get(
    'CONFIRMATION_THRESHOLD_MINOR', 1000
)


def dispatch(phone_identity: PhoneIdentity, parsed: ParsedCommand) -> dict:
    """
    Main dispatch — routes a ParsedCommand to the appropriate handler.
    Returns a WhatsApp message payload dict ready to send.
    """
    session = get_session(phone_identity)

    # ── Handle interactive confirm/edit in the context of an active session ──
    if parsed.command == COMMAND_CONFIRM and session.flow == 'CREATE_REQUEST':
        return _handle_confirm_create(phone_identity, session)
    if parsed.command == COMMAND_EDIT and session.flow == 'CREATE_REQUEST':
        clear_session(phone_identity)
        return rc.text_reply(
            "✏️ Cancelled. Send a new request:\n`request 2500 for INV-1002`"
        )

    # ── Primary commands ──────────────────────────────────────────────────────
    if parsed.command == COMMAND_REQUEST:
        return _handle_request(phone_identity, parsed, session)
    if parsed.command == COMMAND_TODAY:
        return _handle_today(phone_identity)
    if parsed.command == COMMAND_STATUS:
        return _handle_status(phone_identity, parsed)
    if parsed.command == COMMAND_LAST:
        return _handle_last(phone_identity, parsed)
    if parsed.command == COMMAND_CANCEL:
        return _handle_cancel(phone_identity, parsed)
    if parsed.command == COMMAND_HELP:
        return rc.help_menu()

    # ── Unknown ───────────────────────────────────────────────────────────────
    return rc.unknown_command_reply(parsed.raw)


# ─── Command handlers ─────────────────────────────────────────────────────────

def _handle_request(phone_identity: PhoneIdentity, parsed: ParsedCommand, session) -> dict:
    """
    Create a payment request — or, if above the threshold and no reference provided,
    ask for confirmation first via interactive buttons (§8.2).
    """
    amount = parsed.amount
    reference = parsed.reference or _auto_reference()
    description = parsed.description or ''

    # Prompt for confirmation above the threshold
    if amount >= CONFIRMATION_THRESHOLD:
        # Store pending state in session and ask for confirm/edit
        set_session_flow(phone_identity, 'CREATE_REQUEST', {
            'amount': amount,
            'reference': reference,
            'description': description,
        })
        return rc.confirm_create_request_prompt(amount, reference)

    # Below threshold — create immediately
    return _do_create_request(phone_identity, amount, reference, description)


def _handle_confirm_create(phone_identity: PhoneIdentity, session) -> dict:
    """Called when merchant taps 'Confirm' on the create-request prompt."""
    state = session.state
    amount = state.get('amount')
    reference = state.get('reference', _auto_reference())
    description = state.get('description', '')

    if not amount:
        clear_session(phone_identity)
        return rc.text_reply("⚠️ Session expired. Please send a new request command.")

    clear_session(phone_identity)
    return _do_create_request(phone_identity, amount, reference, description)


def _do_create_request(phone_identity: PhoneIdentity, amount: int, reference: str, description: str) -> dict:
    from apps.payments.services import create_payment_request
    try:
        pr = create_payment_request(
            tenant=phone_identity.tenant,
            amount_minor=amount,
            reference=reference,
            description=description,
            initiated_by_phone_identity=phone_identity,
        )
        return rc.payment_link_reply_text(pr)
    except ValueError as e:
        return rc.text_reply(f"⚠️ Could not create request: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error creating payment request: {e}")
        return rc.text_reply("⚠️ Something went wrong. Please try again in a moment.")


def _handle_today(phone_identity: PhoneIdentity) -> dict:
    from apps.payments.services import get_today_summary
    summary = get_today_summary(phone_identity.tenant)
    return rc.today_summary_reply(summary)


def _handle_status(phone_identity: PhoneIdentity, parsed: ParsedCommand) -> dict:
    from apps.payments.services import get_request_by_reference
    pr = get_request_by_reference(phone_identity.tenant, parsed.reference)
    if not pr:
        return rc.text_reply(
            f"🔍 No payment request found for reference `{parsed.reference}`.\n\n"
            f"Double-check the reference or use `last 5` to see recent requests."
        )
    return rc.status_reply(pr)


def _handle_last(phone_identity: PhoneIdentity, parsed: ParsedCommand) -> dict:
    from apps.payments.services import get_recent_transactions
    n = parsed.n or 5
    txs = get_recent_transactions(phone_identity.tenant, n)
    return rc.recent_transactions_reply(txs)


def _handle_cancel(phone_identity: PhoneIdentity, parsed: ParsedCommand) -> dict:
    """
    Cancel a payment request.
    - CREATED (not yet attempted) → cancel directly, no step-up (§7.2)
    - PENDING (in-flight attempt) → requires step-up (§7.2, §7.4)
    """
    from apps.payments.services import get_request_by_reference, cancel_payment_request
    from apps.identity.services import issue_step_up_challenge

    pr = get_request_by_reference(phone_identity.tenant, parsed.reference)
    if not pr:
        return rc.text_reply(
            f"🔍 No open payment request found for `{parsed.reference}`.\n\n"
            f"It may have already been completed or cancelled."
        )

    if pr.status in ('SUCCEEDED', 'CANCELLED', 'EXPIRED'):
        return rc.text_reply(
            f"That request ({parsed.reference}) is already *{pr.status}* and cannot be cancelled."
        )

    if pr.status == 'PENDING':
        # In-flight — requires step-up
        challenge, raw_token = issue_step_up_challenge(
            phone_identity=phone_identity,
            action_type='CANCEL_INFLIGHT',
            action_payload={'payment_request_id': str(pr.id), 'reference': pr.reference},
        )
        return rc.step_up_prompt(challenge, raw_token)

    # CREATED — cancel directly
    try:
        pr = cancel_payment_request(
            tenant=phone_identity.tenant,
            payment_request_id=str(pr.id),
            initiated_by_phone_identity=phone_identity,
        )
        return rc.cancel_success_reply(pr)
    except ValueError as e:
        return rc.text_reply(f"⚠️ Could not cancel: {e}")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _auto_reference() -> str:
    """Generate an auto-reference when the merchant doesn't provide one."""
    return f"WA-{secrets.token_hex(3).upper()}"
