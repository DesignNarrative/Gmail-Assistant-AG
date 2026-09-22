import React, { useState, useEffect, useRef } from 'react';
import AppShell from '../components/layout/AppShell';
import { chatApi, ChatMessage } from '../api/chat';
import client from '../api/client';
import { 
  Bot, User, Sparkles, Trash2, FileText, 
  HelpCircle, RefreshCw, Plus, Download,
  MessageSquare, ArrowUp, Copy, Check, PanelLeftClose, PanelLeft,
  ChevronDown, Layers, Clock, Mail
} from 'lucide-react';

const SUGGESTED_PROMPTS = [
  {
    title: "Summarize recent emails",
    desc: "Key updates and news from your latest synced inbox",
    prompt: "Summarize key updates from the latest synced emails."
  },
  {
    title: "Find invoices & payments",
    desc: "Check receipts, fees, amounts, and payment dates",
    prompt: "Are there any invoices, payments, or receipts attached? Give me the amounts and dates."
  },
  {
    title: "Meeting discussions",
    desc: "Review past client conversations and action items",
    prompt: "What are the most recent project updates or meeting discussions in my emails?"
  },
  {
    title: "Attachment analysis",
    desc: "Extract info from contracts, resumes, and PDF documents",
    prompt: "Search for applicant or candidate details in attached documents."
  }
];

export default function AiChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [inputQuestion, setInputQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingHistory, setFetchingHistory] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isNewChat, setIsNewChat] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadHistory = async () => {
    setFetchingHistory(true);
    try {
      const data = await chatApi.getHistory();
      setMessages(data);
      if (data.length > 0) {
        setIsNewChat(false);
      } else {
        setIsNewChat(true);
      }
    } catch (err) {
      console.error('Failed to load chat history:', err);
    } finally {
      setFetchingHistory(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    if (!isNewChat) {
      scrollToBottom();
    }
  }, [messages, loading, isNewChat]);

  const handleStartNewChat = () => {
    setIsNewChat(true);
    setActiveChatId(null);
    setInputQuestion('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleSelectChat = (id: string) => {
    setIsNewChat(false);
    setActiveChatId(id);
    // Smooth scroll to selected message
    const el = document.getElementById(`msg-${id}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleSend = async (questionText?: string) => {
    const q = (questionText || inputQuestion).trim();
    if (!q || loading) return;

    setInputQuestion('');
    setLoading(true);
    setIsNewChat(false);

    const tempUserMsg: ChatMessage = {
      id: 'temp-' + Date.now(),
      question: q,
      answer: null,
      sources: [],
      model_used: 'openai/gpt-oss-120b',
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await chatApi.ask(q);
      setMessages((prev) => 
        prev.map((msg) => (msg.id === tempUserMsg.id ? res : msg))
      );
      setActiveChatId(res.id);
    } catch (err: any) {
      console.error('Chat error:', err);
      const errMsg = err?.response?.data?.detail || 'Failed to get answer. Please check your connection.';
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === tempUserMsg.id 
            ? { ...msg, answer: '⚠️ Error: ' + errMsg } 
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSingle = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversation item?')) return;
    try {
      await chatApi.deleteMessage(id);
      setMessages((prev) => prev.filter((m) => m.id !== id));
      if (activeChatId === id) {
        setActiveChatId(null);
      }
    } catch (err) {
      console.error('Failed to delete message:', err);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to clear your entire conversation history?')) return;
    try {
      await chatApi.clearHistory();
      setMessages([]);
      setIsNewChat(true);
      setActiveChatId(null);
    } catch (err) {
      console.error('Failed to clear history:', err);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleExport = async () => {
    try {
      const response = await client.get('/api/v1/chat/export', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'inboxiq_chat_export.txt');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (e) {
      console.error('Export failed:', e);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Group messages for sidebar
  const groupMessagesByDate = () => {
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    
    const groups: { [key: string]: ChatMessage[] } = {
      'Today': [],
      'Yesterday': [],
      'Previous 7 Days': [],
      'Older': []
    };

    [...messages].reverse().forEach((msg) => {
      const d = new Date(msg.created_at).toDateString();
      const diffDays = Math.floor((Date.now() - new Date(msg.created_at).getTime()) / (1000 * 60 * 60 * 24));
      
      if (d === today) {
        groups['Today'].push(msg);
      } else if (d === yesterday) {
        groups['Yesterday'].push(msg);
      } else if (diffDays <= 7) {
        groups['Previous 7 Days'].push(msg);
      } else {
        groups['Older'].push(msg);
      }
    });

    return groups;
  };

  const grouped = groupMessagesByDate();

  return (
    <AppShell>
      <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-white -m-6">
        
        {/* ================================================================= */}
        {/* 1. CHATGPT-STYLE CONVERSATION SIDEBAR                            */}
        {/* ================================================================= */}
        <aside 
          className={`h-full border-r border-slate-200 bg-slate-50/80 flex flex-col transition-all duration-200 z-20 shrink-0 ${
            sidebarOpen ? 'w-64' : 'w-0 overflow-hidden border-none'
          }`}
        >
          {/* Top: New Chat Button & Collapse */}
          <div className="p-3 pb-2 flex items-center gap-2">
            <button
              onClick={handleStartNewChat}
              className="flex-1 flex items-center justify-between px-3 py-2 rounded-xl bg-white hover:bg-slate-100/80 text-slate-800 text-xs font-semibold border border-slate-200 shadow-xs transition-all active:scale-[0.99] group"
              title="Start a new chat"
            >
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-md bg-blue-600 text-white flex items-center justify-center text-xs">
                  <Plus className="w-3.5 h-3.5" />
                </div>
                <span>New chat</span>
              </div>
              <span className="text-[10px] text-slate-400 font-mono">Ctrl+K</span>
            </button>

            <button
              onClick={() => setSidebarOpen(false)}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors shrink-0"
              title="Close sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* Chat List Grouped by Date */}
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-4">
            {fetchingHistory ? (
              <div className="flex items-center justify-center py-10 text-slate-400 gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                <span className="text-xs">Loading chats...</span>
              </div>
            ) : messages.length === 0 ? (
              <div className="text-center py-12 px-3 text-slate-400 text-xs">
                <MessageSquare className="w-6 h-6 mx-auto mb-2 opacity-40" />
                <p className="font-medium text-slate-600">No chats yet</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Start a conversation below</p>
              </div>
            ) : (
              Object.entries(grouped).map(([category, items]) => {
                if (items.length === 0) return null;
                return (
                  <div key={category} className="space-y-1">
                    <div className="px-2 text-[11px] font-semibold text-slate-400 tracking-wider uppercase">
                      {category}
                    </div>
                    {items.map((msg) => {
                      const isActive = activeChatId === msg.id;
                      return (
                        <div
                          key={msg.id}
                          onClick={() => handleSelectChat(msg.id)}
                          className={`group flex items-center justify-between px-2.5 py-2 rounded-xl text-xs cursor-pointer transition-all ${
                            isActive
                              ? 'bg-blue-50 text-blue-700 font-semibold'
                              : 'text-slate-700 hover:bg-slate-200/60'
                          }`}
                        >
                          <div className="flex items-center gap-2 overflow-hidden">
                            <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
                            <span className="truncate">{msg.question}</span>
                          </div>
                          <button
                            onClick={(e) => handleDeleteSingle(e, msg.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:text-rose-600 hover:bg-rose-50 transition-all shrink-0 text-slate-400"
                            title="Delete chat"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>

          {/* Bottom Controls */}
          {messages.length > 0 && (
            <div className="p-3 border-t border-slate-200 bg-white/50 flex items-center justify-between text-xs text-slate-500">
              <button
                onClick={handleExport}
                className="flex items-center gap-1.5 hover:text-slate-800 transition-colors"
                title="Export all chat history"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export</span>
              </button>

              <button
                onClick={handleClearAll}
                className="flex items-center gap-1.5 text-slate-500 hover:text-rose-600 transition-colors"
                title="Clear all conversations"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear all</span>
              </button>
            </div>
          )}
        </aside>

        {/* ================================================================= */}
        {/* 2. MAIN CHATGPT CANVAS & MESSAGE STREAM                           */}
        {/* ================================================================= */}
        <main className="flex-1 flex flex-col h-full bg-white relative overflow-hidden">
          
          {/* Top Bar with Model Picker & Toggle */}
          <header className="h-12 border-b border-slate-100 px-4 flex items-center justify-between shrink-0 bg-white z-10">
            <div className="flex items-center gap-2">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
                  title="Open sidebar"
                >
                  <PanelLeft className="w-4 h-4" />
                </button>
              )}

              {/* Model Dropdown Pill (ChatGPT style) */}
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl hover:bg-slate-100 cursor-pointer transition-colors text-slate-800 font-semibold text-sm">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>InboxIQ 1.0</span>
                <ChevronDown className="w-3 h-3 text-slate-400 ml-0.5" />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleStartNewChat}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
                title="New chat"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </header>

          {/* Conversation Messages Container */}
          <div className="flex-1 overflow-y-auto px-4 py-6 scroll-smooth">
            <div className="max-w-3xl mx-auto space-y-6">
              
              {/* Empty State / Welcome Screen (ChatGPT style) */}
              {isNewChat || messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 animate-fade-in">
                  <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center mb-4 shadow-md shadow-blue-500/20">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <h1 className="text-2xl font-bold text-slate-900 mb-2">
                    What can I help with?
                  </h1>
                  <p className="text-xs text-slate-500 max-w-md mb-8">
                    Ask questions, extract information, or summarize your synced Gmail messages and PDF attachments.
                  </p>

                  {/* 2x2 Grid of Starter Prompts (ChatGPT style) */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl text-left">
                    {SUGGESTED_PROMPTS.map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(item.prompt)}
                        className="p-3.5 rounded-2xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/30 transition-all text-left group shadow-xs hover:shadow-sm"
                      >
                        <p className="text-xs font-semibold text-slate-800 group-hover:text-blue-600 transition-colors mb-0.5">
                          {item.title}
                        </p>
                        <p className="text-[11px] text-slate-500 line-clamp-1">
                          {item.desc}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Chat Messages Stream */
                messages.map((msg) => {
                  const isHighlighted = activeChatId === msg.id;
                  return (
                    <div 
                      key={msg.id} 
                      id={`msg-${msg.id}`}
                      className={`space-y-4 py-2 transition-all ${
                        isHighlighted ? 'bg-blue-50/50 -mx-4 px-4 rounded-2xl' : ''
                      }`}
                    >
                      {/* USER PROMPT (ChatGPT style pill right-aligned) */}
                      <div className="flex justify-end">
                        <div className="max-w-xl bg-slate-100 hover:bg-slate-200/80 transition-colors px-4 py-3 rounded-2xl rounded-tr-xs text-slate-900 text-sm leading-relaxed whitespace-pre-wrap shadow-xs">
                          {msg.question}
                        </div>
                      </div>

                      {/* AI RESPONSE (ChatGPT style full width answer) */}
                      <div className="flex items-start gap-3">
                        <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                          <Bot className="w-4 h-4" />
                        </div>

                        <div className="flex-1 space-y-3 min-w-0">
                          {msg.answer === null ? (
                            <div className="flex items-center gap-2 text-slate-500 text-xs py-2">
                              <Sparkles className="w-4 h-4 text-blue-600 animate-spin" />
                              <span className="animate-pulse">Thinking & searching your emails...</span>
                            </div>
                          ) : (
                            <>
                              {/* Formatted Markdown Content */}
                              <div className="text-slate-800 text-sm leading-relaxed space-y-2 prose prose-slate max-w-none">
                                {msg.answer.split('\n\n').map((para, pIdx) => {
                                  if (para.startsWith('## ') || para.startsWith('### ')) {
                                    return (
                                      <h3 key={pIdx} className="font-bold text-slate-900 text-base mt-3 mb-1">
                                        {para.replace(/^#+\s*/, '')}
                                      </h3>
                                    );
                                  }
                                  if (para.startsWith('- ') || para.startsWith('* ')) {
                                    return (
                                      <ul key={pIdx} className="list-disc pl-5 space-y-1 text-slate-700">
                                        {para.split('\n').map((li, liIdx) => (
                                          <li key={liIdx}>{li.replace(/^[-*]\s*/, '')}</li>
                                        ))}
                                      </ul>
                                    );
                                  }
                                  return (
                                    <p key={pIdx} className="whitespace-pre-wrap text-slate-800">
                                      {para}
                                    </p>
                                  );
                                })}
                              </div>

                              {/* Source Citations Badges */}
                              {msg.sources && msg.sources.length > 0 && (
                                <div className="pt-3 border-t border-slate-100">
                                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                    <FileText className="w-3 h-3 text-blue-600" />
                                    <span>Sources Referenced ({msg.sources.length})</span>
                                  </p>
                                  <div className="flex flex-wrap gap-1.5">
                                    {msg.sources.map((src, sIdx) => (
                                      <div
                                        key={sIdx}
                                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700 hover:bg-slate-100 transition-colors"
                                      >
                                        <Mail className="w-3 h-3 text-blue-500" />
                                        <span className="font-medium truncate max-w-xs">{src.filename}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Action Footer (Copy, Model Info) */}
                              <div className="flex items-center gap-3 pt-1 text-slate-400 text-xs">
                                <button
                                  onClick={() => handleCopy(msg.id, msg.answer || '')}
                                  className="flex items-center gap-1 hover:text-slate-700 transition-colors p-1 rounded"
                                  title="Copy response"
                                >
                                  {copiedId === msg.id ? (
                                    <>
                                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                                      <span className="text-[11px] text-emerald-600">Copied</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="w-3.5 h-3.5" />
                                      <span className="text-[11px]">Copy</span>
                                    </>
                                  )}
                                </button>
                                <span>•</span>
                                <span className="text-[10px] text-slate-400 font-mono">
                                  {msg.model_used || 'InboxIQ AI'}
                                </span>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={chatEndRef} />
            </div>
          </div>

          {/* ================================================================= */}
          {/* 3. CHATGPT-STYLE FLOATING BOTTOM INPUT BAR                        */}
          {/* ================================================================= */}
          <div className="p-4 pt-2 bg-gradient-to-t from-white via-white to-transparent shrink-0">
            <div className="max-w-3xl mx-auto space-y-2">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
                className="flex items-end bg-slate-100 hover:bg-slate-100/90 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-500/15 focus-within:border-slate-300 border border-slate-200 rounded-3xl p-2 pl-4 transition-all shadow-xs"
              >
                <textarea
                  ref={textareaRef}
                  value={inputQuestion}
                  onChange={(e) => setInputQuestion(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  placeholder="Message InboxIQ..."
                  disabled={loading}
                  className="flex-1 bg-transparent text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none resize-none py-1.5 max-h-32 disabled:opacity-50"
                  style={{ minHeight: '24px' }}
                />

                {/* ChatGPT-style circular ArrowUp send button */}
                <button
                  type="submit"
                  disabled={!inputQuestion.trim() || loading}
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shrink-0 ml-2 ${
                    inputQuestion.trim() && !loading
                      ? 'bg-slate-900 text-white hover:bg-blue-600 active:scale-95 shadow-xs'
                      : 'bg-slate-300 text-slate-500 cursor-not-allowed opacity-60'
                  }`}
                  title="Send prompt"
                >
                  <ArrowUp className="w-4 h-4 stroke-[2.5]" />
                </button>
              </form>

              <p className="text-[11px] text-center text-slate-400">
                InboxIQ answers are grounded strictly in your synced emails. Verify important information.
              </p>
            </div>
          </div>

        </main>
      </div>
    </AppShell>
  );
}
