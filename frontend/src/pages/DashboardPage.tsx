import React, { useState, useEffect } from 'react';
import AppShell from '../components/layout/AppShell';
import { useAuthStore } from '../store/authStore';
import { getGreeting } from '../utils/helpers';
import { Mail, Search, FileText, BarChart, ExternalLink, Bot, Clock, RefreshCw, AlertCircle, CheckCircle, Download } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { gmailApi, SyncStats, SyncLogEntry } from '../api/gmail';
import { authApi } from '../api/auth';
import client from '../api/client';

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

  // Load stats and log history
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

    // Check URL query parameters for connection success or error
    const params = new URLSearchParams(window.location.search);
    if (params.get('sync_connected') === 'true') {
      setSuccessMsg("Gmail account connected successfully!");
      // Refresh user context to ensure store knows Gmail is connected
      authApi.getMe().then(updatedUser => {
        setUser(updatedUser);
      });
      // Clean query params
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get('error')) {
      setErrorMsg("Failed to connect Gmail. Please try again.");
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Poll status when syncing is active
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
              setSuccessMsg(`Sync complete! Labeled emails: ${statsData.latest_sync.emails_synced}, Attachments: ${statsData.latest_sync.attachments_downloaded}`);
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
      const res = await gmailApi.triggerSync();
      setSuccessMsg("Synchronization started in background...");
      loadData();
    } catch (e: any) {
      setIsSyncing(false);
      setErrorMsg(e.response?.data?.detail || "Failed to start synchronization.");
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
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'new_emails.zip');
      document.body.appendChild(link);
      link.click();
      setSuccessMsg("New emails downloaded successfully!");
    } catch (e: any) {
      console.error("Export failed:", e);
      setErrorMsg("Failed to download email catalog.");
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
      <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              {getGreeting()}, {user?.full_name.split(' ')[0]}
            </h1>
            <p className="text-text-secondary mt-1">Here is your corporate memory overview for today.</p>
          </div>
          {user?.is_gmail_connected && (
            <Button 
              variant="secondary" 
              leftIcon={<RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />}
              onClick={loadData}
              disabled={isSyncing}
            >
              Refresh
            </Button>
          )}
        </div>

        {/* Feedback alerts */}
        {errorMsg && (
          <div className="p-4 bg-status-error/10 border border-status-error/20 rounded-xl text-status-error flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Action Failed</p>
              <p className="text-xs text-status-error/80 mt-0.5">{errorMsg}</p>
            </div>
          </div>
        )}

        {successMsg && (
          <div className="p-4 bg-status-success/10 border border-status-success/20 rounded-xl text-status-success flex items-start gap-3">
            <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Success</p>
              <p className="text-xs text-status-success/80 mt-0.5">{successMsg}</p>
            </div>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            icon={Mail} 
            label="Emails Synced" 
            value={stats.total_emails.toString()} 
            trend={user?.is_gmail_connected ? "Gmail Connected" : "Connection Required"} 
            trendDown={!user?.is_gmail_connected} 
          />
          <StatCard 
            icon={Search} 
            label="Active Threads" 
            value={stats.total_threads.toString()} 
            trend="Organized conversations" 
          />
          <StatCard 
            icon={FileText} 
            label="Attachments Synced" 
            value={stats.total_attachments.toString()} 
            trend={formatSize(stats.total_size_bytes)} 
          />
          <StatCard 
            icon={BarChart} 
            label="AI Memory Size" 
            value={stats.total_emails > 0 ? "Ready" : "Waiting for Sync"} 
            trend="RAG grounding layer" 
            trendDown={stats.total_emails === 0}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Main Action Area */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Sync Setup Card */}
            {!user?.is_gmail_connected ? (
              <div className="glass-panel p-6 rounded-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-primary-blue/10 rounded-full blur-2xl -mr-10 -mt-10" />
                <h2 className="text-xl font-semibold text-white flex items-center gap-2 mb-4">
                  <Mail className="w-5 h-5 text-status-warning" />
                  Gmail Sync Required
                </h2>
                <p className="text-text-secondary mb-6 max-w-lg">
                  To build your Corporate Memory system, link your Gmail account. We will synchronize ONLY emails matching the label <strong className="text-white">"Director's AI Assistant"</strong>.
                </p>
                <Button 
                  variant="primary" 
                  leftIcon={<ExternalLink className="w-4 h-4" />}
                  onClick={handleConnectGmail}
                >
                  Connect Gmail Account
                </Button>
              </div>
            ) : (
              <div className="glass-panel p-6 rounded-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-status-success/5 rounded-full blur-2xl -mr-10 -mt-10" />
                <h2 className="text-xl font-semibold text-white flex items-center gap-2 mb-4">
                  <CheckCircle className="w-5 h-5 text-status-success" />
                  Gmail Connected
                </h2>
                <p className="text-text-secondary mb-6 max-w-lg">
                  Your inbox integration is configured to sync labeled emails containing the label <strong className="text-white">"Director's AI Assistant"</strong>. Trigger a manual sync run below to pull latest documents.
                </p>
                <div className="flex flex-wrap gap-4 items-center">
                  <Button 
                    variant="gold" 
                    leftIcon={<RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />}
                    onClick={handleTriggerSync}
                    disabled={isSyncing}
                  >
                    {isSyncing ? "Synchronizing Inbox..." : "Sync Labeled Emails"}
                  </Button>

                  {!isSyncing && stats.total_emails > 0 && (
                    <Button
                      variant="secondary"
                      leftIcon={<Download className="w-4 h-4" />}
                      onClick={handleDownloadEmails}
                    >
                      Download New Emails (.docx)
                    </Button>
                  )}

                  {isSyncing && (
                    <span className="text-sm text-text-secondary animate-pulse flex items-center gap-2">
                      Please keep this window open while processing attachments...
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Active AI Chat & Search Action Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass-panel p-6 rounded-xl border border-purple-500/20 bg-purple-500/[0.03] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <div className="p-2 rounded-xl bg-purple-500/20 text-purple-400">
                      <Bot className="w-5 h-5" />
                    </div>
                    <h3 className="font-bold text-white text-base">AI Intelligence Chat</h3>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/30 text-purple-200">ACTIVE</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Ask natural language questions grounded in your synced emails and extracted PDF attachments using LLaMA 3.3.
                </p>
                <button
                  onClick={() => window.location.href = '/chat'}
                  className="w-full py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs transition-all shadow-md flex items-center justify-center space-x-2"
                >
                  <span>Launch AI Chat</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="glass-panel p-6 rounded-xl border border-amber-500/20 bg-amber-500/[0.03] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400">
                      <Search className="w-5 h-5" />
                    </div>
                    <h3 className="font-bold text-white text-base">Global Intelligence Search</h3>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/30 text-amber-200">ACTIVE</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Perform instant full-text search with filters across all emails, OCR documents, and attachments.
                </p>
                <button
                  onClick={() => window.location.href = '/search'}
                  className="w-full py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-dark-bg font-bold text-xs transition-all shadow-md flex items-center justify-center space-x-2"
                >
                  <span>Open Global Search</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

          </div>

          {/* Right Sidebar - Activity Logs */}
          <div className="glass-panel p-6 rounded-xl flex flex-col h-full min-h-[400px]">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Clock className="w-4 h-4 text-text-secondary" />
              Sync Log History
            </h2>
            
            <div className="flex-1 space-y-4 overflow-y-auto max-h-[350px] pr-2">
              {syncLogs.length > 0 ? (
                syncLogs.map((log) => (
                  <div key={log.id} className="p-3 bg-dark-card/50 border border-dark-border/40 rounded-lg space-y-1.5">
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded uppercase tracking-wider bg-dark-bg border border-dark-border">
                        {log.sync_type}
                      </span>
                      <span className={`text-xs font-semibold uppercase ${
                        log.status === 'success' ? 'text-status-success' :
                        log.status === 'failed' ? 'text-status-error' : 'text-status-warning animate-pulse'
                      }`}>
                        {log.status}
                      </span>
                    </div>
                    <div className="text-xs text-text-secondary">
                      Started: {new Date(log.started_at).toLocaleString()}
                    </div>
                    {log.status === 'success' && (
                      <div className="text-xs text-text-primary flex justify-between">
                        <span>Emails: {log.emails_synced}</span>
                        <span>Attachments: {log.attachments_downloaded}</span>
                      </div>
                    )}
                    {log.status === 'failed' && log.error_message && (
                      <div className="text-[10px] text-status-error bg-status-error/5 p-1 rounded border border-status-error/15 break-words">
                        {log.error_message}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center p-4">
                  <div className="w-12 h-12 bg-dark-card rounded-full flex items-center justify-center mb-4 border border-dark-border">
                    <Clock className="w-5 h-5 text-text-secondary/50" />
                  </div>
                  <p className="text-text-primary font-medium mb-1 text-sm">No runs recorded</p>
                  <p className="text-xs text-text-secondary">Sync your email to create execution logs.</p>
                </div>
              )}
            </div>
          </div>

        </div>

      </div>
    </AppShell>
  );
}

function StatCard({ icon: Icon, label, value, trend, trendDown = false }: { icon: any, label: string, value: string, trend: string, trendDown?: boolean }) {
  return (
    <div className="glass-panel p-5 rounded-xl hover:border-secondary-blue/30 transition-colors group">
      <div className="flex items-start justify-between mb-2">
        <span className="text-sm font-medium text-text-secondary">{label}</span>
        <div className="p-2 rounded-lg bg-dark-card group-hover:bg-primary-blue/10 transition-colors">
          <Icon className="w-4 h-4 text-secondary-blue" />
        </div>
      </div>
      <div className="text-3xl font-bold text-white mb-1 tracking-tight">{value}</div>
      <div className={`text-xs ${trendDown ? 'text-status-warning' : 'text-status-success'}`}>
        {trend}
      </div>
    </div>
  );
}
