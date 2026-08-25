"""
api/magic_link_urls.py — Magic-link and step-up views (§12.2, §7.4, §14.1)
GET  /api/v1/view/report/<token>/          — read-only report view
GET  /api/v1/view/step-up/<token>/         — step-up confirmation display
POST /api/v1/view/step-up/<token>/confirm/ — execute the step-up action
"""
from django.urls import path
from apps.api.magic_link_views import ReportView, StepUpView, StepUpConfirmView

urlpatterns = [
    path('report/<str:token>/', ReportView.as_view(), name='magic-link-report'),
    path('step-up/<str:token>/', StepUpView.as_view(), name='step-up-view'),
    path('step-up/<str:token>/confirm/', StepUpConfirmView.as_view(), name='step-up-confirm'),
]
