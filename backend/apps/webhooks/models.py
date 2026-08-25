import uuid
from django.db import models

class WebhookEvent(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSED', 'Processed'),
        ('FAILED', 'Failed'),
        ('DUPLICATE', 'Duplicate Ignored'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=50)
    external_event_id = models.CharField(max_length=255)
    payload_hash = models.CharField(max_length=64, blank=True, default='')
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('provider', 'external_event_id')

    def __str__(self):
        return f"Webhook {self.provider}:{self.external_event_id} ({self.processing_status})"
