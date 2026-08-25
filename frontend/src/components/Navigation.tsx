import React from 'react';
import {
  LayoutDashboard, CreditCard, Receipt, MessageSquare,
  FlaskConical, ShieldCheck, Settings, Sparkles, Building2
} from 'lucide-react';

interface NavigationProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  tenantName: string;
  onOpenOnboarding: () => void;
}

export const Navigation: React.FC<NavigationProps> = ({
  currentTab, setCurrentTab, tenantName, onOpenOnboarding
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'payment-requests', label: 'Payment Requests', icon: CreditCard },
    { id: 'transactions', label: 'Transactions', icon: Receipt },
    { id: 'whatsapp', label: 'WhatsApp Hub', icon: MessageSquare },
    { id: 'simulator', label: 'STK Simulator', icon: FlaskConical, badge: 'Sandbox' },
    { id: 'audit', label: 'Audit Logs', icon: ShieldCheck },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#0F172A]/90 backdrop-blur-xl border-r border-slate-800/80 flex flex-col justify-between p-4 min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-3 py-4 mb-6 border-b border-slate-800/80">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 font-bold text-white text-xl">
            IP
          </div>
          <div>
            <h1 className="font-extrabold text-lg text-white tracking-wide flex items-center gap-1.5">
              IMARA PAY
              <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/30">KE</span>
            </h1>
            <p className="text-xs text-slate-400">Payment Orchestration</p>
          </div>
        </div>

        {/* Tenant Active Card */}
        <div className="mb-6 p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2 overflow-hidden">
            <Building2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <div className="truncate">
              <p className="text-xs text-slate-400 font-medium">Active Merchant</p>
              <p className="text-sm font-semibold text-white truncate">{tenantName}</p>
            </div>
          </div>
          <button
            onClick={onOpenOnboarding}
            className="text-[10px] bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 px-2 py-1 rounded font-medium transition cursor-pointer"
            title="Re-run Setup Wizard"
          >
            Setup
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-gradient-to-r from-emerald-500/20 to-emerald-500/5 text-emerald-400 border border-emerald-500/30 shadow-md shadow-emerald-500/10'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-5 h-5 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="pt-4 border-t border-slate-800/80">
        <div className="p-3 rounded-xl bg-gradient-to-r from-emerald-950/40 to-slate-900 border border-emerald-800/30">
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold mb-1">
            <Sparkles className="w-4 h-4 animate-spin-slow" />
            <span>M-Pesa STK Active</span>
          </div>
          <p className="text-[11px] text-slate-400">Multi-tenant, zero secret storage, server-side verified.</p>
        </div>
      </div>
    </aside>
  );
};
