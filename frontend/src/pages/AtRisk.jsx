import React from 'react';
import AtRiskList from '../components/AtRiskList';
import { AlertTriangle, ArrowLeft, ShieldAlert } from 'lucide-react';

export default function AtRisk({
  batches = [],
  onSelectLot,
  onHoldLot,
  heldLots = {},
  onNavigate,
}) {
  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border-subtle pb-4">
        <div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber" />
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white uppercase font-mono">
              Upcoming At-Risk Production Queue
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-sans">
            Predictive early warning: lots scheduled or in-progress matching classified failure signatures from degraded equipment.
          </p>
        </div>

        {onNavigate && (
          <button
            onClick={() => onNavigate('dashboard')}
            className="flex items-center gap-1.5 rounded-lg border border-border-subtle bg-surface-1 px-3 py-1.5 text-xs font-mono text-slate-300 hover:text-white hover:border-cyan/40 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Dashboard</span>
          </button>
        )}
      </div>

      <AtRiskList
        batches={batches}
        onSelectLot={onSelectLot}
        onHoldLot={onHoldLot}
        heldLots={heldLots}
      />
    </div>
  );
}
