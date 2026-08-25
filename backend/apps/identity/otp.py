"""
identity/otp.py
===============
Generates and verifies one-time codes for the phone-binding OTP round-trip (§7.1).
Uses a 6-digit random code with a 10-minute validity window.
"""
import hashlib
import secrets
import string
from django.utils import timezone
import datetime

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


def generate_otp() -> str:
    """Return a 6-digit numeric OTP."""
    return ''.join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))


def hash_otp(otp: str) -> str:
    """Hash an OTP for safe storage. Raw OTP is never stored."""
    return hashlib.sha256(otp.encode()).hexdigest()


def is_otp_valid(phone_identity) -> bool:
    """Check if the stored OTP hash is still within the expiry window."""
    if not phone_identity.otp_sent_at:
        return False
    expiry = phone_identity.otp_sent_at + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)
    return timezone.now() < expiry


def verify_otp(phone_identity, submitted_otp: str) -> bool:
    """
    Verify a submitted OTP against the stored hash.
    Increments attempt counter on every call; returns False if expired or exhausted.
    """
    if phone_identity.otp_attempts >= MAX_OTP_ATTEMPTS:
        return False
    if not is_otp_valid(phone_identity):
        return False

    phone_identity.otp_attempts += 1
    phone_identity.save(update_fields=['otp_attempts'])

    submitted_hash = hash_otp(submitted_otp.strip())
    return secrets.compare_digest(submitted_hash, phone_identity.pending_otp_hash)
