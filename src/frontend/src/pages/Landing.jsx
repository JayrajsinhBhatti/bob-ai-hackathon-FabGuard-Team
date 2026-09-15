import React from 'react';
import {
  ArrowRight,
  ShieldCheck,
  Cpu,
  Activity,
  Layers,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Compass,
} from 'lucide-react';
import WaferMap3D from '../components/WaferMap3D';

export default function Landing({ onNavigate, onOpenChat, sampleLot, sampleDefects }) {
  return (
    <div className="min-h-screen bg-canvas text-white bg-cleanroom-grid">
      
      {/* SECTION 1: HERO */}
      <section className="relative overflow-hidden pt-12 pb-20 px-4 sm:px-6 lg:px-8 border-b border-border-subtle">
        <div className="mx-auto max-w-5xl text-center">
          
          {/* Tag badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan/40 bg-cyan/10 px-3.5 py-1 text-xs font-mono text-cyan mb-6 shadow-cyan-glow">
            <span className="flex h-2 w-2 rounded-full bg-cyan animate-ping"></span>
            SEMI E10 & SECS/GEM V2.4 PHYSICS-INFORMED AI ENGINE
          </div>

          {/* Headline based on Cost Hook */}
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
            A 1% yield drop costs tens of millions a month.{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan to-cyan-bright">
              Bob finds the root cause in seconds
            </span>{' '}
            — and proves how often it's right.
          </h1>

          {/* Subheadline: 3 Key Differentiators */}
          <p className="mt-6 text-base sm:text-lg text-slate-300 max-w-3xl mx-auto leading-relaxed">
            Built for modern cleanrooms: <strong className="text-white">calibrated Bayesian probabilities</strong> (not arbitrary guess-scores), an empirical <strong className="text-white">validation gate against known fab ground truth</strong>, and an engineering copilot with <strong className="text-white">strict DOE caveats that never overclaims</strong>.
          </p>

          {/* CTAs */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4 font-mono text-xs">
            <button
              onClick={() => onNavigate('dashboard')}
              className="flex items-center gap-2 rounded-lg bg-cyan px-6 py-3.5 font-bold text-canvas hover:bg-cyan-bright shadow-cyan-glow transition-all hover:scale-105"
            >
              <span>Open the Dashboard</span>
              <ArrowRight className="h-4 w-4" />
            </button>

            <button
              onClick={onOpenChat}
              className="flex items-center gap-2 rounded-lg border border-cyan/40 bg-surface-1 px-6 py-3.5 font-bold text-cyan hover:bg-cyan/15 hover:border-cyan transition-all"
            >
              <Sparkles className="h-4 w-4" />
              <span>Ask Bob a Question</span>
            </button>
          </div>
        </div>
      </section>

      {/* SECTION 2: THE PROBLEM (Scannable Stat Callouts) */}
      <section className="py-14 px-4 sm:px-6 lg:px-8 border-b border-border-subtle bg-surface-1/40">
        <div className="mx-auto max-w-5xl">
          <div className="text-center mb-8">
            <span className="text-xs font-mono uppercase tracking-widest text-slate-400">
              The Reality of Sub-5nm Fabrication
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 font-mono text-center">
            <div className="rounded-xl border border-border-subtle bg-surface-1 p-6 shadow-glass">
              <span className="text-4xl sm:text-5xl font-extrabold text-amber block tracking-tight">
                $90B<span className="text-2xl text-slate-400 font-normal">/yr</span>
              </span>
              <p className="text-xs text-slate-300 mt-2 font-sans font-medium">
                Global semiconductor yield excursion & maintenance overhead worldwide.
              </p>
            </div>

            <div className="rounded-xl border border-border-subtle bg-surface-1 p-6 shadow-glass">
              <span className="text-4xl sm:text-5xl font-extrabold text-red-400 block tracking-tight">
                3–6 <span className="text-2xl text-slate-400 font-normal">Weeks</span>
              </span>
              <p className="text-xs text-slate-300 mt-2 font-sans font-medium">
                Average manual root-cause investigation across 500+ FDC sensors & optical inspection tools.
              </p>
            </div>

            <div className="rounded-xl border border-border-subtle bg-surface-1 p-6 shadow-glass">
              <span className="text-4xl sm:text-5xl font-extrabold text-cyan block tracking-tight">
                1% <span className="text-2xl text-slate-400 font-normal">Drop</span>
              </span>
              <p className="text-xs text-slate-300 mt-2 font-sans font-medium">
                A single percent yield excursion on 3nm wafers exposes tens of millions in monthly wafer scrap.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3: WHAT MAKES BOB DIFFERENT (The 3 Differentiation Pillars) */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-b border-border-subtle">
        <div className="mx-auto max-w-5xl">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan block mb-2">
              Competitive Differentiation
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Why Bob is Not Just Another Dashboard
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Pillar 1 */}
            <div className="rounded-xl border border-cyan/40 bg-surface-1/90 p-6 shadow-glass relative flex flex-col justify-between">
              <div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan/20 text-cyan mb-4">
                  <Activity className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-white mb-2 font-mono">
                  1. "Not a Black Box"
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed font-sans mb-4">
                  Every candidate cause ships with true statistical provenance: degraded Cpk, sample sizes ($n=14$), and Bayesian confidence intervals instead of an arbitrary 0–100 score.
                </p>
              </div>
              <div className="rounded bg-surface-deep p-2 text-[11px] font-mono text-cyan border border-border-subtle">
                Proof: Direct Cpk & z-score readouts inline.
              </div>
            </div>

            {/* Pillar 2 */}
            <div className="rounded-xl border border-amber/40 bg-surface-1/90 p-6 shadow-glass relative flex flex-col justify-between">
              <div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber/20 text-amber mb-4">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-white mb-2 font-mono">
                  2. "Not Overclaiming"
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed font-sans mb-4">
                  Real process engineers do not blindly trust software. Bob enforces mandatory inline DOE (Design of Experiments) confirmation caveats before any chamber recipe is altered.
                </p>
              </div>
              <div className="rounded bg-surface-deep p-2 text-[11px] font-mono text-amber border border-border-subtle">
                Proof: Strict 2-wafer DOE alert inline.
              </div>
            </div>

            {/* Pillar 3 */}
            <div className="rounded-xl border border-emerald/40 bg-surface-1/90 p-6 shadow-glass relative flex flex-col justify-between">
              <div>
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald/20 text-emerald mb-4">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <h3 className="text-base font-bold text-white mb-2 font-mono">
                  3. "Provably Accurate"
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed font-sans mb-4">
                  We don't ask you to trust a slide deck. Our live Validation Gate shows real 93.2% Top-1 and 98.6% Top-3 accuracy against 74 injected ground-truth scenarios directly in the app.
                </p>
              </div>
              <div className="rounded bg-surface-deep p-2 text-[11px] font-mono text-emerald border border-border-subtle">
                Proof: Live reliability calibration curve.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 4: LIVE INTERACTIVE PREVIEW (3D Wafer Map Showcase) */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-b border-border-subtle bg-surface-deep/70">
        <div className="mx-auto max-w-5xl">
          <div className="text-center max-w-2xl mx-auto mb-8">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan block mb-1">
              Live Product Demonstration
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Interactive 300mm Wafer Defect Metrology
            </h2>
            <p className="text-xs text-slate-400 mt-2">
              Drag to orbit 360° • Classified spatial signature: <strong className="text-red-400">EDGE-RING</strong> (ETCH-07 Chamber Pressure Drift)
            </p>
          </div>

          <div className="max-w-2xl mx-auto">
            <WaferMap3D
              lotId={sampleLot?.lot_id || 'LOT-2231'}
              defects={sampleDefects || []}
              signature="edge-ring"
              severitySummary={{ critical: 180, major: 340, minor: 920 }}
            />
          </div>
        </div>
      </section>

      {/* SECTION 5: HOW IT WORKS (4-Step Pipeline Flow) */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-b border-border-subtle">
        <div className="mx-auto max-w-5xl">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs font-mono uppercase tracking-widest text-slate-400 block mb-1">
              Architecture
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              The 4-Step Causality Pipeline
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
            <div className="rounded-lg border border-border-subtle bg-surface-1 p-4">
              <span className="text-cyan font-bold block mb-1">01 / SENSOR DATA</span>
              <p className="text-slate-300 font-sans text-xs">
                Streams SECS/GEM high-frequency FDC telemetry & optical wafer inspection defect coordinates.
              </p>
            </div>

            <div className="rounded-lg border border-border-subtle bg-surface-1 p-4">
              <span className="text-cyan font-bold block mb-1">02 / PATTERN ENGINE</span>
              <p className="text-slate-300 font-sans text-xs">
                Classifies spatial defect morphology (edge-ring, center-cluster, scratch, donut) and SPC violations.
              </p>
            </div>

            <div className="rounded-lg border border-border-subtle bg-surface-1 p-4">
              <span className="text-cyan font-bold block mb-1">03 / CALIBRATED RANKING</span>
              <p className="text-slate-300 font-sans text-xs">
                Ranks candidate root causes with honest calibrated Bayesian probability, degraded Cpk, and sample sizes.
              </p>
            </div>

            <div className="rounded-lg border border-border-subtle bg-surface-1 p-4">
              <span className="text-cyan font-bold block mb-1">04 / COPILOT ACTION</span>
              <p className="text-slate-300 font-sans text-xs">
                Synthesizes plain-English root causes, cites evidence cards, and stages verification DOE split tests.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 6: FOOTER CTA */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 text-center bg-surface-1/80">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-4">
            Ready to inspect the live cleanroom telemetry?
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mb-8 font-mono">
            Directly connected to bob_fab.db • 119 Lots • 219,707 Defects • 74 Ground Truth Audits
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4 font-mono text-xs">
            <button
              onClick={() => onNavigate('dashboard')}
              className="flex items-center gap-2 rounded-lg bg-cyan px-6 py-3 font-bold text-canvas hover:bg-cyan-bright shadow-cyan-glow transition-all"
            >
              <span>Launch Live Dashboard</span>
              <ArrowRight className="h-4 w-4" />
            </button>
            <button
              onClick={() => onNavigate('validation')}
              className="flex items-center gap-2 rounded-lg border border-emerald/40 bg-emerald/10 px-6 py-3 font-bold text-emerald hover:bg-emerald/20 transition-all"
            >
              <ShieldCheck className="h-4 w-4" />
              <span>Inspect Validation Proof</span>
            </button>
          </div>
        </div>
      </section>

    </div>
  );
}
