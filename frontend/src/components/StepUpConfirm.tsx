import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import type { StepUpChallenge } from '../types';

interface StepUpConfirmProps {
  token: string;
  onClose: () => void;
}

export const StepUpConfirm: React.FC<StepUpConfirmProps> = ({ token, onClose }) => {
  const [challenge, setChallenge] = useState<StepUpChallenge | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isConfirming, setIsConfirming] = useState(false);

  useEffect(() => {
    const fetchChallenge = async () => {
      try {
        const res = await api.getStepUpChallenge(token);
        setChallenge(res);
      } catch (err: any) {
        setError(err.response?.status === 404 ? 'This confirmation link is expired or has already been used.' : 'Failed to load challenge.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchChallenge();
  }, [token]);

  const handleConfirm = async () => {
    setIsConfirming(true);
    setError('');
    try {
      const res = await api.confirmStepUpChallenge(token);
      setSuccessMsg(res.message || 'Action completed successfully!');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to complete action.');
    } finally {
      setIsConfirming(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0A0F1D] flex items-center justify-center text-slate-100">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Securing Connection...</p>
        </div>
      </div>
    );
  }

  if (error && !challenge) {
    return (
      <div className="min-h-screen bg-[#0A0F1D] flex items-center justify-center p-6 text-slate-100">
        <div className="glass-card-glow max-w-md w-full p-8 rounded-3xl text-center space-y-4 border border-red-500/30 shadow-2xl">
          <ShieldAlert className="w-12 h-12 text-red-500 mx-auto animate-bounce" />
          <h3 className="text-lg font-bold text-white">Verification Link Invalid</h3>
          <p className="text-xs text-slate-400">{error}</p>
          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-bold rounded-xl transition cursor-pointer text-slate-300 hover:text-white"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0F1D] flex items-center justify-center p-6 text-slate-100">
      <div className="glass-card-glow max-w-lg w-full p-8 rounded-3xl border border-cyan-500/30 shadow-2xl space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          {successMsg ? (
            <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto" />
          ) : (
            <ShieldCheck className="w-14 h-14 text-cyan-400 mx-auto animate-pulse" />
          )}
          <h2 className="text-xl font-bold text-white">
            {successMsg ? 'Security Action Complete' : 'Step-Up Authorization'}
          </h2>
          <p className="text-xs text-slate-400">
            {successMsg ? 'The requested action has been performed.' : 'A sensitive action has been requested from WhatsApp.'}
          </p>
        </div>

        {/* Challenge details */}
        {challenge && !successMsg && (
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4 text-xs">
            <div className="space-y-1">
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Business tenant</p>
              <p className="text-sm font-bold text-white">{challenge.tenant_name}</p>
            </div>

            <div className="space-y-1">
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Action Description</p>
              <p className="text-sm font-semibold text-cyan-300 bg-cyan-500/10 p-3 rounded-xl border border-cyan-500/20">
                {challenge.action_label}
              </p>
            </div>

            {/* Custom display based on payload parameters */}
            {challenge.action_payload && Object.keys(challenge.action_payload).length > 0 && (
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Details</p>
                <div className="space-y-1.5 font-mono text-[10px] bg-slate-950 p-3 rounded-xl">
                  {Object.entries(challenge.action_payload).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-slate-500">{k}:</span>
                      <span className="text-slate-300 font-bold">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="text-center pt-2 text-[10px] text-slate-500 flex items-center justify-center gap-1.5">
              <span>This link expires in:</span>
              <span className="font-bold text-cyan-400">{Math.floor(challenge.expires_in_seconds / 60)}m {challenge.expires_in_seconds % 60}s</span>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400 flex items-center gap-2">
            <XCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Success Msg */}
        {successMsg && (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-xs text-emerald-400 text-center font-semibold">
            {successMsg}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          {successMsg ? (
            <button
              onClick={onClose}
              className="w-full py-3 bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-bold rounded-xl transition text-slate-300 text-center cursor-pointer"
            >
              Close Window
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-3 bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-bold rounded-xl transition text-slate-300 text-center cursor-pointer"
              >
                Cancel / Decline
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={isConfirming}
                className="flex-1 py-3 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 text-slate-950 font-bold rounded-xl text-xs transition flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-cyan-500/20"
              >
                {isConfirming ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <span>Authorize Action</span>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
export default StepUpConfirm;
