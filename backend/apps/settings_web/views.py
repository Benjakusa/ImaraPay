"""
settings_web/views.py
=====================
OWNER/ADMIN-only web views for staff management, settlement details, and audit log (§12.3).
These stay behind email/password login — not magic links — because they ARE the actions
that step-up auth is designed to protect (§7.3, §12.3).
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone

from apps.identity.models import PhoneIdentity
from apps.identity.services import (
    initiate_phone_binding, confirm_phone_binding, revoke_phone_identity,
    list_phone_identities, issue_step_up_challenge
)
from apps.audit.models import AuditLog
from apps.audit.services import log_action

logger = logging.getLogger(__name__)


def _get_tenant(request):
    tenant = getattr(request, 'tenant', None)
    return tenant


def _check_owner_admin(request, tenant):
    from apps.tenants.models import TenantUser
    membership = TenantUser.objects.filter(user=request.user, tenant=tenant).first()
    if not membership or membership.role not in ('OWNER', 'ADMIN'):
        return False
    return True


class StaffPhoneListView(APIView):
    """List and add staff phone numbers (§12.3)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = _get_tenant(request)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _check_owner_admin(request, tenant):
            return Response({'error': 'OWNER or ADMIN required'}, status=status.HTTP_403_FORBIDDEN)

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

    def post(self, request):
        """Initiate binding of a new staff phone number — sends OTP via WhatsApp."""
        tenant = _get_tenant(request)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _check_owner_admin(request, tenant):
            return Response({'error': 'OWNER or ADMIN required'}, status=status.HTTP_403_FORBIDDEN)

        phone_number = request.data.get('phone_number')
        role = request.data.get('role', 'STAFF')

        if not phone_number:
            return Response({'error': 'phone_number is required'}, status=status.HTTP_400_BAD_REQUEST)

        if role not in ('OWNER', 'ADMIN', 'STAFF'):
            return Response({'error': 'role must be OWNER, ADMIN, or STAFF'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pi, otp = initiate_phone_binding(tenant, phone_number, role, request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Send OTP via WhatsApp
        try:
            from apps.whatsapp.adapter import WhatsAppBusinessAdapter
            wa = WhatsAppBusinessAdapter()
            wa.send_raw_message(pi.phone_number, {
                'type': 'text',
                'text': {'body': (
                    f"🔐 *Imara Pay — Number Verification*\n\n"
                    f"Your verification code to link this number to *{tenant.name}*:\n\n"
                    f"*{otp}*\n\n"
                    f"Enter this code on the setup page. Valid for 10 minutes."
                )}
            })
        except Exception as e:
            logger.error(f"Failed to send OTP via WhatsApp: {e}")
            # OTP is generated; surface it in development so dev can verify
            return Response({
                'message': 'Binding initiated. OTP sending failed — check WhatsApp config.',
                'phone_identity_id': str(pi.id),
                'dev_otp': otp if __import__('django.conf', fromlist=['settings']).settings.DEBUG else None,
            }, status=status.HTTP_201_CREATED)

        return Response({
            'message': f'OTP sent to {pi.phone_number} via WhatsApp. Enter it to confirm.',
            'phone_identity_id': str(pi.id),
        }, status=status.HTTP_201_CREATED)


class StaffPhoneConfirmView(APIView):
    """Confirm an OTP to complete phone binding."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant = _get_tenant(request)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')

        if not phone_number or not otp:
            return Response({'error': 'phone_number and otp are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pi = confirm_phone_binding(tenant, phone_number, otp, request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': f'{pi.phone_number} is now active for {tenant.name}.',
            'phone_identity': {
                'id': str(pi.id),
                'phone_number': pi.phone_number,
                'role': pi.role,
                'status': pi.status,
                'bound_at': pi.bound_at,
            }
        })


class StaffPhoneRevokeView(APIView):
    """
    Revoke a staff phone number — sensitive action, requires step-up confirmation (§7.4).
    Initiating from the web settings (OWNER logged in) counts as the step-up — the OWNER
    is already authenticated with their password, which IS the non-chat channel §7.3 relies on.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, phone_identity_id):
        tenant = _get_tenant(request)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _check_owner_admin(request, tenant):
            return Response({'error': 'OWNER or ADMIN required'}, status=status.HTTP_403_FORBIDDEN)

        try:
            pi = PhoneIdentity.objects.get(id=phone_identity_id, tenant=tenant)
        except PhoneIdentity.DoesNotExist:
            return Response({'error': 'Phone identity not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            pi = revoke_phone_identity(tenant, pi.phone_number, request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f'{pi.phone_number} has been revoked.'})


class SettlementDetailsView(APIView):
    """Update settlement account details — OWNER only."""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        tenant = _get_tenant(request)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

        from apps.tenants.models import TenantUser
        membership = TenantUser.objects.filter(user=request.user, tenant=tenant).first()
        if not membership or membership.role != 'OWNER':
            return Response({'error': 'OWNER role required to change settlement details'},
                            status=status.HTTP_403_FORBIDDEN)

        profile = getattr(tenant, 'merchant_profile', None)
        if not profile:
            return Response({'error': 'Merchant profile not found'}, status=status.HTTP_404_NOT_FOUND)

        settlement_type = request.data.get('settlement_type')
        settlement_number = request.data.get('settlement_number')

        if settlement_type:
            profile.settlement_type = settlement_type
        if settlement_number:
            profile.settlement_number = settlement_number
        profile.save()

        log_action('UPDATE_SETTLEMENT_DETAILS', tenant=tenant, user=request.user,
                   details={'settlement_type': settlement_type, 'via': 'web'})

        return Response({'message': 'Settlement details updated.'})


class FullAuditLogView(APIView):
    """Full audit log — OWNER/ADMIN only, requires web login (§12.3)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = _get_tenant(request)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _check_owner_admin(request, tenant):
            return Response({'error': 'OWNER or ADMIN required'}, status=status.HTTP_403_FORBIDDEN)

        qs = AuditLog.objects.filter(tenant=tenant).order_by('-timestamp')[:200]
        return Response([
            {
                'id': str(a.id),
                'action': a.action,
                'timestamp': a.timestamp,
                'details': a.details,
            }
            for a in qs
        ])
