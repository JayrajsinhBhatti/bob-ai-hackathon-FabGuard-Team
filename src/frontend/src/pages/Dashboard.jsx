import React, { useState } from 'react';
import {
  Activity,
  Layers,
  AlertTriangle,
  TrendingDown,
  ShieldCheck,
  Zap,
  Target,
  ChevronRight,
  ChevronDown,
  Flame,
  PlusCircle,
  UploadCloud,
  X,
  CheckCircle2,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import YieldTrendChart from '../components/YieldTrendChart';
import WaferMap3D from '../components/WaferMap3D';
import RootCauseRankingPanel from '../components/RootCauseRankingPanel';
import AtRiskList from '../components/AtRiskList';
import { api } from '../lib/api';

export default function Dashboard({
  lots = [],
  selectedLot,
  selectedLotId,
  onSelectLot,
  defects = [],
  findings,
  tier,
  onChangeTier,
  atRiskBatches = [],
  heldLots = {},
  onHoldLot,
  isLoading,
  onRefreshLots,
}) {
  const lot = selectedLot || {};
  const isExcursion = lot.final_yield_pct !== null && lot.final_yield_pct < 90;

  // Ingest Lot modal state
  const [isIngestOpen, setIsIngestOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ingestToast, setIngestToast] = useState(null);
  const [ingestForm, setIngestForm] = useState({
    lot_id: `LOT-N3-${Math.floor(100 + Math.random() * 900)}`,
    product_id: 'PROD-3NM-SOC',
    fab_line: 'LINE-01-FAB12',
    final_yield_pct: 69.4,
    signature: 'edge-ring',
    defect_count: 820,
    suspect_tool: 'CMP-02',
    suspect_step: 'cmp',
    suspect_parameter: 'head_downforce',
    z_score_drift: 3.8,
  });

  // Preset templates for quick demo testing
  const presets = [
    {
      label: '3nm CMP Head Downforce Excursion (Edge-Ring)',
      lot_id: 'LOT-CMP-EXP',
      product_id: 'PROD-3NM-SOC',
      final_yield_pct: 68.2,
      signature: 'edge-ring',
      defect_count: 850,
      suspect_tool: 'CMP-02',
      suspect_step: 'cmp',
      suspect_parameter: 'head_downforce',
      z_score_drift: 4.1,
    },
    {
      label: 'EUV Litho Scanner Focus Drift (Center Cluster)',
      lot_id: 'LOT-LITHO-EXP',
      product_id: 'PROD-3NM-AI-ACCEL',
      final_yield_pct: 73.8,
      signature: 'center-cluster',
      defect_count: 650,
      suspect_tool: 'LITHO-01',
      suspect_step: 'litho',
      suspect_parameter: 'focus_offset',
      z_score_drift: 3.5,
    },
    {
      label: 'Robot End-Effector Wafer Scratch (Linear Scratch)',
      lot_id: 'LOT-SCRATCH-01',
      product_id: 'PROD-3NM-SOC',
      final_yield_pct: 64.5,
      signature: 'scratch',
      defect_count: 1100,
      suspect_tool: 'ETCH-02',
      suspect_step: 'etch',
      suspect_parameter: 'rf_power_forward',
      z_score_drift: 4.6,
    },
  ];

  const handleApplyPreset = (p) => {
    setIngestForm({ ...p, fab_line: 'LINE-01-FAB12' });
  };

  const handleIngestSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.ingestLot(ingestForm);
      setIngestToast(`Successfully ingested ${ingestForm.lot_id}! Triggering real-time causality engine...`);
      setIsIngestOpen(false);
      if (onRefreshLots) {
        await onRefreshLots(ingestForm.lot_id);
      }
      setTimeout(() => setIngestToast(null), 4500);
    } catch (err) {
      setIngestToast(`Error: ${err.message}`);
      setTimeout(() => setIngestToast(null), 4500);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Aggregate stats
  const completed = (lots || []).filter((l) => l.final_yield_pct !== null);
  const avgYield = completed.length
    ? (completed.reduce((acc, l) => acc + l.final_yield_pct, 0) / completed.length).toFixed(1)
    : '95.2';
  const excursionCount = completed.filter((l) => l.final_yield_pct < 90).length;
  const highRiskCount = (atRiskBatches || []).filter((b) => (b.probability || 0) >= 0.7).length;

  // Quick jump targets for demo
  const worstLot = (lots || [])
    .filter((l) => l.final_yield_pct !== null)
    .sort((a, b) => a.final_yield_pct - b.final_yield_pct)[0];

  return (
    <div className="space-y-6 pb-12">
      
      {/* TOP KPI BANNER */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 font-mono">
        <div className="glass-panel rounded-xl p-3.5 sm:p-4 border-l-2 border-l-cyan shadow-glass">
          <span className="text-[10px] sm:text-[11px] text-slate-400 uppercase tracking-wider block">
            Fleet Avg Yield
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-white">{avgYield}%</span>
            <span className="text-[10px] sm:text-[11px] text-slate-400">Spec: 95.0%</span>
          </div>
        </div>

        <div className="glass-panel rounded-xl p-3.5 sm:p-4 border-l-2 border-l-red-500 shadow-glass">
          <span className="text-[10px] sm:text-[11px] text-slate-400 uppercase tracking-wider block">
            Active Excursions
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-red-400">{excursionCount}</span>
            <span className="text-[10px] sm:text-[11px] text-slate-400">&lt;90% Yield</span>
          </div>
        </div>

        <div className="glass-panel rounded-xl p-3.5 sm:p-4 border-l-2 border-l-amber shadow-glass">
          <span className="text-[10px] sm:text-[11px] text-slate-400 uppercase tracking-wider block">
            At-Risk Queue
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-amber">{highRiskCount}</span>
            <span className="text-[10px] sm:text-[11px] text-slate-400">Critical Batches</span>
          </div>
        </div>

        <div className="glass-panel rounded-xl p-3.5 sm:p-4 border-l-2 border-l-emerald shadow-glass">
          <span className="text-[10px] sm:text-[11px] text-slate-400 uppercase tracking-wider block">
            Validation Gate
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-emerald">93.2%</span>
            <span className="text-[10px] sm:text-[11px] text-emerald font-semibold">Top-1 Passed</span>
          </div>
        </div>
      </div>

      {/* YIELD TREND CHART SECTION */}
      <YieldTrendChart
        lots={lots}
        selectedLotId={selectedLotId}
        onSelectLot={onSelectLot}
      />

      {/* ACTIVE LOT CONTEXT STRIP WITH INTERACTIVE LOT SELECTOR */}
      <div className="rounded-xl border border-border-subtle bg-surface-1/95 px-4 sm:px-5 py-3 font-mono text-xs flex flex-wrap items-center justify-between gap-3 sm:gap-4 shadow-glass">
        {/* Left: Interactive Lot Selector Dropdown */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          <span className="text-slate-400 text-[11px] font-bold uppercase tracking-wider">
            INSPECT LOT:
          </span>
          <div className="relative">
            <select
              value={selectedLotId || ''}
              onChange={(e) => onSelectLot(e.target.value)}
              className="appearance-none rounded-lg border border-cyan/40 bg-surface-2 py-1.5 pl-3 pr-8 text-xs font-mono font-bold text-cyan hover:border-cyan focus:border-cyan focus:outline-none transition-all cursor-pointer shadow-cyan-glow"
            >
              {lots.map((l) => (
                <option key={l.lot_id} value={l.lot_id} className="bg-surface-1 text-slate-200">
                  {l.lot_id} {l.final_yield_pct != null ? `(${l.final_yield_pct}%)` : `(${l.status})`}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-cyan" />
          </div>

          {/* New Lot Ingestion Trigger Button */}
          <button
            onClick={() => setIsIngestOpen(true)}
            className="flex items-center gap-1.5 rounded-lg border border-cyan/50 bg-cyan/15 hover:bg-cyan/25 px-2.5 py-1.5 text-xs font-mono font-bold text-cyan transition-all shadow-cyan-glow"
            title="Ingest and analyze a newly built failed chip lot"
          >
            <PlusCircle className="h-3.5 w-3.5" />
            <span>+ Ingest Lot Data</span>
          </button>

          <span className="text-slate-600 hidden sm:inline">|</span>
          <span className="text-slate-300 text-xs hidden sm:inline">{lot.product_id}</span>
          <span className="text-slate-600 hidden sm:inline">|</span>
          <span className="text-slate-300 text-xs hidden md:inline">{lot.fab_line}</span>
        </div>

        {/* Live Lot Metrics & Quick Anomaly Shortcuts */}
        <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-[11px]">
          <span className="text-slate-400">
            Yield:{' '}
            <strong className={isExcursion ? 'text-red-400' : 'text-emerald'}>
              {lot.final_yield_pct != null ? `${lot.final_yield_pct}%` : 'In Progress'}
            </strong>
          </span>
          <span className="text-slate-400">
            Defects: <strong className="text-white">{lot.defect_count || defects.length}</strong>
          </span>
          <span className="text-slate-400">
            Signature:{' '}
            <strong className="text-cyan uppercase">
              {lot.primary_signature || findings?.candidate_causes?.[0]?.spatial_signature || 'random'}
            </strong>
          </span>

          {/* Quick Demo Shortcuts */}
          {worstLot && worstLot.lot_id !== selectedLotId && (
            <button
              onClick={() => onSelectLot(worstLot.lot_id)}
              className="flex items-center gap-1 rounded bg-red-500/15 border border-red-500/40 px-2 py-0.5 text-[10px] text-red-300 hover:bg-red-500/25 transition-colors"
              title="Inspect lowest yield lot"
            >
              <Flame className="h-3 w-3 text-red-400" />
              <span>Worst Excursion ({worstLot.lot_id})</span>
            </button>
          )}
        </div>
      </div>

      {/* CORE TWO-COLUMN COCKPIT WITH RESPONSIVE BREAKPOINTS */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left: 3D Wafer Defect Map (5 Cols on xl, full width on lg/md/sm) */}
        <div className="xl:col-span-5 flex flex-col">
          <WaferMap3D
            lotId={lot.lot_id || selectedLotId}
            defects={defects}
            signature={lot.primary_signature || findings?.candidate_causes?.[0]?.spatial_signature || 'random'}
            severitySummary={{
              critical: defects.filter((d) => d.severity === 'critical').length,
              major: defects.filter((d) => d.severity === 'major').length,
              minor: defects.filter((d) => d.severity === 'minor').length,
            }}
          />
        </div>

        {/* Right: Root Cause Ranking Panel (7 Cols on xl, full width on lg/md/sm) */}
        <div className="xl:col-span-7 flex flex-col">
          <RootCauseRankingPanel
            lotId={lot.lot_id || selectedLotId}
            findings={findings}
            tier={tier}
            onChangeTier={onChangeTier}
          />
        </div>
      </div>

      {/* AT-RISK UPCOMING BATCHES TABLE */}
      <AtRiskList
        batches={atRiskBatches}
        onSelectLot={onSelectLot}
        onHoldLot={onHoldLot}
        heldLots={heldLots}
      />

      {/* INGESTION TOAST NOTIFICATION */}
      {ingestToast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-xl border border-cyan/50 bg-surface-1/95 p-4 shadow-cyan-glow text-xs font-mono text-cyan flex items-center gap-3 animate-bounce">
          <CheckCircle2 className="h-5 w-5 text-cyan shrink-0" />
          <span>{ingestToast}</span>
        </div>
      )}

      {/* INGEST NEW WAFER LOT MODAL */}
      {isIngestOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="glass-panel w-full max-w-2xl rounded-2xl p-6 shadow-2xl border border-cyan/40 bg-surface-1 font-mono text-slate-200 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border-subtle pb-3 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan/15 text-cyan border border-cyan/40">
                  <UploadCloud className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Ingest New Wafer Lot Telemetry
                  </h3>
                  <p className="text-[11px] text-slate-400 font-sans">
                    Simulate a new chip build / metrology defect run to analyze causality in real time
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsIngestOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-surface-2 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Quick Presets */}
            <div className="mb-4">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-bold mb-2">
                Quick Demonstration Templates:
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {presets.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleApplyPreset(p)}
                    className="text-left rounded-lg border border-border-subtle bg-surface-2 p-2 text-[11px] hover:border-cyan/50 hover:bg-cyan/5 transition-all"
                  >
                    <span className="font-bold text-white block truncate">{p.label}</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5 font-mono">
                      {p.signature} • {p.final_yield_pct}% Yield
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleIngestSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Lot ID */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Lot Identifier:</label>
                  <input
                    type="text"
                    required
                    value={ingestForm.lot_id}
                    onChange={(e) => setIngestForm({ ...ingestForm, lot_id: e.target.value })}
                    className="w-full rounded-lg border border-border-subtle bg-surface-deep px-3 py-2 text-white font-mono focus:border-cyan focus:outline-none"
                    placeholder="e.g. LOT-3001"
                  />
                </div>

                {/* Product ID */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Product Family:</label>
                  <select
                    value={ingestForm.product_id}
                    onChange={(e) => setIngestForm({ ...ingestForm, product_id: e.target.value })}
                    className="w-full rounded-lg border border-border-subtle bg-surface-deep px-3 py-2 text-white font-mono focus:border-cyan focus:outline-none"
                  >
                    <option value="PROD-3NM-SOC">PROD-3NM-SOC (Mobile SoC)</option>
                    <option value="PROD-3NM-AI-ACCEL">PROD-3NM-AI-ACCEL (Datacenter AI)</option>
                    <option value="PROD-2NM-GAA">PROD-2NM-GAA (Gate-All-Around NextGen)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Final Yield */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Final Test Yield %:</label>
                  <input
                    type="number"
                    step="0.1"
                    min="30"
                    max="99"
                    value={ingestForm.final_yield_pct}
                    onChange={(e) => setIngestForm({ ...ingestForm, final_yield_pct: parseFloat(e.target.value) })}
                    className="w-full rounded-lg border border-border-subtle bg-surface-deep px-3 py-2 text-white font-mono focus:border-cyan focus:outline-none"
                  />
                  <span className="text-[10px] text-red-400 mt-0.5 block">&lt;90% = Excursion</span>
                </div>

                {/* Spatial Signature */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Defect Spatial Pattern:</label>
                  <select
                    value={ingestForm.signature}
                    onChange={(e) => setIngestForm({ ...ingestForm, signature: e.target.value })}
                    className="w-full rounded-lg border border-border-subtle bg-surface-deep px-3 py-2 text-white font-mono focus:border-cyan focus:outline-none"
                  >
                    <option value="edge-ring">edge-ring (Bevel / CMP Ring)</option>
                    <option value="center-cluster">center-cluster (Gas Showerhead)</option>
                    <option value="scratch">scratch (Wafer Handler Slip)</option>
                    <option value="donut">donut (Thermal Non-Uniformity)</option>
                    <option value="random">random (Airborne Particle)</option>
                  </select>
                </div>

                {/* Defect Count */}
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Defect Count (Scanned):</label>
                  <input
                    type="number"
                    min="50"
                    max="4000"
                    value={ingestForm.defect_count}
                    onChange={(e) => setIngestForm({ ...ingestForm, defect_count: parseInt(e.target.value) || 500 })}
                    className="w-full rounded-lg border border-border-subtle bg-surface-deep px-3 py-2 text-white font-mono focus:border-cyan focus:outline-none"
                  />
                </div>
              </div>

              {/* Injected FDC Sensor Out-of-Control Parameter */}
              <div className="rounded-lg border border-border-subtle bg-surface-2 p-3 space-y-3">
                <span className="text-[11px] text-cyan uppercase tracking-wider block font-bold">
                  Injected Equipment Telemetry Anomaly:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Suspect Tool:</label>
                    <input
                      type="text"
                      value={ingestForm.suspect_tool}
                      onChange={(e) => setIngestForm({ ...ingestForm, suspect_tool: e.target.value })}
                      className="w-full rounded border border-border-subtle bg-surface-deep px-2.5 py-1.5 text-white font-mono focus:border-cyan focus:outline-none text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Suspect Parameter:</label>
                    <input
                      type="text"
                      value={ingestForm.suspect_parameter}
                      onChange={(e) => setIngestForm({ ...ingestForm, suspect_parameter: e.target.value })}
                      className="w-full rounded border border-border-subtle bg-surface-deep px-2.5 py-1.5 text-white font-mono focus:border-cyan focus:outline-none text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 block mb-1">Z-Score Drift (σ):</label>
                    <input
                      type="number"
                      step="0.1"
                      min="2.0"
                      max="6.0"
                      value={ingestForm.z_score_drift}
                      onChange={(e) => setIngestForm({ ...ingestForm, z_score_drift: parseFloat(e.target.value) || 3.0 })}
                      className="w-full rounded border border-border-subtle bg-surface-deep px-2.5 py-1.5 text-white font-mono focus:border-cyan focus:outline-none text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-subtle">
                <button
                  type="button"
                  onClick={() => setIsIngestOpen(false)}
                  className="rounded-lg border border-border-subtle bg-surface-2 px-3.5 py-2 text-xs text-slate-300 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-2 rounded-lg bg-cyan px-4 py-2 text-xs font-mono font-bold text-canvas hover:bg-cyan-bright transition-all shadow-cyan-glow disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Ingesting & Processing...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Ingest & Run Metrology Causality</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

