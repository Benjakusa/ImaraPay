"""
identity/models.py
==================
PhoneIdentity  — binds a WhatsApp phone number to a tenant (§6.12)
StepUpChallenge — pending sensitive-action confirmation via magic link (§6.14)
MagicLinkToken  — short-lived authenticated web session token (§6.15)
"""
import uuid
import hashlib
from django.db import models
from django.utils import timezone
from apps.tenants.models import Tenant


class PhoneIdentity(models.Model):
    """
    Binds a WhatsApp E.164 phone number to a tenant.
    A number can be bound to at most one tenant at a time (unique on phone_number).
    Created during web onboarding (§7.1) after OTP round-trip confirmation.
    """
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('ADMIN', 'Admin'),
        ('STAFF', 'Staff'),
    ]
    STATUS_CHOICES = [
        ('PENDING_VERIFICATION', 'Pending Verification'),
        ('ACTIVE', 'Active'),
        ('REVOKED', 'Revoked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='phone_identities')
    # E.164 format, globally unique — a number belongs to at most one tenant
    phone_number = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='OWNER')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='PENDING_VERIFICATION')

    # Audit trail
    bound_at = models.DateTimeField(null=True, blank=True)
    bound_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bound_phone_identities'
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='revoked_phone_identities'
    )

    # OTP for the binding confirmation round-trip (§7.1)
    pending_otp_hash = models.CharField(max_length=128, blank=True, default='')
    otp_sent_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Phone Identity'
        verbose_name_plural = 'Phone Identities'

    def is_active(self):
        return self.status == 'ACTIVE'

    def __str__(self):
        return f"{self.phone_number} → {self.tenant.name} [{self.role}/{self.status}]"

    @classmethod
    def resolve(cls, phone_number):
        """
        Return a PhoneIdentity for the given number if it exists and is ACTIVE.
        Returns None for unrecognized or REVOKED numbers — callers must issue the
        generic onboarding reply in that case, never leak tenant info.
        """
        try:
            pi = cls.objects.select_related('tenant').get(phone_number=phone_number)
            if pi.status == 'ACTIVE':
                return pi
        except cls.DoesNotExist:
            pass
        return None


class StepUpChallenge(models.Model):
    """
    Issued when a sensitive action is requested via WhatsApp (§7.4).
    The action is NOT performed until this challenge is confirmed via a single-use
    magic link opened in a browser.
    """
    ACTION_CHOICES = [
        ('REMOVE_STAFF_NUMBER', 'Remove Staff Number'),
        ('CHANGE_SETTLEMENT_ACCOUNT', 'Change Settlement Account'),
        ('REFUND', 'Refund'),
        ('CANCEL_INFLIGHT', 'Cancel In-Flight Payment'),
        ('VIEW_AUDIT_LOG', 'View Audit Log'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='step_up_challenges')
    initiated_by = models.ForeignKey(
        PhoneIdentity, on_delete=models.CASCADE, related_name='step_up_challenges'
    )
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    # The specific parameters of the pending action — re-validated at confirm-time
    action_payload = models.JSONField(default=dict)
    # Hash of single-use magic-link token; raw token never stored
    token_hash = models.CharField(max_length=128)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['token_hash']),
            models.Index(fields=['status', 'expires_at']),
        ]

    def is_valid(self):
        return self.status == 'PENDING' and timezone.now() < self.expires_at

    def __str__(self):
        return f"StepUp [{self.action_type}] for {self.tenant.name} ({self.status})"


class MagicLinkToken(models.Model):
    """
    General-purpose short-lived authenticated web session (§6.15).
    Used for both step-up confirmation and read-only report views.
    Raw token is NEVER stored — only the hash.
    """
    PURPOSE_CHOICES = [
        ('REPORT_VIEW', 'Report View'),
        ('SETTINGS_VIEW', 'Settings View'),
        ('STEP_UP_CONFIRM', 'Step-Up Confirmation'),
        ('PHONE_BIND_CONFIRM', 'Phone Bind Confirmation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='magic_link_tokens')
    # Hash of the token embedded in the URL; raw token never stored or logged
    token_hash = models.CharField(max_length=128, unique=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    # e.g. {"step_up_challenge_id": "..."} or {"date_from": "...", "date_to": "..."}
    scope = models.JSONField(default=dict)
    # True for STEP_UP_CONFIRM (consumed on first use); False for time-boxed report views
    single_use = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['token_hash']),
        ]

    def is_valid(self):
        now = timezone.now()
        if now >= self.expires_at:
            return False
        if self.single_use and self.used_at is not None:
            return False
        return True

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    def __str__(self):
        return f"MagicLink [{self.purpose}] for {self.tenant.name}"
