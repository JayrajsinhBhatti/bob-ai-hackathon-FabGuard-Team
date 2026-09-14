# Obsidian Cleanroom Telemetry — Design System Specification

Generated via **Stitch MCP** for **Bob Fab Copilot** (`BOBathon-collab`).

## Brand & Aesthetic
- **Environment**: Cleanroom semiconductor operations, physics-informed AI, high-density aerospace/fab cockpit.
- **Visual Language**: Obsidian deep dark mode, laser grid underlays, precision cyan status paths, electric amber excursion alerts, yield emerald milestones, razor-thin 1px slate glass borders.

## Color Tokens
```yaml
Canvas & Neutrals:
  surface-canvas: '#0B0F17'
  surface-tier1: '#111827' # Subsystem containers / Tool panels
  surface-tier2: '#1A2234' # Elevated cards, hover highlights
  border-subtle: '#1E293B' # 1px laser borders
  border-active: '#334155'
  text-primary: '#F8FAFC'
  text-secondary: '#94A3B8'
  text-muted: '#475569'

Luminescent Accents:
  precision-cyan: '#06B6D4'  # Active telemetry, interactive primary
  precision-cyan-glow: '0 0 16px -2px rgba(6, 182, 212, 0.25)'
  electric-amber: '#F59E0B'  # Thermal/FDC excursion warnings, AI copilot laser-rule
  electric-amber-glow: '0 0 20px -2px rgba(245, 158, 11, 0.35)'
  yield-emerald: '#10B981'   # Target yield (>95%), nominal Cpk (>1.33), passed tests
  yield-emerald-glow: '0 0 16px -2px rgba(16, 185, 129, 0.25)'
  critical-red: '#EF4444'    # Severe defect clusters, Cpk < 1.0, chamber lockouts
```

## Typography
- **Headings & Body UI**: `Plus Jakarta Sans`
- **Telemetry Readouts & Metrology Data**: `JetBrains Mono` (tabular figures)
- Uppercase tracking (`letter-spacing: 0.04em` to `0.06em`) for technical badges and SECS/GEM indicators.

## Honesty Mechanism Specification
- **Calibrated Probability** (Tier 2 ML): Cyan badge with confidence intervals, sample size `n`, and logistic regression tag.
- **Heuristic Risk Score** (Tier 1 Composite): Amber badge with raw correlation score.
- **DOE Confirmation Caveat**: Inline mandatory alert badge: *"Strict Protocol: Requires inline 2-wafer DOE verification prior to equipment adjustment"*.
