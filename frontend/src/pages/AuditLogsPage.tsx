import React, { useState, useEffect } from 'react';
import AppShell from '../components/layout/AppShell';
import { auditApi, AuditLogItem } from '../api/audit';
import { Shield, RefreshCw, Filter, Calendar, CheckCircle2, AlertTriangle, Activity } from 'lucide-react';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');

  const loadLogs = async () => {
    setLoading(true);
    try {
      const res = await auditApi.getLogs({ action: actionFilter || undefined, limit: 50 });
      setLogs(res.logs);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [actionFilter]);

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto px-4 py-2 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between py-2 border-b border-white/10">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-indigo-400" />
              Security & Compliance Audit Logs
            </h1>
            <p className="text-xs text-slate-400">Complete immutable record of all system events, authentication, and data access</p>
          </div>
          <button
            onClick={loadLogs}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-xs text-white font-medium flex items-center space-x-1.5 transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center space-x-3 bg-white/[0.03] border border-white/10 rounded-xl p-3 backdrop-blur-sm">
          <Filter className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            placeholder="Filter by action name (e.g. LOGIN, GMAIL_SYNC, SEARCH)..."
            className="flex-1 bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        {/* Audit Table */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-white/[0.05] text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-white/10">
                <tr>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Resource</th>
                  <th className="py-3 px-4">IP Address</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {loading && logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-400">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-400" />
                      Fetching audit logs...
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      No audit logs recorded yet.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-white/[0.04] transition-colors">
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 font-medium text-white flex items-center space-x-1.5">
                        <Activity className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                        <span>{log.action}</span>
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {log.resource_type ? `${log.resource_type} (${log.resource_id || 'N/A'})` : 'System'}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {log.ip_address || '127.0.0.1'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          log.status === 'success' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        }`}>
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
