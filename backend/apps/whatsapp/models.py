"""
whatsapp/models.py
==================
InboundWhatsAppEvent — durable store of raw inbound webhook payloads (§11.3).
Stored before any processing so a crash never silently drops a message.
"""
import uuid
from django.db import models


class InboundWhatsAppEvent(models.Model):
    """Durable log of every inbound Meta webhook message payload."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wamid = models.CharField(max_length=255, unique=True, help_text="Meta message ID for dedup")
    from_number = models.CharField(max_length=20, help_text="Sender phone in E.164")
    # Full Meta webhook payload for this message
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['wamid']),
            models.Index(fields=['from_number']),
            models.Index(fields=['received_at']),
        ]

    def mark_processed(self, error: str = ''):
        from django.utils import timezone
        self.processed_at = timezone.now()
        self.processing_error = error
        self.save(update_fields=['processed_at', 'processing_error'])

    def __str__(self):
        return f"WA inbound {self.wamid} from {self.from_number}"
