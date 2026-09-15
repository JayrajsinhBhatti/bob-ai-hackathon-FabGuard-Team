import React, { useState } from 'react';

export default function WaferMap2DFallback({
  defects = [],
  signature = 'random',
  lotId,
}) {
  const [hoveredDefect, setHoveredDefect] = useState(null);

  const radius = 170; // 380x380 SVG
  const center = 190;

  const severityColors = {
    critical: '#EF4444',
    major: '#F59E0B',
    minor: '#06B6D4',
  };

  return (
    <div className="relative flex flex-col items-center justify-center p-4">
      <svg
        width="380"
        height="380"
        viewBox="0 0 380 380"
        className="select-none filter drop-shadow-[0_0_20px_rgba(6,182,212,0.15)]"
      >
        <defs>
          {/* Wafer surface gradient */}
          <radialGradient id="waferGrad2D" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#1E293B" />
            <stop offset="70%" stopColor="#111827" />
            <stop offset="100%" stopColor="#0B0F17" />
          </radialGradient>

          {/* Edge exclusion halo */}
          <linearGradient id="edgeRingGlow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#06B6D4" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#38BDF8" stopOpacity="0.1" />
          </linearGradient>
        </defs>

        {/* Outer Wafer Disc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="url(#waferGrad2D)"
          stroke="#334155"
          strokeWidth="2.5"
        />

        {/* Concentric Reticle Rings */}
        <circle cx={center} cy={center} r={radius * 0.75} fill="none" stroke="#1E293B" strokeDasharray="3 3" />
        <circle cx={center} cy={center} r={radius * 0.50} fill="none" stroke="#1E293B" strokeDasharray="3 3" />
        <circle cx={center} cy={center} r={radius * 0.25} fill="none" stroke="#1E293B" strokeDasharray="3 3" />

        {/* Crosshair Axes */}
        <line x1={center - radius} y1={center} x2={center + radius} y2={center} stroke="#1E293B" strokeWidth="1" />
        <line x1={center} y1={center - radius} x2={center} y2={center + radius} stroke="#1E293B" strokeWidth="1" />

        {/* Silicon Wafer Notch (SEMI standard alignment notch at bottom) */}
        <path
          d={`M ${center - 8} ${center + radius - 1} Q ${center} ${center + radius - 8} ${center + 8} ${center + radius - 1}`}
          fill="#0B0F17"
          stroke="#38BDF8"
          strokeWidth="2"
        />

        {/* Signature Region Highlights */}
        {signature === 'edge-ring' && (
          <circle
            cx={center}
            cy={center}
            r={radius * 0.88}
            fill="none"
            stroke="#EF4444"
            strokeWidth="12"
            opacity="0.25"
          />
        )}
        {signature === 'center-cluster' && (
          <circle
            cx={center}
            cy={center}
            r={radius * 0.35}
            fill="#EF4444"
            opacity="0.2"
          />
        )}
        {signature === 'donut' && (
          <circle
            cx={center}
            cy={center}
            r={radius * 0.60}
            fill="none"
            stroke="#F59E0B"
            strokeWidth="16"
            opacity="0.25"
          />
        )}
        {signature === 'scratch' && (
          <line
            x1={center - radius * 0.6}
            y1={center - radius * 0.5}
            x2={center + radius * 0.7}
            y2={center + radius * 0.6}
            stroke="#EF4444"
            strokeWidth="8"
            opacity="0.3"
            strokeLinecap="round"
          />
        )}

        {/* Defect Scatter Points */}
        {defects.slice(0, 1200).map((d) => {
          const cx = center + d.x * (radius - 10);
          const cy = center - d.y * (radius - 10); // flip y for standard Cartesian
          const color = severityColors[d.severity] || '#06B6D4';
          const r = d.severity === 'critical' ? 2.5 : d.severity === 'major' ? 2.0 : 1.5;

          return (
            <circle
              key={d.id}
              cx={cx}
              cy={cy}
              r={r}
              fill={color}
              opacity={0.85}
              className="cursor-pointer hover:scale-150 transition-transform"
              onMouseEnter={() => setHoveredDefect(d)}
              onMouseLeave={() => setHoveredDefect(null)}
            />
          );
        })}
      </svg>

      {/* Hover Info Tooltip */}
      {hoveredDefect && (
        <div className="absolute bottom-2 rounded border border-border-active bg-surface-2/95 px-3 py-1.5 text-[11px] font-mono text-slate-200 shadow-glass">
          <span className="font-bold uppercase text-white">{hoveredDefect.defect_type}</span>{' '}
          [{hoveredDefect.severity}] • X: {hoveredDefect.x.toFixed(3)}, Y: {hoveredDefect.y.toFixed(3)} •{' '}
          {hoveredDefect.wafer_id}
        </div>
      )}
    </div>
  );
}
