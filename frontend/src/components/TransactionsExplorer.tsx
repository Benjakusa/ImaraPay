import React, { useState } from 'react';
import { Search, ShieldCheck } from 'lucide-react';
import type { Transaction } from '../types';

interface TransactionsExplorerProps {
  transactions: Transaction[];
}

export const TransactionsExplorer: React.FC<TransactionsExplorerProps> = ({ transactions }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);

  const filtered = transactions.filter(t =>
    t.mpesa_receipt_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
    t.payment_reference.toLowerCase().includes(searchTerm.toLowerCase()) ||
    t.customer_phone.includes(searchTerm)
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Transactions Explorer</h2>
          <p className="text-xs text-slate-400">Authoritative Safaricom M-Pesa settlement ledger</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full border border-emerald-500/30 font-semibold flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" />
            <span>Server-side Authoritative</span>
          </span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="glass-card p-4 rounded-2xl flex items-center gap-3">
        <Search className="w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by M-Pesa receipt code (e.g. QHK9182374), reference, or customer phone..."
          className="bg-transparent border-none text-white text-sm focus:outline-none w-full placeholder-slate-500"
        />
      </div>

      {/* Table */}
      <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-xs text-slate-400 uppercase font-semibold">
                <th className="p-4">M-Pesa Receipt</th>
                <th className="p-4">Amount</th>
                <th className="p-4">Reference</th>
                <th className="p-4">Customer Phone</th>
                <th className="p-4">Date & Time</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-sm">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-400 text-xs">
                    No transactions recorded yet. Complete an STK push in the checkout page to create transactions.
                  </td>
                </tr>
              ) : (
                filtered.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-800/40 transition">
                    <td className="p-4 font-mono font-bold text-emerald-400">
                      {tx.mpesa_receipt_number}
                    </td>
                    <td className="p-4 font-bold text-white">
                      KES {tx.amount_minor.toLocaleString()}
                    </td>
                    <td className="p-4 font-mono text-slate-300">
                      {tx.payment_reference}
                    </td>
                    <td className="p-4 text-slate-300">
                      {tx.customer_phone}
                    </td>
                    <td className="p-4 text-xs text-slate-400">
                      {new Date(tx.paid_at).toLocaleString()}
                    </td>
                    <td className="p-4">
                      <span className="badge-succeeded text-[10px] font-bold px-2.5 py-0.5 rounded-full">
                        {tx.status}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => setSelectedTx(tx)}
                        className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded-lg transition cursor-pointer"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-card-glow max-w-md w-full rounded-3xl p-6 space-y-4 border border-emerald-500/30">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white">M-Pesa Transaction Receipt</h3>
              <button onClick={() => setSelectedTx(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Receipt Code:</span>
                  <span className="font-mono text-emerald-400 font-bold text-sm">{selectedTx.mpesa_receipt_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Amount Paid:</span>
                  <span className="font-bold text-white text-sm">KES {selectedTx.amount_minor.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Reference:</span>
                  <span className="font-mono text-slate-200">{selectedTx.payment_reference}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Customer Phone:</span>
                  <span className="text-slate-200">{selectedTx.customer_phone}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Settlement Status:</span>
                  <span className="text-emerald-400 font-bold">COMPLETED</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => setSelectedTx(null)}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold transition cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
