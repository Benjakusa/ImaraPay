"""
api/magic_link_views.py
=======================
Magic-link and step-up confirmation views (§12.2, §7.4, §14.1).
All return 404 (not 403) for invalid/expired tokens — never leaking whether a token existed.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.utils import timezone

logger = logging.getLogger(__name__)

# Default tenant resolver for magic-link requests (token carries tenant scope in its payload)
def _resolve_tenant_from_token(ml_token):
    return ml_token.tenant


class ReportView(APIView):
    """
    Read-only transaction report opened via magic link (§12.2).
    Returns 404 for any invalid/expired token — no 403, no information about the token.
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        from apps.identity.services import consume_magic_link
        from apps.payments.models import PaymentRequest, Transaction

        # We need to find which tenant this token belongs to — search by hash
        from apps.identity.models import MagicLinkToken
        token_hash = MagicLinkToken.hash_token(token)
        try:
            ml = MagicLinkToken.objects.get(token_hash=token_hash)
        except MagicLinkToken.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Validate without consuming (report links are time-boxed, not single-use)
        if not ml.is_valid():
            return Response(status=status.HTTP_404_NOT_FOUND)

        tenant = ml.tenant
        scope = ml.scope

        # Apply scope filters
        qs = Transaction.objects.filter(tenant=tenant).order_by('-paid_at')
        if scope.get('date_from'):
            qs = qs.filter(paid_at__date__gte=scope['date_from'])
        if scope.get('date_to'):
            qs = qs.filter(paid_at__date__lte=scope['date_to'])

        transactions = [
            {
                'id': str(t.id),
                'amount_minor': t.amount_minor,
                'currency': t.currency,
                'mpesa_receipt_number': t.mpesa_receipt_number,
                'customer_phone': t.customer_phone,
                'reference': t.payment_request.reference if t.payment_request_id else '',
                'paid_at': t.paid_at,
                'status': t.status,
            }
            for t in qs[:500]
        ]

        return Response({
            'tenant_name': tenant.name,
            'scope': scope,
            'transactions': transactions,
            'expires_at': ml.expires_at,
        })


class StepUpView(APIView):
    """
    Display a pending step-up challenge action for merchant confirmation (§7.4).
    Returns 404 for any invalid/expired token.
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        from apps.identity.models import MagicLinkToken, StepUpChallenge

        token_hash = MagicLinkToken.hash_token(token)
        try:
            challenge = StepUpChallenge.objects.select_related('tenant').get(token_hash=token_hash)
        except StepUpChallenge.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not challenge.is_valid():
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Human-readable action descriptions for the confirmation page
        action_labels = {
            'REMOVE_STAFF_NUMBER': 'Remove a staff phone number',
            'CHANGE_SETTLEMENT_ACCOUNT': 'Change settlement account',
            'REFUND': 'Process a refund',
            'CANCEL_INFLIGHT': 'Cancel an in-flight payment',
            'VIEW_AUDIT_LOG': 'View full audit log',
        }

        return Response({
            'action_type': challenge.action_type,
            'action_label': action_labels.get(challenge.action_type, challenge.action_type),
            'action_payload': challenge.action_payload,
            'tenant_name': challenge.tenant.name,
            'expires_at': challenge.expires_at,
            'expires_in_seconds': max(0, int((challenge.expires_at - timezone.now()).total_seconds())),
        })


class StepUpConfirmView(APIView):
    """
    Execute a step-up challenge after merchant confirmation (§7.4).
    Single-use — second call returns 404. Always returns 404 for invalid/expired tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request, token):
        from apps.identity.models import MagicLinkToken, StepUpChallenge
        from apps.identity.services import confirm_step_up_challenge
        from apps.audit.services import log_action

        token_hash = MagicLinkToken.hash_token(token)
        try:
            challenge = StepUpChallenge.objects.select_related('tenant').get(token_hash=token_hash)
        except StepUpChallenge.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not challenge.is_valid():
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Confirm and consume the challenge
        try:
            challenge = confirm_step_up_challenge(token, challenge.tenant)
        except ValueError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Execute the action
        result = _execute_step_up_action(challenge)
        if not result['success']:
            return Response({'error': result.get('error', 'Action failed')}, status=status.HTTP_400_BAD_REQUEST)

        # Notify the merchant via WhatsApp that the action completed
        try:
            _notify_step_up_completion(challenge, result)
        except Exception as e:
            logger.warning(f"Failed to send step-up completion notification: {e}")

        return Response({
            'message': result.get('message', 'Action completed successfully.'),
            'action_type': challenge.action_type,
        })


def _execute_step_up_action(challenge) -> dict:
    """Route a confirmed StepUpChallenge to its action handler."""
    payload = challenge.action_payload
    tenant = challenge.tenant

    if challenge.action_type == 'CANCEL_INFLIGHT':
        from apps.payments.services import cancel_payment_request_step_up_confirmed
        pr_id = payload.get('payment_request_id')
        try:
            pr = cancel_payment_request_step_up_confirmed(tenant, pr_id, challenge)
            return {'success': True, 'message': f"Payment request {pr.reference} cancelled."}
        except ValueError as e:
            return {'success': False, 'error': str(e)}

    elif challenge.action_type == 'REMOVE_STAFF_NUMBER':
        from apps.identity.services import revoke_phone_identity
        phone = payload.get('phone_number')
        try:
            revoke_phone_identity(tenant, phone, None)
            return {'success': True, 'message': f"{phone} has been removed."}
        except ValueError as e:
            return {'success': False, 'error': str(e)}

    else:
        logger.warning(f"Unhandled step-up action type: {challenge.action_type}")
        return {'success': True, 'message': 'Action recorded. No automated execution for this type.'}


def _notify_step_up_completion(challenge, result):
    """Send the merchant a WhatsApp message confirming the step-up action completed."""
    from apps.identity.models import PhoneIdentity
    from apps.whatsapp.adapter import WhatsAppBusinessAdapter
    from apps.conversation.reply_composer import text_reply

    wa = WhatsAppBusinessAdapter()
    msg = text_reply(
        f"✅ *Security Action Confirmed*\n\n"
        f"{result.get('message', 'Your requested action has been completed.')}\n\n"
        f"This action was confirmed via your secure confirmation link."
    )
    recipients = PhoneIdentity.objects.filter(
        tenant=challenge.tenant, status='ACTIVE', role__in=['OWNER', 'ADMIN']
    )
    for pi in recipients:
        wa.send_raw_message(pi.phone_number, msg)
