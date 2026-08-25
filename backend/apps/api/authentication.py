from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

User = get_user_model()

class BearerTokenAuthentication(BaseAuthentication):
    """
    Custom Bearer authentication for simple auth in dev/demo environment.
    Accepts 'Authorization: Bearer demo-token-user-<username>' or 'Authorization: Bearer <username>'.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        token = parts[1]
        username = token.replace('demo-token-user-', '')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, email=f"{username}@imarapay.example", password="demo-password-2026")

        return (user, None)
