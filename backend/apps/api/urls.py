from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.api.views import (
    RegisterView, LoginView, MerchantMeView, OnboardingCompleteView,
    PaymentRequestViewSet, PublicCheckoutView, TransactionViewSet,
    WebhookReceiverView, WebhookSimulatorView, WhatsAppView,
    DashboardSummaryView, AuditLogViewSet
)

router = DefaultRouter()
router.register(r'payment-requests', PaymentRequestViewSet, basename='payment-requests')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-logs')

urlpatterns = [
    # Auth & Onboarding
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('onboarding/complete/', OnboardingCompleteView.as_view(), name='onboarding-complete'),
    path('merchant/me/', MerchantMeView.as_view(), name='merchant-me'),

    # ── v3: WhatsApp Webhook (primary merchant entrypoint, §14.1) ──
    path('whatsapp/webhook/', include('apps.api.whatsapp_urls')),

    # ── v3: Phone Identity binding (§7.1) ──
    path('onboarding/phone-identity/', include('apps.api.phone_identity_urls')),

    # ── v3: Magic-link views (§12.2, §7.4) ──
    path('view/', include('apps.api.magic_link_urls')),

    # ── v3: Settings (§12.3) ──
    path('settings/', include('apps.settings_web.urls')),

    # Payment Request extra actions
    path('payment-requests/<uuid:pk>/cancel/', PaymentRequestViewSet.as_view({'post': 'cancel'}), name='payment-request-cancel'),
    path('payment-requests/<uuid:pk>/share-whatsapp/', PaymentRequestViewSet.as_view({'post': 'share_whatsapp'}), name='payment-request-share-whatsapp'),

    # Public Customer Checkout
    path('checkout/<str:public_token>/', PublicCheckoutView.as_view(), name='public-checkout-detail'),
    path('checkout/<str:public_token>/pay/', PublicCheckoutView.as_view(), name='public-checkout-pay'),

    # Webhooks & Sandbox Simulator
    path('webhooks/simulator/trigger/', WebhookSimulatorView.as_view(), name='webhook-simulator-trigger'),
    path('webhooks/<str:provider>/', WebhookReceiverView.as_view(), name='webhook-receiver'),

    # WhatsApp (legacy sim) & Dashboard
    path('whatsapp/', WhatsAppView.as_view(), name='whatsapp-actions'),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),

    # Router endpoints
    path('', include(router.urls)),
]
