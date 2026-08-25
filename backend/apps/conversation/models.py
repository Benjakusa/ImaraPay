"""
conversation/models.py
======================
ConversationSession  — short-lived multi-turn state for guided flows (§6.13)
ProcessedWhatsAppMessage — wamid dedup table for idempotency (§15.1)
"""
import uuid
import datetime
from django.db import models
from django.utils import timezone
from apps.identity.models import PhoneIdentity


class ConversationSession(models.Model):
    """
    Holds in-progress state for guided multi-turn flows (§6.13).
    Never stores more than the current in-progress interaction.
    Expired sessions are treated as abandoned, not resumed.
    """
    FLOW_CHOICES = [
        ('NONE', 'None'),
        ('CREATE_REQUEST', 'Creating Payment Request'),
        ('CANCEL_REQUEST', 'Cancelling Payment Request'),
        ('STEP_UP_PENDING', 'Step-Up Challenge Pending'),
        ('PHONE_BIND', 'Phone Binding OTP'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_identity = models.OneToOneField(
        PhoneIdentity, on_delete=models.CASCADE, related_name='conversation_session'
    )
    flow = models.CharField(max_length=20, choices=FLOW_CHOICES, default='NONE')
    # Small, flow-specific structured state (e.g. {"amount": 2500} awaiting reference)
    state = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['phone_identity'])]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def reset(self):
        """Clear the session to NONE state."""
        self.flow = 'NONE'
        self.state = {}
        self.expires_at = _default_expiry()
        self.save()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = _default_expiry()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Session [{self.flow}] for {self.phone_identity.phone_number}"


class ProcessedWhatsAppMessage(models.Model):
    """
    Durable log of processed wamids for idempotency (§15.1).
    Meta may redeliver the same inbound message; a repeat wamid is a no-op.
    """
    wamid = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['wamid'])]

    def __str__(self):
        return f"wamid:{self.wamid} ({self.phone_number})"


def _default_expiry():
    return timezone.now() + datetime.timedelta(minutes=10)
