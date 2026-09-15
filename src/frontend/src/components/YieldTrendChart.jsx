import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';
import { TrendingDown, Activity, CheckCircle2, AlertCircle } from 'lucide-react';

export default function YieldTrendChart({ lots = [], selectedLotId, onSelectLot }) {
  const [selectedFabLine, setSelectedFabLine] = useState('ALL');

  // Filter lots
  const filteredLots = lots
    .filter((l) => l.final_yield_pct !== null)
    .filter((l) => (selectedFabLine === 'ALL' ? true : l.fab_line === selectedFabLine));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const isExcursion = data.final_yield_pct < 90;
      return (
        <div className="rounded-lg border border-border-active bg-surface-2 p-3 shadow-glass font-mono text-xs">
          <div className="flex items-center justify-between gap-4 border-b border-border-subtle pb-1.5 mb-1.5">
            <span className="font-bold text-white">{data.lot_id}</span>
            <span
              className={`rounded px-1.5 py-0.2 text-[10px] uppercase font-semibold ${
                isExcursion
                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                  : 'bg-emerald/20 text-emerald border border-emerald/30'
              }`}
            >
              {isExcursion ? 'Excursion' : 'Nominal'}
            </span>
          </div>
          <p className="text-slate-300">
            Yield:{' '}
            <span className={`font-bold ${isExcursion ? 'text-red-400' : 'text-emerald'}`}>
              {data.final_yield_pct}%
            </span>
          </p>
          <p className="text-slate-400 text-[11px]">Product: {data.product_id}</p>
          <p className="text-slate-400 text-[11px]">Defects: {data.defect_count}</p>
          <p className="text-slate-400 text-[11px]">Signature: {data.primary_signature}</p>
          <p className="text-cyan text-[10px] mt-1">Click dot to inspect wafer</p>
        </div>
      );
    }
    return null;
  };

  const completedLots = filteredLots.filter((l) => l.final_yield_pct !== null);
  const avgYield =
    completedLots.length > 0
      ? (
          completedLots.reduce((acc, l) => acc + l.final_yield_pct, 0) /
          completedLots.length
        ).toFixed(1)
      : '95.0';

  const excursionCount = completedLots.filter((l) => l.final_yield_pct < 90).length;

  return (
    <div className="glass-panel rounded-xl p-5 shadow-glass">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan" />
            <h3 className="text-sm font-bold tracking-tight text-white uppercase font-mono">
              Yield Trend & Anomaly Timeline
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            SECS/GEM inline lot yields across manufacturing sequence
          </p>
        </div>

        {/* Filter Controls & Summary KPIs */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Average:</span>
            <span className="font-bold text-white">{avgYield}%</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">Excursions:</span>
            <span className="font-bold text-red-400">{excursionCount}</span>
          </div>

          <div className="flex rounded-md border border-border-subtle bg-surface-1 p-0.5 text-xs font-mono">
            {['ALL', 'LINE-01-FAB12', 'LINE-02-FAB12'].map((line) => (
              <button
                key={line}
                onClick={() => setSelectedFabLine(line)}
                className={`rounded px-2.5 py-1 transition-colors ${
                  selectedFabLine === line
                    ? 'bg-cyan/20 text-cyan border border-cyan/40 font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {line === 'ALL' ? 'All Lines' : line.replace('-FAB12', '')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-60 w-full font-mono text-xs">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={filteredLots}
            margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
            onClick={(e) => {
              if (e && e.activePayload && e.activePayload.length) {
                onSelectLot(e.activePayload[0].payload.lot_id);
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
            <XAxis
              dataKey="lot_id"
              stroke="#64748B"
              tick={{ fill: '#64748B', fontSize: 10 }}
              tickLine={false}
              interval={Math.ceil(filteredLots.length / 12)}
            />
            <YAxis
              domain={[65, 100]}
              stroke="#64748B"
              tick={{ fill: '#64748B', fontSize: 10 }}
              tickLine={false}
              unit="%"
            />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Target 95% Spec Line */}
            <ReferenceLine
              y={95}
              stroke="#10B981"
              strokeDasharray="4 4"
              label={{
                value: 'SPEC TARGET: 95.0%',
                fill: '#10B981',
                fontSize: 10,
                position: 'insideTopRight',
              }}
            />

            <Line
              type="monotone"
              dataKey="final_yield_pct"
              stroke="#06B6D4"
              strokeWidth={2}
              dot={(props) => {
                const { cx, cy, payload } = props;
                const isSelected = payload.lot_id === selectedLotId;
                const isExcursion = payload.final_yield_pct < 90;

                return (
                  <circle
                    key={payload.lot_id}
                    cx={cx}
                    cy={cy}
                    r={isSelected ? 6 : isExcursion ? 4.5 : 2.5}
                    fill={isSelected ? '#38BDF8' : isExcursion ? '#EF4444' : '#06B6D4'}
                    stroke={isSelected ? '#FFFFFF' : isExcursion ? '#FCA5A5' : '#0891B2'}
                    strokeWidth={isSelected ? 2 : 1}
                    className="cursor-pointer hover:scale-150 transition-transform"
                    onClick={() => onSelectLot(payload.lot_id)}
                  />
                );
              }}
              activeDot={{ r: 6, fill: '#38BDF8', stroke: '#FFFFFF', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Quick Indicator Footer */}
      <div className="mt-3 flex items-center justify-between border-t border-border-subtle pt-2.5 text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-cyan"></span> Nominal Lot
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-red-500"></span> Excursion (&lt;90% Yield)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-white border border-cyan"></span> Selected Lot ({selectedLotId})
          </span>
        </div>
        <span className="hidden sm:inline text-slate-500">
          Showing {filteredLots.length} lot runs
        </span>
      </div>
    </div>
  );
}
