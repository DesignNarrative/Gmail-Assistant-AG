import React, { useState, useEffect } from 'react';
import AppShell from '../components/layout/AppShell';
import { searchApi, SearchResultItem } from '../api/search';
import { 
  Search, Filter, Mail, FileText, Calendar, User, 
  Paperclip, RefreshCw, Layers, FileCheck2, ChevronRight 
} from 'lucide-react';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [senderFilter, setSenderFilter] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [hasAttachmentFilter, setHasAttachmentFilter] = useState<boolean | undefined>(undefined);
  
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

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

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto px-4 py-2 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between py-2 border-b border-white/10">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Search className="w-5 h-5 text-gold-accent" />
              Global Intelligence Search
            </h1>
            <p className="text-xs text-slate-400">Instant full-text and entity search across all emails and OCR-extracted documents</p>
          </div>
        </div>

        {/* Search Bar & Filter Controls */}
        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-4 space-y-4 backdrop-blur-sm shadow-xl">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              performSearch();
            }}
            className="flex items-center space-x-3 bg-dark-bg border border-white/15 focus-within:border-gold-accent/50 focus-within:ring-2 focus-within:ring-gold-accent/20 rounded-xl p-2.5 transition-all"
          >
            <Search className="w-5 h-5 text-slate-400 ml-2" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by keywords, names, receipt numbers, courses, or email content..."
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-400 px-2 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-dark-bg font-semibold text-xs transition-all shadow-md flex items-center space-x-1.5"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>Search</span>}
            </button>
          </form>

          {/* Filters Row */}
          <div className="flex flex-wrap items-center gap-3 pt-2 text-xs">
            <div className="flex items-center space-x-1.5 text-slate-400 font-medium mr-2">
              <Filter className="w-3.5 h-3.5 text-gold-accent" />
              <span>Filters:</span>
            </div>

            {/* Sender Filter */}
            <input
              type="text"
              value={senderFilter}
              onChange={(e) => setSenderFilter(e.target.value)}
              placeholder="Filter by sender email..."
              className="bg-dark-bg border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-gold-accent/40"
            />

            {/* Document Format */}
            <select
              value={docTypeFilter}
              onChange={(e) => setDocTypeFilter(e.target.value)}
              className="bg-dark-bg border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-gold-accent/40"
            >
              <option value="">All Formats (PDF, Docx, Image)</option>
              <option value="pdf">PDF Documents</option>
              <option value="image">Scanned Images</option>
              <option value="word">Word Documents</option>
            </select>

            {/* Attachment Toggle */}
            <button
              type="button"
              onClick={() => {
                if (hasAttachmentFilter === undefined) setHasAttachmentFilter(true);
                else if (hasAttachmentFilter === true) setHasAttachmentFilter(false);
                else setHasAttachmentFilter(undefined);
              }}
              className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-all flex items-center space-x-1.5 ${
                hasAttachmentFilter === true
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : hasAttachmentFilter === false
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                  : 'bg-dark-bg text-slate-400 border-white/10'
              }`}
            >
              <Paperclip className="w-3.5 h-3.5" />
              <span>
                {hasAttachmentFilter === true ? 'With Attachments Only' : hasAttachmentFilter === false ? 'No Attachments Only' : 'Attachments (Any)'}
              </span>
            </button>
          </div>
        </div>

        {/* Results Info */}
        <div className="flex items-center justify-between text-xs text-slate-400 px-1">
          <span>Found <strong className="text-white">{total}</strong> results</span>
          {loading && (
            <span className="flex items-center space-x-1 text-gold-accent">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Searching database...</span>
            </span>
          )}
        </div>

        {/* Results List */}
        <div className="space-y-3">
          {results.length === 0 && !loading ? (
            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-12 text-center text-slate-400 space-y-2">
              <FileCheck2 className="w-10 h-10 mx-auto text-slate-600 mb-2" />
              <p className="text-sm font-medium text-slate-300">No search results found</p>
              <p className="text-xs text-slate-500">Try adjusting your keywords or clearing filters.</p>
            </div>
          ) : (
            results.map((item) => (
              <div
                key={item.id}
                className="bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 rounded-xl p-4 transition-all duration-200 shadow-md group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <div className={`p-2.5 rounded-xl ${
                      item.type === 'document' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {item.type === 'document' ? <FileText className="w-5 h-5" /> : <Mail className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                          item.type === 'document' ? 'bg-indigo-500/20 text-indigo-300' : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {item.type}
                        </span>
                        <h2 className="text-sm font-semibold text-white group-hover:text-gold-accent transition-colors">
                          {item.title}
                        </h2>
                      </div>

                      {/* Metadata row */}
                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 mt-1">
                        {item.sender && (
                          <span className="flex items-center gap-1">
                            <User className="w-3 h-3 text-slate-500" />
                            {item.sender}
                          </span>
                        )}
                        {item.date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3 text-slate-500" />
                            {new Date(item.date).toLocaleDateString()} {new Date(item.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>

                      {/* Snippet */}
                      <p className="text-xs text-slate-300 mt-2.5 leading-relaxed bg-black/20 p-2.5 rounded-lg border border-white/5 font-mono">
                        {item.snippet}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}
