import React, { useState } from 'react';
import { FlaskConical, Play, CheckCircle2, Smartphone, RefreshCw } from 'lucide-react';
import type { PaymentRequest } from '../types';
import { api } from '../services/api';

interface SandboxSimulatorProps {
  requests: PaymentRequest[];
  onRefresh: () => void;
}

export const SandboxSimulator: React.FC<SandboxSimulatorProps> = ({ onRefresh }) => {
  const [checkoutReqId, setCheckoutReqId] = useState<string>('ws_CO_250820261145320984');
  const [scenario, setScenario] = useState<'SUCCESS' | 'USER_CANCELLED' | 'WRONG_PIN' | 'TIMEOUT'>('SUCCESS');
  const [isTriggering, setIsTriggering] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleTrigger = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsTriggering(true);
    setResult(null);

    try {
      const res = await api.triggerSimulatorCallback(checkoutReqId, scenario);
      setResult(res);
      onRefresh();
    } catch (err: any) {
      setResult({ error: err?.response?.data?.error || 'Failed to trigger callback' });
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest">Sandbox Test Engine</span>
            <span className="text-[10px] bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/30 font-bold">
              Interactive
            </span>
          </div>
          <h2 className="text-xl font-bold text-white mt-1">M-Pesa STK Push Sandbox Simulator</h2>
          <p className="text-xs text-slate-400">Simulate incoming Safaricom callbacks (Success, Wrong PIN, User Cancelled, Timeout) without real money.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls Card */}
        <div className="glass-card-glow p-6 rounded-2xl space-y-4 border border-cyan-500/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold">
              <FlaskConical className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Trigger Provider Callback</h3>
              <p className="text-xs text-slate-400">Select scenario & send simulated webhook</p>
            </div>
          </div>

          <form onSubmit={handleTrigger} className="space-y-4 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Checkout Request ID</label>
              <input
                type="text"
                value={checkoutReqId}
                onChange={(e) => setCheckoutReqId(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-500"
                placeholder="ws_CO_..."
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Callback Scenario</label>
              <div className="space-y-2">
                {[
                  { id: 'SUCCESS', title: '✅ Success (0)', desc: 'User enters correct PIN -> Payment SUCCEEDED' },
                  { id: 'USER_CANCELLED', title: '🚫 Cancelled (1032)', desc: 'User cancels STK prompt on phone' },
                  { id: 'WRONG_PIN', title: '🔑 Wrong PIN (2001)', desc: 'User enters invalid PIN' },
                  { id: 'TIMEOUT', title: '⏳ Timeout (1037)', desc: 'Phone unanswered / timed out' },
                ].map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setScenario(s.id as any)}
                    className={`w-full p-3 rounded-xl border text-left transition cursor-pointer ${
                      scenario === s.id
                        ? 'bg-cyan-500/20 border-cyan-500 text-white'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="font-bold text-xs">{s.title}</div>
                    <div className="text-[11px] text-slate-400">{s.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={isTriggering}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-400 hover:to-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-cyan-500/20 transition flex items-center justify-center gap-2 cursor-pointer"
            >
              {isTriggering ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              <span>Execute Webhook Callback</span>
            </button>
          </form>
        </div>

        {/* Output & Logs Screen */}
        <div className="lg:col-span-2 glass-card p-6 rounded-2xl space-y-4 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-cyan-400" />
                <span>Simulated Phone & Server Reaction</span>
              </h3>
              <span className="text-[10px] font-mono text-slate-400">Idempotency Checked</span>
            </div>

            <div className="mt-4 space-y-4">
              {result ? (
                <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Response Status:</span>
                    <span className={`font-bold ${result.status === 'SUCCEEDED' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {result.status || (result.already_processed ? 'ALREADY PROCESSED' : 'EXECUTED')}
                    </span>
                  </div>

                  {result.mpesa_receipt && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">M-Pesa Receipt:</span>
                      <span className="text-emerald-400 font-bold">{result.mpesa_receipt}</span>
                    </div>
                  )}

                  <div className="pt-2 border-t border-slate-800">
                    <span className="text-slate-500 text-[11px]">Raw JSON Event Output:</span>
                    <pre className="mt-1 p-3 bg-black/60 rounded-xl text-[11px] text-cyan-300 overflow-x-auto">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="text-center py-16 text-slate-500 text-xs border border-dashed border-slate-800 rounded-2xl">
                  Select a callback scenario on the left and click "Execute Webhook Callback" to simulate Safaricom M-Pesa processing.
                </div>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <p>Every callback generates an immutable <code className="text-emerald-300">WebhookEvent</code> and <code className="text-emerald-300">Transaction</code> record with unique deduplication keys.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
