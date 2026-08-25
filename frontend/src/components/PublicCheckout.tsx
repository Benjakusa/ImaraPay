import React, { useState, useEffect } from 'react';
import {
  Smartphone, ShieldCheck, CheckCircle2, AlertCircle,
  Lock, Building2, RefreshCw
} from 'lucide-react';
import type { PublicCheckoutDetails } from '../types';
import { api } from '../services/api';

interface PublicCheckoutProps {
  publicToken: string;
  onBackToDashboard?: () => void;
}

export const PublicCheckout: React.FC<PublicCheckoutProps> = ({ publicToken, onBackToDashboard }) => {
  const [details, setDetails] = useState<PublicCheckoutDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Phone input state
  const [phone, setPhone] = useState('0712345678');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [checkoutReqId, setCheckoutReqId] = useState<string | null>(null);

  // STK Modal state
  const [showStkModal, setShowStkModal] = useState(false);
  const [stkState, setStkState] = useState<'PROMPT_SENT' | 'PIN_ENTERED' | 'SUCCESS' | 'FAILED'>('PROMPT_SENT');
  const [mpesaReceipt, setMpesaReceipt] = useState<string | null>(null);

  const fetchDetails = async () => {
    try {
      const data = await api.getCheckoutDetails(publicToken);
      setDetails(data);
      if (data.status === 'SUCCEEDED') {
        setStkState('SUCCESS');
      }
    } catch {
      setDetails({
        id: 'demo-pr',
        public_token: publicToken,
        merchant_name: 'Nairobi Electronics & Tech',
        amount_minor: 2500,
        currency: 'KES',
        reference: 'INV-10021',
        description: 'Website development & hosting deposit',
        customer_phone: '0712345678',
        status: 'CREATED',
        expires_at: new Date(Date.now() + 86400000).toISOString(),
        is_expired: false
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
    const interval = setInterval(() => {
      fetchDetails();
    }, 3000);
    return () => clearInterval(interval);
  }, [publicToken]);

  const handlePay = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const res = await api.initiateCheckoutPay(publicToken, phone);
      setCheckoutReqId(res.checkout_request_id);
      setShowStkModal(true);
      setStkState('PROMPT_SENT');
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Failed to initiate M-Pesa payment.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSimulatePinInput = async (scenario: 'SUCCESS' | 'WRONG_PIN' | 'USER_CANCELLED') => {
    if (!checkoutReqId) return;

    try {
      const res = await api.triggerSimulatorCallback(checkoutReqId, scenario);
      if (scenario === 'SUCCESS') {
        setStkState('SUCCESS');
        setMpesaReceipt(res.mpesa_receipt || 'QHK9182374');
      } else {
        setStkState('FAILED');
      }
      fetchDetails();
    } catch {
      setStkState('FAILED');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0F1D] flex items-center justify-center p-4">
        <div className="text-center space-y-3">
          <div className="w-12 h-12 border-4 border-emerald-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold text-slate-300">Loading Secure Checkout...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0F1D] text-slate-100 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background Glow Accents */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-0 right-0 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

      {onBackToDashboard && (
        <button
          onClick={onBackToDashboard}
          className="absolute top-6 left-6 text-xs bg-slate-900 border border-slate-800 text-slate-400 hover:text-white px-3 py-1.5 rounded-xl font-bold transition cursor-pointer"
        >
          ← Return to Dashboard
        </button>
      )}

      {/* Main Mobile-First Checkout Card */}
      <div className="w-full max-w-md glass-card-glow rounded-3xl overflow-hidden shadow-2xl border border-emerald-500/30">
        {/* Merchant Header */}
        <div className="p-6 bg-gradient-to-br from-emerald-950/80 via-slate-900 to-slate-950 border-b border-emerald-500/20 text-center relative">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 to-cyan-500 mx-auto flex items-center justify-center shadow-xl shadow-emerald-500/20 font-bold text-white text-2xl mb-3">
            <Building2 className="w-7 h-7" />
          </div>

          <div className="flex items-center justify-center gap-1.5 text-xs text-emerald-400 font-bold mb-1">
            <ShieldCheck className="w-4 h-4" />
            <span>Verified Merchant</span>
          </div>

          <h1 className="text-xl font-extrabold text-white">{details?.merchant_name}</h1>
          <p className="text-xs text-slate-400 font-mono mt-1">Ref: {details?.reference}</p>
        </div>

        {/* Payment Amount Display */}
        <div className="p-6 space-y-6">
          <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 text-center space-y-1">
            <span className="text-xs text-slate-400 font-medium">Total Amount Due</span>
            <div className="text-3xl font-black text-white tracking-tight">
              KES {details?.amount_minor.toLocaleString()}
            </div>
            {details?.description && (
              <p className="text-xs text-slate-300 pt-1 line-clamp-2">{details.description}</p>
            )}
          </div>

          {/* Status Alert if Succeeded */}
          {details?.status === 'SUCCEEDED' ? (
            <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
              <h3 className="text-lg font-bold text-white">Payment Completed!</h3>
              <p className="text-xs text-emerald-300">
                Authoritative M-Pesa receipt confirmed on server. Thank you!
              </p>
            </div>
          ) : (
            /* Form to Enter Phone */
            <form onSubmit={handlePay} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5 flex items-center justify-between">
                  <span>M-Pesa Registered Phone Number</span>
                  <span className="text-[10px] text-emerald-400">Safaricom Express</span>
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-3.5 text-slate-400 font-bold text-sm">🇰🇪</span>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    required
                    placeholder="0712 345 678"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-12 pr-4 py-3 text-white focus:outline-none focus:border-emerald-500 text-base font-bold tracking-wide"
                  />
                </div>
                <p className="text-[11px] text-slate-400 mt-1">An STK Push prompt will be sent directly to this phone.</p>
              </div>

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs font-semibold">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting || details?.is_expired}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white font-extrabold text-sm shadow-xl shadow-emerald-500/25 transition active:scale-98 flex items-center justify-center gap-2 cursor-pointer"
              >
                {isSubmitting ? (
                  <RefreshCw className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    <Lock className="w-4 h-4" />
                    <span>PAY KES {details?.amount_minor.toLocaleString()} WITH M-PESA</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* Guarantee Footer */}
          <div className="pt-4 border-t border-slate-800 text-center text-[11px] text-slate-400 space-y-1">
            <div className="flex items-center justify-center gap-1 text-slate-300 font-semibold">
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              <span>Imara Pay Encrypted Infrastructure</span>
            </div>
            <p>No PINs or card credentials are stored. Direct Safaricom Daraja STK rail.</p>
          </div>
        </div>
      </div>

      {/* Interactive STK Push Modal Simulator */}
      {showStkModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-card-glow max-w-sm w-full rounded-3xl p-6 space-y-5 text-center border border-emerald-500/40 shadow-2xl">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center animate-pulse">
              <Smartphone className="w-8 h-8" />
            </div>

            {stkState === 'PROMPT_SENT' && (
              <div className="space-y-3">
                <h3 className="text-xl font-extrabold text-white">STK Push Sent!</h3>
                <p className="text-xs text-slate-300">
                  Please check phone <strong className="text-emerald-400">{phone}</strong> and enter your M-Pesa PIN on your phone.
                </p>

                {/* Simulated Phone Buttons for testing */}
                <div className="pt-3 p-4 bg-slate-900/90 rounded-2xl border border-slate-800 space-y-2 text-xs">
                  <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Simulator Controls (Test Phone PIN Input):</p>
                  <button
                    onClick={() => handleSimulatePinInput('SUCCESS')}
                    className="w-full py-2.5 rounded-xl bg-emerald-500 text-slate-950 font-bold hover:bg-emerald-400 transition cursor-pointer"
                  >
                    🔑 Enter Correct PIN (Approve)
                  </button>
                  <button
                    onClick={() => handleSimulatePinInput('WRONG_PIN')}
                    className="w-full py-2 rounded-xl bg-slate-800 text-red-400 font-semibold hover:bg-slate-700 transition cursor-pointer"
                  >
                    Wrong PIN
                  </button>
                  <button
                    onClick={() => handleSimulatePinInput('USER_CANCELLED')}
                    className="w-full py-2 rounded-xl bg-slate-800 text-slate-400 font-semibold hover:bg-slate-700 transition cursor-pointer"
                  >
                    Cancel Prompt
                  </button>
                </div>
              </div>
            )}

            {stkState === 'SUCCESS' && (
              <div className="space-y-3">
                <CheckCircle2 className="w-16 h-16 text-emerald-400 mx-auto" />
                <h3 className="text-2xl font-extrabold text-white">Payment Successful!</h3>
                <p className="text-xs text-slate-300">
                  M-Pesa Receipt: <strong className="text-emerald-400 font-mono text-sm">{mpesaReceipt || 'QHK9182374'}</strong>
                </p>
                <p className="text-[11px] text-slate-400">Confirmation WhatsApp message has been dispatched.</p>
                <button
                  onClick={() => setShowStkModal(false)}
                  className="w-full py-3 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs transition cursor-pointer"
                >
                  Done
                </button>
              </div>
            )}

            {stkState === 'FAILED' && (
              <div className="space-y-3">
                <AlertCircle className="w-16 h-16 text-red-400 mx-auto" />
                <h3 className="text-xl font-bold text-white">Payment Unsuccessful</h3>
                <p className="text-xs text-red-300">Transaction was cancelled or invalid PIN entered.</p>
                <button
                  onClick={() => setShowStkModal(false)}
                  className="w-full py-3 rounded-xl bg-slate-800 text-white font-bold text-xs transition cursor-pointer"
                >
                  Try Again
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
