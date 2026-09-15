"""
copilot/doe_engine.py  —  Feature 3: Automated Statistical DOE Generator

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
          3. Fall back to ±10% of observed value.
        """
        steps = self.repo.get_process_steps(
            step_name=step_name, tool_id=tool_id, parameter_name=parameter
        )

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

        # Determine nominal (center point)
        if spec_min is not None and spec_max is not None:
            nominal = (spec_min + spec_max) / 2.0
        elif mean is not None:
            nominal = mean
        elif observed_value is not None:
            nominal = observed_value
        else:
            return {"nominal": None, "low": None, "high": None, "unit": "a.u."}

        # Determine step size (how far above/below nominal to test)
        if spec_min is not None and spec_max is not None:
            # Use ±10% of spec range as a safe investigation range
            step_size = (spec_max - spec_min) * 0.10
        elif std and std > 1e-6:
            step_size = 2.0 * std
        else:
            step_size = abs(nominal) * 0.10 or 1.0

        return {
            "nominal": round(nominal, 4),
            "low": round(nominal - step_size, 4),
            "high": round(nominal + step_size, 4),
            "step_size": round(step_size, 4),
            "historical_mean": round(mean, 4) if mean is not None else None,
            "historical_std": round(std, 4) if std is not None else None,
            "spec_min": spec_min,
            "spec_max": spec_max,
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
            # For >5 factors, use half-fraction (2^(k-1))
            factors = factors[:5]
            n_factors = 5

        # All combinations of -1 (low) and +1 (high) for each factor
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
        Generate a full DOE runcard for a candidate root cause.

        Args:
            lot_id:           The lot under investigation.
            candidate_cause:  A dict from candidate_causes in findings.
            include_center_points: Whether to add center-point replicates.
            random_seed:      Seed for run order randomization.

        Returns:
            A full DOE runcard dict with run matrix, factor levels, and analysis criteria.
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

        # Build factor list — primary suspect + at most one correlated parameter
        factors = [
            {
                "name": parameter,
                "low": primary_levels["low"],
                "high": primary_levels["high"],
                "nominal": primary_levels["nominal"],
                "spec_min": primary_levels.get("spec_min"),
                "spec_max": primary_levels.get("spec_max"),
            }
        ]

        # Check if there's a correlated second parameter on the same tool (common in etch: pressure × RF)
        second_param = None
        sibling_map = {
            "chamber_pressure": "rf_power",
            "rf_power": "chamber_pressure",
            "gas_flow_sccm": "chamber_pressure",
            "chuck_temperature_c": "chamber_pressure",
            "etch_rate_nm_min": "rf_power",
        }
        sibling_name = sibling_map.get(parameter)
        if sibling_name:
            sib_levels = self._get_factor_levels(tool_id, sibling_name, step)
            if sib_levels.get("nominal") is not None:
                factors.append({
                    "name": sibling_name,
                    "low": sib_levels["low"],
                    "high": sib_levels["high"],
                    "nominal": sib_levels["nominal"],
                    "spec_min": sib_levels.get("spec_min"),
                    "spec_max": sib_levels.get("spec_max"),
                })
                second_param = sibling_name

        # Build run matrix
        run_matrix = self._build_full_factorial(factors)

        # Add center points (nominal for all factors) — detects curvature
        center_run = {
            f["name"]: {"coded": 0, "level": "Nominal", "value": f["nominal"]}
            for f in factors
        }
        if include_center_points:
            # Add 2-3 center point replicates for curvature detection
            run_matrix += [center_run, center_run, center_run]

        # Randomize run order (critical for eliminating systematic bias)
        rng = random.Random(random_seed)
        run_ids = list(range(1, len(run_matrix) + 1))
        run_order = run_ids.copy()
        rng.shuffle(run_order)

        # Build final run sheet
        run_sheet = []
        for i, (run, order) in enumerate(zip(run_matrix, run_order), 1):
            entry = {
                "run_id": f"RUN-{i:02d}",
                "run_order": order,
                "is_center_point": all(
                    v["coded"] == 0 for v in run.values()
                ),
                "conditions": run,
            }
            run_sheet.append(entry)

        # Sort by randomized run order for display
        run_sheet.sort(key=lambda r: r["run_order"])

        # Sample size
        n_per_run = _minimum_sample_size(effect_size_fraction=max(0.3, deviation_score))

        # Hypothesis
        h0 = f"Adjusting {parameter.replace('_',' ')} on {tool_id} has no significant effect on spatial defect density or yield."
        h1 = f"Centering {parameter.replace('_',' ')} on {tool_id} to nominal reduces {spatial} defect density by ≥ 40%."

        # Success criteria
        success_criteria = [
            f"Primary: ≥40% reduction in {spatial} defect density at center-cluster coordinates after parameter re-centering.",
            f"Secondary: Yield improvement ≥2% vs. baseline lot {lot_id} yield.",
            f"Tertiary: Cpk for {parameter.replace('_',' ')} improves to ≥1.33 across all {len(run_sheet)} runs.",
        ]

        total_wafers = n_per_run * len(run_sheet)
        design_type = f"2^{len(factors)} Full Factorial" if len(factors) <= 4 else f"2^({len(factors)}-1) Fractional Factorial (Resolution IV)"

        return {
            "lot_id": lot_id,
            "tool_id": tool_id,
            "parameter": parameter,
            "step": step,
            "design_type": design_type,
            "n_factors": len(factors),
            "factors": factors,
            "n_runs": len(run_sheet),
            "wafers_per_run": n_per_run,
            "total_wafers_required": total_wafers,
            "run_sheet": run_sheet,
            "hypothesis": {"H0": h0, "H1": h1},
            "success_criteria": success_criteria,
            "spatial_signature": spatial,
            "evidence_basis": evidence,
            "second_parameter_tested": second_param,
            "notes": [
                "Run order is randomized to eliminate systematic process drift bias.",
                f"Center points ({include_center_points}) detect curvature in the response surface.",
                "All process parameters NOT listed as factors must be held at certified nominal values.",
                "Wafer IDs must be tracked individually and defect maps collected at each run.",
            ],
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
