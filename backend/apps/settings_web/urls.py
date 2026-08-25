from django.urls import path
from apps.settings_web.views import (
    StaffPhoneListView, StaffPhoneConfirmView, StaffPhoneRevokeView,
    SettlementDetailsView, FullAuditLogView,
)

urlpatterns = [
    path('staff/', StaffPhoneListView.as_view(), name='settings-staff-list'),
    path('staff/confirm/', StaffPhoneConfirmView.as_view(), name='settings-staff-confirm'),
    path('staff/<uuid:phone_identity_id>/revoke/', StaffPhoneRevokeView.as_view(), name='settings-staff-revoke'),
    path('settlement/', SettlementDetailsView.as_view(), name='settings-settlement'),
    path('audit/', FullAuditLogView.as_view(), name='settings-audit'),
]
