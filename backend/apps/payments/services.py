"""
payments/services.py
====================
Internal service layer for payment operations (§4.1).
Both WhatsApp (conversation) and web (api views) call these functions.
There is ONE implementation of "create a payment request" — never two.
"""
import datetime
import logging
import secrets
from django.utils import timezone
from django.db.models import Sum, Count, Q

from apps.payments.models import PaymentRequest, Transaction
from apps.audit.services import log_action

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY_HOURS = 24


def create_payment_request(
    tenant,
    amount_minor: int,
    reference: str = None,
    description: str = '',
    expires_in_hours: int = DEFAULT_EXPIRY_HOURS,
    initiated_by_user=None,
    initiated_by_phone_identity=None,
) -> PaymentRequest:
    """
    Create a PaymentRequest.
    Called identically from WhatsApp (conversation/handlers.py) and web (api/views.py).
    amount_minor is always a positive integer (KES shillings for MVP, i.e. not sub-units).
    """
    if amount_minor <= 0:
        raise ValueError(f"Amount must be positive, got {amount_minor}.")

    if not reference:
        reference = f"WA-{secrets.token_hex(3).upper()}"

    provider_acc = tenant.provider_accounts.filter(is_active=True).first()
    expires_at = timezone.now() + datetime.timedelta(hours=expires_in_hours)

    pr = PaymentRequest.objects.create(
        tenant=tenant,
        amount_minor=amount_minor,
        currency='KES',
        reference=reference,
        description=description,
        expires_at=expires_at,
        status='CREATED',
        provider_account=provider_acc,
    )

    actor_details = {}
    if initiated_by_phone_identity:
        actor_details['via'] = 'whatsapp'
        actor_details['phone'] = initiated_by_phone_identity.phone_number
    elif initiated_by_user:
        actor_details['via'] = 'web'

    log_action(
        'CREATE_PAYMENT_REQUEST',
        tenant=tenant,
        user=initiated_by_user,
        details={'amount': amount_minor, 'ref': reference, **actor_details}
    )
    return pr


def cancel_payment_request(
    tenant,
    payment_request_id: str,
    initiated_by_user=None,
    initiated_by_phone_identity=None,
) -> PaymentRequest:
    """
    Cancel a CREATED PaymentRequest. PENDING cancellation requires step-up
    and must be routed through the step-up confirmation flow — see handlers.py.
    Raises ValueError if cancellation is not allowed.
    """
    try:
        pr = PaymentRequest.objects.get(id=payment_request_id, tenant=tenant)
    except PaymentRequest.DoesNotExist:
        raise ValueError(f"Payment request {payment_request_id} not found.")

    if pr.status in ('SUCCEEDED', 'CANCELLED', 'EXPIRED'):
        raise ValueError(f"Cannot cancel request in status {pr.status}.")

    if pr.status == 'PENDING':
        raise ValueError(
            "Cancelling an in-flight (PENDING) request requires step-up confirmation. "
            "This should not be called directly — use the step-up flow."
        )

    pr.status = 'CANCELLED'
    pr.save(update_fields=['status'])

    log_action(
        'CANCEL_PAYMENT_REQUEST',
        tenant=tenant,
        user=initiated_by_user,
        details={
            'payment_request_id': str(pr.id),
            'via': 'whatsapp' if initiated_by_phone_identity else 'web',
        }
    )
    return pr


def cancel_payment_request_step_up_confirmed(
    tenant,
    payment_request_id: str,
    step_up_challenge,
) -> PaymentRequest:
    """
    Cancel a PENDING PaymentRequest after step-up confirmation.
    Only called from the step-up confirmation view (§7.4).
    """
    try:
        pr = PaymentRequest.objects.get(id=payment_request_id, tenant=tenant)
    except PaymentRequest.DoesNotExist:
        raise ValueError(f"Payment request {payment_request_id} not found.")

    if pr.status in ('SUCCEEDED', 'CANCELLED', 'EXPIRED'):
        raise ValueError(f"Cannot cancel — request is already {pr.status}.")

    pr.status = 'CANCELLED'
    pr.save(update_fields=['status'])

    log_action(
        'CANCEL_PAYMENT_REQUEST_STEP_UP',
        tenant=tenant,
        details={
            'payment_request_id': str(pr.id),
            'step_up_challenge_id': str(step_up_challenge.id),
        }
    )
    return pr


def get_request_by_reference(tenant, reference: str) -> PaymentRequest:
    """Fetch a PaymentRequest by reference within a tenant. Returns None if not found."""
    return PaymentRequest.objects.filter(tenant=tenant, reference=reference).first()


def get_today_summary(tenant) -> dict:
    """
    Today's totals for the 'today' WhatsApp command.
    Returns succeeded/pending/failed counts and amounts.
    """
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    qs = PaymentRequest.objects.filter(tenant=tenant, created_at__gte=today_start)

    succeeded = qs.filter(status='SUCCEEDED').aggregate(
        count=Count('id'), total=Sum('amount_minor')
    )
    pending = qs.filter(status='PENDING').aggregate(
        count=Count('id'), total=Sum('amount_minor')
    )
    failed = qs.filter(status__in=['FAILED', 'EXPIRED']).aggregate(count=Count('id'))

    return {
        'succeeded_count': succeeded['count'] or 0,
        'succeeded_amount': succeeded['total'] or 0,
        'pending_count': pending['count'] or 0,
        'pending_amount': pending['total'] or 0,
        'failed_count': failed['count'] or 0,
    }


def get_recent_transactions(tenant, n: int = 5) -> list:
    """Last N completed transactions for the 'last N' WhatsApp command."""
    from apps.payments.models import Transaction
    n = min(n, 10)  # cap per spec
    txs = Transaction.objects.filter(tenant=tenant).order_by('-paid_at')[:n]
    return [
        {
            'id': str(t.id),
            'amount_minor': t.amount_minor,
            'reference': t.payment_request.reference,
            'mpesa_receipt': t.mpesa_receipt_number,
            'paid_at': t.paid_at.strftime('%d %b %H:%M'),
            'customer_phone': t.customer_phone,
        }
        for t in txs
    ]
