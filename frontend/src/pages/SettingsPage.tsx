import React, { useState } from 'react';
import AppShell from '../components/layout/AppShell';
import { useAuthStore } from '../store/authStore';
import { getInitials } from '../utils/helpers';
import { gmailApi } from '../api/gmail';
import { authApi } from '../api/auth';
import { 
  Settings, User, Mail, CheckCircle2, AlertCircle, 
  Tag, Info, ShieldCheck, Calendar, Unlink, Trash2, 
  AlertTriangle, X, RefreshCw
} from 'lucide-react';

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);
  const [deleteSyncedData, setDeleteSyncedData] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDisconnect = async () => {
    setDisconnecting(true);
    setErrorMessage(null);
    try {
      const res = await gmailApi.disconnectGmail(deleteSyncedData);
      try {
        const freshUser = await authApi.getMe();
        setUser(freshUser);
      } catch {
        if (user) {
          setUser({ ...user, is_gmail_connected: false });
        }
      }
      setShowDisconnectModal(false);
      setSuccessMessage(res.detail || "Gmail account has been permanently disconnected.");
    } catch (err: any) {
      console.error("Failed to disconnect Gmail:", err);
      setErrorMessage(err.response?.data?.detail || "Failed to disconnect Gmail account. Please try again.");
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto space-y-6 animate-fade-in pb-12">
        
        {/* Page Header */}
        <div className="pb-4 border-b border-slate-200">
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Settings className="w-5 h-5 text-blue-600" />
            Account & Sync Settings
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">Manage your profile, view Gmail integration status, and sync instructions</p>
        </div>

        {/* Feedback Alerts */}
        {successMessage && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-start gap-3 shadow-xs">
            <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-600 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-sm">Success</p>
              <p className="text-xs text-emerald-700 mt-0.5">{successMessage}</p>
            </div>
            <button onClick={() => setSuccessMessage(null)} className="text-emerald-500 hover:text-emerald-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 flex items-start gap-3 shadow-xs">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-600 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-sm">Notice</p>
              <p className="text-xs text-rose-700 mt-0.5">{errorMessage}</p>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* 1. Account Profile Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-5 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <User className="w-4 h-4 text-blue-600" />
              Profile Information
            </h2>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-semibold">
              <ShieldCheck className="w-3 h-3" />
              Active Account
            </span>
          </div>

          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-sm shrink-0">
              {user ? getInitials(user.full_name) : 'U'}
            </div>

            <div className="space-y-1.5 flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-bold text-slate-900 truncate">
                  {user?.full_name || 'User'}
                </h3>
              </div>

              <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                <span className="flex items-center gap-1 font-mono text-slate-600">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  {user?.email}
                </span>
                {user?.created_at && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    Member since {new Date(user.created_at).toLocaleDateString([], { month: 'short', year: 'numeric' })}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 2. Gmail Sync Configuration & Disconnect Option */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-5 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3 flex-wrap gap-2">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Mail className="w-4 h-4 text-blue-600" />
              Gmail Synchronization
            </h2>

            <div className="flex items-center gap-3">
              {user?.is_gmail_connected ? (
                <>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Connected
                  </span>
                  <button
                    onClick={() => {
                      setDeleteSyncedData(false);
                      setShowDisconnectModal(true);
                    }}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 transition-colors shadow-xs"
                    title="Permanently disconnect Gmail account"
                  >
                    <Unlink className="w-3.5 h-3.5" />
                    <span>Disconnect Gmail</span>
                  </button>
                </>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-[11px] font-semibold">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Connection Required
                </span>
              )}
            </div>
          </div>

          <div className="space-y-4">
            {/* Active Fixed Label Display */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-xs">
                  <Tag className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs text-slate-500 font-medium">Required Gmail Label</div>
                  <div className="text-base font-extrabold text-slate-900 flex items-center gap-1.5">
                    <span>InboxIQ</span>
                    <span className="text-xs font-semibold px-2 py-0.2 rounded bg-blue-100/70 text-blue-700">
                      Standard
                    </span>
                  </div>
                </div>
              </div>

              <div className="text-xs text-slate-500 bg-white border border-slate-200 px-3 py-1.5 rounded-lg font-mono">
                label:"InboxIQ"
              </div>
            </div>

            {/* Step-by-Step Instructions */}
            <div className="p-4.5 rounded-xl bg-blue-50/50 border border-blue-100 space-y-2.5">
              <div className="flex items-center gap-1.5 text-xs font-bold text-blue-900">
                <Info className="w-4 h-4 text-blue-600 shrink-0" />
                <span>How to sync your emails:</span>
              </div>
              <ol className="list-decimal list-inside space-y-2 text-xs text-slate-700 pl-1 leading-relaxed">
                <li>
                  Open your <strong className="text-slate-900">Gmail</strong> and create a label named <strong className="text-blue-700 font-semibold bg-white px-1.5 py-0.5 rounded border border-blue-200">InboxIQ</strong>.
                </li>
                <li>
                  Tag or apply the <strong className="text-slate-900">InboxIQ</strong> label to any emails, receipts, contracts, or attachments you want InboxIQ to analyze.
                </li>
                <li>
                  Go to your <strong className="text-slate-900">Dashboard</strong> and click the blue <strong className="text-blue-700 font-semibold">"Sync Now"</strong> button to import and analyze them.
                </li>
              </ol>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Only emails tagged with the <span className="font-semibold text-slate-600">"InboxIQ"</span> label in your Gmail are imported. This protects your privacy and keeps non-work personal emails excluded.
            </p>
          </div>
        </div>

        {/* 3. Subtle Clean Status Footer */}
        <div className="pt-2 flex items-center justify-between text-xs text-slate-400 px-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
            <span className="font-medium text-slate-500">All systems operational</span>
          </div>
          <span className="font-mono text-[11px]">InboxIQ v1.0.0</span>
        </div>

      </div>

      {/* ===================================================================== */}
      {/* DISCONNECT GMAIL CONFIRMATION MODAL                                   */}
      {/* ===================================================================== */}
      {showDisconnectModal && (
        <div 
          className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-fade-in"
          onClick={() => !disconnecting && setShowDisconnectModal(false)}
        >
          <div 
            className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 space-y-5 animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-900">
                  Disconnect Gmail Account?
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  This will immediately revoke InboxIQ's access to your Google account and stop all email synchronization.
                </p>
              </div>
            </div>

            {/* Data Wipe Option Checkbox */}
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
              <label className="flex items-start gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={deleteSyncedData}
                  onChange={(e) => setDeleteSyncedData(e.target.checked)}
                  disabled={disconnecting}
                  className="mt-0.5 rounded border-slate-300 text-rose-600 focus:ring-rose-500/20"
                />
                <div className="space-y-0.5">
                  <span className="text-xs font-semibold text-slate-800 block">
                    Also delete all synced data from InboxIQ
                  </span>
                  <span className="text-[11px] text-slate-500 block leading-relaxed">
                    Permanently purges all downloaded emails, attachments, and conversation history for your account. This cannot be undone.
                  </span>
                </div>
              </label>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-2.5 pt-1">
              <button
                type="button"
                onClick={() => setShowDisconnectModal(false)}
                disabled={disconnecting}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl transition-all shadow-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDisconnect}
                disabled={disconnecting}
                className="px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 rounded-xl transition-all shadow-xs flex items-center gap-1.5"
              >
                {disconnecting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Disconnecting...</span>
                  </>
                ) : (
                  <>
                    <Unlink className="w-3.5 h-3.5" />
                    <span>Confirm Disconnect</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
