import React from 'react';
import {
  DollarSign, CheckCircle2, Clock, TrendingUp,
  Plus, ArrowUpRight, Copy, Check, MessageSquare
} from 'lucide-react';
import type { DashboardSummary, PaymentRequest } from '../types';

interface DashboardOverviewProps {
  summary: DashboardSummary | null;
  onRequestNewPayment: () => void;
  onSelectRequest: (req: PaymentRequest) => void;
  onOpenSimulator: () => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  summary, onRequestNewPayment, onOpenSimulator
}) => {
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const volumeKES = summary?.total_volume_kes ?? 0;
  const succeededCount = summary?.succeeded_count ?? 0;
  const pendingCount = summary?.pending_count ?? 0;
  const conversionRate = summary?.conversion_rate ?? 0;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-emerald-950/60 via-slate-900 to-cyan-950/40 p-6 rounded-2xl border border-emerald-500/20 shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="text-xs font-semibold text-emerald-400 tracking-wider uppercase">Live Payment Orchestration</span>
          </div>
          <h2 className="text-2xl font-bold text-white">Merchant Overview</h2>
          <p className="text-sm text-slate-300">Generate KSh payment links, share over WhatsApp, and track M-Pesa STK Push settlements in real time.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onOpenSimulator}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold border border-slate-700 transition flex items-center gap-2 cursor-pointer"
          >
            <span>STK Push Simulator</span>
          </button>

          <button
            onClick={onRequestNewPayment}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white text-sm font-bold shadow-lg shadow-emerald-500/25 transition transform active:scale-95 flex items-center gap-2 cursor-pointer"
          >
            <Plus className="w-5 h-5" />
            <span>Create Payment Request</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Volume */}
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden group">
          <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-emerald-500/10 rounded-full blur-xl group-hover:bg-emerald-500/20 transition"></div>
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Total Value Settled</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-white">
            KES {volumeKES.toLocaleString()}
          </p>
          <div className="flex items-center gap-1 text-xs text-emerald-400 mt-2 font-medium">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Authoritative server-side verified</span>
          </div>
        </div>

        {/* Successful Payments */}
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Successful Payments</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-white">{succeededCount}</p>
          <p className="text-xs text-slate-400 mt-2">M-Pesa STK Push callbacks confirmed</p>
        </div>

        {/* Pending Requests */}
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Pending Requests</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-amber-400">{pendingCount}</p>
          <p className="text-xs text-slate-400 mt-2">Awaiting customer M-Pesa PIN input</p>
        </div>

        {/* Conversion Rate */}
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden group">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Conversion Rate</span>
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-cyan-400">{conversionRate}%</p>
          <p className="text-xs text-slate-400 mt-2">Completed checkout ratio</p>
        </div>
      </div>

      {/* Main Content Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Payment Requests */}
        <div className="lg:col-span-2 glass-card p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-white">Recent Payment Requests</h3>
              <p className="text-xs text-slate-400">Public tokens & shareable checkout links</p>
            </div>
            <button
              onClick={onRequestNewPayment}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center gap-1 cursor-pointer"
            >
              + Create Request
            </button>
          </div>

          <div className="space-y-3">
            {(!summary?.recent_requests || summary.recent_requests.length === 0) ? (
              <div className="text-center py-10 border border-dashed border-slate-800 rounded-xl">
                <p className="text-slate-400 text-sm">No payment requests created yet.</p>
                <button
                  onClick={onRequestNewPayment}
                  className="mt-3 text-xs bg-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded-lg border border-emerald-500/30 cursor-pointer"
                >
                  Create your first KSh request
                </button>
              </div>
            ) : (
              summary.recent_requests.map((req) => (
                <div
                  key={req.id}
                  className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-2.5 rounded-xl text-xs font-bold ${
                      req.status === 'SUCCEEDED' ? 'bg-emerald-500/10 text-emerald-400' :
                      req.status === 'PENDING' ? 'bg-amber-500/10 text-amber-400' :
                      req.status === 'FAILED' ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'
                    }`}>
                      {req.currency}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-base">KES {req.amount_minor.toLocaleString()}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          req.status === 'SUCCEEDED' ? 'badge-succeeded' :
                          req.status === 'PENDING' ? 'badge-pending' :
                          req.status === 'FAILED' ? 'badge-failed' : 'badge-created'
                        }`}>
                          {req.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">Ref: {req.reference}</p>
                      {req.description && <p className="text-xs text-slate-300 mt-1 line-clamp-1">{req.description}</p>}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      onClick={() => copyToClipboard(req.checkout_url, req.id)}
                      className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition flex items-center gap-1 cursor-pointer"
                      title="Copy Checkout Link"
                    >
                      {copiedId === req.id ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                      <span className="hidden sm:inline">Copy Link</span>
                    </button>

                    <a
                      href={req.checkout_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 text-xs font-semibold transition flex items-center gap-1"
                    >
                      <span>Checkout</span>
                      <ArrowUpRight className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Live Transactions Feed */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white">Settled Transactions</h3>
              <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/30 font-semibold">
                M-Pesa Verified
              </span>
            </div>

            <div className="space-y-3">
              {(!summary?.recent_transactions || summary.recent_transactions.length === 0) ? (
                <div className="text-center py-8 text-slate-400 text-xs">
                  No completed transactions yet. Initiate STK Push in the checkout link to test!
                </div>
              ) : (
                summary.recent_transactions.map((tx) => (
                  <div key={tx.id} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono text-emerald-400 font-bold">
                        {tx.mpesa_receipt_number}
                      </span>
                      <span className="text-xs font-bold text-white">
                        +KES {tx.amount_minor.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>Ref: {tx.payment_reference}</span>
                      <span>{new Date(tx.paid_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-6 p-4 rounded-xl bg-gradient-to-br from-slate-900 to-emerald-950/40 border border-emerald-500/20 text-xs">
            <div className="flex items-center gap-2 text-emerald-400 font-bold mb-1">
              <MessageSquare className="w-4 h-4" />
              <span>WhatsApp Integration Active</span>
            </div>
            <p className="text-slate-300">Automated WhatsApp receipts are sent immediately after M-Pesa callbacks are processed.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
