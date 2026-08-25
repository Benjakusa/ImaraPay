import datetime
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth import get_user_model, authenticate
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.tenants.models import Tenant, TenantUser
from apps.merchants.models import MerchantProfile, PaymentProviderAccount, WhatsAppAccount
from apps.payments.models import PaymentRequest, PaymentAttempt, Transaction
from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.providers.mpesa_sandbox import MPesaSandboxAdapter
from apps.whatsapp.adapter import WhatsAppBusinessAdapter
from apps.api.serializers import (
    UserSerializer, TenantSerializer, MerchantProfileSerializer,
    PaymentProviderAccountSerializer, WhatsAppAccountSerializer,
    PaymentRequestSerializer, PaymentAttemptSerializer, TransactionSerializer, AuditLogSerializer
)

User = get_user_model()

def get_or_create_demo_tenant(user, business_name="Nairobi Tech Supplies"):
    membership = TenantUser.objects.filter(user=user).first()
    if membership:
        return membership.tenant

    slug = f"tenant-{user.username[:15]}"
    tenant = Tenant.objects.create(name=business_name, slug=slug)
    TenantUser.objects.create(tenant=tenant, user=user, role='OWNER')

    MerchantProfile.objects.create(
        tenant=tenant,
        business_name=business_name,
        owner_name=user.get_full_name() or user.username,
        email=user.email or f"{user.username}@imarapay.example",
        phone="0712345678",
        settlement_type='PAYBILL',
        settlement_number='522522',
        status='ACTIVE',
        kyc_verified=True
    )

    PaymentProviderAccount.objects.create(
        tenant=tenant,
        provider_name='MPESA_SANDBOX',
        account_reference='522522',
        is_active=True
    )

    WhatsAppAccount.objects.create(
        tenant=tenant,
        display_phone_number="+254 712 345 678",
        status='CONNECTED'
    )

    log_action('TENANT_CREATED', tenant=tenant, user=user, details={'business_name': business_name})
    return tenant

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username') or request.data.get('email', '').split('@')[0]
        email = request.data.get('email')
        password = request.data.get('password', 'Password123!')
        business_name = request.data.get('business_name', 'Imara Merchant')

        if not username or not email:
            return Response({'error': 'Email and business name are required'}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password(password)
            user.save()

        tenant = get_or_create_demo_tenant(user, business_name)

        return Response({
            'message': 'Registration successful',
            'token': f"demo-token-user-{user.username}",
            'user': UserSerializer(user).data,
            'tenant': TenantSerializer(tenant).data
        })

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username') or request.data.get('email', '').split('@')[0]
        password = request.data.get('password')

        user = User.objects.filter(Q(username=username) | Q(email=username)).first()
        if not user:
            user = User.objects.create_user(username=username, email=f"{username}@imarapay.example", password=password or "demo123")

        tenant = get_or_create_demo_tenant(user)

        return Response({
            'token': f"demo-token-user-{user.username}",
            'user': UserSerializer(user).data,
            'tenant': TenantSerializer(tenant).data
        })

class MerchantMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            tenant = get_or_create_demo_tenant(request.user)

        profile = getattr(tenant, 'merchant_profile', None)
        whatsapp = getattr(tenant, 'whatsapp_account', None)
        provider = tenant.provider_accounts.filter(is_active=True).first()

        return Response({
            'tenant': TenantSerializer(tenant).data,
            'profile': MerchantProfileSerializer(profile).data if profile else None,
            'whatsapp': WhatsAppAccountSerializer(whatsapp).data if whatsapp else None,
            'provider': PaymentProviderAccountSerializer(provider).data if provider else None,
        })

    def patch(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

        profile = getattr(tenant, 'merchant_profile', None)
        if profile:
            serializer = MerchantProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                log_action('UPDATE_MERCHANT_PROFILE', tenant=tenant, user=request.user, details=request.data)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

class OnboardingCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            tenant = get_or_create_demo_tenant(request.user)

        business_name = request.data.get('business_name', 'Imara Business')
        owner_name = request.data.get('owner_name', request.user.username)
        settlement_type = request.data.get('settlement_type', 'PAYBILL')
        settlement_number = request.data.get('settlement_number', '522522')

        profile, _ = MerchantProfile.objects.get_or_create(tenant=tenant)
        profile.business_name = business_name
        profile.owner_name = owner_name
        profile.settlement_type = settlement_type
        profile.settlement_number = settlement_number
        profile.status = 'ACTIVE'
        profile.kyc_verified = True
        profile.save()

        WhatsAppAccount.objects.get_or_create(
            tenant=tenant,
            defaults={'status': 'CONNECTED', 'display_phone_number': '+254 712 345 678'}
        )

        log_action('ONBOARDING_COMPLETED', tenant=tenant, user=request.user)
        return Response({'message': 'Onboarding complete', 'profile': MerchantProfileSerializer(profile).data})

class PaymentRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentRequestSerializer

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant = get_or_create_demo_tenant(self.request.user)
        return PaymentRequest.objects.filter(tenant=tenant).order_by('-created_at')

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant = get_or_create_demo_tenant(self.request.user)

        expires_in = int(self.request.data.get('expires_in_minutes', 1440))
        expires_at = timezone.now() + datetime.timedelta(minutes=expires_in)

        provider_acc = tenant.provider_accounts.filter(is_active=True).first()

        pr = serializer.save(
            tenant=tenant,
            expires_at=expires_at,
            provider_account=provider_acc
        )
        log_action(
            'CREATE_PAYMENT_REQUEST',
            tenant=tenant,
            user=self.request.user,
            details={'amount': pr.amount_minor, 'ref': pr.reference}
        )

    def cancel(self, request, pk=None):
        pr = self.get_object()
        if pr.status in ['SUCCEEDED', 'CANCELLED']:
            return Response({'error': f'Cannot cancel request in status {pr.status}'}, status=status.HTTP_400_BAD_REQUEST)

        pr.status = 'CANCELLED'
        pr.save()
        log_action('CANCEL_PAYMENT_REQUEST', tenant=pr.tenant, user=request.user, details={'pr_id': str(pr.id)})
        return Response({'message': 'Payment request cancelled', 'payment_request': PaymentRequestSerializer(pr).data})

    def share_whatsapp(self, request, pk=None):
        pr = self.get_object()
        wa_adapter = WhatsAppBusinessAdapter()
        res = wa_adapter.send_payment_link(pr, request.data.get('customer_phone'))
        return Response(res)

class PublicCheckoutView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, public_token):
        pr = PaymentRequest.objects.filter(public_token=public_token).first()
        if not pr:
            return Response({'error': 'Invalid payment request token'}, status=status.HTTP_404_NOT_FOUND)

        if pr.is_expired() and pr.status != 'SUCCEEDED':
            pr.status = 'EXPIRED'
            pr.save()

        merchant = getattr(pr.tenant, 'merchant_profile', None)

        return Response({
            'id': str(pr.id),
            'public_token': pr.public_token,
            'merchant_name': merchant.business_name if merchant else pr.tenant.name,
            'amount_minor': pr.amount_minor,
            'currency': pr.currency,
            'reference': pr.reference,
            'description': pr.description,
            'customer_phone': pr.customer_phone,
            'status': pr.status,
            'expires_at': pr.expires_at,
            'is_expired': pr.is_expired(),
            'paid_at': pr.paid_at
        })

    def post(self, request, public_token):
        """
        Initiates M-Pesa STK Push
        """
        pr = PaymentRequest.objects.filter(public_token=public_token).first()
        if not pr:
            return Response({'error': 'Invalid payment request token'}, status=status.HTTP_404_NOT_FOUND)

        if pr.status == 'SUCCEEDED':
            return Response({'error': 'This payment has already been completed'}, status=status.HTTP_400_BAD_REQUEST)

        if pr.is_expired():
            pr.status = 'EXPIRED'
            pr.save()
            return Response({'error': 'This payment link has expired'}, status=status.HTTP_400_BAD_REQUEST)

        phone = request.data.get('phone_number')
        if not phone:
            return Response({'error': 'Please provide your M-Pesa phone number'}, status=status.HTTP_400_BAD_REQUEST)

        # Standardize Kenyan phone format
        clean_phone = phone.strip().replace('+', '').replace(' ', '')
        if clean_phone.startswith('0'):
            clean_phone = '254' + clean_phone[1:]

        pr.customer_phone = clean_phone
        pr.save()

        # Create PaymentAttempt
        attempt = PaymentAttempt.objects.create(
            payment_request=pr,
            tenant=pr.tenant,
            provider='MPESA_SANDBOX',
            customer_phone=clean_phone,
            status='INITIATED'
        )

        adapter = MPesaSandboxAdapter()
        init_res = adapter.initiate_payment(attempt)

        log_action(
            'INITIATE_STK_PUSH',
            tenant=pr.tenant,
            details={'checkout_request_id': init_res.get('checkout_request_id'), 'phone': clean_phone}
        )

        return Response({
            'message': 'STK Push initiated successfully',
            'checkout_request_id': init_res.get('checkout_request_id'),
            'attempt_id': str(attempt.id),
            'status': pr.status,
            'customer_phone': clean_phone
        })

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant = get_or_create_demo_tenant(self.request.user)
        return Transaction.objects.filter(tenant=tenant).order_by('-paid_at')

class WebhookReceiverView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, provider='MPESA_SANDBOX'):
        adapter = MPesaSandboxAdapter()
        res = adapter.handle_webhook(request.data, headers=request.headers)
        return Response(res, status=status.HTTP_200_OK)

class WebhookSimulatorView(APIView):
    """
    Interactive test endpoint for the UI Sandbox Simulator.
    Allows frontend to trigger Safaricom STK Push callbacks (Success, Cancelled, Wrong PIN, Timeout).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        checkout_request_id = request.data.get('checkout_request_id')
        scenario = request.data.get('scenario', 'SUCCESS') # SUCCESS, USER_CANCELLED, WRONG_PIN, TIMEOUT

        if not checkout_request_id:
            return Response({'error': 'checkout_request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        adapter = MPesaSandboxAdapter()

        if scenario == 'SUCCESS':
            res = adapter.process_callback(
                checkout_request_id=checkout_request_id,
                result_code=0,
                result_desc="The service request is processed successfully."
            )
        elif scenario == 'USER_CANCELLED':
            res = adapter.process_callback(
                checkout_request_id=checkout_request_id,
                result_code=1032,
                result_desc="Request cancelled by user."
            )
        elif scenario == 'WRONG_PIN':
            res = adapter.process_callback(
                checkout_request_id=checkout_request_id,
                result_code=2001,
                result_desc="The initiator information is invalid / wrong PIN entered."
            )
        else:
            res = adapter.process_callback(
                checkout_request_id=checkout_request_id,
                result_code=1037,
                result_desc="Timeout in completing transaction."
            )

        return Response(res)

class WhatsAppView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action = request.data.get('action')
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            tenant = get_or_create_demo_tenant(request.user)

        if action == 'connect':
            wa, _ = WhatsAppAccount.objects.get_or_create(tenant=tenant)
            wa.status = 'CONNECTED'
            wa.display_phone_number = request.data.get('phone', '+254 712 345 678')
            wa.save()
            log_action('CONNECT_WHATSAPP', tenant=tenant, user=request.user)
            return Response({'message': 'WhatsApp Business connected', 'whatsapp': WhatsAppAccountSerializer(wa).data})

        elif action == 'simulate_command':
            raw_command = request.data.get('command', 'request 2500')
            adapter = WhatsAppBusinessAdapter()
            res = adapter.handle_incoming_merchant_command(tenant, raw_command)
            return Response(res)

        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            tenant = get_or_create_demo_tenant(request.user)

        requests = PaymentRequest.objects.filter(tenant=tenant)

        total_volume = requests.filter(status='SUCCEEDED').aggregate(total=Sum('amount_minor'))['total'] or 0
        total_succeeded_count = requests.filter(status='SUCCEEDED').count()
        total_pending_count = requests.filter(status='PENDING').count()
        total_failed_count = requests.filter(status='FAILED').count()
        total_created_count = requests.count()

        conversion_rate = (total_succeeded_count / total_created_count * 100) if total_created_count > 0 else 0

        recent_requests = PaymentRequestSerializer(requests[:5], many=True).data
        recent_transactions = TransactionSerializer(Transaction.objects.filter(tenant=tenant).order_by('-paid_at')[:5], many=True).data

        return Response({
            'total_volume_kes': total_volume,
            'succeeded_count': total_succeeded_count,
            'pending_count': total_pending_count,
            'failed_count': total_failed_count,
            'total_count': total_created_count,
            'conversion_rate': round(conversion_rate, 1),
            'recent_requests': recent_requests,
            'recent_transactions': recent_transactions
        })

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            tenant = get_or_create_demo_tenant(self.request.user)
        return AuditLog.objects.filter(tenant=tenant).order_by('-timestamp')
