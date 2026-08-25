"""
api/phone_identity_urls.py — Phone identity binding (§7.1, §14.1)
POST /api/v1/onboarding/phone-identity/         — initiate binding
POST /api/v1/onboarding/phone-identity/confirm/ — confirm OTP
"""
from django.urls import path
from apps.api.phone_identity_views import PhoneIdentityBindView, PhoneIdentityConfirmView

urlpatterns = [
    path('', PhoneIdentityBindView.as_view(), name='phone-identity-bind'),
    path('confirm/', PhoneIdentityConfirmView.as_view(), name='phone-identity-confirm'),
]
