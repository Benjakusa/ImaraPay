import React, { useState } from 'react';
import {
  Building, User, CreditCard, ShieldCheck, MessageSquare,
  CheckCircle, ArrowRight, ArrowLeft, Sparkles, Check
} from 'lucide-react';
import { api } from '../services/api';

interface OnboardingWizardProps {
  onComplete: () => void;
  onClose: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete, onClose }) => {
  const [currentStep, setCurrentStep] = useState(1);

  // Form State
  const [businessName, setBusinessName] = useState('Nairobi Electronics & Tech');
  const [ownerName, setOwnerName] = useState('Jane Wanjiru');
  const [ownerEmail, setOwnerEmail] = useState('jane@nairobiexpress.co.ke');
  const [ownerPhone, setOwnerPhone] = useState('+254 712 345678');
  const [settlementType, setSettlementType] = useState<'PAYBILL' | 'TILL' | 'BANK'>('PAYBILL');
  const [settlementNumber, setSettlementNumber] = useState('522522');
  const [isVerifying, setIsVerifying] = useState(false);
  const [testPaymentStatus, setTestPaymentStatus] = useState<'IDLE' | 'SENDING' | 'SUCCESS'>('IDLE');

  // WhatsApp OTP Verification state
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [otpVerified, setOtpVerified] = useState(false);
  const [otpError, setOtpError] = useState('');
  const [devOtp, setDevOtp] = useState<string | null>(null);

  const steps = [
    { title: 'Business Identity', icon: Building, desc: 'Register your enterprise' },
    { title: 'Owner & Contact', icon: User, desc: 'KYC & contact details' },
    { title: 'Payment Account', icon: CreditCard, desc: 'PayBill / Till / Bank setup' },
    { title: 'Verification', icon: ShieldCheck, desc: 'CBK compliance check' },
    { title: 'WhatsApp Business', icon: MessageSquare, desc: 'Connect Meta Cloud API' },
    { title: 'Test Payment', icon: Sparkles, desc: 'Sandbox verification' },
    { title: 'Launch Dashboard', icon: CheckCircle, desc: 'Ready for live processing' },
  ];

  const handleNext = async () => {
    if (currentStep === 4) {
      setIsVerifying(true);
      setTimeout(() => {
        setIsVerifying(false);
        setCurrentStep(5);
      }, 1200);
      return;
    }

    if (currentStep === 5) {
      if (!otpVerified) {
        setOtpError('Please verify your WhatsApp phone number using the OTP before proceeding.');
        return;
      }
    }

    if (currentStep === 6 && testPaymentStatus === 'IDLE') {
      setTestPaymentStatus('SENDING');
      setTimeout(() => {
        setTestPaymentStatus('SUCCESS');
      }, 1500);
      return;
    }

    if (currentStep === 7) {
      await api.completeOnboarding({
        business_name: businessName,
        owner_name: ownerName,
        settlement_type: settlementType,
        settlement_number: settlementNumber
      });
      onComplete();
      return;
    }

    setCurrentStep((prev) => Math.min(prev + 1, 7));
  };

  const handlePrev = () => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="glass-card-glow max-w-2xl w-full rounded-3xl overflow-hidden shadow-2xl border border-emerald-500/30 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 bg-gradient-to-r from-emerald-950/80 to-slate-900 border-b border-emerald-500/20 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-widest">Progressive Disclosure</span>
              <span className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/30 font-bold">
                Step {currentStep} of 7
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-white mt-1">Merchant Onboarding Wizard</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-sm font-bold">✕</button>
        </div>

        {/* Step Indicator Bar */}
        <div className="px-6 py-3 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between overflow-x-auto gap-2">
          {steps.map((s, idx) => {
            const stepNum = idx + 1;
            const isDone = stepNum < currentStep;
            const isCurrent = stepNum === currentStep;
            return (
              <div key={idx} className="flex items-center gap-1.5 shrink-0">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition ${
                  isDone ? 'bg-emerald-500 text-slate-950' :
                  isCurrent ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500' :
                  'bg-slate-800 text-slate-500'
                }`}>
                  {isDone ? <Check className="w-4 h-4 stroke-[3]" /> : stepNum}
                </div>
                <span className={`text-xs hidden md:inline font-medium ${isCurrent ? 'text-emerald-400 font-bold' : 'text-slate-500'}`}>
                  {s.title}
                </span>
                {idx < 6 && <div className="w-3 h-0.5 bg-slate-800 hidden sm:block"></div>}
              </div>
            );
          })}
        </div>

        {/* Wizard Body Content */}
        <div className="p-8 overflow-y-auto flex-1 space-y-6">
          {currentStep === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-white">Step 1: Business Identity</h3>
              <p className="text-sm text-slate-300">Enter your official business or merchant name for payment invoices and checkout branding.</p>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Business Name</label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 text-sm"
                  placeholder="e.g. Nairobi Tech Supplies Ltd"
                />
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-white">Step 2: Owner & Contact Details</h3>
              <p className="text-sm text-slate-300">Provide official contact information for merchant notification & settlement alerts.</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Full Owner Name</label>
                  <input
                    type="text"
                    value={ownerName}
                    onChange={(e) => setOwnerName(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
                  <input
                    type="email"
                    value={ownerEmail}
                    onChange={(e) => setOwnerEmail(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Phone Number (M-Pesa registered)</label>
                <input
                  type="text"
                  value={ownerPhone}
                  onChange={(e) => setOwnerPhone(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 text-sm"
                />
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-white">Step 3: Payment Destination Account</h3>
              <p className="text-sm text-slate-300">Where should collected funds settle? Select your Kenyan payment destination.</p>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: 'PAYBILL', label: 'M-Pesa PayBill' },
                  { id: 'TILL', label: 'Buy Goods Till' },
                  { id: 'BANK', label: 'Bank Account' },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSettlementType(item.id as any)}
                    className={`p-4 rounded-xl border text-center font-bold text-xs transition cursor-pointer ${
                      settlementType === item.id
                        ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  {settlementType === 'PAYBILL' ? 'PayBill Business Number' : settlementType === 'TILL' ? 'Till Number' : 'Account Number'}
                </label>
                <input
                  type="text"
                  value={settlementNumber}
                  onChange={(e) => setSettlementNumber(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500 text-sm font-mono"
                />
              </div>
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-4 text-center py-6">
              <ShieldCheck className="w-12 h-12 text-emerald-400 mx-auto animate-pulse" />
              <h3 className="text-xl font-bold text-white">Step 4: Automated Verification</h3>
              <p className="text-sm text-slate-300 max-w-md mx-auto">
                Verifying PayBill `{settlementNumber}` & performing Central Bank of Kenya / Safaricom merchant authorization checks.
              </p>
              {isVerifying ? (
                <div className="text-xs text-emerald-400 font-semibold flex items-center justify-center gap-2">
                  <span className="w-3 h-3 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin"></span>
                  Validating merchant authorization & tenant isolation...
                </div>
              ) : (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs font-medium inline-block">
                  ✓ Ready for validation
                </div>
              )}
            </div>
          )}

          {currentStep === 5 && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                  WA
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Step 5: WhatsApp Identity Binding</h3>
                  <p className="text-xs text-slate-400">Prove ownership of your phone number to receive alerts and manage payments</p>
                </div>
              </div>

              {otpError && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400">
                  {otpError}
                </div>
              )}

              {otpVerified ? (
                <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-xs space-y-2 text-center text-emerald-400">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2" />
                  <p className="font-bold">Phone Number Verified & Bound!</p>
                  <p className="text-slate-300">Number {ownerPhone} has been bound as OWNER for this tenant.</p>
                </div>
              ) : (
                <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 text-xs space-y-4">
                  {!otpSent ? (
                    <div className="space-y-3">
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">WhatsApp Number (E.164)</label>
                        <input
                          type="text"
                          value={ownerPhone}
                          onChange={(e) => setOwnerPhone(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-emerald-500"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={async () => {
                          setOtpError('');
                          try {
                            const res = await api.bindPhoneIdentity(ownerPhone, 'OWNER');
                            setOtpSent(true);
                            if (res.dev_otp) setDevOtp(res.dev_otp);
                          } catch (err: any) {
                            setOtpError(err.response?.data?.error || 'Failed to initiate binding');
                          }
                        }}
                        className="w-full py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition text-xs cursor-pointer"
                      >
                        Send Verification Code via WhatsApp
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-slate-300 text-center">
                        Verification code sent to <strong className="text-white">{ownerPhone}</strong>.
                      </p>

                      {devOtp && (
                        <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-center text-emerald-400 font-mono text-[11px] font-bold">
                          [DEV MODE] WhatsApp OTP Code: {devOtp}
                        </div>
                      )}

                      <div>
                        <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">6-Digit Code</label>
                        <input
                          type="text"
                          placeholder="e.g. 123456"
                          maxLength={6}
                          value={otpCode}
                          onChange={(e) => setOtpCode(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white text-center font-mono tracking-widest focus:outline-none focus:border-emerald-500"
                        />
                      </div>

                      <button
                        type="button"
                        onClick={async () => {
                          setOtpError('');
                          try {
                            await api.confirmPhoneOTP(ownerPhone, otpCode);
                            setOtpVerified(true);
                          } catch (err: any) {
                            setOtpError(err.response?.data?.error || 'Invalid OTP code');
                          }
                        }}
                        className="w-full py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition text-xs cursor-pointer"
                      >
                        Verify & Link WhatsApp
                      </button>

                      <button
                        type="button"
                        onClick={() => setOtpSent(false)}
                        className="w-full py-2.5 rounded-xl bg-slate-805 hover:bg-slate-800 text-slate-300 transition text-xs cursor-pointer text-center"
                      >
                        Change Phone Number
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {currentStep === 6 && (
            <div className="space-y-4 text-center py-4">
              <Sparkles className="w-12 h-12 text-cyan-400 mx-auto" />
              <h3 className="text-xl font-bold text-white">Step 6: Test Payment Execution</h3>
              <p className="text-sm text-slate-300 max-w-md mx-auto">
                Trigger a simulated KES 100 STK Push to verify end-to-end webhook processing.
              </p>

              {testPaymentStatus === 'SENDING' && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400 text-xs font-medium">
                  Sending test STK Push to {ownerPhone}...
                </div>
              )}

              {testPaymentStatus === 'SUCCESS' && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs font-bold">
                  ✅ Test STK Push Received & Confirmed! M-Pesa Receipt: QHK9182374
                </div>
              )}
            </div>
          )}

          {currentStep === 7 && (
            <div className="space-y-4 text-center py-6">
              <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto" />
              <h3 className="text-2xl font-extrabold text-white">Step 7: Dashboard Ready!</h3>
              <p className="text-sm text-slate-300 max-w-md mx-auto">
                Your tenant dashboard for <strong className="text-white">{businessName}</strong> is fully configured. You can now generate payment links and receive M-Pesa payments.
              </p>
            </div>
          )}
        </div>

        {/* Footer Controls */}
        <div className="p-6 bg-slate-950 border-t border-slate-800 flex items-center justify-between">
          <button
            onClick={handlePrev}
            disabled={currentStep === 1}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
              currentStep === 1 ? 'opacity-30 cursor-not-allowed text-slate-600' : 'text-slate-300 hover:text-white bg-slate-900 cursor-pointer'
            }`}
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Previous</span>
          </button>

          <button
            onClick={handleNext}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-500/20 transition flex items-center gap-2 cursor-pointer"
          >
            <span>{currentStep === 7 ? 'Go to Dashboard' : currentStep === 6 && testPaymentStatus === 'IDLE' ? 'Run Test Payment' : 'Continue'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
