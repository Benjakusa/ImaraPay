export type PaymentStatus = 'CREATED' | 'PENDING' | 'SUCCEEDED' | 'FAILED' | 'EXPIRED' | 'CANCELLED';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  is_active: boolean;
}

export interface MerchantProfile {
  id: string;
  business_name: string;
  owner_name: string;
  email: string;
  phone: string;
  settlement_type: 'PAYBILL' | 'TILL' | 'BANK';
  settlement_number: string;
  settlement_bank_name?: string;
  status: 'ACTIVE' | 'PENDING_VERIFICATION' | 'SUSPENDED';
  kyc_verified: boolean;
  created_at: string;
}

export interface PaymentProviderAccount {
  id: string;
  provider_name: string;
  account_reference: string;
  is_active: boolean;
  created_at: string;
}

export interface WhatsAppAccount {
  id: string;
  phone_number_id: string;
  display_phone_number: string;
  waba_id: string;
  status: 'CONNECTED' | 'PENDING' | 'DISCONNECTED';
  auto_send_receipts: boolean;
  connected_at: string;
}

export interface PaymentRequest {
  id: string;
  public_token: string;
  amount_minor: number;
  currency: string;
  reference: string;
  description: string;
  customer_phone: string;
  status: PaymentStatus;
  expires_at: string;
  created_at: string;
  paid_at?: string;
  checkout_url: string;
  is_expired: boolean;
}

export interface Transaction {
  id: string;
  payment_reference: string;
  description: string;
  amount_minor: number;
  currency: string;
  mpesa_receipt_number: string;
  customer_phone: string;
  status: 'SUCCEEDED' | 'REFUNDED';
  paid_at: string;
}

export interface DashboardSummary {
  total_volume_kes: number;
  succeeded_count: number;
  pending_count: number;
  failed_count: number;
  total_count: number;
  conversion_rate: number;
  recent_requests: PaymentRequest[];
  recent_transactions: Transaction[];
}

export interface PublicCheckoutDetails {
  id: string;
  public_token: string;
  merchant_name: string;
  amount_minor: number;
  currency: string;
  reference: string;
  description: string;
  customer_phone: string;
  status: PaymentStatus;
  expires_at: string;
  is_expired: boolean;
  paid_at?: string;
}

export interface AuditLog {
  id: string;
  action: string;
  user_email: string;
  ip_address?: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface PhoneIdentity {
  id: string;
  phone_number: string;
  role: 'OWNER' | 'ADMIN' | 'STAFF';
  status: 'PENDING_VERIFICATION' | 'ACTIVE' | 'REVOKED';
  bound_at?: string;
}

export interface StepUpChallenge {
  id: string;
  action_type: 'REMOVE_STAFF_NUMBER' | 'CHANGE_SETTLEMENT_ACCOUNT' | 'REFUND' | 'CANCEL_INFLIGHT' | 'VIEW_AUDIT_LOG';
  action_label: string;
  action_payload: Record<string, any>;
  tenant_name: string;
  expires_at: string;
  expires_in_seconds: number;
}

export interface MagicLinkToken {
  id: string;
  purpose: 'REPORT_VIEW' | 'SETTINGS_VIEW' | 'STEP_UP_CONFIRM' | 'PHONE_BIND_CONFIRM';
  scope: Record<string, any>;
  expires_at: string;
}
