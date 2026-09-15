import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  X,
  Send,
  Cpu,
  Sparkles,
  Loader2,
  Trash2,
  History,
  ChevronLeft,
  ChevronRight,
  Clock,
  Zap,
  Bot,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../lib/api';

// Detect LLM provider from env (VITE_LLM_PROVIDER) or default display
const LLM_PROVIDER = (import.meta.env?.VITE_LLM_PROVIDER || 'gemini').toLowerCase();
const PROVIDER_LABELS = {
  watsonx: { label: 'IBM watsonx.ai', short: 'IBM Bob', color: 'text-blue-400', border: 'border-blue-500/40', bg: 'bg-blue-500/10' },
  gemini: { label: 'Google Gemini', short: 'Gemini', color: 'text-purple-400', border: 'border-purple-500/40', bg: 'bg-purple-500/10' },
  groq: { label: 'Groq LPU', short: 'Groq', color: 'text-orange-400', border: 'border-orange-500/40', bg: 'bg-orange-500/10' },
};
const providerInfo = PROVIDER_LABELS[LLM_PROVIDER] || PROVIDER_LABELS.gemini;

// Minimal markdown-like renderer for bold, bullet, blockquote, table
function BobMessage({ text }) {
  if (!text) return null;
  const lines = text.split('\n');
  return (
    <div className="space-y-1 leading-relaxed">
      {lines.map((line, i) => {
        if (line.startsWith('> ')) {
          return (
            <div key={i} className="border-l-2 border-amber-500/60 pl-2 text-amber-300/90 italic text-[11px]">
              {renderInline(line.slice(2))}
            </div>
          );
        }
        if (line.startsWith('| ') && line.endsWith(' |')) {
          return <div key={i} className="font-mono text-[10px] text-slate-400 truncate">{line}</div>;
        }
        if (line.match(/^[-*] /)) {
          return (
            <div key={i} className="flex gap-1.5 items-start">
              <span className="text-cyan mt-0.5 shrink-0">•</span>
              <span>{renderInline(line.slice(2))}</span>
            </div>
          );
        }
        if (line.match(/^\d+\. /)) {
          const [num, ...rest] = line.split('. ');
          return (
            <div key={i} className="flex gap-1.5 items-start">
              <span className="text-cyan font-bold shrink-0 text-[10px] mt-0.5">{num}.</span>
              <span>{renderInline(rest.join('. '))}</span>
            </div>
          );
        }
        if (line.startsWith('## ') || line.startsWith('### ')) {
          return <div key={i} className="font-bold text-white text-xs mt-2">{renderInline(line.replace(/^#+\s/, ''))}</div>;
        }
        if (line === '' || line === '---') return <div key={i} className="h-1" />;
        return <div key={i}>{renderInline(line)}</div>;
      })}
    </div>
  );
}

function renderInline(text) {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} className="rounded bg-surface-deep px-1 py-0.5 font-mono text-cyan text-[10px]">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

export default function ChatPanel({ lotId, isOpen, onClose, onLotChange }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [currentLot, setCurrentLot] = useState(lotId);

  // Past conversations sidebar
  const [showSessions, setShowSessions] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const messagesEndRef = useRef(null);

  const starterQuestions = [
    `Why did ${currentLot} have a yield drop?`,
    `What parameter drifted in the suspect tool?`,
    `What should I check first?`,
    `Show DOE verification matrix`,
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Escape to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Sync lotId prop to currentLot
  useEffect(() => {
    setCurrentLot(lotId);
  }, [lotId]);

  // Load chat history when lot or panel changes
  const loadHistory = useCallback(async (lot) => {
    if (!lot || !isOpen) return;
    try {
      const res = await api.getChatHistory(lot);
      if (res.history && res.history.length > 0) {
        const loaded = res.history.map((h) => ({
          sender: h.sender,
          text: h.message,
          citations: h.citations || [],
          timestamp: new Date(h.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }));
        setMessages(loaded);
        setHistory(res.history.map((h) => ({
          role: h.sender === 'user' ? 'user' : 'assistant',
          content: h.message,
        })));
      } else {
        setMessages([{
          sender: 'bob',
          text: `Hello! I'm **Bob**, your Cleanroom Semiconductor Copilot monitoring **${lot}**.\n\nAsk me about FDC sensor drift, Cpk degradation, spatial defect signatures, or recommended DOE split tests.`,
          citations: [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }]);
        setHistory([]);
      }
    } catch (err) {
      console.warn('Could not load history:', err);
    }
  }, [isOpen]);

  useEffect(() => {
    loadHistory(currentLot);
  }, [currentLot, isOpen, loadHistory]);

  // Load past sessions
  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const res = await api.getChatSessions();
      setSessions(res.sessions || []);
    } catch (err) {
      console.warn('Could not load sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const handleToggleSessions = () => {
    if (!showSessions) loadSessions();
    setShowSessions((v) => !v);
  };

  const handleSwitchLot = (lot) => {
    setCurrentLot(lot);
    setShowSessions(false);
    if (onLotChange) onLotChange(lot);
  };

  const handleClearHistory = async () => {
    if (!currentLot) return;
    try {
      await api.clearChatHistory(currentLot);
      setMessages([{
        sender: 'bob',
        text: `Chat history cleared. Still monitoring **${currentLot}**. How can I help you?`,
        citations: [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
      setHistory([]);
    } catch (err) {
      console.error('Error clearing history:', err);
    }
  };

  const handleSend = async (queryText) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || isLoading) return;

    const userMsg = {
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInput('');
    setIsLoading(true);

    try {
      const res = await api.sendChat(currentLot, textToSend, history);
      const bobMsg = {
        sender: 'bob',
        text: res.response,
        citations: res.cited_findings || [],
        provider: LLM_PROVIDER,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, bobMsg]);
      if (res.conversation_history) setHistory(res.conversation_history);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bob',
          text: `⚠️ **Communication timeout** — backend unreachable. Please ensure the backend server is running on port 8005.`,
          citations: [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/65 backdrop-blur-sm transition-opacity duration-300 ease-out"
        aria-hidden="true"
      />

      {/* Right Slide-Over Drawer */}
      <aside
        className="fixed top-0 right-0 bottom-0 z-50 flex h-full w-full sm:w-[500px] md:w-[540px] flex-col border-l border-cyan/40 bg-surface-1 shadow-2xl backdrop-blur-2xl transition-transform duration-300 ease-out font-sans animate-slide-left"
        aria-label="Ask Bob Copilot Panel"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border-subtle p-4 bg-surface-2/90 shrink-0">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-cyan/15 border border-cyan/40 text-cyan shadow-cyan-glow">
              <Cpu className="h-5 w-5 animate-pulse-cyan" />
              <span className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald opacity-75"></span>
                <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald border border-surface-1"></span>
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-sm font-bold text-white font-mono tracking-tight">Ask Bob</h2>
                <span className="rounded border border-cyan/40 bg-cyan/15 px-2 py-0.5 text-[10px] font-mono font-bold text-cyan uppercase tracking-wider">
                  Grounded
                </span>
                {/* IBM Bob / LLM Provider Badge */}
                <span className={`rounded border ${providerInfo.border} ${providerInfo.bg} px-2 py-0.5 text-[10px] font-mono font-bold ${providerInfo.color} uppercase tracking-wider flex items-center gap-1`}>
                  <Bot className="h-2.5 w-2.5" />
                  {providerInfo.short}
                </span>
              </div>
              <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                Monitoring: <span className="text-cyan font-bold">{currentLot}</span> · SECS/GEM V2.4
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Past Conversations */}
            <button
              onClick={handleToggleSessions}
              className={`flex h-8 w-8 items-center justify-center rounded-lg border transition-colors ${showSessions ? 'border-cyan/50 text-cyan bg-cyan/10' : 'border-border-subtle bg-surface-1 text-slate-400 hover:text-cyan hover:border-cyan/40'}`}
              title="Past Conversations"
            >
              <History className="h-4 w-4" />
            </button>
            {/* Clear */}
            <button
              onClick={handleClearHistory}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-subtle bg-surface-1 text-slate-400 hover:text-red-400 hover:border-red-500/40 transition-colors"
              title="Clear This Lot's History"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            {/* Close */}
            <button
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-subtle bg-surface-1 text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
              title="Close (Esc)"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Past Conversations Panel (collapsible) */}
        {showSessions && (
          <div className="border-b border-border-subtle bg-surface-deep shrink-0 max-h-56 overflow-y-auto">
            <div className="flex items-center gap-2 px-4 py-2.5 text-[10px] font-mono uppercase tracking-wider text-slate-400 border-b border-border-subtle/50">
              <History className="h-3 w-3 text-cyan" />
              <span>Past Conversations</span>
              <span className="ml-auto text-slate-600">{sessions.length} lots</span>
            </div>
            {sessionsLoading ? (
              <div className="flex items-center justify-center gap-2 py-4 text-xs font-mono text-slate-400">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Loading sessions...</span>
              </div>
            ) : sessions.length === 0 ? (
              <div className="px-4 py-3 text-xs font-mono text-slate-500 text-center">No saved conversations yet.</div>
            ) : (
              <div className="divide-y divide-border-subtle/40">
                {sessions.map((s) => (
                  <button
                    key={s.lot_id}
                    onClick={() => handleSwitchLot(s.lot_id)}
                    className={`w-full text-left px-4 py-2.5 flex items-center gap-3 hover:bg-surface-2 transition-colors group ${s.lot_id === currentLot ? 'bg-cyan/5 border-l-2 border-cyan' : ''}`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-mono font-bold ${s.lot_id === currentLot ? 'text-cyan' : 'text-white group-hover:text-cyan transition-colors'}`}>
                          {s.lot_id}
                        </span>
                        {s.lot_id === currentLot && (
                          <span className="rounded bg-cyan/20 px-1.5 py-0.5 text-[9px] font-mono text-cyan uppercase">Active</span>
                        )}
                        <span className="ml-auto text-[10px] font-mono text-slate-500 flex items-center gap-1">
                          <MessageSquare className="h-2.5 w-2.5" />
                          {s.message_count}
                        </span>
                      </div>
                      {s.last_user_message && (
                        <p className="text-[10px] font-mono text-slate-500 truncate mt-0.5">
                          {s.last_user_message.slice(0, 60)}{s.last_user_message.length > 60 ? '…' : ''}
                        </p>
                      )}
                      {s.last_active && (
                        <p className="text-[9px] font-mono text-slate-600 mt-0.5 flex items-center gap-1">
                          <Clock className="h-2 w-2" />
                          {new Date(s.last_active).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </p>
                      )}
                    </div>
                    <ChevronRight className="h-3.5 w-3.5 text-slate-600 group-hover:text-cyan transition-colors shrink-0" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Quick Inquiry Chips */}
        <div className="border-b border-border-subtle bg-surface-deep/80 px-4 py-3 shrink-0">
          <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-2">
            <Sparkles className="h-3 w-3 text-cyan" />
            <span>Suggested Inquiries:</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {starterQuestions.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                disabled={isLoading}
                className="rounded-md border border-border-subtle bg-surface-2 px-2.5 py-1 text-[11px] font-mono text-slate-300 hover:border-cyan/50 hover:text-cyan hover:bg-surface-3 transition-all text-left disabled:opacity-40"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs font-sans">
          {messages.map((m, i) => {
            const isBob = m.sender === 'bob';
            return (
              <div key={i} className={`flex flex-col ${isBob ? 'items-start' : 'items-end'}`}>
                {isBob && (
                  <div className="flex items-center gap-2 mb-1 px-1">
                    <div className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan/20 border border-cyan/30">
                      <Bot className="h-3 w-3 text-cyan" />
                    </div>
                    <span className="text-[10px] font-mono font-bold text-cyan">BOB</span>
                    {m.provider && (
                      <span className={`text-[9px] font-mono ${PROVIDER_LABELS[m.provider]?.color || 'text-slate-500'} flex items-center gap-1`}>
                        <Zap className="h-2 w-2" />
                        {PROVIDER_LABELS[m.provider]?.label || m.provider}
                      </span>
                    )}
                  </div>
                )}
                <div
                  className={`max-w-[92%] rounded-xl p-3.5 leading-relaxed ${
                    isBob
                      ? 'border border-border-subtle bg-surface-2 text-slate-200 border-l-4 border-l-cyan shadow-glass'
                      : 'bg-gradient-to-r from-cyan to-cyan-bright text-canvas font-semibold shadow-cyan-glow'
                  }`}
                >
                  {isBob ? (
                    <BobMessage text={m.text} />
                  ) : (
                    <div className="whitespace-pre-wrap">{m.text}</div>
                  )}

                  {/* Citation Badges */}
                  {isBob && m.citations && m.citations.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-border-subtle text-[11px] font-mono space-y-1.5">
                      <span className="text-slate-400 block text-[10px] uppercase tracking-wider font-bold flex items-center gap-1">
                        <CheckCircle2 className="h-2.5 w-2.5 text-emerald" />
                        Traceable Evidence:
                      </span>
                      {m.citations.map((c, cIdx) => (
                        <div
                          key={cIdx}
                          className="rounded-lg bg-surface-deep p-2 border border-cyan/30 text-slate-300 flex items-center justify-between"
                        >
                          <div>
                            <span className="font-bold text-cyan">{c.tool_id}</span>{' '}
                            <span className="text-slate-400">({c.parameter})</span>
                            <span className="text-slate-400 block text-[10px]">
                              Cpk:{' '}
                              <strong className={c.cpk < 1.33 ? 'text-red-400' : 'text-emerald'}>
                                {c.cpk}
                              </strong>{' '}
                              · Step: {c.step}
                            </span>
                          </div>
                          {c.probability && (
                            <span className="rounded bg-cyan/15 px-2 py-0.5 font-bold text-cyan text-[10px] border border-cyan/40">
                              {Math.round(c.probability * 100)}% Prob
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <span className="text-[10px] font-mono text-slate-500 mt-1 px-1">{m.timestamp}</span>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex items-center gap-2 rounded-lg border border-cyan/30 bg-surface-2 p-3 text-xs font-mono text-cyan">
              <Loader2 className="h-4 w-4 animate-spin text-cyan" />
              <span>Synthesising FDC telemetry · Cpk models · {providerInfo.label}…</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="border-t border-border-subtle p-3.5 bg-surface-2/95 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask Bob about ${currentLot}…`}
              className="flex-1 rounded-lg border border-border-subtle bg-surface-deep px-3.5 py-2.5 text-xs font-mono text-white placeholder-slate-500 focus:border-cyan focus:outline-none focus:ring-1 focus:ring-cyan"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan text-canvas hover:bg-cyan-bright transition-all shadow-cyan-glow disabled:opacity-40 disabled:hover:bg-cyan shrink-0"
              title="Send"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
          <div className="flex items-center justify-between mt-2">
            <p className="text-[10px] font-mono text-slate-500">Physics-grounded · DOE-caveated · strictly non-hallucinating</p>
            <span className={`text-[10px] font-mono ${providerInfo.color} flex items-center gap-1`}>
              <Zap className="h-2.5 w-2.5" />
              {providerInfo.label}
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}
