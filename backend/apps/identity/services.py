"""
identity/services.py
====================
Internal service layer for all identity-related operations.
Both WhatsApp and web surfaces call these functions — never the models directly
from views without going through here.
"""
import secrets
import datetime
import logging
from django.utils import timezone
from django.conf import settings

from apps.tenants.models import Tenant
from apps.identity.models import PhoneIdentity, StepUpChallenge, MagicLinkToken
from apps.identity.otp import generate_otp, hash_otp
from apps.audit.services import log_action

logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
STEP_UP_EXPIRY_MINUTES = getattr(settings, 'STEP_UP_EXPIRY_MINUTES', 5)
MAGIC_LINK_EXPIRY_HOURS = getattr(settings, 'MAGIC_LINK_EXPIRY_HOURS', 24)
REPORT_LINK_EXPIRY_HOURS = getattr(settings, 'REPORT_LINK_EXPIRY_HOURS', 24)


# ─── Phone Identity ────────────────────────────────────────────────────────────

def initiate_phone_binding(tenant: Tenant, phone_number: str, role: str, bound_by_user) -> PhoneIdentity:
    """
    Start the binding flow: create (or reset) a PhoneIdentity in PENDING_VERIFICATION
    and generate a fresh OTP for the WhatsApp round-trip.

    Returns the PhoneIdentity (caller is responsible for sending the OTP via WhatsApp).
    """
    phone_number = normalise_phone(phone_number)

    # Check if this number is already bound to another tenant
    existing = PhoneIdentity.objects.filter(phone_number=phone_number).exclude(
        tenant=tenant
    ).filter(status='ACTIVE').first()
    if existing:
        raise ValueError(f"Phone number {phone_number} is already bound to another tenant.")

    pi, _ = PhoneIdentity.objects.get_or_create(
        phone_number=phone_number,
        defaults={
            'tenant': tenant,
            'role': role,
            'status': 'PENDING_VERIFICATION',
            'bound_by': bound_by_user,
        }
    )
    # Reset OTP regardless of whether it already existed
    otp = generate_otp()
    pi.pending_otp_hash = hash_otp(otp)
    pi.otp_sent_at = timezone.now()
    pi.otp_attempts = 0
    pi.status = 'PENDING_VERIFICATION'
    pi.tenant = tenant
    pi.role = role
    pi.bound_by = bound_by_user
    pi.save()

    log_action('PHONE_BINDING_INITIATED', tenant=tenant, user=bound_by_user,
               details={'phone_number': phone_number, 'role': role})
    return pi, otp


def confirm_phone_binding(tenant: Tenant, phone_number: str, submitted_otp: str, bound_by_user) -> PhoneIdentity:
    """
    Verify the OTP submitted on the web page and activate the PhoneIdentity.
    Raises ValueError on failure — caller converts to HTTP 400.
    """
    from apps.identity.otp import verify_otp

    phone_number = normalise_phone(phone_number)
    try:
        pi = PhoneIdentity.objects.get(phone_number=phone_number, tenant=tenant)
    except PhoneIdentity.DoesNotExist:
        raise ValueError("No pending binding for this phone number on this tenant.")

    if pi.status == 'ACTIVE':
        return pi  # Already confirmed — idempotent

    if not verify_otp(pi, submitted_otp):
        raise ValueError("Invalid or expired OTP.")

    pi.status = 'ACTIVE'
    pi.bound_at = timezone.now()
    pi.pending_otp_hash = ''
    pi.save()

    log_action('PHONE_BINDING_CONFIRMED', tenant=tenant, user=bound_by_user,
               details={'phone_number': phone_number, 'role': pi.role})
    return pi


def revoke_phone_identity(tenant: Tenant, phone_number: str, revoked_by_user) -> PhoneIdentity:
    """
    Revoke an active PhoneIdentity. This is a sensitive action and should only be
    called after step-up confirmation (§7.4). Caller is responsible for enforcing that.
    """
    phone_number = normalise_phone(phone_number)
    try:
        pi = PhoneIdentity.objects.get(phone_number=phone_number, tenant=tenant, status='ACTIVE')
    except PhoneIdentity.DoesNotExist:
        raise ValueError("No active binding for this phone number on this tenant.")

    pi.status = 'REVOKED'
    pi.revoked_at = timezone.now()
    pi.revoked_by = revoked_by_user
    pi.save()

    log_action('PHONE_IDENTITY_REVOKED', tenant=tenant, user=revoked_by_user,
               details={'phone_number': phone_number})
    return pi


def list_phone_identities(tenant: Tenant):
    """Return all non-revoked PhoneIdentities for a tenant."""
    return PhoneIdentity.objects.filter(tenant=tenant).exclude(status='REVOKED').order_by('role', 'phone_number')


# ─── Step-Up Auth ─────────────────────────────────────────────────────────────

def issue_step_up_challenge(
    phone_identity: PhoneIdentity,
    action_type: str,
    action_payload: dict,
) -> tuple[StepUpChallenge, str]:
    """
    Create a StepUpChallenge for a sensitive action (§7.4).
    Returns (challenge, raw_token). raw_token must be embedded in the magic link;
    it is never stored — only its hash is persisted.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = MagicLinkToken.hash_token(raw_token)

    expires_at = timezone.now() + datetime.timedelta(minutes=STEP_UP_EXPIRY_MINUTES)

    challenge = StepUpChallenge.objects.create(
        tenant=phone_identity.tenant,
        initiated_by=phone_identity,
        action_type=action_type,
        action_payload=action_payload,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    log_action('STEP_UP_CHALLENGE_ISSUED', tenant=phone_identity.tenant,
               details={'action_type': action_type, 'challenge_id': str(challenge.id)})
    return challenge, raw_token


def confirm_step_up_challenge(raw_token: str, tenant: Tenant):
    """
    Verify and consume a step-up token. Returns the confirmed StepUpChallenge.
    Raises ValueError if token is invalid, expired, or already used.
    """
    token_hash = MagicLinkToken.hash_token(raw_token)
    try:
        challenge = StepUpChallenge.objects.get(token_hash=token_hash, tenant=tenant)
    except StepUpChallenge.DoesNotExist:
        raise ValueError("Invalid or expired step-up token.")

    if not challenge.is_valid():
        raise ValueError("Step-up challenge has expired or already been used.")

    challenge.status = 'CONFIRMED'
    challenge.confirmed_at = timezone.now()
    challenge.save()

    log_action('STEP_UP_CHALLENGE_CONFIRMED', tenant=tenant,
               details={'action_type': challenge.action_type, 'challenge_id': str(challenge.id)})
    return challenge


def get_step_up_challenge_by_token(raw_token: str, tenant: Tenant) -> StepUpChallenge:
    """Fetch a challenge by its raw token for display purposes (does not consume it)."""
    token_hash = MagicLinkToken.hash_token(raw_token)
    try:
        return StepUpChallenge.objects.get(token_hash=token_hash, tenant=tenant)
    except StepUpChallenge.DoesNotExist:
        raise ValueError("Invalid or expired step-up token.")


# ─── Magic Links ──────────────────────────────────────────────────────────────

def issue_magic_link(tenant: Tenant, purpose: str, scope: dict, single_use: bool = True,
                     expiry_hours: int = None) -> tuple[MagicLinkToken, str]:
    """
    Issue a magic-link token for a given purpose. Returns (token_record, raw_token).
    raw_token is embedded in the URL; never stored or logged in full.
    """
    hours = expiry_hours or (1 if single_use else MAGIC_LINK_EXPIRY_HOURS)
    raw_token = secrets.token_urlsafe(32)
    token_hash = MagicLinkToken.hash_token(raw_token)

    ml = MagicLinkToken.objects.create(
        tenant=tenant,
        token_hash=token_hash,
        purpose=purpose,
        scope=scope,
        single_use=single_use,
        expires_at=timezone.now() + datetime.timedelta(hours=hours),
    )
    return ml, raw_token


def consume_magic_link(raw_token: str, tenant: Tenant) -> MagicLinkToken:
    """
    Validate a magic-link token and mark it used if single_use.
    Returns 404-equivalent None if invalid/expired — caller returns 404 (not 403).
    """
    token_hash = MagicLinkToken.hash_token(raw_token)
    try:
        ml = MagicLinkToken.objects.get(token_hash=token_hash, tenant=tenant)
    except MagicLinkToken.DoesNotExist:
        return None

    if not ml.is_valid():
        return None

    if ml.single_use and ml.used_at is None:
        ml.used_at = timezone.now()
        ml.save(update_fields=['used_at'])

    return ml


# ─── Helpers ──────────────────────────────────────────────────────────────────

def normalise_phone(phone: str) -> str:
    """
    Normalise a Kenyan phone number to E.164 format (2547XXXXXXXX).
    Handles: 07XX, +2547XX, 2547XX.
    """
    p = phone.strip().replace(' ', '').replace('-', '').replace('+', '')
    if p.startswith('0') and len(p) == 10:
        p = '254' + p[1:]
    if not p.startswith('254'):
        p = '254' + p.lstrip('0')
    return '+' + p if not p.startswith('+') else p
