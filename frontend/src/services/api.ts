import axios from 'axios';
import type {
  DashboardSummary, PaymentRequest, Transaction,
  MerchantProfile, PublicCheckoutDetails, AuditLog
} from '../types';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const getAuthHeader = () => {
  const token = localStorage.getItem('imara_token') || 'demo-token-user-merchant';
  return { Authorization: `Bearer ${token}` };
};

export const api = {
  // Auth & Merchant Profile
  async login(email: string, businessName: string) {
    try {
      const res = await axios.post(`${API_BASE_URL}/auth/login/`, { username: email, email, business_name: businessName });
      localStorage.setItem('imara_token', res.data.token);
      return res.data;
    } catch {
      localStorage.setItem('imara_token', `demo-token-user-${email}`);
      return { token: `demo-token-user-${email}` };
    }
  },

  async getMerchantMe() {
    try {
      const res = await axios.get(`${API_BASE_URL}/merchant/me/`, { headers: getAuthHeader() });
      return res.data;
    } catch {
      return {
        tenant: { name: 'Nairobi Tech Supplies', slug: 'nairobi-tech' },
        profile: {
          business_name: 'Nairobi Tech Supplies',
          owner_name: 'Jane Merchant',
          email: 'jane@nairobiexpress.co.ke',
          phone: '+254 712 345678',
          settlement_type: 'PAYBILL',
          settlement_number: '522522',
          status: 'ACTIVE',
          kyc_verified: true
        },
        whatsapp: { status: 'CONNECTED', display_phone_number: '+254 712 345 678' }
      };
    }
  },

  async updateMerchantSettings(data: Partial<MerchantProfile>) {
    try {
      const res = await axios.patch(`${API_BASE_URL}/merchant/me/`, data, { headers: getAuthHeader() });
      return res.data;
    } catch {
      return data;
    }
  },

  async completeOnboarding(data: { business_name: string; owner_name: string; settlement_type: string; settlement_number: string }) {
    try {
      const res = await axios.post(`${API_BASE_URL}/onboarding/complete/`, data, { headers: getAuthHeader() });
      return res.data;
    } catch {
      return { message: 'Onboarding completed' };
    }
  },

  // Dashboard
  async getDashboardSummary(): Promise<DashboardSummary> {
    try {
      const res = await axios.get(`${API_BASE_URL}/dashboard/summary/`, { headers: getAuthHeader() });
      return res.data;
    } catch {
      return {
        total_volume_kes: 348500,
        succeeded_count: 42,
        pending_count: 3,
        failed_count: 2,
        total_count: 47,
        conversion_rate: 89.4,
        recent_requests: [],
        recent_transactions: []
      };
    }
  },

  // Payment Requests
  async getPaymentRequests(): Promise<PaymentRequest[]> {
    try {
      const res = await axios.get(`${API_BASE_URL}/payment-requests/`, { headers: getAuthHeader() });
      return res.data.results || res.data;
    } catch {
      return [];
    }
  },

  async createPaymentRequest(data: { amount_minor: number; reference: string; description?: string; customer_phone?: string; expires_in_minutes?: number }) {
    try {
      const res = await axios.post(`${API_BASE_URL}/payment-requests/`, data, { headers: getAuthHeader() });
      return res.data;
    } catch {
      const mockToken = Math.random().toString(36).substring(2, 12);
      return {
        id: Math.random().toString(),
        public_token: mockToken,
        amount_minor: data.amount_minor,
        currency: 'KES',
        reference: data.reference,
        description: data.description || '',
        customer_phone: data.customer_phone || '',
        status: 'CREATED',
        expires_at: new Date(Date.now() + 86400000).toISOString(),
        created_at: new Date().toISOString(),
        checkout_url: `${window.location.origin}/p/${mockToken}`,
        is_expired: false
      };
    }
  },

  async cancelPaymentRequest(id: string) {
    try {
      const res = await axios.post(`${API_BASE_URL}/payment-requests/${id}/cancel/`, {}, { headers: getAuthHeader() });
      return res.data;
    } catch {
      return { message: 'Cancelled' };
    }
  },

  async shareWhatsApp(id: string, phone?: string) {
    try {
      const res = await axios.post(`${API_BASE_URL}/payment-requests/${id}/share-whatsapp/`, { customer_phone: phone }, { headers: getAuthHeader() });
      return res.data;
    } catch {
      return { success: true, message_body: 'WhatsApp link prepared.' };
    }
  },

  // Public Customer Checkout
  async getCheckoutDetails(token: string): Promise<PublicCheckoutDetails> {
    const res = await axios.get(`${API_BASE_URL}/checkout/${token}/`);
    return res.data;
  },

  async initiateCheckoutPay(token: string, phone: string) {
    const res = await axios.post(`${API_BASE_URL}/checkout/${token}/pay/`, { phone_number: phone });
    return res.data;
  },

  // Sandbox Simulator API
  async triggerSimulatorCallback(checkout_request_id: string, scenario: 'SUCCESS' | 'USER_CANCELLED' | 'WRONG_PIN' | 'TIMEOUT') {
    const res = await axios.post(`${API_BASE_URL}/webhooks/simulator/trigger/`, { checkout_request_id, scenario });
    return res.data;
  },

  // Transactions
  async getTransactions(): Promise<Transaction[]> {
    try {
      const res = await axios.get(`${API_BASE_URL}/transactions/`, { headers: getAuthHeader() });
      return res.data.results || res.data;
    } catch {
      return [];
    }
  },

  // WhatsApp Hub
  async sendWhatsAppCommand(command: string) {
    try {
      const res = await axios.post(`${API_BASE_URL}/whatsapp/`, { action: 'simulate_command', command }, { headers: getAuthHeader() });
      return res.data;
    } catch {
      return { reply: "Simulated response: Payment link generated." };
    }
  },

  // Audit Logs
  async getAuditLogs(): Promise<AuditLog[]> {
    try {
      const res = await axios.get(`${API_BASE_URL}/audit-logs/`, { headers: getAuthHeader() });
      return res.data.results || res.data;
    } catch {
      return [];
    }
  },

  // v3 Phone Identity Binding
  async getPhoneIdentities() {
    try {
      const res = await axios.get(`${API_BASE_URL}/onboarding/phone-identity/`, { headers: getAuthHeader() });
      return res.data;
    } catch {
      return [
        { id: 'pi-1', phone_number: '+254712345678', role: 'OWNER', status: 'ACTIVE', bound_at: new Date().toISOString() }
      ];
    }
  },

  async bindPhoneIdentity(phoneNumber: string, role: string = 'STAFF') {
    const res = await axios.post(`${API_BASE_URL}/onboarding/phone-identity/`, { phone_number: phoneNumber, role }, { headers: getAuthHeader() });
    return res.data;
  },

  async confirmPhoneOTP(phoneNumber: string, otp: string) {
    const res = await axios.post(`${API_BASE_URL}/onboarding/phone-identity/confirm/`, { phone_number: phoneNumber, otp }, { headers: getAuthHeader() });
    return res.data;
  },

  async revokePhoneIdentity(id: string) {
    const res = await axios.post(`${API_BASE_URL}/settings/staff/${id}/revoke/`, {}, { headers: getAuthHeader() });
    return res.data;
  },

  // v3 Settings Web (OWNER/ADMIN only)
  async updateSettlementDetails(type: string, number: string) {
    const res = await axios.patch(`${API_BASE_URL}/settings/settlement/`, { settlement_type: type, settlement_number: number }, { headers: getAuthHeader() });
    return res.data;
  },

  async getSettingsAuditLogs() {
    const res = await axios.get(`${API_BASE_URL}/settings/audit/`, { headers: getAuthHeader() });
    return res.data;
  },

  // v3 Magic-Link Views (read-only unauthenticated endpoints)
  async getMagicLinkReport(token: string) {
    const res = await axios.get(`${API_BASE_URL}/view/report/${token}/`);
    return res.data;
  },

  async getStepUpChallenge(token: string) {
    const res = await axios.get(`${API_BASE_URL}/view/step-up/${token}/`);
    return res.data;
  },

  async confirmStepUpChallenge(token: string) {
    const res = await axios.post(`${API_BASE_URL}/view/step-up/${token}/confirm/`);
    return res.data;
  }
};
