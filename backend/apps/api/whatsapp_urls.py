"""
api/whatsapp_urls.py — WhatsApp webhook endpoint (§14.1)
GET  /api/v1/whatsapp/webhook/ — Meta verification challenge
POST /api/v1/whatsapp/webhook/ — Inbound messages (primary merchant entrypoint)
"""
from django.urls import path
from apps.api.whatsapp_views import WhatsAppWebhookView

urlpatterns = [
    path('', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
]
