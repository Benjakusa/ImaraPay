"""
api/phone_identity_views.py
===========================
Phone identity binding API views (§7.1, §14.1).
Called during web onboarding to bind a WhatsApp number to a tenant.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

logger = logging.getLogger(__name__)


def _get_tenant(request):
    from apps.api.views import get_or_create_demo_tenant
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        tenant = get_or_create_demo_tenant(request.user)
    return tenant


class PhoneIdentityBindView(APIView):
    """Initiate phone number binding — sends OTP via WhatsApp."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.identity.services import initiate_phone_binding
        from apps.whatsapp.adapter import WhatsAppBusinessAdapter
        from django.conf import settings

        tenant = _get_tenant(request)
        phone_number = request.data.get('phone_number')
        role = request.data.get('role', 'OWNER')

        if not phone_number:
            return Response({'error': 'phone_number is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pi, otp = initiate_phone_binding(tenant, phone_number, role, request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Send OTP via WhatsApp
        wa = WhatsAppBusinessAdapter()
        wa.send_raw_message(pi.phone_number, {
            'type': 'text',
            'text': {'body': (
                f"🔐 *Imara Pay — Verify Your Number*\n\n"
                f"Your 6-digit verification code:\n\n"
                f"*{otp}*\n\n"
                f"Enter this code to link your number to *{tenant.name}*.\n"
                f"Valid for 10 minutes. Don't share this code."
            )}
        })

        resp = {
            'message': f'OTP sent to {pi.phone_number} via WhatsApp.',
            'phone_identity_id': str(pi.id),
            'phone_number': pi.phone_number,
        }
        # Expose OTP in DEBUG mode for development convenience
        if settings.DEBUG:
            resp['dev_otp'] = otp

        return Response(resp, status=status.HTTP_201_CREATED)

    def get(self, request):
        """List current phone identities for this tenant."""
        from apps.identity.services import list_phone_identities
        tenant = _get_tenant(request)
        identities = list_phone_identities(tenant)
        return Response([
            {
                'id': str(pi.id),
                'phone_number': pi.phone_number,
                'role': pi.role,
                'status': pi.status,
                'bound_at': pi.bound_at,
            }
            for pi in identities
        ])


class PhoneIdentityConfirmView(APIView):
    """Confirm OTP to activate a phone binding."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.identity.services import confirm_phone_binding

        tenant = _get_tenant(request)
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')

        if not phone_number or not otp:
            return Response({'error': 'phone_number and otp are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pi = confirm_phone_binding(tenant, phone_number, otp, request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Send welcome message
        try:
            from apps.whatsapp.adapter import WhatsAppBusinessAdapter
            from apps.conversation.reply_composer import onboarding_welcome
            wa = WhatsAppBusinessAdapter()
            wa.send_raw_message(pi.phone_number, onboarding_welcome())
        except Exception as e:
            logger.warning(f"Failed to send welcome message: {e}")

        return Response({
            'message': f'{pi.phone_number} is now active for {tenant.name}!',
            'phone_identity': {
                'id': str(pi.id),
                'phone_number': pi.phone_number,
                'role': pi.role,
                'status': pi.status,
                'bound_at': pi.bound_at,
            }
        })
