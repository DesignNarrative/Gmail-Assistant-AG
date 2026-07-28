import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import { useAuthStore } from '../store/authStore';
import { Mail, ArrowUp, RefreshCw, AlertCircle, CheckCircle, Download, ChevronDown, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { gmailApi, SyncStats } from '../api/gmail';
import { authApi } from '../api/auth';
import client from '../api/client';

const SUGGESTIONS = [
  'Summarize my recent emails',
  "What's inside my attachments?",
  'Any payments or receipts?',
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, setUser } = useAuthStore();
  const [stats, setStats] = useState<SyncStats>({
    total_emails: 0,
    total_threads: 0,
    total_attachments: 0,
    total_size_bytes: 0,
    latest_sync: null
  });
  const [question, setQuestion] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const downloadMenuRef = useRef<HTMLDivElement>(null);

  // Load stats
  const loadData = async () => {
    try {
      const statsData = await gmailApi.getSyncStats();
      setStats(statsData);
      setIsSyncing(!!statsData.latest_sync && statsData.latest_sync.status === 'running');
    } catch (e) {
      console.error('Failed to load dashboard stats:', e);
    }
  };

  useEffect(() => {
    loadData();

    // Check URL query parameters for connection success or error
    const params = new URLSearchParams(window.location.search);
    if (params.get('sync_connected') === 'true') {
      setSuccessMsg('Your Gmail is connected!');
      authApi.getMe().then(updatedUser => {
        setUser(updatedUser);
      });
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get('error')) {
      setErrorMsg("Couldn't connect Gmail. Please try again.");
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Close download menu when clicking outside
  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (downloadMenuRef.current && !downloadMenuRef.current.contains(e.target as Node)) {
        setShowDownloadMenu(false);
      }
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  // Poll status while updating
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSyncing) {
      interval = setInterval(async () => {
        try {
          const statsData = await gmailApi.getSyncStats();
          setStats(statsData);

          if (statsData.latest_sync && statsData.latest_sync.status !== 'running') {
            setIsSyncing(false);
            if (statsData.latest_sync.status === 'success') {
              setSuccessMsg('Your emails are up to date.');
            } else {
              setErrorMsg("Something went wrong while updating. Please try again.");
            }
            clearInterval(interval);
          }
        } catch (e) {
          console.error('Error polling sync status:', e);
          setIsSyncing(false);
          clearInterval(interval);
        }
      }, 3500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSyncing]);

  const handleAsk = (text?: string) => {
    const q = (text ?? question).trim();
    if (!q) return;
    sessionStorage.setItem('pendingQuestion', q);
    navigate('/chat');
  };

  const handleConnectGmail = async () => {
    try {
      setErrorMsg(null);
      setSuccessMsg(null);
      const res = await authApi.getGoogleOAuthUrl();
      if (res.url) {
        window.location.href = res.url;
      }
    } catch (e: any) {
      setErrorMsg(e.response?.data?.detail || "Couldn't start the Gmail connection.");
    }
  };

  const handleTriggerSync = async () => {
    try {
      setErrorMsg(null);
      setSuccessMsg(null);
      setIsSyncing(true);
      await gmailApi.triggerSync();
      loadData();
    } catch (e: any) {
      setIsSyncing(false);
      setErrorMsg(e.response?.data?.detail || "Couldn't start the update.");
    }
  };

  const handleDownloadEmails = async (downloadAll: boolean = false) => {
    setShowDownloadMenu(false);
    try {
      setErrorMsg(null);
      setSuccessMsg(null);
      const response = await client.get('/api/v1/gmail/export', {
        responseType: 'blob',
        params: downloadAll ? { download_all: true } : {},
      });

      if (response.status === 204) {
        setSuccessMsg(downloadAll
          ? 'Nothing to download yet. Update your emails first.'
          : 'You already have everything — no new emails to download.');
        return;
      }

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', downloadAll ? 'all_emails.zip' : 'new_emails.zip');
      document.body.appendChild(link);
      link.click();
      setSuccessMsg('Your download has started.');
    } catch (e: any) {
      console.error('Export failed:', e);
      setErrorMsg("Couldn't download your emails.");
    }
  };

  const lastUpdated = stats.latest_sync?.completed_at
    ? new Date(stats.latest_sync.completed_at).toLocaleString(undefined, {
        day: '2-digit', month: 'short', hour: 'numeric', minute: '2-digit'
      })
    : null;

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto flex flex-col justify-center min-h-[calc(100vh-10rem)] space-y-8 animate-fade-in py-8">

        {/* Feedback alerts */}
        {errorMsg && (
          <div className="p-4 bg-status-error/10 border border-status-error/20 rounded-xl text-status-error flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="text-sm">{errorMsg}</p>
          </div>
        )}
        {successMsg && (
          <div className="p-4 bg-status-success/10 border border-status-success/20 rounded-xl text-status-success flex items-start gap-3">
            <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="text-sm">{successMsg}</p>
          </div>
        )}

        {/* Greeting */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-white tracking-tight">
            What can I help with?
          </h1>
          <p className="text-text-secondary text-base">Ask me anything about your emails.</p>
        </div>

        {user?.is_gmail_connected ? (
          <>
            {/* Big ask box */}
            <form
              onSubmit={(e) => { e.preventDefault(); handleAsk(); }}
              className="flex items-center gap-2 bg-dark-card border border-dark-border focus-within:border-secondary-blue focus-within:ring-2 focus-within:ring-secondary-blue/20 rounded-2xl p-2.5 pl-5 shadow-xl transition-all"
            >
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  // Enter asks; Shift+Enter inserts a new line (like ChatGPT)
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleAsk();
                  }
                }}
                placeholder="Ask anything..."
                autoFocus
                rows={1}
                className="flex-1 bg-transparent text-base text-white placeholder:text-text-secondary focus:outline-none resize-none"
              />
              <button
                type="submit"
                disabled={!question.trim()}
                title="Ask"
                className="p-2.5 rounded-xl bg-white text-dark-bg hover:bg-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0"
              >
                <ArrowUp className="w-5 h-5" />
              </button>
            </form>

            {/* Suggestion chips */}
            <div className="flex flex-wrap justify-center gap-2 -mt-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleAsk(s)}
                  className="px-4 py-2 rounded-full bg-dark-card/60 border border-dark-border text-sm text-text-secondary hover:text-white hover:border-secondary-blue/40 transition-all"
                >
                  {s}
                </button>
              ))}
            </div>

            {/* Quiet status line */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 text-sm text-text-secondary pt-4">
              {isSyncing ? (
                <span className="flex items-center gap-2 animate-pulse">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Updating your emails... please keep this window open.
                </span>
              ) : (
                <>
                  <span>
                    {stats.total_emails} emails and {stats.total_attachments} files ready
                    {lastUpdated && <span className="text-text-secondary/60"> · Updated {lastUpdated}</span>}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                      onClick={handleTriggerSync}
                      className="!py-1.5 !px-3 !text-xs"
                    >
                      Update emails
                    </Button>
                    {stats.total_emails > 0 && (
                      <div className="relative" ref={downloadMenuRef}>
                        <Button
                          variant="secondary"
                          leftIcon={<Download className="w-3.5 h-3.5" />}
                          onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                          className="!py-1.5 !px-3 !text-xs"
                        >
                          Download
                          <ChevronDown className="w-3 h-3 ml-1" />
                        </Button>
                        {showDownloadMenu && (
                          <div className="absolute top-full mt-2 right-0 w-44 bg-dark-card border border-dark-border rounded-xl shadow-2xl overflow-hidden z-20">
                            <button
                              onClick={() => handleDownloadEmails(false)}
                              className="w-full text-left px-4 py-2.5 text-xs text-text-primary hover:bg-dark-bg transition-colors"
                            >
                              New emails only
                            </button>
                            <button
                              onClick={() => handleDownloadEmails(true)}
                              className="w-full text-left px-4 py-2.5 text-xs text-text-primary hover:bg-dark-bg transition-colors border-t border-dark-border"
                            >
                              All emails
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </>
        ) : (
          /* Not connected yet — one simple card */
          <div className="glass-panel p-8 rounded-2xl text-center space-y-4">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-primary-blue/10 border border-primary-blue/20 flex items-center justify-center">
              <Mail className="w-7 h-7 text-secondary-blue" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Connect your Gmail to get started</h2>
              <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
                Your assistant will read only the emails you label for it — nothing else.
              </p>
            </div>
            <Button
              variant="primary"
              leftIcon={<Sparkles className="w-4 h-4" />}
              onClick={handleConnectGmail}
            >
              Connect Gmail
            </Button>
          </div>
        )}

      </div>
    </AppShell>
  );
}
