"""
identity/tasks.py
=================
Celery tasks for expiring identity-related records.
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(name='identity.expire_step_up_challenges')
def expire_step_up_challenges():
    """Mark all PENDING StepUpChallenges past their expiry as EXPIRED."""
    from apps.identity.models import StepUpChallenge
    expired = StepUpChallenge.objects.filter(
        status='PENDING',
        expires_at__lt=timezone.now()
    )
    count = expired.update(status='EXPIRED')
    if count:
        logger.info(f"Expired {count} step-up challenge(s).")
    return count


@shared_task(name='identity.expire_magic_link_tokens')
def expire_magic_link_tokens():
    """No DB update needed — is_valid() checks expires_at at read time. Log for observability."""
    from apps.identity.models import MagicLinkToken
    expired_count = MagicLinkToken.objects.filter(
        expires_at__lt=timezone.now(),
        used_at__isnull=True
    ).count()
    logger.debug(f"Found {expired_count} expired unused magic-link token(s) (no action needed).")
    return expired_count
