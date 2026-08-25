import React, { useState, useEffect } from 'react';
import { Building, Key, Save, Check, UserCheck, Trash2, ShieldAlert, CheckCircle2 } from 'lucide-react';
import type { MerchantProfile, PaymentProviderAccount, PhoneIdentity } from '../types';
import { api } from '../services/api';

interface SettingsViewProps {
  profile: MerchantProfile | null;
  provider: PaymentProviderAccount | null;
  onRefresh: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ profile, provider, onRefresh }) => {
  const businessName = profile?.business_name || 'Nairobi Electronics & Tech';
  const ownerName = profile?.owner_name || 'Jane Wanjiru';
  const [settlementType, setSettlementType] = useState<string>(profile?.settlement_type || 'PAYBILL');
  const [settlementNumber, setSettlementNumber] = useState(profile?.settlement_number || '522522');
  const [isSaved, setIsSaved] = useState(false);

  // Staff Phone Identities State
  const [identities, setIdentities] = useState<PhoneIdentity[]>([]);
  const [newPhone, setNewPhone] = useState('');
  const [newRole, setNewRole] = useState<'ADMIN' | 'STAFF'>('STAFF');
  const [otpVerifyPhone, setOtpVerifyPhone] = useState<string | null>(null);
  const [otpInput, setOtpInput] = useState('');
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [staffError, setStaffError] = useState('');
  const [staffSuccess, setStaffSuccess] = useState('');

  const loadIdentities = async () => {
    try {
      const data = await api.getPhoneIdentities();
      setIdentities(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadIdentities();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.updateSettlementDetails(settlementType, settlementNumber);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2500);
    onRefresh();
  };

  const handleAddPhone = async (e: React.FormEvent) => {
    e.preventDefault();
    setStaffError('');
    setStaffSuccess('');
    setDevOtp(null);

    if (!newPhone.trim()) {
      setStaffError('Please enter a phone number');
      return;
    }

    try {
      const res = await api.bindPhoneIdentity(newPhone, newRole);
      setOtpVerifyPhone(newPhone);
      setStaffSuccess(res.message || 'OTP sent successfully!');
      if (res.dev_otp) {
        setDevOtp(res.dev_otp);
      }
    } catch (err: any) {
      setStaffError(err.response?.data?.error || 'Failed to bind phone number');
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setStaffError('');
    setStaffSuccess('');

    if (!otpVerifyPhone || !otpInput) return;

    try {
      await api.confirmPhoneOTP(otpVerifyPhone, otpInput);
      setStaffSuccess(`Successfully verified and linked ${otpVerifyPhone}!`);
      setOtpVerifyPhone(null);
      setOtpInput('');
      setNewPhone('');
      setDevOtp(null);
      loadIdentities();
    } catch (err: any) {
      setStaffError(err.response?.data?.error || 'Invalid or expired OTP');
    }
  };

  const handleRevokePhone = async (id: string) => {
    setStaffError('');
    setStaffSuccess('');

    if (!confirm('Are you sure you want to revoke this phone identity?')) return;

    try {
      await api.revokePhoneIdentity(id);
      setStaffSuccess('Phone number access revoked.');
      loadIdentities();
    } catch (err: any) {
      setStaffError(err.response?.data?.error || 'Failed to revoke phone number');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white">Merchant Settings & Credentials</h2>
        <p className="text-xs text-slate-400">Configure business identity, M-Pesa destination, and authorized staff numbers</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings Form */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={handleSave} className="glass-card p-6 rounded-2xl space-y-4 border border-slate-800">
            <h3 className="text-sm font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
              <Building className="w-4 h-4 text-emerald-400" />
              <span>Business Profile & Settlement Account</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Business Name</label>
                <input
                  type="text"
                  disabled
                  value={businessName}
                  className="w-full bg-slate-950 border border-slate-850 rounded-xl px-4 py-2.5 text-slate-400 text-xs focus:outline-none cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Owner Name</label>
                <input
                  type="text"
                  disabled
                  value={ownerName}
                  className="w-full bg-slate-950 border border-slate-850 rounded-xl px-4 py-2.5 text-slate-400 text-xs focus:outline-none cursor-not-allowed"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Settlement Type</label>
                <select
                  value={settlementType}
                  onChange={(e) => setSettlementType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-xs focus:outline-none focus:border-emerald-500"
                >
                  <option value="PAYBILL">M-Pesa PayBill</option>
                  <option value="TILL">M-Pesa Buy Goods Till</option>
                  <option value="BANK">Bank Account</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">PayBill / Till / Bank Account No</label>
                <input
                  type="text"
                  value={settlementNumber}
                  onChange={(e) => setSettlementNumber(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-xs font-mono focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              {isSaved ? (
                <span className="text-xs text-emerald-400 font-bold flex items-center gap-1">
                  <Check className="w-4 h-4" /> Settlement Saved!
                </span>
              ) : <span></span>}

              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 text-white font-bold text-xs transition cursor-pointer flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                <span>Save Changes</span>
              </button>
            </div>
          </form>

          {/* Linked Staff Numbers */}
          <div className="glass-card p-6 rounded-2xl space-y-4 border border-slate-800">
            <h3 className="text-sm font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-emerald-400" />
              <span>Bound Phone Identities (Staff access)</span>
            </h3>

            <div className="space-y-3">
              {identities.map((id) => (
                <div key={id.id} className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-white">{id.phone_number}</span>
                    <span className="text-[9px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700">
                      {id.role}
                    </span>
                    {id.status === 'ACTIVE' && (
                      <span className="text-[9px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full">Active</span>
                    )}
                  </div>

                  {id.role !== 'OWNER' && (
                    <button
                      onClick={() => handleRevokePhone(id.id)}
                      className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Add Staff / Security Details */}
        <div className="space-y-4">
          <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Key className="w-4 h-4 text-cyan-400" />
              <span>Link Staff Phone</span>
            </h3>
            <p className="text-xs text-slate-400">Add staff numbers to allow payment links generation from chat.</p>

            {staffError && (
              <div className="p-2.5 bg-red-500/10 border border-red-500/20 rounded-xl text-[11px] text-red-400 flex items-start gap-1">
                <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>{staffError}</span>
              </div>
            )}

            {staffSuccess && (
              <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-[11px] text-emerald-400 flex items-start gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <div>
                  <p>{staffSuccess}</p>
                  {devOtp && <p className="font-mono text-emerald-300">OTP: {devOtp}</p>}
                </div>
              </div>
            )}

            {!otpVerifyPhone ? (
              <form onSubmit={handleAddPhone} className="space-y-3">
                <input
                  type="text"
                  placeholder="e.g. +254712345678"
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as any)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="STAFF">Staff (Create requests)</option>
                  <option value="ADMIN">Admin (Create & totals)</option>
                </select>
                <button
                  type="submit"
                  className="w-full py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl text-xs transition cursor-pointer"
                >
                  Add Staff Number
                </button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOTP} className="space-y-2">
                <p className="text-[11px] text-slate-300">Confirm code sent to {otpVerifyPhone}:</p>
                <input
                  type="text"
                  placeholder="6-digit OTP"
                  value={otpInput}
                  onChange={(e) => setOtpInput(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono tracking-widest text-center focus:outline-none focus:border-cyan-500"
                />
                <button
                  type="submit"
                  className="w-full py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl text-xs transition cursor-pointer"
                >
                  Verify Code
                </button>
              </form>
            )}
          </div>

          <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Provider Rail:</span>
              <span className="font-bold text-emerald-400">{provider?.provider_name || 'MPESA_SANDBOX'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Account Ref:</span>
              <span className="font-mono text-slate-200">{provider?.account_reference || '522522'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
