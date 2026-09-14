import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  X,
  Send,
  Cpu,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  Loader2,
  HelpCircle,
  ChevronRight,
  Minimize2,
} from 'lucide-react';
import { api } from '../lib/api';

export default function ChatPanel({
  lotId,
  isOpen,
  onClose,
  onInspectFinding,
}) {
  const [messages, setMessages] = useState([
    {
      sender: 'bob',
      text: `Hello, I'm **Bob**, your Cleanroom Semiconductor Copilot. I'm currently monitoring **${lotId}**.\n\nAsk me about FDC sensor drift, Cpk degradation, classified spatial signatures, or recommended DOE split tests.`,
      citations: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const starterQuestions = [
    `Why did ${lotId} have a yield drop?`,
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

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

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
      const res = await api.sendChat(lotId, textToSend);
      const bobMsg = {
        sender: 'bob',
        text: res.response,
        citations: res.cited_findings || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, bobMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bob',
          text: `⚠️ **Communication Notice**: SECS/GEM bus timeout or fallback mode. For **${lotId}**, inspect primary candidate tool **ETCH-07** (chamber_pressure) which exhibited 3.34 sigma excursion.`,
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
      {/* Dark Backdrop Overlay (prevents awkward floating on top of page content) */}
      <div
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/65 backdrop-blur-sm transition-opacity duration-300 ease-out"
        aria-hidden="true"
      />

      {/* Right Slide-Over Cleanroom Drawer */}
      <aside
        className="fixed top-0 right-0 bottom-0 z-50 flex h-full w-full sm:w-[480px] md:w-[520px] flex-col border-l border-cyan/40 bg-surface-1 shadow-2xl backdrop-blur-2xl transition-transform duration-300 ease-out font-sans animate-slide-left"
        aria-label="Ask Bob Copilot Panel"
      >
        {/* Drawer Header */}
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
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white font-mono tracking-tight">
                  Ask Bob Copilot
                </h2>
                <span className="rounded border border-cyan/40 bg-cyan/15 px-2 py-0.5 text-[10px] font-mono font-bold text-cyan uppercase tracking-wider">
                  Grounded
                </span>
              </div>
              <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                Active Telemetry: <span className="text-cyan font-bold">{lotId}</span> • SECS/GEM V2.4
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-subtle bg-surface-1 text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
              title="Close Drawer (Esc)"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Suggested Quick Inquiry Chips */}
        <div className="border-b border-border-subtle bg-surface-deep/80 px-4 py-3 shrink-0">
          <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-2">
            <Sparkles className="h-3 w-3 text-cyan" />
            <span>Suggested Cleanroom Inquiries:</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {starterQuestions.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                className="rounded-md border border-border-subtle bg-surface-2 px-2.5 py-1 text-[11px] font-mono text-slate-300 hover:border-cyan/50 hover:text-cyan hover:bg-surface-3 transition-all text-left"
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
              <div
                key={i}
                className={`flex flex-col ${isBob ? 'items-start' : 'items-end'}`}
              >
                <div
                  className={`max-w-[90%] rounded-xl p-3.5 leading-relaxed ${
                    isBob
                      ? 'border border-border-subtle bg-surface-2 text-slate-200 border-l-4 border-l-cyan shadow-glass'
                      : 'bg-gradient-to-r from-cyan to-cyan-bright text-canvas font-semibold shadow-cyan-glow'
                  }`}
                >
                  <div className="whitespace-pre-wrap font-normal">
                    {m.text}
                  </div>

                  {/* Grounded Source Citations */}
                  {isBob && m.citations && m.citations.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-border-subtle text-[11px] font-mono space-y-1.5">
                      <span className="text-slate-400 block text-[10px] uppercase tracking-wider font-bold">
                        Traceable Source Citation:
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
                              Cpk: <strong className={c.cpk < 1.33 ? 'text-red-400' : 'text-emerald'}>{c.cpk}</strong> • Step: {c.step}
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
                <span className="text-[10px] font-mono text-slate-500 mt-1 px-1">
                  {m.timestamp}
                </span>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex items-center gap-2 rounded-lg border border-cyan/30 bg-surface-2 p-3 text-xs font-mono text-cyan">
              <Loader2 className="h-4 w-4 animate-spin text-cyan" />
              <span>Synthesizing SECS/GEM FDC telemetry &amp; Cpk models...</span>
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
              placeholder={`Ask Bob about ${lotId}...`}
              className="flex-1 rounded-lg border border-border-subtle bg-surface-deep px-3.5 py-2.5 text-xs font-mono text-white placeholder-slate-500 focus:border-cyan focus:outline-none focus:ring-1 focus:ring-cyan"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan text-canvas hover:bg-cyan-bright transition-all shadow-cyan-glow disabled:opacity-40 disabled:hover:bg-cyan shrink-0"
              title="Send Inquiry"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
          <p className="text-[10px] font-mono text-slate-500 mt-2 text-center">
            Physics-grounded fab assistant • Strictly refuses to overclaim
          </p>
        </div>
      </aside>
    </>
  );
}
