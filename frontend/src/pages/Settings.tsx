import React, { useState, useEffect } from 'react';
import {
  Database,
  Eye,
  GitFork,
  Cpu,
  Save,
  CheckCircle,
  HelpCircle,
  Mail,
  RefreshCw,
  LogOut,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { gmailService } from '../services/api';

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrl] = useState(import.meta.env.VITE_API_URL || 'http://localhost:5000');
  const [useMock, setUseMock] = useState(true);
  const [modelType, setModelType] = useState('gemini-1.5-pro');
  const [physicsSpeed, setPhysicsSpeed] = useState('medium');
  const [apiKey, setApiKey] = useState('••••••••••••••••••••••••••••••••');

  const [showSavedToast, setShowSavedToast] = useState(false);

  // Gmail integration state
  const [gmailConfigured, setGmailConfigured] = useState(false);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailEmail, setGmailEmail] = useState<string | null>(null);
  const [gmailState, setGmailState] = useState<string | null>(null);
  const [gmailLoading, setGmailLoading] = useState(false);
  const [gmailError, setGmailError] = useState<string | null>(null);
  const [gmailSuccess, setGmailSuccess] = useState<string | null>(null);
  const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSavedToast(true);
    setTimeout(() => setShowSavedToast(false), 3000);
  };

  // Load Gmail status on mount
  useEffect(() => {
    const loadGmailStatus = async () => {
      try {
        const savedState = sessionStorage.getItem('gmailOAuthState');
        const status = await gmailService.getStatus(savedState || undefined);
        setGmailConfigured(status.configured);
        setGmailConnected(status.connected);
        setGmailEmail(status.email || null);
        if (status.connected && savedState) {
          setGmailState(savedState);
        } else {
          sessionStorage.removeItem('gmailOAuthState');
          setGmailState(null);
        }
      } catch (err) {
        console.error('Failed to load Gmail status:', err);
      }
    };
    loadGmailStatus();
  }, []);

  const handleSwitchGmailAccount = async () => {
    if (!gmailState) {
      setGmailError('No Gmail account is currently connected.');
      return;
    }

    setGmailLoading(true);
    setGmailError(null);
    setGmailSuccess(null);

    try {
      const oldState = gmailState;
      const newState = await gmailService.switchAccount(oldState);
      sessionStorage.setItem('gmailOAuthState', newState);
      setGmailState(newState);
      setGmailSuccess('Gmail account switched successfully.');
      // Reload status to get new email
      const status = await gmailService.getStatus(newState);
      setGmailConnected(status.connected);
      setGmailEmail(status.email || null);
    } catch (err) {
      setGmailError(err instanceof Error ? err.message : 'Failed to switch Gmail account.');
    } finally {
      setGmailLoading(false);
    }
  };

  const handleDisconnectGmail = async () => {
    if (!gmailState) {
      setGmailError('No Gmail account is currently connected.');
      return;
    }

    setGmailLoading(true);
    setGmailError(null);
    setGmailSuccess(null);

    try {
      await gmailService.disconnect(gmailState);
      sessionStorage.removeItem('gmailOAuthState');
      setGmailState(null);
      setGmailConnected(false);
      setGmailEmail(null);
      setGmailSuccess('Gmail account disconnected successfully.');
      setShowDisconnectConfirm(false);
    } catch (err) {
      setGmailError(err instanceof Error ? err.message : 'Failed to disconnect Gmail account.');
    } finally {
      setGmailLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300">
      
      {/* HEADER */}
      <div className="space-y-2">
        <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight">System Settings</h1>
        <p className="text-sm text-slate-400">
          Configure API connection parameters, customize visual physics, and alter AI LLM models.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        
        {/* API LAYER CONNECTIONS CARD */}
        <section className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-dark-border/40 pb-3">
            <Database size={14} className="text-brand-500" />
            Backend Connection API
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 block">Service Base URL</label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://localhost:5000"
                className="w-full bg-slate-900 border border-dark-border focus:border-brand-500 rounded-xl py-2 px-3.5 text-xs text-slate-100 placeholder-slate-500 outline-none transition-colors"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 block">Ingestion Service Mode</label>
              <div className="flex items-center gap-3 h-9">
                <button
                  type="button"
                  onClick={() => setUseMock(true)}
                  className={`flex-1 py-1.5 px-3 rounded-lg border text-xs font-semibold transition-all duration-150 ${
                    useMock 
                      ? 'bg-brand-600/10 border-brand-500/40 text-brand-400' 
                      : 'bg-slate-900 border-dark-border text-slate-400'
                  }`}
                >
                  Mock Sandbox
                </button>
                <button
                  type="button"
                  onClick={() => setUseMock(false)}
                  className={`flex-1 py-1.5 px-3 rounded-lg border text-xs font-semibold transition-all duration-150 ${
                    !useMock 
                      ? 'bg-brand-600/10 border-brand-500/40 text-brand-400' 
                      : 'bg-slate-900 border-dark-border text-slate-400'
                  }`}
                >
                  Live Server
                </button>
              </div>
            </div>
          </div>
          
          <div className="p-3 rounded-xl bg-slate-900 border border-dark-border text-[11px] text-slate-400 flex items-start gap-2">
            <HelpCircle size={14} className="text-brand-500 shrink-0 mt-0.5" />
            <span>Mock Sandbox executes processing client-side. Live Server attempts REST connections to POST /api/resumes/upload.</span>
          </div>
        </section>

        {/* GMAIL INTEGRATION CARD */}
        <section className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-dark-border/40 pb-3">
            <Mail size={14} className="text-brand-500" />
            Gmail Integration
          </h3>

          <div className="space-y-3">
            {!gmailConfigured && (
              <div className="p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-[11px] text-yellow-300 flex items-start gap-2">
                <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                <span>Gmail OAuth is not configured. Contact your administrator to set up Google OAuth credentials.</span>
              </div>
            )}

            {gmailConfigured && !gmailConnected && (
              <div className="p-3 rounded-xl bg-slate-900 border border-dark-border text-[11px] text-slate-400">
                No Gmail account is currently connected. Visit the Gmail Import page to connect an account.
              </div>
            )}

            {gmailConfigured && gmailConnected && (
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-dark-border">
                  <div className="flex items-center gap-3">
                    <CheckCircle size={16} className="text-emerald-400" />
                    <div>
                      <p className="text-xs font-semibold text-white">Connected Gmail Account</p>
                      <p className="text-[11px] text-slate-400">{gmailEmail || 'Unknown'}</p>
                    </div>
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-full">
                    Connected
                  </span>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleSwitchGmailAccount}
                    disabled={gmailLoading}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg border border-dark-border bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-all duration-150 disabled:opacity-50"
                  >
                    {gmailLoading ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <RefreshCw size={14} />
                    )}
                    Switch Account
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowDisconnectConfirm(true)}
                    disabled={gmailLoading}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-xs font-semibold text-red-300 transition-all duration-150 disabled:opacity-50"
                  >
                    <LogOut size={14} />
                    Disconnect
                  </button>
                </div>
              </div>
            )}

            {gmailError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-[11px] text-red-300 flex items-start gap-2">
                <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                <span>{gmailError}</span>
              </div>
            )}

            {gmailSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-[11px] text-emerald-300 flex items-start gap-2">
                <CheckCircle size={14} className="shrink-0 mt-0.5" />
                <span>{gmailSuccess}</span>
              </div>
            )}
          </div>
        </section>

        {/* AI LLM MODELS ENGINE OPTIONS */}
        <section className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-dark-border/40 pb-3">
            <Cpu size={14} className="text-brand-500" />
            AI Parsing Engine
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 block">LLM Processing Core</label>
              <select
                value={modelType}
                onChange={(e) => setModelType(e.target.value)}
                className="w-full bg-slate-900 border border-dark-border focus:border-brand-500 rounded-xl py-2 px-3 text-xs text-slate-300 outline-none"
              >
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (Google)</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash (Google)</option>
                <option value="gpt-4o">GPT-4o (OpenAI)</option>
                <option value="llama-3-70b">Llama 3 70B (Meta)</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 block">Provider API Secret Token</label>
              <div className="relative">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full bg-slate-900 border border-dark-border focus:border-brand-500 rounded-xl py-2 pl-3.5 pr-10 text-xs text-slate-100 outline-none transition-colors"
                />
                <Eye size={14} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 cursor-pointer hover:text-slate-300" />
              </div>
            </div>
          </div>
        </section>

        {/* GRAPH PHYSICS INTERACTIVE PROPERTIES */}
        <section className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5 border-b border-dark-border/40 pb-3">
            <GitFork size={14} className="text-brand-500" />
            Graph Dynamics Settings
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 block">Physics Update Iteration Speed</label>
              <select
                value={physicsSpeed}
                onChange={(e) => setPhysicsSpeed(e.target.value)}
                className="w-full bg-slate-900 border border-dark-border focus:border-brand-500 rounded-xl py-2 px-3 text-xs text-slate-300 outline-none"
              >
                <option value="slow">Slow Damping (Low CPU)</option>
                <option value="medium">Standard Converge (Balanced)</option>
                <option value="fast">High-Fidelity Realtime (High CPU)</option>
              </select>
            </div>

            <div className="space-y-2 flex flex-col justify-end">
              <div className="flex items-center justify-between p-2.5 rounded-xl border border-dark-border/40 bg-slate-950 text-xs text-slate-400">
                <span>Enable Graph Node Collisions</span>
                <input type="checkbox" defaultChecked className="accent-brand-600 rounded cursor-pointer" />
              </div>
            </div>
          </div>
        </section>

        {/* ACTION SUBMIT FOOTER */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            className="bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs py-3 px-6 rounded-xl flex items-center gap-1.5 shadow-lg shadow-brand-700/25 transition-all duration-150"
          >
            <Save size={14} />
            <span>Save System Preferences</span>
          </button>
        </div>

      </form>

      {/* SUCCESS POPUP TOAST */}
      {showSavedToast && (
        <div className="fixed bottom-6 right-6 z-50 glass-panel rounded-2xl p-4 border-l-4 border-emerald-500 shadow-xl flex items-center gap-2.5 animate-in slide-in-from-bottom duration-300">
          <CheckCircle size={18} className="text-emerald-400 shrink-0" />
          <div>
            <h4 className="text-xs font-bold text-white">Preferences Saved</h4>
            <p className="text-[10px] text-slate-400">Local workspace configurations updated</p>
          </div>
        </div>
      )}

      {/* DISCONNECT CONFIRMATION MODAL */}
      {showDisconnectConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="glass-panel rounded-2xl p-6 max-w-md w-full mx-4 space-y-4 animate-in zoom-in duration-200">
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="text-yellow-500 shrink-0 mt-0.5" />
              <div className="space-y-2">
                <h3 className="text-sm font-bold text-white">Disconnect Gmail Account?</h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  This will disconnect <span className="font-semibold text-white">{gmailEmail || 'your Gmail account'}</span>. You will need to reconnect Gmail to use the Gmail Import feature. Previously imported resumes and candidate data will remain unchanged.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowDisconnectConfirm(false)}
                disabled={gmailLoading}
                className="px-4 py-2 rounded-lg border border-dark-border bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition-all duration-150 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDisconnectGmail}
                disabled={gmailLoading}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-xs font-semibold text-white transition-all duration-150 disabled:opacity-50 flex items-center gap-2"
              >
                {gmailLoading ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <LogOut size={14} />
                )}
                Disconnect
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
