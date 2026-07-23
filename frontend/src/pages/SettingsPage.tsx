import React, { useState, useEffect } from 'react';
import AppShell from '../components/layout/AppShell';
import { auditApi, SystemStatusResponse } from '../api/audit';
import { gmailApi } from '../api/gmail';
import { Settings, Server, Cpu, Mail, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function SettingsPage() {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [gmailLabel, setGmailLabel] = useState("");
  const [updatingLabel, setUpdatingLabel] = useState(false);
  const [labelSuccess, setLabelSuccess] = useState(false);
  const [labelError, setLabelError] = useState("");

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await auditApi.getSystemStatus();
      setStatus(res);
      if (res && res.active_label) {
        setGmailLabel(res.active_label);
      }
    } catch (err) {
      console.error('Failed to load system status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateLabel = async () => {
    if (!gmailLabel.trim()) return;
    setUpdatingLabel(true);
    setLabelSuccess(false);
    setLabelError("");
    try {
      await gmailApi.updateGmailLabel(gmailLabel.trim());
      setLabelSuccess(true);
      // Refresh status info to show updated label
      const res = await auditApi.getSystemStatus();
      setStatus(res);
    } catch (err: any) {
      console.error('Failed to update Gmail label:', err);
      setLabelError(err.response?.data?.detail || "Failed to update sync label.");
    } finally {
      setUpdatingLabel(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 py-2 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between py-2 border-b border-white/10">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-amber-500" />
              System Settings & Configurations
            </h1>
            <p className="text-xs text-slate-400">View active AI models, customize sync configurations, and check service health</p>
          </div>
          <button
            onClick={loadStatus}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-xs text-white font-medium flex items-center space-x-1.5 transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Health</span>
          </button>
        </div>

        {/* Gmail Sync Settings */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5 space-y-4 shadow-xl">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2 border-b border-white/10 pb-3">
            <Mail className="w-4 h-4 text-amber-500" />
            Gmail Sync Target Configuration
          </h2>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="gmail-label-input" className="text-xs text-slate-400 font-medium">Custom Sync Label Name</label>
              <div className="flex gap-2">
                <input
                  id="gmail-label-input"
                  type="text"
                  value={gmailLabel}
                  onChange={(e) => setGmailLabel(e.target.value)}
                  placeholder="e.g. Director's AI Assistant"
                  className="bg-dark-bg border border-white/10 rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500/50 flex-1 transition-all"
                />
                <button
                  onClick={handleUpdateLabel}
                  disabled={updatingLabel || !gmailLabel.trim()}
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:bg-amber-800 text-xs font-semibold text-dark-bg rounded-xl transition-all"
                >
                  {updatingLabel ? 'Saving...' : 'Update Label'}
                </button>
              </div>
              <p className="text-[10px] text-slate-400">Only emails matching this label in your Gmail account will be imported.</p>
            </div>

            {labelSuccess && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 rounded-xl">
                <CheckCircle2 className="w-4 h-4" />
                <span>Sync label updated successfully!</span>
              </div>
            )}
            
            {labelError && (
              <div className="flex items-center gap-1.5 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 px-3 py-2 rounded-xl">
                <AlertCircle className="w-4 h-4" />
                <span>{labelError}</span>
              </div>
            )}
          </div>
        </div>

        {/* System Services Status */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5 space-y-4 shadow-xl">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2 border-b border-white/10 pb-3">
            <Server className="w-4 h-4 text-emerald-400" />
            Backend Infrastructure Health
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-3.5 rounded-xl bg-dark-bg border border-white/10 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">PostgreSQL Database</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-sm font-bold text-white uppercase">{status?.database_status || 'Operational'}</p>
            </div>

            <div className="p-3.5 rounded-xl bg-dark-bg border border-white/10 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">Redis Broker</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-sm font-bold text-white uppercase">{status?.redis_status || 'Operational'}</p>
            </div>

            <div className="p-3.5 rounded-xl bg-dark-bg border border-white/10 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">Celery Task Workers</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-sm font-bold text-white uppercase">{status?.celery_worker_status || 'Operational'}</p>
            </div>
          </div>
        </div>

        {/* AI & RAG Configuration */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5 space-y-4 shadow-xl">
          <h2 className="text-sm font-semibold text-white flex items-center gap-2 border-b border-white/10 pb-3">
            <Cpu className="w-4 h-4 text-purple-400" />
            AI & Vector Engine Configuration
          </h2>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center p-3 rounded-xl bg-dark-bg border border-white/10">
              <span className="text-slate-400 font-medium">Embedding Model</span>
              <span className="text-purple-300 font-mono font-semibold">{status?.vector_search_engine}</span>
            </div>

            <div className="flex justify-between items-center p-3 rounded-xl bg-dark-bg border border-white/10">
              <span className="text-slate-400 font-medium">Generative AI LLM</span>
              <span className="text-purple-300 font-mono font-semibold">{status?.llm_model}</span>
            </div>

            <div className="flex justify-between items-center p-3 rounded-xl bg-dark-bg border border-white/10">
              <span className="text-slate-400 font-medium">Currently Selected Label</span>
              <span className="text-amber-300 font-mono font-semibold">"{status?.active_label}"</span>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
