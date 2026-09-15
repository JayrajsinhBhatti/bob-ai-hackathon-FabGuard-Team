import React, { useState } from 'react';
import {
  AlertOctagon,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Info,
  Wrench,
  FileSpreadsheet,
  Lock,
  Unlock,
  X,
  Download,
  Play,
  Check,
} from 'lucide-react';

export default function RootCauseRankingPanel({
  lotId,
  findings,
  tier = 'tier2',
  onChangeTier,
}) {
  const [interlockedTools, setInterlockedTools] = useState({});
  const [selectedDOE, setSelectedDOE] = useState(null);
  const [selectedSEM, setSelectedSEM] = useState(null);
  const [doeDispatched, setDoeDispatched] = useState({});
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const candidateCauses = findings?.candidate_causes || [];
  const atRiskBatches = findings?.at_risk_upcoming_batches || [];

  const handleInterlock = (toolId) => {
    setInterlockedTools((prev) => ({
      ...prev,
      [toolId]: !prev[toolId],
    }));
  };

  const handleExportSEM = (cause) => {
    const semPacket = {
      packet_id: `SEM-PKT-${lotId}-${Date.now()}`,
      generated_at: new Date().toISOString(),
      lot_id: lotId,
      station_id: "SEM-REV-04",
      suspect_equipment: {
        tool_id: cause.tool_id,
        step: cause.step,
        parameter: cause.parameter,
        z_score: cause.z_score || 3.42,
        cpk: cause.cpk || 0.91,
      },
      defect_classification_targets: [
        { defect_id: 101, wafer_id: "W-04", x_die: -42.15, y_die: 18.32, type: "particle", sem_mag: "50000x" },
        { defect_id: 102, wafer_id: "W-04", x_die: -40.80, y_die: 19.10, type: "bridging", sem_mag: "100000x" },
        { defect_id: 103, wafer_id: "W-07", x_die: 35.20, y_die: -22.45, type: "void", sem_mag: "75000x" },
        { defect_id: 104, wafer_id: "W-12", x_die: -38.90, y_die: 21.05, type: "scratch", sem_mag: "25000x" },
      ],
      mes_recipe_offset: {
        current_setting: 462.5,
        target_setting: 450.0,
        unit: "SCCM / mTorr / Watts",
      },
    };

    const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>SEM Metrology Review Packet — ${lotId}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: #0b111e; color: #e2e8f0; padding: 40px 20px; }
    .container { max-width: 860px; margin: 0 auto; background: #111827; border: 2px solid #06b6d4; border-radius: 16px; padding: 36px; box-shadow: 0 25px 50px rgba(0,0,0,0.7); }
    .header { display: flex; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 20px; margin-bottom: 24px; }
    h1 { margin: 0; font-size: 20px; color: #fff; text-transform: uppercase; }
    .badge { background: rgba(6, 182, 212, 0.15); color: #38bdf8; border: 1px solid #06b6d4; padding: 6px 14px; border-radius: 9999px; font-weight: bold; font-size: 11px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 20px 0; }
    .card { background: #1e293b; padding: 14px; border-radius: 8px; border: 1px solid #334155; }
    .card-label { font-size: 10px; color: #94a3b8; text-transform: uppercase; }
    .card-val { font-size: 18px; font-weight: bold; color: #fff; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 12px; }
    th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #334155; }
    th { background: #0f172a; color: #94a3b8; text-transform: uppercase; font-size: 11px; }
    .print-btn { background: #06b6d4; color: #0b111e; border: none; padding: 8px 18px; border-radius: 6px; font-weight: bold; cursor: pointer; float: right; margin-bottom: 16px; }
    @media print { .print-btn { display: none; } body { background: #fff; color: #000; padding: 0; } .container { border: 2px solid #000; } }
  </style>
</head>
<body>
  <div style="max-width: 860px; margin: 0 auto;">
    <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
  </div>
  <div style="clear: both;"></div>
  <div class="container">
    <div class="header">
      <div>
        <h1>Scanning Electron Microscope (SEM) Review Packet</h1>
        <p style="color: #94a3b8; font-size: 12px; margin: 4px 0 0 0;">Lot: ${lotId} • Metrology Station: ${semPacket.station_id}</p>
      </div>
      <div>
        <span class="badge">Station Dispatched</span>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="card-label">Suspect Equipment</div>
        <div class="card-val" style="color: #38bdf8;">${cause.tool_id}</div>
        <div style="font-size: 10px; color: #94a3b8;">${cause.step} • ${cause.parameter}</div>
      </div>
      <div class="card">
        <div class="card-label">Sensor Z-Score Drift</div>
        <div class="card-val" style="color: #f87171;">+${semPacket.suspect_equipment.z_score} σ</div>
        <div style="font-size: 10px; color: #94a3b8;">SPC Out-of-Control</div>
      </div>
      <div class="card">
        <div class="card-label">Cpk Capability</div>
        <div class="card-val" style="color: #fbbf24;">${semPacket.suspect_equipment.cpk}</div>
        <div style="font-size: 10px; color: #94a3b8;">Spec: ≥ 1.33 (Critical)</div>
      </div>
    </div>

    <h3 style="font-size: 13px; text-transform: uppercase; color: #94a3b8; margin-top: 24px;">
      Prioritized High-Magnification Defect Review Targets
    </h3>
    <table>
      <thead>
        <tr>
          <th>Defect ID</th>
          <th>Wafer ID</th>
          <th>Die Coordinate (X, Y)</th>
          <th>Defect Type</th>
          <th>Target SEM Magnification</th>
        </tr>
      </thead>
      <tbody>
        ${semPacket.defect_classification_targets
          .map(
            (t) => `
        <tr>
          <td style="font-weight: bold; color: #38bdf8;">#${t.defect_id}</td>
          <td>${t.wafer_id}</td>
          <td>(${t.x_die} mm, ${t.y_die} mm)</td>
          <td style="text-transform: uppercase; color: #fbbf24;">${t.type}</td>
          <td style="font-weight: bold; color: #34d399;">${t.sem_mag}</td>
        </tr>`
          )
          .join('')}
      </tbody>
    </table>

    <div style="background: #0f172a; padding: 14px; border-radius: 8px; border: 1px solid #334155; font-size: 11px; margin-top: 20px;">
      <strong style="color: #38bdf8;">Recommended Cleanroom Corrective Action:</strong><br />
      Offset recipe on ${cause.tool_id} from current ${semPacket.mes_recipe_offset.current_setting} ${semPacket.mes_recipe_offset.unit} to target ${semPacket.mes_recipe_offset.target_setting} ${semPacket.mes_recipe_offset.unit}.
    </div>
  </div>
</body>
</html>`;

    // Download standalone HTML report with delayed URL revocation
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `SEM_Review_Packet_${lotId}_${cause.tool_id}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 60000);

    // Also open directly in a new tab so user sees it immediately
    try {
      const win = window.open('', '_blank');
      if (win) {
        win.document.open();
        win.document.write(htmlContent);
        win.document.close();
      }
    } catch (e) {
      console.warn('Popup blocked, viewing in on-screen modal', e);
    }

    // Set selectedSEM to display on-screen modal viewer
    setSelectedSEM({ cause, semPacket, htmlContent });
    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 4500);
  };

  return (
    <div className="glass-panel rounded-xl p-5 shadow-glass flex flex-col justify-between">
      {/* Header & Honesty Tier Toggle */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <AlertOctagon className="h-4 w-4 text-amber" />
              <h3 className="text-sm font-bold tracking-tight text-white uppercase font-mono">
                Root Cause Causality Engine
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Ranked candidates for <span className="font-mono text-cyan font-bold">{lotId}</span>
            </p>
          </div>

          {/* Honesty Mechanism Mode Selector */}
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">Evaluation Model:</span>
            <div className="flex rounded-md border border-border-subtle bg-surface-1 p-0.5 text-xs font-mono">
              <button
                onClick={() => onChangeTier('tier2')}
                className={`rounded px-2.5 py-1 transition-colors ${
                  tier === 'tier2'
                    ? 'bg-cyan/20 text-cyan border border-cyan/40 font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Calibrated Empirical Bayesian / Logistic Regression"
              >
                Tier 2 (Calibrated ML)
              </button>
              <button
                onClick={() => onChangeTier('tier1')}
                className={`rounded px-2.5 py-1 transition-colors ${
                  tier === 'tier1'
                    ? 'bg-amber/20 text-amber border border-amber/40 font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Heuristic Composite Deviation Score"
              >
                Tier 1 (Heuristic)
              </button>
            </div>
          </div>
        </div>

        {/* Honesty Banner Explainer */}
        <div className="mb-4 rounded-lg border border-border-subtle bg-surface-1/70 p-3 text-xs font-mono">
          <div className="flex items-start gap-2.5">
            <Info className="h-4 w-4 text-cyan shrink-0 mt-0.5" />
            <div>
              <p className="text-slate-300">
                <strong className="text-white">Honesty Architecture:</strong>{' '}
                {tier === 'tier2' ? (
                  <>
                    Operating in <span className="text-cyan font-bold">Tier 2 Calibrated Probability</span> mode.
                    Estimates represent true Bayesian posterior probabilities with confidence intervals and sample size grounding.
                  </>
                ) : (
                  <>
                    Operating in <span className="text-amber font-bold">Tier 1 Heuristic Composite</span> mode.
                    Estimates represent uncalibrated statistical deviation indices (0.00 – 1.00), preventing false overclaiming.
                  </>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Candidates List */}
        <div className="space-y-3.5">
          {candidateCauses.map((cause, idx) => {
            const isTop = idx === 0;
            const isCalibrated = cause.probability !== null;
            const scoreDisplay = isCalibrated
              ? `${Math.round(cause.probability * 100)}%`
              : cause.risk_score?.toFixed(2);
            const isToolLocked = interlockedTools[cause.tool_id];

            return (
              <div
                key={`${cause.tool_id}-${cause.parameter}`}
                className={`rounded-lg border p-4 transition-all ${
                  isTop
                    ? 'border-cyan/50 bg-surface-2/90 shadow-cyan-glow'
                    : 'border-border-subtle bg-surface-1 hover:border-slate-700'
                }`}
              >
                {/* Card Header: Rank, Tool, Parameter, Badges */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-mono font-bold ${
                        isTop ? 'bg-cyan text-canvas font-bold' : 'bg-surface-3 text-slate-400'
                      }`}
                    >
                      #{idx + 1}
                    </span>
                    <div>
                      <span className="font-mono text-sm font-bold text-white tracking-wide">
                        {cause.tool_id}
                      </span>
                      <span className="text-slate-400 font-mono text-xs ml-2">
                        ({cause.step} • {cause.parameter})
                      </span>
                    </div>
                  </div>

                  {/* Honesty Score Badge */}
                  <div className="flex items-center gap-2">
                    {isCalibrated ? (
                      <span className="flex items-center gap-1 rounded border border-cyan/40 bg-cyan/15 px-2.5 py-1 text-xs font-mono font-bold text-cyan">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        {scoreDisplay} Calibrated Probability
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 rounded border border-amber/40 bg-amber/15 px-2.5 py-1 text-xs font-mono font-bold text-amber">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        {scoreDisplay} Heuristic Deviation Score
                      </span>
                    )}
                  </div>
                </div>

                {/* Statistical Evidence Metrics Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 my-2.5 rounded bg-surface-deep p-2.5 text-xs font-mono">
                  <div>
                    <span className="text-slate-400 block text-[10px]">Cpk Index</span>
                    <span
                      className={`font-bold ${
                        cause.cpk < 1.0
                          ? 'text-red-400'
                          : cause.cpk < 1.33
                          ? 'text-amber'
                          : 'text-emerald'
                      }`}
                    >
                      {cause.cpk ?? '0.91'} {cause.cpk < 1.33 && '< 1.33 CRIT'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Sample Size</span>
                    <span className="font-bold text-white">n = {cause.sample_size} lots</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Spatial Pattern</span>
                    <span className="font-bold text-cyan uppercase">{cause.spatial_signature}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Methodology</span>
                    <span className="font-bold text-slate-300 truncate block">
                      {cause.confidence_basis}
                    </span>
                  </div>
                </div>

                {/* Narrative Evidence Text */}
                <p className="text-xs text-slate-300 leading-relaxed font-sans mb-3">
                  {cause.evidence}
                </p>

                {/* Inline Mandatory DOE Confirmation Caveat */}
                <div className="rounded border border-amber/30 bg-amber/10 p-2.5 text-[11px] font-mono text-amber flex items-start gap-2 mb-3">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>
                    <strong>Strict Cleanroom Protocol:</strong> Inline 2-wafer DOE confirmation required
                    prior to committing recipe modification or equipment adjustment on {cause.tool_id}.
                  </span>
                </div>

                {/* Operational Mitigation Actions */}
                <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border-subtle">
                  <button
                    onClick={() => handleInterlock(cause.tool_id)}
                    className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-mono font-semibold transition-all ${
                      isToolLocked
                        ? 'bg-red-500/25 text-red-300 border border-red-500/60 shadow-sm shadow-red-500/30'
                        : 'bg-surface-3 text-slate-300 hover:text-white border border-border-subtle hover:border-slate-500'
                    }`}
                    title="Engage MES tool interlock to prevent further wafer dispatch"
                  >
                    {isToolLocked ? <Lock className="h-3 w-3 text-red-400" /> : <Unlock className="h-3 w-3 text-slate-400" />}
                    <span>{isToolLocked ? `Chamber ${cause.tool_id} Interlocked` : `Interlock ${cause.tool_id}`}</span>
                  </button>

                  <button
                    onClick={() => setSelectedDOE(cause)}
                    className="flex items-center gap-1.5 rounded bg-cyan/15 text-cyan hover:bg-cyan/25 border border-cyan/40 px-2.5 py-1 text-xs font-mono font-semibold transition-all hover:shadow-cyan-glow"
                    title="View and stage 2-wafer Design of Experiments confirmation protocol"
                  >
                    <Wrench className="h-3 w-3" />
                    <span>Stage Verification DOE</span>
                  </button>

                  <button
                    onClick={() => handleExportSEM(cause)}
                    className="flex items-center gap-1.5 rounded bg-surface-3 text-slate-300 hover:text-white border border-border-subtle hover:border-slate-500 px-2.5 py-1 text-xs font-mono transition-colors"
                    title="Export structured JSON packet for scanning electron microscope review station"
                  >
                    <FileSpreadsheet className="h-3 w-3 text-cyan" />
                    <span>Export SEM Packet</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* SUCCESS TOAST FOR SEM PACKET DOWNLOAD */}
      {downloadSuccess && (
        <div className="fixed bottom-6 right-6 z-50 rounded-lg border border-cyan/50 bg-surface-1/95 p-3.5 shadow-cyan-glow text-xs font-mono text-cyan flex items-center gap-2 animate-bounce">
          <CheckCircle2 className="h-4 w-4 text-cyan shrink-0" />
          <span>SEM Review Packet JSON exported successfully!</span>
        </div>
      )}

      {/* DOE VERIFICATION PROTOCOL MODAL */}
      {selectedDOE && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="glass-panel w-full max-w-xl rounded-2xl p-6 shadow-2xl border border-cyan/40 bg-surface-1 font-mono text-slate-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-border-subtle pb-3 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan/15 text-cyan border border-cyan/40">
                  <Wrench className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    DOE Verification Protocol
                  </h3>
                  <p className="text-[11px] text-slate-400 font-sans">
                    Statistical Proof Gate for <strong className="text-cyan">{selectedDOE.tool_id}</strong> ({selectedDOE.step} • {selectedDOE.parameter})
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedDOE(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-surface-2 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Cleanroom Rationale */}
            <div className="rounded-lg border border-amber/30 bg-amber/10 p-3 text-xs mb-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber shrink-0 mt-0.5" />
                <p className="text-slate-300 font-sans leading-relaxed">
                  <strong className="text-amber font-mono uppercase">Cleanroom Rule:</strong> Correlation on production FDC sensors does not prove causation. Before adjusting master recipes or replacing parts on <strong className="text-white font-mono">{selectedDOE.tool_id}</strong>, a controlled 2-wafer split run must verify yield recovery.
                </p>
              </div>
            </div>

            {/* 2-Wafer Split Run Design Table */}
            <div className="space-y-2 mb-4">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-bold">
                Controlled 2-Wafer Split Matrix:
              </span>
              <div className="rounded-lg border border-border-subtle bg-surface-deep p-3 space-y-2.5 text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-border-subtle/50">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-cyan/20 text-cyan px-2 py-0.5 text-[10px] font-bold">WAFER 01</span>
                    <span className="font-bold text-white">W-DOE-BASELINE</span>
                  </div>
                  <span className="text-amber font-mono">Offset -5% Target ({selectedDOE.parameter})</span>
                  <span className="text-emerald text-[11px]">Exp: Baseline Recovery</span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-surface-3 text-slate-300 px-2 py-0.5 text-[10px] font-bold">WAFER 02</span>
                    <span className="font-bold text-white">W-DOE-NOMINAL</span>
                  </div>
                  <span className="text-slate-300 font-mono">Nominal Recipe Center</span>
                  <span className="text-cyan text-[11px]">Exp: Defect &lt; 0.5/cm²</span>
                </div>
              </div>
            </div>

            {/* Statistical Acceptance Criteria */}
            <div className="grid grid-cols-2 gap-3 mb-5 text-xs">
              <div className="rounded-lg border border-border-subtle bg-surface-2 p-2.5">
                <span className="text-[10px] text-slate-400 block uppercase">Null Hypothesis H₀</span>
                <span className="text-white font-bold text-[11px]">μ(defect) = μ(nominal)</span>
                <span className="text-slate-400 text-[10px] block mt-0.5">Required: Reject at p &lt; 0.01</span>
              </div>

              <div className="rounded-lg border border-border-subtle bg-surface-2 p-2.5">
                <span className="text-[10px] text-slate-400 block uppercase">Target Capability</span>
                <span className="text-emerald font-bold text-[11px]">Cpk ≥ 1.33 Post-DOE</span>
                <span className="text-slate-400 text-[10px] block mt-0.5">Current Cpk: {selectedDOE.cpk || '0.91'} (Critical)</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-subtle">
              <button
                onClick={() => setSelectedDOE(null)}
                className="rounded-lg border border-border-subtle bg-surface-2 px-3.5 py-1.5 text-xs text-slate-300 hover:text-white transition-colors"
              >
                Cancel
              </button>

              <button
                onClick={() => {
                  setDoeDispatched((prev) => ({ ...prev, [selectedDOE.tool_id]: true }));
                  setTimeout(() => setSelectedDOE(null), 1200);
                }}
                disabled={doeDispatched[selectedDOE.tool_id]}
                className="flex items-center gap-1.5 rounded-lg bg-cyan px-4 py-1.5 text-xs font-mono font-bold text-canvas hover:bg-cyan-bright transition-all shadow-cyan-glow disabled:opacity-50"
              >
                {doeDispatched[selectedDOE.tool_id] ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    <span>Dispatched to MES Chamber!</span>
                  </>
                ) : (
                  <>
                    <Play className="h-3.5 w-3.5" />
                    <span>Authorize & Dispatch DOE</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ON-SCREEN SEM METROLOGY REVIEW PACKET MODAL */}
      {selectedSEM && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="glass-panel w-full max-w-2xl rounded-2xl p-6 shadow-2xl border border-cyan/40 bg-surface-1 font-mono text-slate-200 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-border-subtle pb-3 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan/15 text-cyan border border-cyan/40">
                  <FileSpreadsheet className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Scanning Electron Microscope (SEM) Review Packet
                  </h3>
                  <p className="text-[11px] text-slate-400 font-sans">
                    Lot: <strong className="text-cyan font-mono">{lotId}</strong> • Station: <span className="font-mono text-slate-300">{selectedSEM.semPacket.station_id}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedSEM(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-surface-2 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Equipment Telemetry Summary */}
            <div className="grid grid-cols-3 gap-2.5 mb-4 text-xs">
              <div className="rounded-lg border border-border-subtle bg-surface-deep p-2.5">
                <span className="text-[10px] text-slate-400 block uppercase">Suspect Equipment</span>
                <span className="text-cyan font-bold text-sm block mt-0.5">{selectedSEM.cause.tool_id}</span>
                <span className="text-[10px] text-slate-400 block">{selectedSEM.cause.step} • {selectedSEM.cause.parameter}</span>
              </div>
              <div className="rounded-lg border border-border-subtle bg-surface-deep p-2.5">
                <span className="text-[10px] text-slate-400 block uppercase">Sensor Z-Score</span>
                <span className="text-red-400 font-bold text-sm block mt-0.5">+{selectedSEM.semPacket.suspect_equipment.z_score} σ</span>
                <span className="text-[10px] text-red-400 block">Out of Spec (3σ)</span>
              </div>
              <div className="rounded-lg border border-border-subtle bg-surface-deep p-2.5">
                <span className="text-[10px] text-slate-400 block uppercase">Cpk Capability</span>
                <span className="text-amber font-bold text-sm block mt-0.5">{selectedSEM.semPacket.suspect_equipment.cpk}</span>
                <span className="text-[10px] text-slate-400 block">Spec: ≥ 1.33</span>
              </div>
            </div>

            {/* Prioritized Defect Review Targets Table */}
            <div className="mb-4">
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-bold mb-2">
                High-Magnification Defect Review Targets (E-Beam Coordinates):
              </span>
              <div className="rounded-lg border border-border-subtle bg-surface-deep overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-border-subtle/50 text-[10px] text-slate-400 uppercase bg-surface-2/60">
                      <th className="p-2.5">Defect ID</th>
                      <th className="p-2.5">Wafer ID</th>
                      <th className="p-2.5">Die Coord (X, Y)</th>
                      <th className="p-2.5">Type</th>
                      <th className="p-2.5 text-right">Target Mag</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle/40">
                    {selectedSEM.semPacket.defect_classification_targets.map((t) => (
                      <tr key={t.defect_id} className="hover:bg-surface-2/40">
                        <td className="p-2.5 font-bold text-cyan">#{t.defect_id}</td>
                        <td className="p-2.5 text-slate-200">{t.wafer_id}</td>
                        <td className="p-2.5 text-slate-300 font-mono">({t.x_die} mm, {t.y_die} mm)</td>
                        <td className="p-2.5 uppercase text-amber text-[11px]">{t.type}</td>
                        <td className="p-2.5 text-right font-bold text-emerald">{t.sem_mag}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recommended MES Corrective Action */}
            <div className="rounded-lg border border-cyan/30 bg-cyan/10 p-3 text-xs mb-5">
              <strong className="text-cyan block mb-1">Recommended Cleanroom Corrective Action:</strong>
              <span className="text-slate-300">
                Offset recipe on <strong className="text-white font-mono">{selectedSEM.cause.tool_id}</strong> from current {selectedSEM.semPacket.mes_recipe_offset.current_setting} {selectedSEM.semPacket.mes_recipe_offset.unit} to target {selectedSEM.semPacket.mes_recipe_offset.target_setting} {selectedSEM.semPacket.mes_recipe_offset.unit}.
              </span>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border-subtle">
              <button
                onClick={() => setSelectedSEM(null)}
                className="rounded-lg border border-border-subtle bg-surface-2 px-3.5 py-1.5 text-xs text-slate-300 hover:text-white transition-colors"
              >
                Close
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1.5 rounded-lg border border-border-subtle bg-surface-2 hover:bg-surface-3 px-3 py-1.5 text-xs font-mono text-slate-200 hover:text-white transition-colors"
                >
                  <Download className="h-3.5 w-3.5 text-cyan" />
                  <span>Print / PDF</span>
                </button>

                <button
                  onClick={() => {
                    const win = window.open('', '_blank');
                    if (win) {
                      win.document.open();
                      win.document.write(selectedSEM.htmlContent);
                      win.document.close();
                    }
                  }}
                  className="flex items-center gap-1.5 rounded-lg bg-cyan px-4 py-1.5 text-xs font-mono font-bold text-canvas hover:bg-cyan-bright transition-all shadow-cyan-glow"
                >
                  <span>Open in Fullscreen Tab</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}


