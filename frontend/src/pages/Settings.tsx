import React, { useState } from 'react';
import { 
  Database, 
  Eye, 
  GitFork, 
  Cpu, 
  Save, 
  CheckCircle,
  HelpCircle
} from 'lucide-react';

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrl] = useState(import.meta.env.VITE_API_URL || 'http://localhost:5000');
  const [useMock, setUseMock] = useState(true);
  const [modelType, setModelType] = useState('gemini-1.5-pro');
  const [physicsSpeed, setPhysicsSpeed] = useState('medium');
  const [apiKey, setApiKey] = useState('••••••••••••••••••••••••••••••••');
  
  const [showSavedToast, setShowSavedToast] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSavedToast(true);
    setTimeout(() => setShowSavedToast(false), 3000);
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

    </div>
  );
};
