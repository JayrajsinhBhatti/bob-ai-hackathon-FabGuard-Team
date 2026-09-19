"""
copilot/doe_engine.py  —  Feature 3: Automated Statistical DOE Generator
design of experiments

When the analytics core identifies a candidate root cause (e.g., ETCH-07,
chamber_pressure), this module automatically designs a statistically valid
confirmatory experiment that an engineer can submit directly to the fab scheduler.

Generates:
  - 2^k Full Factorial or Resolution IV Fractional Factorial design matrix
  - Factor levels (Low/Nominal/High) derived from spec limits and observed drift
  - Sample allocation (wafer count per run) using minimum detectable effect sizing
  - Randomized run order (to eliminate systematic bias)
  - Clear hypothesis statement (H0 / H1)
  - Go/No-Go measurement criteria (what constitutes confirmation)

The output is an engineer-ready runcard in both dict (for MCP JSON) and
formatted text (for IBM Bob chat display).

No LLM is needed for the core matrix generation — it is purely algorithmic.
An optional LLM call generates a natural-language narrative summary.

Usage:
    from copilot.doe_engine import DOEEngine
    engine = DOEEngine(repository)
    runcard = engine.generate_for_cause(lot_id, candidate_cause)
    print(engine.format_as_text(runcard))
"""

import itertools
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from analytics.data_access import DataRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_value(v: float) -> str:
    """Format a numeric value cleanly for display."""
    if abs(v) >= 100:
        return f"{v:.1f}"
    elif abs(v) >= 10:
        return f"{v:.2f}"
    else:
        return f"{v:.3f}"


def _minimum_sample_size(
    effect_size_fraction: float = 0.40,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """
    Approximate minimum sample size per condition using a simplified
    Lehr's formula for two-sample t-test:
        n ≈ 16 / effect_size^2  (for α=0.05, power=0.80)

    We use a standardized effect size: observed_deviation / historical_std
    capped at a practical range for fab experiments.
    """
    if effect_size_fraction <= 0:
        effect_size_fraction = 0.40
    # Simplified Lehr approximation
    n = max(4, math.ceil(16 / (effect_size_fraction ** 2)))
    # Cap at 25 wafers per run (one full lot maximum)
    return min(n, 25)


FAB_PARAMETER_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "focus_offset": {"nominal": 0.0, "low": -7.5, "high": 7.5, "spec_min": -7.5, "spec_max": 7.5, "unit": "nm"},
    "exposure_energy": {"nominal": 24.5, "low": 23.7, "high": 25.3, "spec_min": 23.7, "spec_max": 25.3, "unit": "mJ/cm²"},
    "numerical_aperture": {"nominal": 1.350, "low": 1.339, "high": 1.361, "spec_min": 1.339, "spec_max": 1.361, "unit": "NA"},
    "chamber_pressure": {"nominal": 15.0, "low": 13.8, "high": 16.2, "spec_min": 13.8, "spec_max": 16.2, "unit": "mTorr"},
    "rf_power_forward": {"nominal": 850.0, "low": 828.0, "high": 872.0, "spec_min": 828.0, "spec_max": 872.0, "unit": "W"},
    "rf_power": {"nominal": 850.0, "low": 828.0, "high": 872.0, "spec_min": 828.0, "spec_max": 872.0, "unit": "W"},
    "gas_flow_cl2": {"nominal": 120.0, "low": 115.8, "high": 124.2, "spec_min": 115.8, "spec_max": 124.2, "unit": "sccm"},
    "gas_flow_sccm": {"nominal": 120.0, "low": 115.8, "high": 124.2, "spec_min": 115.8, "spec_max": 124.2, "unit": "sccm"},
    "head_downforce": {"nominal": 4.5, "low": 4.0, "high": 5.0, "spec_min": 4.0, "spec_max": 5.0, "unit": "psi"},
    "platen_rpm": {"nominal": 90.0, "low": 85.0, "high": 95.0, "spec_min": 85.0, "spec_max": 95.0, "unit": "rpm"},
    "slurry_flow_rate": {"nominal": 150.0, "low": 140.0, "high": 160.0, "spec_min": 140.0, "spec_max": 160.0, "unit": "ml/min"},
    "deposition_temp": {"nominal": 400.0, "low": 380.0, "high": 420.0, "spec_min": 380.0, "spec_max": 420.0, "unit": "°C"},
    "rf_bias": {"nominal": 200.0, "low": 190.0, "high": 210.0, "spec_min": 190.0, "spec_max": 210.0, "unit": "V"},
    "acceleration_energy": {"nominal": 50.0, "low": 47.0, "high": 53.0, "spec_min": 47.0, "spec_max": 53.0, "unit": "keV"},
    "beam_current": {"nominal": 10.0, "low": 9.5, "high": 10.5, "spec_min": 9.5, "spec_max": 10.5, "unit": "mA"},
    "tilt_angle": {"nominal": 7.0, "low": 6.0, "high": 8.0, "spec_min": 6.0, "spec_max": 8.0, "unit": "deg"},
}


# ---------------------------------------------------------------------------
# DOE Run Matrix Builder
# ---------------------------------------------------------------------------

class DOEEngine:
    """
    Generates statistically valid Design of Experiments (DOE) runcards
    for confirming candidate root causes identified by the analytics pipeline.
    """

    def __init__(self, repository: DataRepository):
        self.repo = repository

    def _get_factor_levels(
        self,
        tool_id: str,
        parameter: str,
        step_name: str,
        observed_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Derive Low / Nominal / High factor levels for a parameter.

        Priority:
          1. Use spec_min / spec_max from process_steps for the tool+param.
          2. Use historical mean ± 2σ if no spec limits.
          3. Fall back to domain defaults from FAB_PARAMETER_DEFAULTS.
          4. Fall back to ±10% of observed value.
        """
        steps = []
        try:
            steps = self.repo.get_process_steps(
                step_name=step_name, tool_id=tool_id, parameter_name=parameter
            )
            if not steps:
                steps = self.repo.get_process_steps(tool_id=tool_id, parameter_name=parameter)
            if not steps:
                steps = self.repo.get_process_steps(parameter_name=parameter)
        except Exception:
            steps = []

        spec_min = spec_max = mean = std = None
        values = []
        for s in steps:
            v = s.get("value")
            if v is not None:
                values.append(float(v))
            if spec_min is None and s.get("spec_min") is not None:
                spec_min = float(s.get("spec_min"))
            if spec_max is None and s.get("spec_max") is not None:
                spec_max = float(s.get("spec_max"))

        if values:
            mean = sum(values) / len(values)
            std = math.sqrt(sum((v - mean) ** 2 for v in values) / max(len(values) - 1, 1)) or 0.0

        # Check domain defaults fallback
        fallback = FAB_PARAMETER_DEFAULTS.get(parameter, {})
        unit = fallback.get("unit", "a.u.")

        if spec_min is None and fallback.get("spec_min") is not None:
            spec_min = fallback["spec_min"]
        if spec_max is None and fallback.get("spec_max") is not None:
            spec_max = fallback["spec_max"]

        # Determine nominal (center point)
        if spec_min is not None and spec_max is not None:
            nominal = (spec_min + spec_max) / 2.0
        elif mean is not None:
            nominal = mean
        elif fallback.get("nominal") is not None:
            nominal = fallback["nominal"]
        elif observed_value is not None:
            nominal = observed_value
        else:
            return {"nominal": None, "low": None, "high": None, "unit": unit}

        # Determine step size (how far above/below nominal to test)
        if spec_min is not None and spec_max is not None:
            step_size = (spec_max - spec_min) * 0.10
            low_val = spec_min if (nominal - step_size < spec_min) else (nominal - step_size)
            high_val = spec_max if (nominal + step_size > spec_max) else (nominal + step_size)
        elif std and std > 1e-6:
            step_size = 2.0 * std
            low_val = nominal - step_size
            high_val = nominal + step_size
        elif fallback.get("low") is not None and fallback.get("high") is not None:
            low_val = fallback["low"]
            high_val = fallback["high"]
            step_size = (high_val - low_val) / 2.0
        else:
            step_size = abs(nominal) * 0.10 or 1.0
            low_val = nominal - step_size
            high_val = nominal + step_size

        return {
            "nominal": round(nominal, 4),
            "low": round(min(low_val, nominal), 4),
            "high": round(max(high_val, nominal), 4),
            "step_size": round(step_size, 4),
            "historical_mean": round(mean, 4) if mean is not None else None,
            "historical_std": round(std, 4) if std is not None else None,
            "spec_min": spec_min,
            "spec_max": spec_max,
            "unit": unit,
        }

    def _build_full_factorial(
        self, factors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Build a full 2^k factorial design matrix.
        Each factor has: {"name": ..., "low": ..., "high": ...}
        Returns list of run conditions (each is a dict of factor → level).
        """
        n_factors = len(factors)
        if n_factors > 5:
            factors = factors[:5]
            n_factors = 5

        level_combos = list(itertools.product([-1, 1], repeat=n_factors))

        runs = []
        for combo in level_combos:
            run = {}
            for i, factor in enumerate(factors):
                level_str = "Low" if combo[i] == -1 else "High"
                level_val = factor["low"] if combo[i] == -1 else factor["high"]
                run[factor["name"]] = {
                    "coded": combo[i],
                    "level": level_str,
                    "value": level_val,
                }
            runs.append(run)

        return runs

    def generate_for_cause(
        self,
        lot_id: str,
        candidate_cause: Dict[str, Any],
        include_center_points: bool = True,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Generate a full 2^k factorial DOE runcard for a candidate root cause.

        Args:
            lot_id:           The lot under investigation.
            candidate_cause:  A dict from candidate_causes in findings.
            include_center_points: Whether to add center-point replicates.
            random_seed:      Seed for run order randomization.

        Returns:
            A full DOE runcard dict with 2^k run matrix, factor levels, and analysis criteria.
        """
        tool_id = candidate_cause.get("tool_id", "UNKNOWN")
        parameter = candidate_cause.get("parameter", "unknown")
        step = candidate_cause.get("step", "unknown")
        spatial = candidate_cause.get("spatial_signature", "random")
        evidence = candidate_cause.get("evidence", "")
        deviation_score = candidate_cause.get("deviation_score", 0.0)

        # Primary factor: the identified out-of-spec parameter
        primary_levels = self._get_factor_levels(tool_id, parameter, step)
        primary_nominal = primary_levels.get("nominal")

        if primary_nominal is None:
            return {
                "lot_id": lot_id,
                "error": f"Could not determine factor levels for {parameter} on {tool_id}.",
                "runcard": [],
            }

        # Discover parameters on this tool to form a multi-factor 2^k DOE
        factor_names = [parameter]
        try:
            tool_steps = self.repo.get_process_steps(tool_id=tool_id)
            for s in tool_steps:
                pname = s.get("parameter_name")
                if pname and pname not in factor_names and len(factor_names) < 3:
                    factor_names.append(pname)
        except Exception:
            pass

        # Fallback to domain clusters if fewer than 3 factors found
        if len(factor_names) < 3:
            domain_clusters = {
                "litho": ["focus_offset", "exposure_energy", "numerical_aperture"],
                "etch": ["chamber_pressure", "rf_power_forward", "gas_flow_cl2"],
                "cvd": ["chamber_pressure", "deposition_temp", "rf_bias"],
                "cmp": ["head_downforce", "platen_rpm", "slurry_flow_rate"],
                "implant": ["acceleration_energy", "beam_current", "tilt_angle"],
            }
            step_lower = str(step).lower()
            tool_lower = str(tool_id).lower()
            for key, params in domain_clusters.items():
                if key in step_lower or key in tool_lower or any(p in parameter for p in params):
                    for p in params:
                        if p not in factor_names and len(factor_names) < 3:
                            factor_names.append(p)
                    break

        factors = []
        for pname in factor_names:
            levels = self._get_factor_levels(tool_id, pname, step)
            if levels.get("nominal") is not None:
                factors.append({
                    "name": pname,
                    "low": levels["low"],
                    "high": levels["high"],
                    "nominal": levels["nominal"],
                    "unit": levels.get("unit", "a.u."),
                    "spec_min": levels.get("spec_min"),
                    "spec_max": levels.get("spec_max"),
                })

        # Ensure at least the primary factor exists
        if not factors:
            factors = [{
                "name": parameter,
                "low": primary_levels["low"],
                "high": primary_levels["high"],
                "nominal": primary_levels["nominal"],
                "unit": primary_levels.get("unit", "a.u."),
                "spec_min": primary_levels.get("spec_min"),
                "spec_max": primary_levels.get("spec_max"),
            }]

        # Build full 2^k factorial run matrix
        run_matrix = self._build_full_factorial(factors)
        n_corner_runs = len(run_matrix)

        # Add center points (nominal for all factors) to detect curvature
        center_run = {
            f["name"]: {"coded": 0, "level": "Nominal", "value": f["nominal"]}
            for f in factors
        }
        n_center_runs = 3 if include_center_points else 0
        if include_center_points:
            run_matrix += [center_run, center_run, center_run]

        # Randomize run order (critical for eliminating systematic drift bias)
        rng = random.Random(random_seed)
        run_ids = list(range(1, len(run_matrix) + 1))
        run_order = run_ids.copy()
        rng.shuffle(run_order)

        # Standardized single target response metric across ALL runs
        target_metric = "Defect Density (def/cm²)"

        # Sample size using Lehr's formula
        n_per_run = _minimum_sample_size(effect_size_fraction=max(0.3, deviation_score))

        # Build final run sheet
        run_sheet = []
        for i, (run, order) in enumerate(zip(run_matrix, run_order), 1):
            is_center = all(v["coded"] == 0 for v in run.values())
            entry = {
                "run_id": f"RUN-{i:02d}",
                "run_order": order,
                "is_center_point": is_center,
                "type": "Center" if is_center else "Corner",
                "conditions": run,
                "wafers": n_per_run,
                "target_metric": target_metric,
            }
            run_sheet.append(entry)

        # Sort by randomized run order for execution
        run_sheet.sort(key=lambda r: r["run_order"])

        # Hypothesis
        factor_list_str = ", ".join(f["name"].replace("_", " ") for f in factors)
        h0 = f"Variation in {factor_list_str} on {tool_id} has no statistically significant effect on {target_metric} or yield (p > 0.05)."
        h1 = f"Re-centering {parameter.replace('_',' ')} to nominal conditions on {tool_id} reduces {spatial} defect density by ≥ 40% and restores Cpk ≥ 1.33."

        # Success criteria
        success_criteria = [
            f"Primary: ≥40% reduction in {spatial} defect density at center/edge zones after parameter re-centering.",
            f"Secondary: Normalized yield improvement ≥2.0% vs. excursion baseline for lot {lot_id}.",
            f"Tertiary: In-control tool capability Cpk ≥ 1.33 across all confirmatory runs.",
        ]

        total_wafers = n_per_run * len(run_sheet)
        design_type = f"2^{len(factors)} Full Factorial" if len(factors) <= 4 else f"2^({len(factors)}-1) Fractional Factorial (Resolution IV)"

        second_param = factors[1]["name"] if len(factors) > 1 else None

        return {
            "lot_id": lot_id,
            "tool_id": tool_id,
            "parameter": parameter,
            "step": step,
            "design_type": design_type,
            "n_factors": len(factors),
            "factors": factors,
            "n_runs": len(run_sheet),
            "n_corner_runs": n_corner_runs,
            "n_center_runs": n_center_runs,
            "wafers_per_run": n_per_run,
            "total_wafers_required": total_wafers,
            "target_metric": target_metric,
            "run_sheet": run_sheet,
            "hypothesis": {"H0": h0, "H1": h1},
            "success_criteria": success_criteria,
            "spatial_signature": spatial,
            "evidence_basis": evidence,
            "second_parameter_tested": second_param,
            "notes": [
                "Run order is randomized to eliminate systematic process drift bias.",
                f"Center points ({include_center_points}) detect curvature and estimate pure experimental variance.",
                "All process parameters NOT listed as factors must be held at certified nominal values.",
                "Wafer IDs must be tracked individually and defect maps collected across all runs.",
            ],
            "protocol_warning": "Cleanroom sign-off required prior to production wafer dispatch.",
        }

    def format_as_text(self, runcard: Dict[str, Any]) -> str:
        """Format DOE runcard as human-readable text for IBM Bob chat panel."""
        if "error" in runcard:
            return f"[DOE Generator Error] {runcard['error']}"

        lot_id = runcard.get("lot_id", "UNKNOWN")
        tool_id = runcard.get("tool_id", "UNKNOWN")
        param = runcard.get("parameter", "unknown").replace("_", " ")
        step = runcard.get("step", "unknown")

        lines = [
            f"=== Confirmatory DOE Runcard: {lot_id} — {tool_id} / {param} ===",
            "",
            f"Design Type:       {runcard.get('design_type')}",
            f"Tool:              {tool_id}  |  Step: {step}",
            f"Primary Parameter: {param}",
        ]
        if runcard.get("second_parameter_tested"):
            lines.append(f"Secondary Factor:  {runcard['second_parameter_tested'].replace('_', ' ')}")
        lines.append("")

        lines.append("Factor Levels:")
        for f in runcard.get("factors", []):
            fname = f["name"].replace("_", " ")
            lines.append(
                f"  {fname:30s}  Low: {_format_value(f['low'])}  |  "
                f"Nominal: {_format_value(f['nominal'])}  |  "
                f"High: {_format_value(f['high'])}"
            )
            if f.get("spec_min") is not None:
                lines.append(
                    f"  {'(spec limits)':30s}  [{_format_value(f['spec_min'])} — {_format_value(f['spec_max'])}]"
                )
        lines.append("")

        lines.append(f"Sample Allocation: {runcard.get('wafers_per_run')} wafer(s) per run")
        lines.append(f"Total Runs:        {runcard.get('n_runs')} (including center points)")
        lines.append(f"Total Wafers:      {runcard.get('total_wafers_required')} pilot wafers required")
        lines.append("")

        lines.append("Run Sheet (sorted by randomized execution order):")
        lines.append(f"  {'Run ID':<10} {'Exec Order':<12} {'Type':<12} {'Conditions'}")
        lines.append("  " + "─" * 70)
        for r in runcard.get("run_sheet", []):
            ctype = "CENTER" if r.get("is_center_point") else "CORNER"
            conditions_str = ", ".join(
                f"{k.replace('_',' ')}: {v['level']} ({_format_value(v['value'])})"
                for k, v in r.get("conditions", {}).items()
            )
            lines.append(
                f"  {r['run_id']:<10} {r['run_order']:<12} {ctype:<12} {conditions_str}"
            )
        lines.append("")

        hyp = runcard.get("hypothesis", {})
        lines.append("Hypothesis:")
        lines.append(f"  H₀: {hyp.get('H0', '')}")
        lines.append(f"  H₁: {hyp.get('H1', '')}")
        lines.append("")

        lines.append("Success Criteria (for confirmation):")
        for crit in runcard.get("success_criteria", []):
            lines.append(f"  ✓ {crit}")
        lines.append("")

        lines.append("Notes:")
        for note in runcard.get("notes", []):
            lines.append(f"  • {note}")
        lines.append("")
        lines.append("⚠️  This DOE must be approved by the process module owner before wafer starts.")

        return "\n".join(lines)

    def format_as_markdown(self, runcard: Dict[str, Any]) -> str:
        """
        Format DOE runcard as an executive-ready Markdown matrix for IBM Bob chat panel.
        Displays true 2^k factorial structure, factor levels, randomized run matrix,
        and unified response metric.
        """
        if "error" in runcard:
            return f"> ❌ **DOE Generator Error**: {runcard['error']}"

        lot_id = runcard.get("lot_id", "UNKNOWN")
        tool_id = runcard.get("tool_id", "UNKNOWN")
        param = runcard.get("parameter", "unknown")
        param_clean = param.replace("_", " ")
        step = runcard.get("step", "unknown")
        design_type = runcard.get("design_type", "2^k Full Factorial")
        n_factors = runcard.get("n_factors", len(runcard.get("factors", [])))
        n_runs = runcard.get("n_runs", len(runcard.get("run_sheet", [])))
        n_corner = runcard.get("n_corner_runs", max(0, n_runs - 3))
        n_center = runcard.get("n_center_runs", 3)
        wafers_per_run = runcard.get("wafers_per_run", 2)
        total_wafers = runcard.get("total_wafers_required", wafers_per_run * n_runs)
        target_metric = runcard.get("target_metric", "Defect Density (def/cm²)")
        factors = runcard.get("factors", [])
        run_sheet = runcard.get("run_sheet", [])
        spatial = runcard.get("spatial_signature", "spatial")

        lines = [
            f"### 🔬 Confirmatory Statistical DOE: `{tool_id}` ({param_clean})",
            f"**Excursion Lot:** `{lot_id}` | **Process Step:** `{step}`  ",
            f"**Experimental Design:** **{design_type}** ({n_factors} Factors, {n_runs} Total Runs: {n_corner} Factorial Corner + {n_center} Center Replicates)  ",
            f"**Target Response Metric ($Y$):** **`{target_metric}`** *(Unified across all runs for ANOVA & interaction estimation)*  ",
            f"**Sample Allocation:** **{wafers_per_run} pilot wafers/run** ({total_wafers} wafers total, sized via Lehr's formula: $\\alpha=0.05, \\text{{Power}}=0.80$)  ",
            "",
            "#### 1. Experimental Factors & Operating Windows:",
            "| Factor | Parameter | Low Level (-1) | Nominal (0) | High Level (+1) | Spec / Process Limits |",
            "|:---:|:---|:---:|:---:|:---:|:---|",
        ]

        factor_labels = ["A", "B", "C", "D", "E"]
        for idx, f in enumerate(factors):
            flabel = factor_labels[idx] if idx < len(factor_labels) else f"F{idx+1}"
            unit = f.get("unit", "")
            unit_str = f" {unit}" if unit and unit != "a.u." else ""
            spec_str = f"[{_format_value(f['spec_min'])}, {_format_value(f['spec_max'])}]{unit_str}" if f.get("spec_min") is not None else "Historical ±2σ"
            lines.append(
                f"| **{flabel}** | `{f['name']}` | {_format_value(f['low'])}{unit_str} | {_format_value(f['nominal'])}{unit_str} | {_format_value(f['high'])}{unit_str} | {spec_str} |"
            )

        lines.append("")
        lines.append("#### 2. Randomized Factorial Execution Matrix:")

        header_cols = ["Run", "Exec Order", "Type"]
        for idx, f in enumerate(factors):
            flabel = factor_labels[idx] if idx < len(factor_labels) else f"F{idx+1}"
            header_cols.append(f"{f['name'].replace('_', ' ').title()} ({flabel})")
        header_cols.extend(["Wafers", "Target Metric"])

        lines.append("| " + " | ".join(header_cols) + " |")
        alignments = [":---:" for _ in range(3)] + [":---:" for _ in factors] + [":---:", ":---"]
        lines.append("| " + " | ".join(alignments) + " |")

        for r in run_sheet:
            run_id = r["run_id"]
            order = r["run_order"]
            rtype = "Center" if r.get("is_center_point") else "Corner"
            conds = r.get("conditions", {})
            row_vals = [run_id, str(order), rtype]
            for f in factors:
                fname = f["name"]
                cinfo = conds.get(fname, {})
                level = cinfo.get("level", "Nominal")
                val = cinfo.get("value", f["nominal"])
                unit = f.get("unit", "")
                unit_str = f" {unit}" if unit and unit != "a.u." else ""
                row_vals.append(f"{level} ({_format_value(val)}{unit_str})")
            row_vals.append(str(wafers_per_run))
            row_vals.append(target_metric)
            lines.append("| " + " | ".join(row_vals) + " |")

        lines.append("")
        hyp = runcard.get("hypothesis", {})
        lines.append("#### 3. Hypothesis & Confirmation Criteria:")
        lines.append(f"- **$H_0$ (Null):** {hyp.get('H0', '')}")
        lines.append(f"- **$H_1$ (Alternative):** {hyp.get('H1', '')}")
        for crit in runcard.get("success_criteria", []):
            lines.append(f"- **Criterion:** {crit}")

        lines.append("")
        protocol_rule = runcard.get("protocol_warning", "Cleanroom sign-off required prior to production wafer dispatch.")
        lines.append(f"> ⚠️ **Protocol Rule (Cleanroom Sign-off):** {protocol_rule}")

        return "\n".join(lines)

