from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

from apps.tenants.models import Tenant
from apps.identity.models import PhoneIdentity, StepUpChallenge, MagicLinkToken
from apps.identity.otp import hash_otp
from apps.identity.services import (
    initiate_phone_binding, confirm_phone_binding, revoke_phone_identity,
    list_phone_identities, issue_step_up_challenge, confirm_step_up_challenge,
    issue_magic_link, consume_magic_link, normalise_phone
)

User = get_user_model()


class IdentityServicesTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Imara Tech", slug="imara-tech")
        self.user = User.objects.create_user(username="owner", email="owner@imara.example", password="password")
        self.phone = "+254712345678"

    def test_normalise_phone(self):
        self.assertEqual(normalise_phone("0712345678"), "+254712345678")
        self.assertEqual(normalise_phone("254712345678"), "+254712345678")
        self.assertEqual(normalise_phone("+254712345678"), "+254712345678")
        self.assertEqual(normalise_phone("  0712-345 678 "), "+254712345678")

    def test_phone_binding_flow(self):
        # 1. Initiate binding
        pi, otp = initiate_phone_binding(self.tenant, self.phone, 'OWNER', self.user)
        self.assertEqual(pi.phone_number, self.phone)
        self.assertEqual(pi.status, 'PENDING_VERIFICATION')
        self.assertEqual(len(otp), 6)
        self.assertTrue(pi.otp_sent_at is not None)

        # 2. Try confirming with invalid OTP
        with self.assertRaises(ValueError):
            confirm_phone_binding(self.tenant, self.phone, "000000", self.user)

        # 3. Confirm with correct OTP
        pi = confirm_phone_binding(self.tenant, self.phone, otp, self.user)
        self.assertEqual(pi.status, 'ACTIVE')
        self.assertTrue(pi.bound_at is not None)

        # 4. List bound phone numbers
        identities = list_phone_identities(self.tenant)
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0].phone_number, self.phone)

    def test_phone_binding_prevent_duplicates(self):
        # Bind one number to active
        pi, otp = initiate_phone_binding(self.tenant, self.phone, 'OWNER', self.user)
        confirm_phone_binding(self.tenant, self.phone, otp, self.user)

        # Try binding same number to another tenant should raise ValueError
        other_tenant = Tenant.objects.create(name="Other Tenant", slug="other")
        with self.assertRaises(ValueError):
            initiate_phone_binding(other_tenant, self.phone, 'STAFF', self.user)

    def test_phone_revocation(self):
        pi, otp = initiate_phone_binding(self.tenant, self.phone, 'OWNER', self.user)
        confirm_phone_binding(self.tenant, self.phone, otp, self.user)

        # Revoke
        pi = revoke_phone_identity(self.tenant, self.phone, self.user)
        self.assertEqual(pi.status, 'REVOKED')
        self.assertTrue(pi.revoked_at is not None)

        # Revoked number should not be returned in list
        identities = list_phone_identities(self.tenant)
        self.assertEqual(len(identities), 0)

    def test_step_up_challenge(self):
        pi, otp = initiate_phone_binding(self.tenant, self.phone, 'OWNER', self.user)
        pi = confirm_phone_binding(self.tenant, self.phone, otp, self.user)

        # Issue challenge
        payload = {'phone_number': '+254799999999'}
        challenge, raw_token = issue_step_up_challenge(pi, 'REMOVE_STAFF_NUMBER', payload)

        self.assertEqual(challenge.tenant, self.tenant)
        self.assertEqual(challenge.status, 'PENDING')
        self.assertEqual(challenge.action_type, 'REMOVE_STAFF_NUMBER')
        self.assertEqual(challenge.action_payload, payload)
        self.assertTrue(challenge.is_valid())

        # Confirm challenge
        confirmed = confirm_step_up_challenge(raw_token, self.tenant)
        self.assertEqual(confirmed.status, 'CONFIRMED')
        self.assertTrue(confirmed.confirmed_at is not None)

        # Challenge should no longer be valid (is_valid checks status == 'PENDING')
        self.assertFalse(confirmed.is_valid())

    def test_magic_link_token(self):
        scope = {'transactions_from': '2026-08-01'}
        ml, raw_token = issue_magic_link(self.tenant, 'REPORT_VIEW', scope, single_use=True)

        self.assertEqual(ml.tenant, self.tenant)
        self.assertEqual(ml.purpose, 'REPORT_VIEW')
        self.assertEqual(ml.scope, scope)
        self.assertTrue(ml.is_valid())

        # Consume token
        consumed = consume_magic_link(raw_token, self.tenant)
        self.assertIsNotNone(consumed)
        self.assertTrue(consumed.used_at is not None)

        # Try consuming again — single use should be invalid now
        self.assertFalse(consumed.is_valid())
        second_consume = consume_magic_link(raw_token, self.tenant)
        self.assertIsNone(second_consume)
