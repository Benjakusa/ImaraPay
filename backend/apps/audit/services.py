from apps.audit.models import AuditLog

def log_action(action, tenant=None, user=None, details=None, ip_address=None):
    """
    Helper utility to record system audit logs.
    """
    try:
        AuditLog.objects.create(
            tenant=tenant,
            user=user if (user and user.is_authenticated) else None,
            action=action,
            details=details or {},
            ip_address=ip_address
        )
    except Exception as e:
        # Audit logging should never break core payment flows
        pass
