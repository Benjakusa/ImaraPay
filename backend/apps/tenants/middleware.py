from apps.tenants.models import TenantUser, Tenant

class TenantMiddleware:
    """
    Middleware to resolve and attach current tenant to request.tenant.
    Resolution order:
    1. Header: X-Tenant-ID
    2. User default active tenant
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None

        if hasattr(request, 'user') and request.user.is_authenticated:
            tenant_id_header = request.headers.get('X-Tenant-ID')
            if tenant_id_header:
                try:
                    membership = TenantUser.objects.select_related('tenant').get(
                        user=request.user, tenant_id=tenant_id_header
                    )
                    request.tenant = membership.tenant
                except (TenantUser.DoesNotExist, ValueError):
                    pass

            if not request.tenant:
                first_membership = TenantUser.objects.select_related('tenant').filter(
                    user=request.user
                ).first()
                if first_membership:
                    request.tenant = first_membership.tenant

        response = self.get_response(request)
        return response
