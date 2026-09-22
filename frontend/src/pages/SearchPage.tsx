import React, { useState, useEffect } from 'react';
import AppShell from '../components/layout/AppShell';
import { searchApi, SearchResultItem, EmailDetailResponse, AttachmentDetail } from '../api/search';
import { 
  Search, Filter, Mail, FileText, Calendar, User, 
  Paperclip, RefreshCw, ChevronRight, X, Copy, Check, 
  Bot, Eye, ArrowRight, ExternalLink
} from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';

export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQuery = searchParams.get('q') || '';
  
  const [query, setQuery] = useState(initialQuery);
  const [senderFilter, setSenderFilter] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [hasAttachmentFilter, setHasAttachmentFilter] = useState<boolean | undefined>(undefined);
  
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  // Email Detail Reader Modal state
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [emailDetail, setEmailDetail] = useState<EmailDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [expandedAttachmentId, setExpandedAttachmentId] = useState<string | null>(null);
  const [copiedText, setCopiedText] = useState(false);

  const performSearch = async () => {
    setLoading(true);
    try {
      const res = await searchApi.search({
        q: query || undefined,
        sender: senderFilter || undefined,
        doc_type: docTypeFilter || undefined,
        has_attachment: hasAttachmentFilter,
        page: 1,
        limit: 50
      });
      setResults(res.results);
      setTotal(res.total_results);
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    performSearch();
  }, [senderFilter, docTypeFilter, hasAttachmentFilter]);

  // Handle open email details
  const handleOpenEmail = async (emailId: string) => {
    setSelectedEmailId(emailId);
    setLoadingDetail(true);
    setDetailError(null);
    setEmailDetail(null);
    setExpandedAttachmentId(null);
    setCopiedText(false);

    try {
      const detail = await searchApi.getEmailDetail(emailId);
      setEmailDetail(detail);
    } catch (err: any) {
      console.error('Failed to load email detail:', err);
      setDetailError(err.response?.data?.detail || 'Failed to load full email.');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedEmailId(null);
    setEmailDetail(null);
    setDetailError(null);
  };

  // Keyboard shortcut: close modal on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedEmailId) {
        handleCloseModal();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedEmailId]);

  const handleCopyBody = () => {
    if (emailDetail?.body_text) {
      navigator.clipboard.writeText(emailDetail.body_text);
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    }
  };

  const handleAskAiAboutEmail = () => {
    if (!emailDetail) return;
    const prompt = `Please summarize and analyze this email:\nSubject: ${emailDetail.subject}\nFrom: ${emailDetail.sender_email}`;
    sessionStorage.setItem('inboxiq_prefill_chat', prompt);
    navigate('/chat');
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-6 animate-fade-in pb-12">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <div>
            <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Search className="w-5 h-5 text-blue-600" />
              Search Inbox & Documents
            </h1>
            <p className="text-xs text-slate-500">Search across all your synced emails, scanned attachments, and files</p>
          </div>
        </div>

        {/* Search Bar & Filter Controls */}
        <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3 shadow-xs">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              performSearch();
            }}
            className="flex items-center space-x-2 bg-slate-50 border border-slate-200 focus-within:border-blue-500 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-500/10 rounded-xl p-2 transition-all"
          >
            <Search className="w-4 h-4 text-slate-400 ml-2 shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by keywords, subject, sender, or email text..."
              className="flex-1 bg-transparent text-sm text-slate-900 placeholder-slate-400 px-2 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs transition-all shadow-xs flex items-center space-x-1.5"
            >
              {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <span>Search</span>}
            </button>
          </form>

          {/* Filters Row */}
          <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
            <div className="flex items-center space-x-1 text-slate-500 font-medium mr-1">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span>Filters:</span>
            </div>

            {/* Sender Filter */}
            <input
              type="text"
              value={senderFilter}
              onChange={(e) => setSenderFilter(e.target.value)}
              placeholder="Sender email..."
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />

            {/* Document Format */}
            <select
              value={docTypeFilter}
              onChange={(e) => setDocTypeFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-800 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Document Types</option>
              <option value="PDF">PDF Documents</option>
              <option value="IMAGE">Image Files</option>
              <option value="TEXT">Text & Receipts</option>
            </select>

            {/* Attachment Switch */}
            <button
              type="button"
              onClick={() => setHasAttachmentFilter(hasAttachmentFilter === true ? undefined : true)}
              className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition-all flex items-center space-x-1 ${
                hasAttachmentFilter === true
                  ? 'bg-blue-50 border-blue-200 text-blue-700 font-semibold'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Paperclip className="w-3 h-3" />
              <span>Has Attachments</span>
            </button>
          </div>
        </div>

        {/* Search Results Summary */}
        <div className="flex items-center justify-between text-xs text-slate-500 px-1">
          <span>Found {total} matching result{total === 1 ? '' : 's'} — click any card to view full email</span>
          {loading && <span className="flex items-center gap-1 text-blue-600"><RefreshCw className="w-3 h-3 animate-spin" /> Searching...</span>}
        </div>

        {/* Results List */}
        <div className="space-y-3">
          {results.length > 0 ? (
            results.map((item) => {
              const targetEmailId = item.type === 'email' ? item.id : item.email_id;
              return (
                <div
                  key={item.id}
                  onClick={() => targetEmailId && handleOpenEmail(targetEmailId)}
                  className="bg-white border border-slate-200 hover:border-blue-400 hover:shadow-md p-5 rounded-2xl transition-all shadow-xs space-y-2 group cursor-pointer relative"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center space-x-2.5 overflow-hidden">
                      <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                        {item.type === 'document' ? <FileText className="w-4 h-4" /> : <Mail className="w-4 h-4" />}
                      </div>
                      <div className="overflow-hidden">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors truncate">
                            {item.title || '(No Subject)'}
                          </h3>
                          {item.type === 'document' && (
                            <span className="px-2 py-0.2 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                              Document Match
                            </span>
                          )}
                        </div>
                        <div className="flex items-center space-x-3 text-xs text-slate-500 mt-0.5">
                          {item.sender && (
                            <span className="flex items-center gap-1 truncate">
                              <User className="w-3 h-3 text-slate-400 shrink-0" />
                              <span className="truncate">{item.sender}</span>
                            </span>
                          )}
                          {item.sender && item.date && <span>•</span>}
                          {item.date && (
                            <span className="flex items-center gap-1 shrink-0">
                              <Calendar className="w-3 h-3 text-slate-400" />
                              {new Date(item.date).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {item.mime_type && (
                        <span className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-slate-600 text-[11px] font-medium flex items-center gap-1">
                          <Paperclip className="w-3 h-3" />
                          Attachment
                        </span>
                      )}
                      <div className="p-1 rounded-lg text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all">
                        <ChevronRight className="w-4 h-4" />
                      </div>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed line-clamp-2 pl-10.5">
                    {item.snippet}
                  </p>

                  <div className="pl-10.5 pt-1 flex items-center justify-between">
                    <span className="text-[11px] text-blue-600 font-semibold group-hover:underline flex items-center gap-1">
                      <span>Open full email</span>
                      <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              );
            })
          ) : !loading ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-xs">
              <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-3 text-slate-400">
                <Search className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 mb-1">No matching results found</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Try searching with different keywords or clearing your filters.
              </p>
            </div>
          ) : null}
        </div>
      </div>

      {/* ===================================================================== */}
      {/* FULL EMAIL DETAIL READER MODAL                                        */}
      {/* ===================================================================== */}
      {selectedEmailId && (
        <div 
          className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 animate-fade-in"
          onClick={handleCloseModal}
        >
          <div 
            className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-3xl w-full max-h-[88vh] flex flex-col overflow-hidden animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-100 flex items-start justify-between gap-4 bg-slate-50/50">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 border border-blue-200 text-blue-700">
                    Email Reader
                  </span>
                  {emailDetail?.has_attachments && (
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 border border-amber-200 text-amber-700 flex items-center gap-1">
                      <Paperclip className="w-3 h-3" />
                      {emailDetail.attachments.length} Attachment{emailDetail.attachments.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                <h2 className="text-lg font-bold text-slate-900 leading-snug">
                  {loadingDetail ? 'Loading email...' : emailDetail?.subject || '(No Subject)'}
                </h2>
              </div>

              <button
                onClick={handleCloseModal}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                title="Close (Esc)"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body Container */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {loadingDetail ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 space-y-3">
                  <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
                  <p className="text-sm font-medium text-slate-600">Loading full email content...</p>
                </div>
              ) : detailError ? (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm">
                  {detailError}
                </div>
              ) : emailDetail ? (
                <>
                  {/* Sender & Recipient Information */}
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-2">
                    <div className="flex items-start justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm shadow-xs">
                          {emailDetail.sender_name 
                            ? emailDetail.sender_name.charAt(0).toUpperCase()
                            : emailDetail.sender_email.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-sm font-bold text-slate-900">
                            {emailDetail.sender_name || emailDetail.sender_email}
                          </div>
                          <div className="text-xs text-slate-500 font-mono">
                            {emailDetail.sender_email}
                          </div>
                        </div>
                      </div>

                      <div className="text-xs text-slate-500 flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>
                          {emailDetail.date_sent 
                            ? new Date(emailDetail.date_sent).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
                            : 'Unknown Date'}
                        </span>
                      </div>
                    </div>

                    {/* Recipients List */}
                    {emailDetail.recipients && emailDetail.recipients.length > 0 && (
                      <div className="pt-2 border-t border-slate-200/60 text-xs text-slate-600 flex items-start gap-1">
                        <span className="font-semibold text-slate-500 shrink-0">To:</span>
                        <div className="flex flex-wrap gap-1">
                          {emailDetail.recipients.map((r: any, idx: number) => {
                            const emailStr = typeof r === 'string' ? r : r?.email || r?.name || '';
                            return (
                              <span key={idx} className="px-2 py-0.5 rounded bg-white border border-slate-200 text-[11px] font-mono">
                                {emailStr}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Attachments Section */}
                  {emailDetail.attachments && emailDetail.attachments.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                        <Paperclip className="w-3.5 h-3.5 text-blue-600" />
                        <span>Attachments ({emailDetail.attachments.length})</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {emailDetail.attachments.map((att: AttachmentDetail) => {
                          const isExpanded = expandedAttachmentId === att.id;
                          return (
                            <div 
                              key={att.id}
                              className="p-3 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-all space-y-2 shadow-xs"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex items-center gap-2 overflow-hidden">
                                  <FileText className="w-4 h-4 text-blue-600 shrink-0" />
                                  <div className="overflow-hidden">
                                    <p className="text-xs font-semibold text-slate-900 truncate" title={att.filename}>
                                      {att.filename}
                                    </p>
                                    <p className="text-[10px] text-slate-400">
                                      {formatFileSize(att.file_size)} • {att.mime_type.split('/')[1]?.toUpperCase() || 'FILE'}
                                    </p>
                                  </div>
                                </div>

                                {att.has_extracted_text && (
                                  <button
                                    onClick={() => setExpandedAttachmentId(isExpanded ? null : att.id)}
                                    className="p-1 text-xs text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1 shrink-0"
                                    title="View OCR text preview"
                                  >
                                    <Eye className="w-3.5 h-3.5" />
                                    <span>{isExpanded ? 'Hide' : 'Text'}</span>
                                  </button>
                                )}
                              </div>

                              {/* Expandable OCR text preview */}
                              {isExpanded && att.extracted_text_preview && (
                                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-[11px] text-slate-700 font-mono leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
                                  {att.extracted_text_preview}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Full Email Body */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-slate-700">Message Content</div>
                    <div className="p-4 rounded-xl border border-slate-200 bg-white text-slate-800 text-sm leading-relaxed whitespace-pre-wrap font-sans select-text">
                      {emailDetail.body_text || '(Empty email body)'}
                    </div>
                  </div>
                </>
              ) : null}
            </div>

            {/* Modal Footer Actions */}
            <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/50 gap-2">
              <div className="flex items-center gap-2">
                {emailDetail && (
                  <button
                    onClick={handleCopyBody}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-xs font-medium text-slate-700 transition-all shadow-xs"
                  >
                    {copiedText ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-700 font-semibold">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-slate-500" />
                        <span>Copy Email</span>
                      </>
                    )}
                  </button>
                )}

                {emailDetail && (
                  <button
                    onClick={handleAskAiAboutEmail}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition-all shadow-xs"
                  >
                    <Bot className="w-3.5 h-3.5 text-blue-600" />
                    <span>Ask AI About This Email</span>
                  </button>
                )}
              </div>

              <button
                onClick={handleCloseModal}
                className="px-4 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-all shadow-xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
