import React, { useState, useEffect } from 'react';
import { MessageSquare, Send, CheckCircle2, Bot, Sparkles, UserCheck, ShieldAlert, Key, Plus, Trash2 } from 'lucide-react';
import type { WhatsAppAccount, PhoneIdentity } from '../types';
import { api } from '../services/api';

interface WhatsAppHubProps {
  whatsapp: WhatsAppAccount | null;
  onRefresh: () => void;
}

export const WhatsAppHub: React.FC<WhatsAppHubProps> = ({ whatsapp, onRefresh }) => {
  const [commandText, setCommandText] = useState('request 2500 for INV-1002');
  const [activeSubTab, setActiveSubTab] = useState<'simulator' | 'staff'>('simulator');
  const [messages, setMessages] = useState<Array<{
    sender: 'merchant' | 'bot';
    text?: string;
    payload?: any;
    time: string;
  }>>([
    {
      sender: 'bot',
      text: '👋 Welcome to Imara Pay WhatsApp Bot!\n\nYou can run the business entirely from this chat. Try one of these commands:\n\n• `request 2500`\n• `today`\n• `status INV-1002`\n• `last 5`\n• `cancel INV-1002`\n• `help` — full menu',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [isSending, setIsSending] = useState(false);

  // Phone identities state (for Staff tab)
  const [identities, setIdentities] = useState<PhoneIdentity[]>([]);
  const [newPhone, setNewPhone] = useState('');
  const [newRole, setNewRole] = useState<'ADMIN' | 'STAFF'>('STAFF');
  const [otpVerifyPhone, setOtpVerifyPhone] = useState<string | null>(null);
  const [otpInput, setOtpInput] = useState('');
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [staffError, setStaffError] = useState('');
  const [staffSuccess, setStaffSuccess] = useState('');

  const loadIdentities = async () => {
    try {
      const data = await api.getPhoneIdentities();
      setIdentities(data);
    } catch (err) {
      console.error('Failed to load identities', err);
    }
  };

  useEffect(() => {
    loadIdentities();
  }, []);

  const handleSendCommand = async (e: React.FormEvent, customText?: string) => {
    if (e) e.preventDefault();
    const commandToSubmit = customText || commandText;
    if (!commandToSubmit.trim()) return;

    setMessages((prev) => [
      ...prev,
      {
        sender: 'merchant',
        text: commandToSubmit,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
    if (!customText) setCommandText('');
    setIsSending(true);

    try {
      const res = await api.sendWhatsAppCommand(commandToSubmit);
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: res.reply,
          payload: res.payload,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
      onRefresh();
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: '⚠️ Error executing WhatsApp command. Check server connection.',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsSending(false);
    }
  };

  // Staff Management Form Actions
  const handleAddPhone = async (e: React.FormEvent) => {
    e.preventDefault();
    setStaffError('');
    setStaffSuccess('');
    setDevOtp(null);

    if (!newPhone.trim()) {
      setStaffError('Please enter a phone number');
      return;
    }

    try {
      const res = await api.bindPhoneIdentity(newPhone, newRole);
      setOtpVerifyPhone(newPhone);
      setStaffSuccess(res.message || 'OTP sent successfully!');
      if (res.dev_otp) {
        setDevOtp(res.dev_otp);
      }
    } catch (err: any) {
      setStaffError(err.response?.data?.error || 'Failed to bind phone number');
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setStaffError('');
    setStaffSuccess('');

    if (!otpVerifyPhone || !otpInput) return;

    try {
      await api.confirmPhoneOTP(otpVerifyPhone, otpInput);
      setStaffSuccess(`Successfully verified and linked ${otpVerifyPhone}!`);
      setOtpVerifyPhone(null);
      setOtpInput('');
      setNewPhone('');
      setDevOtp(null);
      loadIdentities();
    } catch (err: any) {
      setStaffError(err.response?.data?.error || 'Invalid or expired OTP');
    }
  };

  const handleRevokePhone = async (id: string) => {
    setStaffError('');
    setStaffSuccess('');

    if (!confirm('Are you sure you want to revoke this phone identity?')) return;

    try {
      await api.revokePhoneIdentity(id);
      setStaffSuccess('Phone number access revoked.');
      loadIdentities();
    } catch (err: any) {
      setStaffError(err.response?.data?.error || 'Failed to revoke phone number');
    }
  };

  const handleInteractiveClick = (actionId: string) => {
    // Map interactive reply to command text
    if (actionId === 'confirm') {
      handleSendCommand(null as any, 'confirm');
    } else if (actionId === 'edit') {
      handleSendCommand(null as any, 'edit');
    } else if (actionId.startsWith('help_')) {
      const command = actionId.replace('help_', '');
      let demo = 'help';
      if (command === 'create') demo = 'request 2500';
      if (command === 'today') demo = 'today';
      if (command === 'status') demo = 'status INV-1002';
      if (command === 'last') demo = 'last 5';
      if (command === 'cancel') demo = 'cancel INV-1002';
      handleSendCommand(null as any, demo);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">WhatsApp Business Hub</h2>
          <p className="text-xs text-slate-400">onboard once on the web, run the business from chat</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full border border-emerald-500/30 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" />
            <span>Cloud API Connected</span>
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-4">
        <button
          onClick={() => setActiveSubTab('simulator')}
          className={`pb-2.5 text-xs font-semibold border-b-2 transition cursor-pointer ${
            activeSubTab === 'simulator'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          WhatsApp Merchant Bot Simulator
        </button>
        <button
          onClick={() => setActiveSubTab('staff')}
          className={`pb-2.5 text-xs font-semibold border-b-2 transition cursor-pointer ${
            activeSubTab === 'staff'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Linked Phone Numbers (Staff)
        </button>
      </div>

      {activeSubTab === 'simulator' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Instructions and Command Helper */}
          <div className="space-y-4">
            <div className="glass-card p-5 rounded-2xl space-y-3 border border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">WhatsApp Connection</h3>
                  <p className="text-xs text-slate-400">{whatsapp?.display_phone_number || '+254 712 345 678'}</p>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Meta Account ID:</span>
                  <span className="font-mono text-slate-200">waba_91823746</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Active Session:</span>
                  <span className="text-emerald-400 font-semibold">24h Window Open</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Security Gate:</span>
                  <span className="text-cyan-400 font-semibold">Step-Up Enabled</span>
                </div>
              </div>
            </div>

            <div className="glass-card p-5 rounded-2xl bg-gradient-to-br from-slate-900 to-emerald-950/40 text-xs space-y-3 border border-emerald-500/20">
              <div className="flex items-center gap-2 text-emerald-400 font-bold">
                <Sparkles className="w-4 h-4" />
                <span>Deterministic Grammar Guide (§8.1)</span>
              </div>
              <p className="text-slate-300">Test the exact message commands parsed by the backend below:</p>
              <div className="space-y-2">
                <button
                  onClick={() => setCommandText('request 2500 for INV-1002')}
                  className="w-full text-left p-2.5 bg-slate-950/80 hover:bg-slate-950 rounded-xl font-mono text-[11px] text-emerald-300 transition border border-slate-800 hover:border-emerald-500/30 cursor-pointer block"
                >
                  <p className="font-semibold text-white">request &lt;amount&gt; for &lt;ref&gt;</p>
                  <p className="text-[10px] text-slate-400">Create a request (Prompt confirmation if &gt;= 1,000)</p>
                </button>

                <button
                  onClick={() => setCommandText('today')}
                  className="w-full text-left p-2.5 bg-slate-950/80 hover:bg-slate-950 rounded-xl font-mono text-[11px] text-emerald-300 transition border border-slate-800 hover:border-emerald-500/30 cursor-pointer block"
                >
                  <p className="font-semibold text-white">today</p>
                  <p className="text-[10px] text-slate-400">Get running totals, pending counts, and volumes</p>
                </button>

                <button
                  onClick={() => setCommandText('status INV-1002')}
                  className="w-full text-left p-2.5 bg-slate-950/80 hover:bg-slate-950 rounded-xl font-mono text-[11px] text-emerald-300 transition border border-slate-800 hover:border-emerald-500/30 cursor-pointer block"
                >
                  <p className="font-semibold text-white">status &lt;ref&gt;</p>
                  <p className="text-[10px] text-slate-400">Verify status of a specific payment link</p>
                </button>

                <button
                  onClick={() => setCommandText('cancel INV-1002')}
                  className="w-full text-left p-2.5 bg-slate-950/80 hover:bg-slate-950 rounded-xl font-mono text-[11px] text-emerald-300 transition border border-slate-800 hover:border-emerald-500/30 cursor-pointer block"
                >
                  <p className="font-semibold text-white">cancel &lt;ref&gt;</p>
                  <p className="text-[10px] text-slate-400">Cancel request (Requires step-up if attempt in-flight)</p>
                </button>
              </div>
            </div>
          </div>

          {/* Chat Simulator */}
          <div className="lg:col-span-2 glass-card rounded-2xl overflow-hidden flex flex-col h-[520px] border border-slate-800">
            {/* Chat Header */}
            <div className="p-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-white">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Imara Pay Merchant Bot</h4>
                  <p className="text-[11px] text-emerald-400 font-medium">Online • v3.0 Cloud API</p>
                </div>
              </div>
            </div>

            {/* Chat Body */}
            <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-[#0B141A]/95">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex flex-col ${msg.sender === 'merchant' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-md p-3.5 rounded-2xl text-xs whitespace-pre-wrap ${
                      msg.sender === 'merchant'
                        ? 'bg-emerald-700 text-white rounded-tr-none shadow-md'
                        : 'bg-slate-800 text-slate-100 rounded-tl-none border border-slate-700 shadow-md'
                    }`}
                  >
                    {msg.text}

                    {/* WhatsApp Interactive Message Rendering */}
                    {msg.payload?.type === 'interactive' && (
                      <div className="mt-3 pt-3 border-t border-slate-700/60 space-y-2">
                        {/* Interactive Buttons (confirm/edit) */}
                        {msg.payload.interactive.type === 'button' && (
                          <div className="flex flex-wrap gap-2 justify-center">
                            {msg.payload.interactive.action.buttons.map((btn: any) => (
                              <button
                                key={btn.reply.id}
                                onClick={() => handleInteractiveClick(btn.reply.id)}
                                className="px-4 py-2 bg-slate-900 hover:bg-slate-950 text-slate-200 text-[11px] font-bold rounded-lg border border-slate-700 transition cursor-pointer"
                              >
                                {btn.reply.title}
                              </button>
                            ))}
                          </div>
                        )}

                        {/* Interactive List (help menu) */}
                        {msg.payload.interactive.type === 'list' && (
                          <div className="space-y-1 bg-slate-900/60 p-2.5 rounded-xl border border-slate-700/50">
                            <p className="text-[10px] text-emerald-400 font-semibold mb-1">
                              {msg.payload.interactive.action.button}
                            </p>
                            {msg.payload.interactive.action.sections.map((sec: any, sIdx: number) => (
                              <div key={sIdx} className="space-y-1">
                                <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider mt-1">{sec.title}</p>
                                {sec.rows.map((row: any) => (
                                  <button
                                    key={row.id}
                                    onClick={() => handleInteractiveClick(row.id)}
                                    className="w-full text-left p-2 hover:bg-slate-950/80 rounded-lg transition text-[11px] flex justify-between items-center group cursor-pointer"
                                  >
                                    <span className="font-medium text-slate-200 group-hover:text-emerald-400">{row.title}</span>
                                    <span className="text-[9px] text-slate-500 font-mono">{row.description}</span>
                                  </button>
                                ))}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* CTA URL Actions */}
                        {msg.payload.interactive.type === 'cta_url' && (
                          <div className="pt-1">
                            <a
                              href={msg.payload.interactive.action.parameters.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="w-full py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-center font-bold rounded-lg transition block text-[11px]"
                            >
                              {msg.payload.interactive.action.parameters.display_text}
                            </a>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.time}</span>
                </div>
              ))}
            </div>

            {/* Chat Input */}
            <form onSubmit={(e) => handleSendCommand(e)} className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2">
              <input
                type="text"
                value={commandText}
                onChange={(e) => setCommandText(e.target.value)}
                placeholder="Type WhatsApp command (e.g. today)..."
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                disabled={isSending}
                className="p-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      )}

      {activeSubTab === 'staff' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Bind Number Form */}
          <div className="space-y-4">
            <div className="glass-card p-5 rounded-2xl border border-slate-800">
              <h3 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-emerald-400" />
                <span>Link Phone Number</span>
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Bind a phone number to your business. Requires OTP verification round-trip via WhatsApp.
              </p>

              {staffError && (
                <div className="p-3 mb-4 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400 flex items-start gap-2">
                  <ShieldAlert className="w-4 h-4 shrink-0" />
                  <span>{staffError}</span>
                </div>
              )}

              {staffSuccess && (
                <div className="p-3 mb-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-400 flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <div>
                    <p>{staffSuccess}</p>
                    {devOtp && (
                      <p className="mt-1 font-semibold text-emerald-300 font-mono">
                        [DEV MODE] OTP Code: {devOtp}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {!otpVerifyPhone ? (
                <form onSubmit={handleAddPhone} className="space-y-3">
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-1">Phone Number (E.164)</label>
                    <input
                      type="text"
                      placeholder="e.g. +254 712 345678"
                      value={newPhone}
                      onChange={(e) => setNewPhone(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-1">Staff Role</label>
                    <select
                      value={newRole}
                      onChange={(e) => setNewRole(e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                    >
                      <option value="STAFF">Staff (Request payments only)</option>
                      <option value="ADMIN">Admin (Request & check summaries)</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    className="w-full py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition flex items-center justify-center gap-2 text-xs mt-2 cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Send Verification Code</span>
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyOTP} className="space-y-3">
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-1">
                      Enter Verification Code
                    </label>
                    <input
                      type="text"
                      placeholder="6-digit code"
                      maxLength={6}
                      value={otpInput}
                      onChange={(e) => setOtpInput(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white font-mono tracking-widest text-center focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold transition text-xs cursor-pointer"
                  >
                    Confirm OTP
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setOtpVerifyPhone(null);
                      setStaffSuccess('');
                      setDevOtp(null);
                    }}
                    className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-950 text-slate-300 border border-slate-800 transition text-xs cursor-pointer"
                  >
                    Cancel
                  </button>
                </form>
              )}
            </div>
          </div>

          {/* List of Bound Identities */}
          <div className="lg:col-span-2 glass-card p-5 rounded-2xl border border-slate-800">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <Key className="w-4 h-4 text-emerald-400" />
              <span>Active Access Permissions</span>
            </h3>

            <div className="space-y-3">
              {identities.length === 0 ? (
                <p className="text-xs text-slate-400 py-6 text-center">No linked phone numbers found.</p>
              ) : (
                identities.map((id) => (
                  <div
                    key={id.id}
                    className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-4 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center font-bold text-slate-300 text-xs">
                        {id.role[0]}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-white">{id.phone_number}</span>
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
                            id.role === 'OWNER' ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' :
                            id.role === 'ADMIN' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' :
                            'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                          }`}>
                            {id.role}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          Linked on: {id.bound_at ? new Date(id.bound_at).toLocaleDateString() : 'N/A'}
                        </p>
                      </div>
                    </div>

                    {id.role !== 'OWNER' && (
                      <button
                        onClick={() => handleRevokePhone(id.id)}
                        className="p-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition cursor-pointer"
                        title="Revoke Number Access"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
