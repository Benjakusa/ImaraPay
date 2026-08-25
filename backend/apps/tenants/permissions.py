from rest_framework.permissions import BasePermission

class IsTenantMember(BasePermission):
    """
    Allows access only to authenticated users with a valid associated tenant.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request, 'tenant', None))
