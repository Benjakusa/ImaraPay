"""
conversation/session.py
=======================
Session management for multi-turn guided flows (§6.13).
"""
import datetime
import logging
from django.utils import timezone
from apps.identity.models import PhoneIdentity
from apps.conversation.models import ConversationSession

logger = logging.getLogger(__name__)

SESSION_EXPIRY_MINUTES = 10


def get_session(phone_identity: PhoneIdentity) -> ConversationSession:
    """
    Get or create a ConversationSession for a PhoneIdentity.
    If the existing session is expired, reset it to NONE before returning.
    """
    session, _ = ConversationSession.objects.get_or_create(
        phone_identity=phone_identity,
        defaults={
            'flow': 'NONE',
            'state': {},
            'expires_at': _expiry(),
        }
    )
    if session.is_expired() and session.flow != 'NONE':
        logger.info(f"Session expired for {phone_identity.phone_number}, resetting.")
        session.flow = 'NONE'
        session.state = {}
        session.expires_at = _expiry()
        session.save()
    return session


def set_session_flow(phone_identity: PhoneIdentity, flow: str, state: dict) -> ConversationSession:
    """Update the session flow and state, resetting the expiry window."""
    session = get_session(phone_identity)
    session.flow = flow
    session.state = state
    session.expires_at = _expiry()
    session.save()
    return session


def clear_session(phone_identity: PhoneIdentity) -> ConversationSession:
    """Reset a session to the NONE/idle state."""
    session = get_session(phone_identity)
    session.reset()
    return session


def _expiry():
    return timezone.now() + datetime.timedelta(minutes=SESSION_EXPIRY_MINUTES)
