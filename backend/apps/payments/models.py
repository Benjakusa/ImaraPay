import uuid
import secrets
from django.db import models
from django.utils import timezone
from apps.tenants.models import Tenant
from apps.merchants.models import PaymentProviderAccount

def generate_public_token():
    return secrets.token_urlsafe(18).replace('-', '').replace('_', '')[:24]

class PaymentRequest(models.Model):
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('PENDING', 'Pending'),
        ('SUCCEEDED', 'Succeeded'),
        ('FAILED', 'Failed'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payment_requests')
    public_token = models.CharField(max_length=64, unique=True, default=generate_public_token)
    amount_minor = models.IntegerField(help_text="Amount in KES integer shillings or minor units")
    currency = models.CharField(max_length=3, default='KES')
    reference = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    customer_phone = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')
    provider_account = models.ForeignKey(
        PaymentProviderAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_requests'
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def is_expired(self):
        if self.status in ['SUCCEEDED', 'CANCELLED', 'FAILED']:
            return False
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"PR-{self.reference} ({self.currency} {self.amount_minor}) - {self.status}"

class PaymentAttempt(models.Model):
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending User Action'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('TIMEOUT', 'Timeout'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_request = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE, related_name='attempts')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payment_attempts')
    provider = models.CharField(max_length=50, default='MPESA_SANDBOX')
    external_reference = models.CharField(max_length=255, blank=True, default='')
    customer_phone = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED')
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Attempt {self.id} for {self.payment_request.reference} ({self.status})"

class Transaction(models.Model):
    STATUS_CHOICES = [
        ('SUCCEEDED', 'Succeeded'),
        ('REFUNDED', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='transactions')
    payment_request = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE, related_name='transactions')
    payment_attempt = models.ForeignKey(PaymentAttempt, on_delete=models.SET_NULL, null=True, blank=True)
    amount_minor = models.IntegerField()
    currency = models.CharField(max_length=3, default='KES')
    mpesa_receipt_number = models.CharField(max_length=100, unique=True)
    customer_phone = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUCCEEDED')
    paid_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Tx: {self.mpesa_receipt_number} - {self.currency} {self.amount_minor}"
