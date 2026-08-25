from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant, TenantUser
from apps.merchants.models import MerchantProfile, PaymentProviderAccount, WhatsAppAccount, APIKey
from apps.payments.models import PaymentRequest, PaymentAttempt, Transaction
from apps.audit.models import AuditLog
from django.conf import settings

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'created_at', 'is_active']

class MerchantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantProfile
        fields = [
            'id', 'business_name', 'owner_name', 'email', 'phone',
            'settlement_type', 'settlement_number', 'settlement_bank_name',
            'status', 'kyc_verified', 'created_at'
        ]

class PaymentProviderAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProviderAccount
        fields = ['id', 'provider_name', 'account_reference', 'is_active', 'created_at']

class WhatsAppAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppAccount
        fields = [
            'id', 'phone_number_id', 'display_phone_number', 'waba_id',
            'status', 'auto_send_receipts', 'connected_at'
        ]

class PaymentRequestSerializer(serializers.ModelSerializer):
    checkout_url = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaymentRequest
        fields = [
            'id', 'public_token', 'amount_minor', 'currency', 'reference',
            'description', 'customer_phone', 'status', 'expires_at',
            'created_at', 'paid_at', 'checkout_url', 'is_expired', 'metadata'
        ]
        read_only_fields = ['id', 'public_token', 'status', 'created_at', 'paid_at']

    def get_checkout_url(self, obj):
        return f"{settings.IMARA_PAY['BASE_URL']}/p/{obj.public_token}"

class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = [
            'id', 'provider', 'external_reference', 'customer_phone',
            'status', 'raw_response', 'created_at', 'updated_at'
        ]

class TransactionSerializer(serializers.ModelSerializer):
    payment_reference = serializers.CharField(source='payment_request.reference', read_only=True)
    description = serializers.CharField(source='payment_request.description', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'payment_reference', 'description', 'amount_minor', 'currency',
            'mpesa_receipt_number', 'customer_phone', 'status', 'paid_at'
        ]

class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'user_email', 'ip_address', 'details', 'timestamp']

    def get_user_email(self, obj):
        return obj.user.email if obj.user else 'System'
