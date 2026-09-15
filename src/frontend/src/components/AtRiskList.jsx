import React, { useState } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  ArrowRight,
  Eye,
  Search,
  Filter,
  Layers,
  Lock,
  Unlock,
  Activity,
  DollarSign,
} from 'lucide-react';

export default function AtRiskList({
  batches = [],
  onSelectLot,
  onHoldLot,
  heldLots = {},
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSignature, setSelectedSignature] = useState('ALL');

  const handleInspect = (lotId) => {
    onSelectLot(lotId);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Filter batches
  const filteredBatches = batches.filter((b) => {
    const matchesSearch = b.lot_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (b.product_id && b.product_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
                          (b.at_risk_tool && b.at_risk_tool.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesSig = selectedSignature === 'ALL' || b.matched_signature === selectedSignature;
    return matchesSearch && matchesSig;
  });

  const criticalCount = batches.filter((b) => (b.probability || 0) >= 0.7 || (b.risk_score || 0) >= 0.7).length;
  const heldCount = Object.values(heldLots).filter(Boolean).length;

  return (
    <div className="space-y-4">
      {/* High-Impact Operational KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 font-mono text-xs">
        <div className="glass-panel rounded-xl p-3 sm:p-4 border-l-2 border-l-red-500 shadow-glass">
          <span className="text-[10px] sm:text-[11px] text-slate-400 uppercase tracking-wider block">
            Critical Risk Batches
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-red-400">{criticalCount}</span>
            <span className="text-[10px] text-slate-400">&gt;70% Excursion Prob</span>
          </div>
        </div>

        <div className="glass-panel rounded-xl p-3 sm:p-4 border-l-2 border-l-amber shadow-glass">
          <span className="text-[10px] sm:text-[11px] text-slate-400 uppercase tracking-wider block">
            Chambers Flagged
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-amber">ETCH-07</span>
            <span className="text-[10px] text-slate-400">Drift Correlated</span>
          </div>
        </div>

        <div className="glass-panel rounded-xl p-3 sm:p-4 border-l-2 border-l-cyan shadow-glass">
          <span className="text-[10px] sm:text-[11px] text-slate-400 uppercase tracking-wider block">
            Dispatches on Hold
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-cyan">{heldCount}</span>
            <span className="text-[10px] text-slate-400">Lots Interlocked</span>
          </div>
        </div>

        <div className="glass-panel rounded-xl p-3 sm:p-4 border-l-2 border-l-emerald shadow-glass">
          <span className="text-[10px] sm:text-[11px] text-slate-400 uppercase tracking-wider block">
            Scrap Loss Averted
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-xl sm:text-2xl font-bold text-emerald">$28.4M</span>
            <span className="text-[10px] text-emerald font-semibold">Protected</span>
          </div>
        </div>
      </div>

      {/* Main Table Container */}
      <div className="glass-panel rounded-xl p-4 sm:p-5 shadow-glass">
        {/* Header & Search / Filter Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-3 mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber" />
            <h3 className="text-xs sm:text-sm font-bold tracking-tight text-white uppercase font-mono">
              At-Risk Upcoming Batches
            </h3>
            <span className="rounded border border-amber/40 bg-amber/10 px-2 py-0.5 text-[10px] font-mono font-semibold text-amber uppercase hidden sm:inline">
              Predictive Early Warning
            </span>
          </div>

          {/* Search & Filter Controls */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono w-full sm:w-auto">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-44">
              <input
                type="text"
                placeholder="Search Lot / Tool..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-md border border-border-subtle bg-surface-1 px-2.5 py-1.5 pl-8 text-xs text-white placeholder-slate-500 focus:border-cyan focus:outline-none"
              />
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
            </div>

            {/* Signature Filter */}
            <select
              value={selectedSignature}
              onChange={(e) => setSelectedSignature(e.target.value)}
              className="rounded-md border border-border-subtle bg-surface-1 px-2.5 py-1.5 text-xs text-slate-300 focus:border-cyan focus:outline-none cursor-pointer"
            >
              <option value="ALL">All Signatures</option>
              <option value="edge-ring">Edge-Ring</option>
              <option value="center-cluster">Center-Cluster</option>
              <option value="scratch">Scratch</option>
              <option value="donut">Donut</option>
            </select>
          </div>
        </div>

        {/* DESKTOP / TABLET RESPONSIVE TABLE (md and above) */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-border-subtle text-slate-400 text-[11px]">
                <th className="pb-2.5 font-medium">LOT ID</th>
                <th className="pb-2.5 font-medium">PRODUCT</th>
                <th className="pb-2.5 font-medium">SUSPECT STEP & TOOL</th>
                <th className="pb-2.5 font-medium">MATCHED SIGNATURE</th>
                <th className="pb-2.5 font-medium">RISK PROBABILITY METER</th>
                <th className="pb-2.5 font-medium text-right">OPERATIONAL ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle/40">
              {filteredBatches.map((b) => {
                const isHeld = heldLots[b.lot_id];
                const prob = b.probability !== null ? b.probability : b.risk_score || 0.5;
                const probPct = Math.round(prob * 100);
                const isCritical = prob >= 0.7;

                return (
                  <tr key={b.lot_id} className="hover:bg-surface-2/70 transition-colors group">
                    <td className="py-3 font-bold text-white whitespace-nowrap">
                      <button
                        onClick={() => handleInspect(b.lot_id)}
                        className="hover:text-cyan transition-colors flex items-center gap-1.5 text-xs"
                      >
                        <span>{b.lot_id}</span>
                        <ArrowRight className="h-3 w-3 text-slate-500 group-hover:text-cyan transition-colors" />
                      </button>
                    </td>

                    <td className="py-3 text-slate-300 whitespace-nowrap">
                      {b.product_id || 'PROD-3NM-SOC'}
                    </td>

                    <td className="py-3 whitespace-nowrap">
                      <span className="rounded bg-surface-3 px-2 py-1 text-slate-200 border border-border-subtle">
                        {b.at_risk_tool || 'ETCH-07'} ({b.at_risk_step || 'etch'})
                      </span>
                    </td>

                    <td className="py-3 whitespace-nowrap">
                      <span
                        className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          b.matched_signature === 'edge-ring'
                            ? 'border-amber/40 bg-amber/15 text-amber'
                            : b.matched_signature === 'center-cluster'
                            ? 'border-red-500/40 bg-red-500/15 text-red-400'
                            : 'border-cyan/40 bg-cyan/15 text-cyan'
                        }`}
                      >
                        {b.matched_signature}
                      </span>
                    </td>

                    {/* Glowing Risk Progress Meter */}
                    <td className="py-3 min-w-[170px]">
                      <div className="flex items-center gap-2.5">
                        <div className="flex-1 h-2 rounded-full bg-surface-deep overflow-hidden border border-border-subtle">
                          <div
                            className={`h-full rounded-full transition-all ${
                              isCritical
                                ? 'bg-gradient-to-r from-amber to-red-500 shadow-sm shadow-red-500/50'
                                : 'bg-gradient-to-r from-cyan to-amber'
                            }`}
                            style={{ width: `${Math.min(probPct, 100)}%` }}
                          />
                        </div>
                        <span
                          className={`font-bold text-xs whitespace-nowrap ${
                            isCritical ? 'text-red-400' : 'text-amber'
                          }`}
                        >
                          {probPct}% {b.probability !== null ? 'Cal.' : 'Risk'}
                        </span>
                      </div>
                    </td>

                    {/* Action Buttons */}
                    <td className="py-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleInspect(b.lot_id)}
                          className="flex items-center gap-1 rounded bg-surface-3 px-2 py-1 text-[11px] text-slate-300 hover:text-white hover:border-cyan/40 border border-border-subtle transition-colors"
                          title="Inspect 3D Wafer Map"
                        >
                          <Eye className="h-3 w-3 text-cyan" />
                          <span>Inspect</span>
                        </button>

                        <button
                          onClick={() => onHoldLot && onHoldLot(b.lot_id)}
                          className={`flex items-center gap-1 rounded px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                            isHeld
                              ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                              : 'bg-amber/15 text-amber hover:bg-amber/25 border border-amber/40'
                          }`}
                        >
                          {isHeld ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
                          <span>{isHeld ? 'On Hold' : 'Hold Dispatch'}</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* MOBILE RESPONSIVE CARDS (< md screens) */}
        <div className="md:hidden space-y-3">
          {filteredBatches.map((b) => {
            const isHeld = heldLots[b.lot_id];
            const prob = b.probability !== null ? b.probability : b.risk_score || 0.5;
            const probPct = Math.round(prob * 100);
            const isCritical = prob >= 0.7;

            return (
              <div
                key={b.lot_id}
                className="rounded-lg border border-border-subtle bg-surface-1 p-3.5 space-y-2.5 font-mono text-xs shadow-glass"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">{b.lot_id}</span>
                    <span className="text-[10px] text-slate-400">{b.product_id}</span>
                  </div>
                  <span
                    className={`rounded border px-2 py-0.5 text-[9px] font-bold uppercase ${
                      isCritical ? 'border-red-500/40 bg-red-500/15 text-red-400' : 'border-amber/40 bg-amber/15 text-amber'
                    }`}
                  >
                    {b.matched_signature}
                  </span>
                </div>

                {/* Step & Tool */}
                <div className="flex items-center justify-between text-slate-300 text-[11px]">
                  <span>Suspect Equipment:</span>
                  <span className="rounded bg-surface-3 px-1.5 py-0.5 text-cyan">
                    {b.at_risk_tool || 'ETCH-07'} ({b.at_risk_step || 'etch'})
                  </span>
                </div>

                {/* Progress bar */}
                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-slate-400">Excursion Probability:</span>
                    <span className={`font-bold ${isCritical ? 'text-red-400' : 'text-amber'}`}>
                      {probPct}% ({b.probability !== null ? 'Calibrated' : 'Risk Score'})
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-surface-deep overflow-hidden">
                    <div
                      className={`h-full rounded-full ${isCritical ? 'bg-red-500' : 'bg-amber'}`}
                      style={{ width: `${Math.min(probPct, 100)}%` }}
                    />
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between gap-2 pt-1 border-t border-border-subtle">
                  <button
                    onClick={() => handleInspect(b.lot_id)}
                    className="flex-1 flex items-center justify-center gap-1.5 rounded bg-surface-3 py-1.5 text-xs text-slate-200 hover:text-white border border-border-subtle"
                  >
                    <Eye className="h-3 w-3 text-cyan" />
                    <span>Inspect 3D</span>
                  </button>
                  <button
                    onClick={() => onHoldLot && onHoldLot(b.lot_id)}
                    className={`flex-1 flex items-center justify-center gap-1.5 rounded py-1.5 text-xs font-semibold ${
                      isHeld
                        ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                        : 'bg-amber/15 text-amber border border-amber/40'
                    }`}
                  >
                    {isHeld ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
                    <span>{isHeld ? 'On Hold' : 'Hold Dispatch'}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Empty state */}
        {filteredBatches.length === 0 && (
          <div className="py-8 text-center text-slate-400 font-mono text-xs">
            No matching batches found for the current search filter.
          </div>
        )}
      </div>
    </div>
  );
}
