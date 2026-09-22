import React, { useState, useEffect } from 'react';
import AppShell from '../components/layout/AppShell';
import { useAuthStore } from '../store/authStore';
import { getGreeting } from '../utils/helpers';
import { Mail, Search, FileText, Bot, Clock, RefreshCw, AlertCircle, CheckCircle2, Download, ArrowRight } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { gmailApi, SyncStats, SyncLogEntry } from '../api/gmail';
import { authApi } from '../api/auth';
import client from '../api/client';
import { Link } from 'react-router-dom';

export default function DashboardPage() {
  const { user, setUser } = useAuthStore();
  const [stats, setStats] = useState<SyncStats>({
    total_emails: 0,
    total_threads: 0,
    total_attachments: 0,
    total_size_bytes: 0,
    latest_sync: null
  });
  const [syncLogs, setSyncLogs] = useState<SyncLogEntry[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const statsData = await gmailApi.getSyncStats();
      setStats(statsData);
      
      const logsData = await gmailApi.getSyncStatus(5);
      setSyncLogs(logsData);

      if (statsData.latest_sync && statsData.latest_sync.status === 'running') {
        setIsSyncing(true);
      } else {
        setIsSyncing(false);
      }
    } catch (e) {
      console.error("Failed to load dashboard sync stats:", e);
    }
  };

  useEffect(() => {
    loadData();

    const params = new URLSearchParams(window.location.search);
    if (params.get('sync_connected') === 'true') {
      setSuccessMsg("Gmail account connected successfully!");
      authApi.getMe().then(updatedUser => {
        setUser(updatedUser);
      });
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get('error')) {
      setErrorMsg("Failed to connect Gmail. Please try again.");
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSyncing) {
      interval = setInterval(async () => {
        try {
          const statsData = await gmailApi.getSyncStats();
          setStats(statsData);
          
          const logsData = await gmailApi.getSyncStatus(5);
          setSyncLogs(logsData);
          
          if (statsData.latest_sync && statsData.latest_sync.status !== 'running') {
            setIsSyncing(false);
            if (statsData.latest_sync.status === 'success') {
              setSuccessMsg(`Sync complete! ${statsData.latest_sync.emails_synced} emails and ${statsData.latest_sync.attachments_downloaded} attachments processed.`);
            } else {
              setErrorMsg(`Sync failed: ${statsData.latest_sync.error_message || "Unknown error"}`);
            }
            clearInterval(interval);
          }
        } catch (e) {
          console.error("Error polling sync status:", e);
          setIsSyncing(false);
          clearInterval(interval);
        }
      }, 3500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSyncing]);

  const handleConnectGmail = async () => {
    try {
      setErrorMsg(null);
      setSuccessMsg(null);
      const res = await authApi.getGoogleOAuthUrl();
      if (res.url) {
        window.location.href = res.url;
      }
    } catch (e: any) {
      setErrorMsg(e.response?.data?.detail || "Failed to initialize Google connection.");
    }
  };

  const handleTriggerSync = async () => {
    try {
      setErrorMsg(null);
      setSuccessMsg(null);
      setIsSyncing(true);
      await gmailApi.triggerSync();
      setSuccessMsg("Email sync started in background...");
      loadData();
    } catch (e: any) {
      setIsSyncing(false);
      setErrorMsg(e.response?.data?.detail || "Failed to start sync.");
    }
  };

  const handleDownloadEmails = async () => {
    try {
      setErrorMsg(null);
      setSuccessMsg(null);
      const response = await client.get('/api/v1/gmail/export', {
        responseType: 'blob',
      });
      
      if (response.status === 204) {
        setSuccessMsg("All synced emails have already been downloaded. No new emails to export!");
        return;
      }
      
      const contentDisp = response.headers['content-disposition'] || '';
      const filenameMatch = contentDisp.match(/filename="?([^"]+)"?/);
      const downloadFilename = filenameMatch ? filenameMatch[1] : 'emails_export.zip';
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', downloadFilename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setSuccessMsg("Emails exported successfully!");
      await loadData();
    } catch (e: any) {
      console.error("Export failed:", e);
      setErrorMsg("Failed to export emails.");
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              {getGreeting()}, {user?.full_name.split(' ')[0]}
            </h1>
            <p className="text-slate-500 text-sm mt-0.5">Here is your inbox summary for today.</p>
          </div>
          {user?.is_gmail_connected && (
            <Button 
              variant="secondary" 
              size="sm"
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-blue-600' : ''}`} />}
              onClick={loadData}
              disabled={isSyncing}
            >
              Refresh
            </Button>
          )}
        </div>

        {/* Feedback Alerts */}
        {errorMsg && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 flex items-start gap-3 shadow-xs">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-600 mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Notice</p>
              <p className="text-xs text-rose-700 mt-0.5">{errorMsg}</p>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-start gap-3 shadow-xs">
            <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-600 mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Success</p>
              <p className="text-xs text-emerald-700 mt-0.5">{successMsg}</p>
            </div>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            icon={Mail} 
            label="Synced Emails" 
            value={stats.total_emails.toLocaleString()} 
            subtext={user?.is_gmail_connected ? "Gmail Connected" : "Connection Required"} 
            isPositive={user?.is_gmail_connected}
          />
          <StatCard 
            icon={Search} 
            label="Email Threads" 
            value={stats.total_threads.toLocaleString()} 
            subtext="Organized conversations" 
            isPositive={true}
          />
          <StatCard 
            icon={FileText} 
            label="Attachments Processed" 
            value={stats.total_attachments.toLocaleString()} 
            subtext={formatSize(stats.total_size_bytes)} 
            isPositive={true}
          />
          <StatCard 
            icon={Bot} 
            label="AI Assistant" 
            value={stats.total_emails > 0 ? "Ready" : "Waiting for Sync"} 
            subtext="Ready to answer questions" 
            isPositive={stats.total_emails > 0}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Main Action Area */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Sync Setup Card */}
            {!user?.is_gmail_connected ? (
              <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-xs relative overflow-hidden">
                <div className="flex items-center gap-2.5 mb-3">
                  <div className="p-2 rounded-lg bg-amber-50 text-amber-600">
                    <Mail className="w-5 h-5" />
                  </div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Connect Your Gmail
                  </h2>
                </div>
                <p className="text-slate-600 text-sm mb-6 max-w-lg leading-relaxed">
                  Link your Gmail account to start searching and asking questions. Only emails with the label <strong className="text-slate-900 font-semibold">"InboxIQ"</strong> will be synced.
                </p>
                <Button 
                  variant="primary" 
                  onClick={handleConnectGmail}
                >
                  Connect Gmail Account
                </Button>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-xs">
                <div className="flex items-center gap-2.5 mb-3">
                  <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Gmail Connected
                  </h2>
                </div>
                <p className="text-slate-600 text-sm mb-6 max-w-lg leading-relaxed">
                  Your inbox is active and monitoring emails with the label <strong className="text-slate-900 font-semibold">"InboxIQ"</strong>. Click sync below to update your latest messages and attachments.
                </p>
                <div className="flex flex-wrap gap-3 items-center">
                  <Button 
                    variant="primary" 
                    leftIcon={<RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />}
                    onClick={handleTriggerSync}
                    disabled={isSyncing}
                  >
                    {isSyncing ? "Syncing Inbox..." : "Sync Now"}
                  </Button>

                  {!isSyncing && stats.total_emails > 0 && (
                    <Button
                      variant="secondary"
                      leftIcon={<Download className="w-4 h-4" />}
                      onClick={handleDownloadEmails}
                    >
                      {stats.undownloaded_emails !== undefined && stats.undownloaded_emails > 0
                        ? `Export Next 50 Emails (${stats.undownloaded_emails} remaining)`
                        : "Export Emails (.docx)"}
                    </Button>
                  )}

                  {isSyncing && (
                    <span className="text-xs text-slate-500 animate-pulse font-medium">
                      {stats.latest_sync && stats.latest_sync.total_emails_found
                        ? `Syncing: ${stats.latest_sync.emails_synced} / ${stats.latest_sync.total_emails_found} emails in batches of 50...`
                        : "Syncing emails continuously in batches of 50..."}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Quick Action Navigation Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Link 
                to="/chat"
                className="bg-white border border-slate-200 hover:border-blue-300 hover:shadow-md p-5 rounded-2xl transition-all group flex flex-col justify-between"
              >
                <div>
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                    <Bot className="w-5 h-5" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-base mb-1">AI Assistant Chat</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Ask questions and get instant factual answers backed by your synced emails and documents.
                  </p>
                </div>
                <div className="mt-4 flex items-center gap-1.5 text-xs font-semibold text-blue-600">
                  <span>Open AI Chat</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>

              <Link 
                to="/search"
                className="bg-white border border-slate-200 hover:border-blue-300 hover:shadow-md p-5 rounded-2xl transition-all group flex flex-col justify-between"
              >
                <div>
                  <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                    <Search className="w-5 h-5" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-base mb-1">Search Inbox</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Search across all your emails, scanned documents, and attachments with filters.
                  </p>
                </div>
                <div className="mt-4 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                  <span>Search Documents</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            </div>

          </div>

          {/* Right Sidebar - Recent Activity */}
          <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-xs flex flex-col h-full min-h-[380px]">
            <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              Recent Sync Activity
            </h2>
            
            <div className="flex-1 space-y-3 overflow-y-auto max-h-[340px] pr-1">
              {syncLogs.length > 0 ? (
                syncLogs.map((log) => (
                  <div key={log.id} className="p-3 bg-slate-50 border border-slate-100 rounded-xl space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wide">
                        {log.sync_type === 'manual' ? 'Manual Sync' : 'Daily Sync'}
                      </span>
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                        log.status === 'success' ? 'bg-emerald-100 text-emerald-700' :
                        log.status === 'failed' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700 animate-pulse'
                      }`}>
                        {log.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      {new Date(log.started_at).toLocaleString()}
                    </div>
                    {log.status === 'running' && (
                      <div className="text-xs text-amber-700 flex justify-between pt-1">
                        <span>{log.emails_synced} {log.total_emails_found ? `/ ${log.total_emails_found}` : ''} synced</span>
                        <span>{log.attachments_downloaded} attachments</span>
                      </div>
                    )}
                    {log.status === 'success' && (
                      <div className="text-xs text-slate-600 flex justify-between pt-1">
                        <span>{log.emails_synced} emails</span>
                        <span>{log.attachments_downloaded} attachments</span>
                      </div>
                    )}
                    {log.status === 'failed' && log.error_message && (
                      <div className="text-[11px] text-rose-600 bg-rose-50 p-1.5 rounded border border-rose-100 break-words mt-1">
                        {log.error_message}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center p-6">
                  <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center mb-3">
                    <Clock className="w-5 h-5 text-slate-400" />
                  </div>
                  <p className="text-slate-800 font-medium text-xs mb-0.5">No sync runs yet</p>
                  <p className="text-[11px] text-slate-400">Sync your inbox to view execution history.</p>
                </div>
              )}
            </div>
          </div>

        </div>

      </div>
    </AppShell>
  );
}

function StatCard({ icon: Icon, label, value, subtext, isPositive = true }: { icon: any, label: string, value: string, subtext: string, isPositive?: boolean }) {
  return (
    <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-xs hover:border-slate-300 transition-all">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
        <div className="p-2 rounded-xl bg-blue-50 text-blue-600">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-2xl font-extrabold text-slate-900 mb-1">{value}</div>
      <div className={`text-xs font-medium ${isPositive ? 'text-emerald-600' : 'text-amber-600'}`}>
        {subtext}
      </div>
    </div>
  );
}
