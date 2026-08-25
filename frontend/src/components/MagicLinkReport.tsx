import React, { useState, useEffect } from 'react';
import { Download, FileText, CheckCircle2, Calendar } from 'lucide-react';
import { api } from '../services/api';

interface MagicLinkReportProps {
  token: string;
  onClose: () => void;
}

export const MagicLinkReport: React.FC<MagicLinkReportProps> = ({ token, onClose }) => {
  const [data, setData] = useState<{
    tenant_name: string;
    scope: any;
    transactions: any[];
    expires_at: string;
  } | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const res = await api.getMagicLinkReport(token);
        setData(res);
      } catch (err: any) {
        setError(err.response?.status === 404 ? 'This magic link report is expired or invalid.' : 'Failed to load report.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchReport();
  }, [token]);

  const handleExportCSV = () => {
    if (!data || data.transactions.length === 0) return;

    const headers = ['Date', 'Receipt No', 'Reference', 'Customer Phone', 'Amount (KES)', 'Status'];
    const rows = data.transactions.map((tx) => [
      new Date(tx.paid_at).toLocaleString(),
      tx.mpesa_receipt_number,
      tx.reference,
      tx.customer_phone,
      tx.amount_minor,
      tx.status,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `ImaraPay_Transactions_${data.tenant_name.replace(/\s+/g, '_')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0A0F1D] flex items-center justify-center text-slate-100">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Loading Secure Report...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0A0F1D] flex items-center justify-center p-6 text-slate-100">
        <div className="glass-card-glow max-w-md w-full p-8 rounded-3xl text-center space-y-4 border border-red-500/30 shadow-2xl">
          <div className="w-12 h-12 bg-red-500/10 text-red-400 rounded-full flex items-center justify-center mx-auto text-xl font-bold">
            !
          </div>
          <h3 className="text-lg font-bold text-white">Access Link Invalid</h3>
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

  if (!data) return null;

  return (
    <div className="min-h-screen bg-[#0A0F1D] text-slate-100 flex flex-col p-6 md:p-10">
      <div className="max-w-6xl w-full mx-auto space-y-6 flex-1 flex flex-col">
        {/* Header section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-emerald-950/40 to-slate-900/60 p-6 rounded-2xl border border-emerald-500/20 shadow-xl">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-400" />
              <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                Magic Link Scoped View
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white">{data.tenant_name}</h2>
            <p className="text-xs text-slate-400 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              <span>Link Expiry: {new Date(data.expires_at).toLocaleString()}</span>
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-center">
            <button
              onClick={handleExportCSV}
              disabled={data.transactions.length === 0}
              className="px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition flex items-center gap-2 cursor-pointer shadow-lg shadow-emerald-500/10"
            >
              <Download className="w-4 h-4" />
              <span>Export CSV</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-bold transition text-slate-300 cursor-pointer"
            >
              Close View
            </button>
          </div>
        </div>

        {/* Stats segment */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="glass-card p-5 rounded-2xl relative overflow-hidden">
            <p className="text-xs font-medium text-slate-400 mb-1">Total Transaction Count</p>
            <p className="text-2xl font-extrabold text-white">{data.transactions.length}</p>
          </div>
          <div className="glass-card p-5 rounded-2xl relative overflow-hidden">
            <p className="text-xs font-medium text-slate-400 mb-1">Volume Summary</p>
            <p className="text-2xl font-extrabold text-white">
              KES {data.transactions.reduce((acc, curr) => acc + curr.amount_minor, 0).toLocaleString()}
            </p>
          </div>
          <div className="glass-card p-5 rounded-2xl relative overflow-hidden">
            <p className="text-xs font-medium text-slate-400 mb-1">Status Verification</p>
            <p className="text-emerald-400 text-sm font-bold flex items-center gap-1.5 mt-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>Safaricom M-Pesa Authoritative</span>
            </p>
          </div>
        </div>

        {/* Transaction Table */}
        <div className="glass-card rounded-2xl border border-slate-850 overflow-hidden flex-1 flex flex-col min-h-[300px]">
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 border-b border-slate-850 text-slate-400 font-bold uppercase tracking-wider">
                  <th className="p-4">Paid At Date</th>
                  <th className="p-4">M-Pesa Receipt No</th>
                  <th className="p-4">Reference</th>
                  <th className="p-4">Customer Phone</th>
                  <th className="p-4 text-right">Amount (KES)</th>
                  <th className="p-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850/60">
                {data.transactions.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-10 text-center text-slate-400">
                      No matching settled transactions found in this time-box.
                    </td>
                  </tr>
                ) : (
                  data.transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-slate-900/40 transition">
                      <td className="p-4 text-slate-300 font-medium">
                        {new Date(tx.paid_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                      </td>
                      <td className="p-4 font-mono text-emerald-400 font-bold">{tx.mpesa_receipt_number}</td>
                      <td className="p-4 text-slate-300">{tx.reference}</td>
                      <td className="p-4 text-slate-400 font-mono">{tx.customer_phone}</td>
                      <td className="p-4 text-right font-extrabold text-white">
                        KES {tx.amount_minor.toLocaleString()}
                      </td>
                      <td className="p-4 text-center">
                        <span className="inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold badge-succeeded">
                          {tx.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
export default MagicLinkReport;
