import uuid
from django.db import models
from apps.tenants.models import Tenant

class MerchantProfile(models.Model):
    SETTLEMENT_TYPES = [
        ('PAYBILL', 'M-Pesa PayBill'),
        ('TILL', 'M-Pesa Buy Goods Till'),
        ('BANK', 'Bank Account'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PENDING_VERIFICATION', 'Pending Verification'),
        ('SUSPENDED', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='merchant_profile')
    business_name = models.CharField(max_length=255)
    owner_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    settlement_type = models.CharField(max_length=20, choices=SETTLEMENT_TYPES, default='PAYBILL')
    settlement_number = models.CharField(max_length=100, help_text="PayBill No, Till No, or Bank Acc No")
    settlement_bank_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ACTIVE')
    kyc_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} ({self.tenant.slug})"

class PaymentProviderAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='provider_accounts')
    provider_name = models.CharField(max_length=50, default='MPESA_SANDBOX')
    account_reference = models.CharField(max_length=100)
    credentials = models.JSONField(default=dict, blank=True, help_text="Encrypted or structured provider settings")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant.name} - {self.provider_name} ({self.account_reference})"

class WhatsAppAccount(models.Model):
    STATUS_CHOICES = [
        ('CONNECTED', 'Connected'),
        ('PENDING', 'Pending Setup'),
        ('DISCONNECTED', 'Disconnected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='whatsapp_account')
    phone_number_id = models.CharField(max_length=100, blank=True, default='')
    display_phone_number = models.CharField(max_length=50, blank=True, default='')
    waba_id = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    access_token = models.TextField(blank=True, default='')
    auto_send_receipts = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"WhatsApp: {self.tenant.name} ({self.status})"

class APIKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=12)
    key_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"APIKey {self.prefix}... ({self.name})"
