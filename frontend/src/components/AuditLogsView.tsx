import React, { useState, useEffect } from 'react';
import { ShieldCheck } from 'lucide-react';
import type { AuditLog } from '../types';
import { api } from '../services/api';

export const AuditLogsView: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);

  useEffect(() => {
    api.getAuditLogs().then((res) => {
      setLogs(res);
    });
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Security & Audit Logs</h2>
          <p className="text-xs text-slate-400">Immutable record of logins, credential changes, payment actions & integration security</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full border border-emerald-500/30 font-semibold flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" />
            <span>Audit Logging Active</span>
          </span>
        </div>
      </div>

      <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-xs text-slate-400 uppercase font-semibold">
                <th className="p-4">Action</th>
                <th className="p-4">User</th>
                <th className="p-4">Details</th>
                <th className="p-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-sm">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-slate-400 text-xs">
                    No security audit logs available.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition">
                    <td className="p-4 font-mono font-bold text-emerald-400">
                      {log.action}
                    </td>
                    <td className="p-4 text-slate-300">
                      {log.user_email}
                    </td>
                    <td className="p-4 text-xs font-mono text-slate-400">
                      {JSON.stringify(log.details)}
                    </td>
                    <td className="p-4 text-xs text-slate-400">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
