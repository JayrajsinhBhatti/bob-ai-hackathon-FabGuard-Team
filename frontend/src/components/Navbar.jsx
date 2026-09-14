import React, { useState } from 'react';
import {
  Cpu,
  Activity,
  ShieldCheck,
  AlertTriangle,
  MessageSquare,
  ChevronDown,
  Menu,
  X,
  Sparkles,
  Layers,
} from 'lucide-react';

export default function Navbar({
  currentRoute,
  onNavigate,
  lots = [],
  selectedLotId,
  onSelectLot,
  onToggleChat,
  isChatOpen,
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleNav = (route) => {
    onNavigate(route);
    setIsMobileMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border-subtle bg-canvas/98 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex h-16 items-center justify-between gap-2 sm:gap-4">
        
        {/* LEFT: BRAND & INLINE STATUS */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => handleNav('landing')}
            className="flex items-center gap-2.5 sm:gap-3 text-left group focus:outline-none"
          >
            <div className="relative flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center rounded-xl border border-cyan/40 bg-surface-1 shadow-cyan-glow group-hover:border-cyan transition-all">
              <Cpu className="h-5 w-5 text-cyan animate-pulse-cyan" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 sm:gap-2">
                <span className="text-sm sm:text-base font-bold tracking-tight text-white group-hover:text-cyan transition-colors whitespace-nowrap font-sans">
                  Bob Fab Copilot
                </span>
                <span className="rounded border border-cyan/40 bg-cyan/10 px-1.5 py-0.5 text-[9px] font-mono font-bold tracking-wider text-cyan uppercase hidden sm:inline">
                  3NM EUV
                </span>
                {/* Compact inline live status dot */}
                <span className="flex items-center gap-1 rounded-full bg-emerald/10 border border-emerald/30 px-1.5 py-0.5 text-[9px] font-mono font-semibold text-emerald ml-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald animate-pulse"></span>
                  <span className="hidden md:inline">FAB-12 95%</span>
                </span>
              </div>
              <p className="text-[10px] font-mono text-slate-400 hidden sm:block truncate">
                Semiconductor Yield & Causality Engine
              </p>
            </div>
          </button>
        </div>

        {/* CENTER: CLEAN NAV TABS */}
        <nav className="hidden md:flex items-center rounded-lg border border-border-subtle bg-surface-1/70 p-1 font-mono text-xs shadow-inner shrink-0">
          <button
            onClick={() => handleNav('landing')}
            className={`rounded-md px-3 py-1.5 font-medium transition-all ${
              currentRoute === 'landing'
                ? 'bg-cyan/20 text-cyan border border-cyan/40 font-bold shadow-cyan-glow'
                : 'text-slate-400 hover:text-white hover:bg-surface-2'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => handleNav('dashboard')}
            className={`rounded-md px-3 py-1.5 font-medium transition-all ${
              currentRoute === 'dashboard'
                ? 'bg-cyan/20 text-cyan border border-cyan/40 font-bold shadow-cyan-glow'
                : 'text-slate-400 hover:text-white hover:bg-surface-2'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => handleNav('validation')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all ${
              currentRoute === 'validation'
                ? 'bg-cyan/20 text-cyan border border-cyan/40 font-bold shadow-cyan-glow'
                : 'text-slate-400 hover:text-white hover:bg-surface-2'
            }`}
          >
            <ShieldCheck className="h-3.5 w-3.5 text-emerald" />
            <span>Validation</span>
          </button>
          <button
            onClick={() => handleNav('at-risk')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all ${
              currentRoute === 'at-risk'
                ? 'bg-amber/20 text-amber border border-amber/40 font-bold shadow-amber-glow'
                : 'text-slate-400 hover:text-white hover:bg-surface-2'
            }`}
          >
            <AlertTriangle className="h-3.5 w-3.5 text-amber" />
            <span>At-Risk Queue</span>
          </button>
        </nav>

        {/* RIGHT: PROMINENT GLOWING ASK BOB BUTTON */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Ask Bob Action Button — PROMINENT, PROPERLY ALIGNED, NEVER CLIPPED */}
          <button
            onClick={onToggleChat}
            className={`flex items-center gap-2 rounded-lg border px-3.5 py-1.5 text-xs font-mono font-bold tracking-wide transition-all shadow-sm shrink-0 ${
              isChatOpen
                ? 'border-cyan bg-cyan text-canvas shadow-cyan-glow'
                : 'border-cyan/50 bg-cyan/15 text-cyan hover:bg-cyan/25 hover:border-cyan shadow-cyan-glow'
            }`}
            title="Open Cleanroom Copilot Drawer"
          >
            <MessageSquare className="h-4 w-4 shrink-0" />
            <span className="font-bold whitespace-nowrap">Ask Bob</span>
            <span className="flex h-1.5 w-1.5 rounded-full bg-emerald animate-pulse shrink-0"></span>
          </button>

          {/* Mobile Hamburger Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden flex h-9 w-9 items-center justify-center rounded-lg border border-border-subtle bg-surface-1 text-slate-400 hover:text-white hover:border-slate-600 transition-colors shrink-0"
            title="Toggle Menu"
          >
            {isMobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>

      </div>

      {/* MOBILE / TABLET EXPANDABLE NAVIGATION DRAWER */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-border-subtle bg-surface-1/98 p-4 font-mono text-xs space-y-3 backdrop-blur-2xl shadow-2xl animate-fade-in">
          <div className="flex items-center justify-between pb-2 border-b border-border-subtle text-slate-400 text-[11px]">
            <span>SECS/GEM FAB-12 STATUS:</span>
            <span className="text-emerald font-bold">ONLINE (95.0% TARGET)</span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleNav('landing')}
              className={`rounded-lg p-2.5 text-left font-medium transition-colors ${
                currentRoute === 'landing' ? 'bg-cyan/20 text-cyan font-bold border border-cyan/40' : 'text-slate-300 hover:bg-surface-2'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => handleNav('dashboard')}
              className={`rounded-lg p-2.5 text-left font-medium transition-colors ${
                currentRoute === 'dashboard' ? 'bg-cyan/20 text-cyan font-bold border border-cyan/40' : 'text-slate-300 hover:bg-surface-2'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => handleNav('validation')}
              className={`rounded-lg p-2.5 text-left font-medium flex items-center gap-1.5 transition-colors ${
                currentRoute === 'validation' ? 'bg-cyan/20 text-cyan font-bold border border-cyan/40' : 'text-slate-300 hover:bg-surface-2'
              }`}
            >
              <ShieldCheck className="h-3.5 w-3.5 text-emerald" />
              <span>Validation Gate</span>
            </button>
            <button
              onClick={() => handleNav('at-risk')}
              className={`rounded-lg p-2.5 text-left font-medium flex items-center gap-1.5 transition-colors ${
                currentRoute === 'at-risk' ? 'bg-amber/20 text-amber font-bold border border-amber/40' : 'text-slate-300 hover:bg-surface-2'
              }`}
            >
              <AlertTriangle className="h-3.5 w-3.5 text-amber" />
              <span>At-Risk Queue</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
