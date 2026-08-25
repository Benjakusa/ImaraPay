import React, { useState } from 'react';
import {
  Plus, Copy, Ban, ExternalLink, Check, Search, MessageSquare
} from 'lucide-react';
import type { PaymentRequest } from '../types';
import { api } from '../services/api';

interface PaymentRequestsListProps {
  requests: PaymentRequest[];
  onRefresh: () => void;
  onOpenCheckout: (token: string) => void;
}

export const PaymentRequestsList: React.FC<PaymentRequestsListProps> = ({
  requests, onRefresh, onOpenCheckout
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Form State
  const [amount, setAmount] = useState('2500');
  const [reference, setReference] = useState(`INV-${Math.floor(10000 + Math.random() * 90000)}`);
  const [description, setDescription] = useState('Website development & hosting deposit');
  const [customerPhone, setCustomerPhone] = useState('0712345678');
  const [expiresIn] = useState('1440');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.createPaymentRequest({
        amount_minor: parseInt(amount, 10),
        reference,
        description,
        customer_phone: customerPhone,
        expires_in_minutes: parseInt(expiresIn, 10)
      });
      setShowCreateModal(false);
      onRefresh();
    } catch (err) {
      console.error('Failed to create payment request', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async (id: string) => {
    if (confirm('Are you sure you want to cancel this payment request?')) {
      await api.cancelPaymentRequest(id);
      onRefresh();
    }
  };

  const handleShareWhatsApp = async (req: PaymentRequest) => {
    await api.shareWhatsApp(req.id, req.customer_phone);
    const text = encodeURIComponent(
      `Pay KES ${req.amount_minor.toLocaleString()} for ${req.reference} via Imara Pay:\n${req.checkout_url}`
    );
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredRequests = requests.filter(r =>
    r.reference.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.customer_phone?.includes(searchTerm)
  );

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Payment Requests</h2>
          <p className="text-xs text-slate-400">Generate KSh checkout URLs & track real-time customer status</p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-500/25 transition flex items-center gap-2 cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>New Payment Request</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="glass-card p-4 rounded-2xl flex items-center gap-3">
        <Search className="w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by reference, phone number, or description..."
          className="bg-transparent border-none text-white text-sm focus:outline-none w-full placeholder-slate-500"
        />
      </div>

      {/* Payment Requests Grid / List */}
      <div className="space-y-3">
        {filteredRequests.length === 0 ? (
          <div className="glass-card p-12 rounded-2xl text-center">
            <p className="text-slate-400 text-sm">No payment requests found.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-3 text-xs bg-emerald-500/20 text-emerald-400 px-4 py-2 rounded-xl border border-emerald-500/30 cursor-pointer font-bold"
            >
              Create New Request
            </button>
          </div>
        ) : (
          filteredRequests.map((req) => (
            <div
              key={req.id}
              className="glass-card p-5 rounded-2xl border border-slate-800 hover:border-slate-700 transition flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-extrabold text-white">
                    KES {req.amount_minor.toLocaleString()}
                  </span>
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                    req.status === 'SUCCEEDED' ? 'badge-succeeded' :
                    req.status === 'PENDING' ? 'badge-pending' :
                    req.status === 'FAILED' ? 'badge-failed' : 'badge-created'
                  }`}>
                    {req.status}
                  </span>
                  {req.is_expired && (
                    <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded">EXPIRED</span>
                  )}
                </div>

                <div className="flex items-center gap-4 text-xs text-slate-400">
                  <span>Ref: <strong className="text-slate-200 font-mono">{req.reference}</strong></span>
                  {req.customer_phone && <span>Phone: <strong className="text-slate-200">{req.customer_phone}</strong></span>}
                  <span>Created: {new Date(req.created_at).toLocaleDateString()}</span>
                </div>

                {req.description && (
                  <p className="text-xs text-slate-300 mt-1">{req.description}</p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 self-end md:self-center">
                <button
                  onClick={() => copyToClipboard(req.checkout_url, req.id)}
                  className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition flex items-center gap-1.5 cursor-pointer"
                  title="Copy Link"
                >
                  {copiedId === req.id ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                  <span>{copiedId === req.id ? 'Copied' : 'Copy Link'}</span>
                </button>

                <button
                  onClick={() => handleShareWhatsApp(req)}
                  className="p-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer"
                  title="Share to WhatsApp"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>WhatsApp</span>
                </button>

                <button
                  onClick={() => onOpenCheckout(req.public_token)}
                  className="p-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer"
                  title="Open Customer Checkout View"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>Checkout</span>
                </button>

                {req.status !== 'SUCCEEDED' && req.status !== 'CANCELLED' && (
                  <button
                    onClick={() => handleCancel(req.id)}
                    className="p-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs transition cursor-pointer"
                    title="Cancel Request"
                  >
                    <Ban className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-card-glow max-w-lg w-full rounded-3xl p-6 space-y-4 border border-emerald-500/30">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white">Create KSh Payment Request</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Amount (KES)</label>
                <div className="relative">
                  <span className="absolute left-4 top-3.5 text-xs font-bold text-emerald-400">KES</span>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                    min="1"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-14 pr-4 py-3 text-white focus:outline-none focus:border-emerald-500 text-base font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Reference Code</label>
                  <input
                    type="text"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    required
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Customer Phone (Optional)</label>
                  <input
                    type="text"
                    value={customerPhone}
                    onChange={(e) => setCustomerPhone(e.target.value)}
                    placeholder="0712345678"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500 text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-emerald-500 text-xs"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 text-white text-xs font-bold shadow-lg shadow-emerald-500/25 transition cursor-pointer"
                >
                  {isSubmitting ? 'Creating...' : 'Generate Payment Link'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
