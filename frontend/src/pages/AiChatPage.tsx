import React, { useState, useEffect, useRef } from 'react';
import AppShell from '../components/layout/AppShell';
import { chatApi, ChatMessage, ChatMode, Conversation } from '../api/chat';
import { 
  Send, Bot, User, Sparkles, Trash2, FileText, 
  HelpCircle, RefreshCw, CheckCircle2, AlertCircle, ExternalLink, BookOpen, ShieldCheck, Plus, MessageSquare 
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SUGGESTED_QUESTIONS = [
  "What is the student name and fee amount in the receipt?",
  "Which college did the applicant attend for HSC?",
  "Summarize the main details from the synced documents.",
  "Are there any payment or fee receipts found?"
];

export default function AiChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingHistory, setFetchingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<ChatMode>('hybrid');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  // id of the temp message currently receiving streamed tokens (shows the typing caret)
  const [streamingId, setStreamingId] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async (selectFirst = false) => {
    try {
      const convs = await chatApi.listConversations();
      setConversations(convs);
      if (selectFirst && convs.length > 0) {
        await loadConversationMessages(convs[0].id);
      } else if (selectFirst) {
        setFetchingHistory(false);
      }
    } catch (err: any) {
      console.error('Failed to load conversations:', err);
      setFetchingHistory(false);
    }
  };

  const loadConversationMessages = async (conversationId: string) => {
    setFetchingHistory(true);
    setError(null);
    try {
      const data = await chatApi.getConversationMessages(conversationId);
      setMessages(data);
      setCurrentConversationId(conversationId);
    } catch (err: any) {
      console.error('Failed to load conversation:', err);
    } finally {
      setFetchingHistory(false);
    }
  };

  useEffect(() => {
    loadConversations(true);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (questionText?: string) => {
    const q = (questionText || inputQuestion).trim();
    if (!q || loading) return;

    setInputQuestion('');
    setError(null);
    setLoading(true);

    // Optimistic UI addition for user question
    const tempUserMsg: ChatMessage = {
      id: 'temp-' + Date.now(),
      question: q,
      answer: null, // thinking
      sources: [],
      model_used: null, // filled in from the real response; don't fake a model
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const wasNewChat = !currentConversationId;
      const updateTemp = (patch: Partial<ChatMessage>) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === tempUserMsg.id ? { ...m, ...patch } : m))
        );
      };

      let res: ChatMessage;
      try {
        // Token-by-token streaming (SSE) — answer text appears live as it's generated
        setStreamingId(tempUserMsg.id);
        res = await chatApi.askStream(q, mode, currentConversationId, {
          onMeta: (sourceType) => updateTemp({ source_type: sourceType }),
          onToken: (fullAnswer) => updateTemp({ answer: fullAnswer }),
          onReset: (sourceType) => updateTemp({ answer: null, source_type: sourceType }),
        });
      } catch (streamErr) {
        // Streaming unavailable (proxy/network/auth) — fall back to the blocking endpoint
        console.warn('Streaming failed, falling back to standard request:', streamErr);
        setStreamingId(null);
        updateTemp({ answer: null, source_type: null });
        res = await chatApi.ask(q, mode, currentConversationId);
      }

      if (res.conversation_id) setCurrentConversationId(res.conversation_id);
      if (wasNewChat || res.conversation_id) loadConversations();
      setMessages((prev) => 
        prev.map((msg) => (msg.id === tempUserMsg.id ? res : msg))
      );
    } catch (err: any) {
      console.error('Chat error:', err);
      const errMsg = err?.response?.data?.detail || 'Failed to get answer. Please check your connection.';
      setError(errMsg);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === tempUserMsg.id 
            ? { ...msg, answer: '⚠️ Error: ' + errMsg } 
            : msg
        )
      );
    } finally {
      setLoading(false);
      setStreamingId(null);
    }
  };

  const handleNewChat = () => {
    setCurrentConversationId(null);
    setMessages([]);
    setError(null);
    setInputQuestion('');
  };

  const handleSelectConversation = (conversationId: string) => {
    if (conversationId === currentConversationId) return;
    loadConversationMessages(conversationId);
  };

  const handleDeleteConversation = async (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this chat? This cannot be undone.')) return;
    try {
      await chatApi.deleteConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      if (conversationId === currentConversationId) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  return (
    <AppShell>
      <div className="flex h-[calc(100vh-6rem)] max-w-6xl mx-auto px-4 py-2 gap-3">
        {/* Conversation sidebar */}
        <div className="w-56 shrink-0 flex flex-col border-r border-white/10 pr-3">
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center gap-1.5 px-3 py-2 mb-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-sm font-medium shadow-md shadow-purple-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
          <div className="flex-1 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent -mr-1 pr-1">
            {conversations.length === 0 ? (
              <p className="text-[11px] text-slate-500 text-center mt-4">No chats yet</p>
            ) : (
              conversations.map((c) => (
                <div
                  key={c.id}
                  onClick={() => handleSelectConversation(c.id)}
                  className={`group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer text-xs transition-all ${
                    c.id === currentConversationId
                      ? 'bg-purple-500/20 text-purple-100 border border-purple-500/30'
                      : 'text-slate-300 hover:bg-white/[0.06] border border-transparent'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5 shrink-0 text-purple-400" />
                  <span className="truncate flex-1">{c.title || 'Untitled chat'}</span>
                  <button
                    onClick={(e) => handleDeleteConversation(c.id, e)}
                    title="Delete chat"
                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-400 transition-all shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Main chat column */}
        <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between py-3 border-b border-white/10 mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Sparkles className="w-5 h-5 text-white animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                AI Intelligence Chat
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  AI Powered
                </span>
              </h1>
              <p className="text-xs text-slate-400">Ask any question grounded in your synced Gmail emails & PDF documents</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Knowledge mode toggle */}
            <div className="flex items-center rounded-lg bg-white/[0.04] border border-white/10 p-0.5 text-xs font-medium">
              <button
                type="button"
                onClick={() => setMode('hybrid')}
                title="Answer from your emails, and fall back to the AI's general knowledge when your emails don't cover it (clearly labelled)."
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
                  mode === 'hybrid'
                    ? 'bg-purple-500/20 text-purple-200 border border-purple-500/30'
                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Email + AI knowledge</span>
              </button>
              <button
                type="button"
                onClick={() => setMode('email_only')}
                title="Strict mode: answer only from your synced emails. If the answer isn't there, the assistant says so instead of guessing."
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
                  mode === 'email_only'
                    ? 'bg-emerald-500/20 text-emerald-200 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Email-only</span>
              </button>
            </div>

            {/* New Chat and past conversations now live in the sidebar */}
          </div>
        </div>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-y-auto pr-2 space-y-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
          {fetchingHistory ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin text-purple-400" />
              <p className="text-sm">Loading chat history...</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto py-12">
              <div className="w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mb-4 text-purple-400">
                <Bot className="w-8 h-8" />
              </div>
              <h2 className="text-lg font-semibold text-white mb-2">How can I assist you today?</h2>
              <p className="text-xs text-slate-400 mb-6 leading-relaxed">
                I've organized your synced Gmail messages and PDF attachments. Ask me anything and I'll answer with source citations.
              </p>

              {/* Suggested Questions */}
              <div className="w-full space-y-2 text-left">
                <p className="text-xs font-medium text-slate-400 mb-2 flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-purple-400" />
                  Try asking one of these:
                </p>
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    className="w-full text-left p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/10 text-xs text-slate-200 hover:text-white transition-all flex items-center justify-between group"
                  >
                    <span>{q}</span>
                    <Sparkles className="w-3.5 h-3.5 text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className="space-y-4">
                {/* User Question */}
                <div className="flex items-start justify-end space-x-3">
                  <div className="max-w-xl rounded-2xl rounded-tr-none bg-gradient-to-r from-purple-600 to-indigo-600 p-4 text-white text-sm shadow-lg shadow-purple-600/10">
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.question}</p>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-slate-700 border border-white/20 flex items-center justify-center text-slate-200 shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                </div>

                {/* AI Answer */}
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white shrink-0 shadow-md shadow-purple-500/20">
                    <Bot className="w-4.5 h-4.5" />
                  </div>
                  <div className="max-w-2xl flex-1 rounded-2xl rounded-tl-none bg-white/[0.05] border border-white/10 p-4.5 text-slate-200 text-sm shadow-xl space-y-3">
                    {msg.answer === null ? (
                      <div className="flex items-center space-x-2 text-purple-300">
                        <Sparkles className="w-4 h-4 animate-spin" />
                        <span className="text-xs font-medium animate-pulse">Searching documents & generating answer with Groq AI...</span>
                      </div>
                    ) : (
                      <>
                        {/* Knowledge-source badge */}
                        {msg.source_type === 'general_knowledge' && (
                          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-medium w-fit">
                            <BookOpen className="w-3.5 h-3.5" />
                            <span>General knowledge — not from your emails</span>
                          </div>
                        )}
                        {msg.source_type === 'email_grounded' && (
                          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[11px] font-medium w-fit">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            <span>Grounded in your emails</span>
                          </div>
                        )}

                        <div className="prose prose-invert prose-sm max-w-none prose-p:my-1.5 prose-p:first:mt-0 prose-p:last:mb-0 prose-headings:mb-2 prose-headings:mt-3 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0 prose-code:before:content-none prose-code:after:content-none prose-pre:bg-black/40 prose-pre:border prose-pre:border-white/10">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              a: ({ href, children, ...rest }: any) => (
                                <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
                                  {children}
                                </a>
                              ),
                            }}
                          >
                            {msg.answer || ''}
                          </ReactMarkdown>
                        </div>

                        {/* Typing caret while the answer is streaming in */}
                        {streamingId === msg.id && (
                          <span className="inline-block w-2 h-4 bg-purple-400 rounded-sm animate-pulse" aria-hidden="true" />
                        )}

                        {/* Source Citations */}
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="pt-3 border-t border-white/10">
                            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5 text-purple-400" />
                              Source Documents ({msg.sources.length})
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {msg.sources.map((src, sIdx) => {
                                const dateStr = src.date
                                  ? new Date(src.date).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
                                  : null;
                                const subtitle = [src.sender, dateStr].filter(Boolean).join('  ·  ');
                                const tooltip = [
                                  src.subject ? `Subject: ${src.subject}` : null,
                                  src.sender ? `From: ${src.sender}${src.sender_email && src.sender_email !== src.sender ? ` <${src.sender_email}>` : ''}` : null,
                                  dateStr ? `Date: ${dateStr}` : null,
                                  `Relevance: ${Math.round(src.score * 100)}%`,
                                ].filter(Boolean).join('\n');
                                return (
                                  <div
                                    key={sIdx}
                                    className="flex flex-col gap-0.5 bg-purple-500/10 border border-purple-500/20 rounded-lg px-2.5 py-1.5 text-xs text-purple-300 max-w-[260px]"
                                    title={tooltip}
                                  >
                                    <div className="flex items-center gap-1.5 font-medium">
                                      <FileText className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                                      <span className="truncate">{src.filename}</span>
                                      <span className="text-[10px] text-purple-400/70 font-mono shrink-0">({Math.round(src.score * 100)}%)</span>
                                    </div>
                                    {subtitle && (
                                      <span className="text-[10px] text-purple-400/60 truncate pl-5">{subtitle}</span>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <div className="mt-3 pt-3 border-t border-white/10">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center space-x-2 bg-white/[0.05] border border-white/15 focus-within:border-purple-500/50 focus-within:ring-2 focus-within:ring-purple-500/20 rounded-2xl p-2 transition-all"
          >
            <input
              type="text"
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              placeholder="Ask a question about your synced emails or documents..."
              disabled={loading}
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-400 px-3 focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputQuestion.trim() || loading}
              className="p-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-purple-600/30 transition-all shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <p className="text-[11px] text-center text-slate-500 mt-2">
            {mode === 'email_only'
              ? 'Email-only mode: answers come strictly from your synced Gmail messages & attachments (LLaMA 3.3).'
              : 'Hybrid mode: answers use your synced emails first, falling back to general AI knowledge (labelled) when needed.'}
          </p>
        </div>
        </div>
      </div>
    </AppShell>
  );
}
