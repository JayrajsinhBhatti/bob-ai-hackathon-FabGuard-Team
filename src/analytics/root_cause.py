"""Root Cause Ranker for Semiconductor Wafer Yield Analysis.

Implements:
- Step-constrained candidate filtering via defect detected_at_step
- Parameter deviation scoring (z-score, spec excursions, Cpk degradation, SPC violations)
- Cross-lot frequency calculation across affected/low-yield lots
- Sample-size calibrated confidence estimation (strictly bounded, never 100% certain)
- Composite scoring: composite_score = deviation_score * frequency_across_lots * confidence
- Dynamic, explainable evidence generation
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from analytics.data_access import DataRepository
from analytics.models import CandidateCause
from analytics.spatial import classify_spatial_signature
from analytics.spc import (
    analyze_parameter_series,
    calculate_cpk,
    detect_western_electric_violations,
    is_out_of_capability,
)


class RootCauseRanker:
    """Ranks equipment and process parameter candidates for wafer yield loss."""

    def __init__(
        self,
        repository: DataRepository,
        low_yield_threshold: float = 90.0,
        min_affected_lots_for_high_conf: int = 10,
    ):
        self.repo = repository
        self.low_yield_threshold = low_yield_threshold
        self.min_affected_lots_for_high_conf = min_affected_lots_for_high_conf

    def rank_causes_for_lot(self, lot_id: str) -> List[CandidateCause]:
        """Identify and rank candidate root causes for a specific lot.

        Args:
            lot_id: The identifier of the lot to analyze.

        Returns:
            List of CandidateCause objects sorted by composite_score in descending order.
        """
        target_lot = self.repo.get_lot(lot_id)
        if not target_lot:
            return []

        # 1. Fetch defects for this lot
        lot_defects = self.repo.get_defects(lot_id=lot_id)
        
        # Determine dominant spatial signature and detected process steps
        spatial_sig = "random"
        detected_steps: List[str] = []
        if lot_defects:
            coords = [(d["x"], d["y"]) for d in lot_defects if "x" in d and "y" in d]
            spatial_sig = classify_spatial_signature(coords)
            detected_steps = list(set([d["detected_at_step"] for d in lot_defects if d.get("detected_at_step")]))

        # If no detected step from defects, fallback to all steps observed on this lot
        lot_steps_data = self.repo.get_process_steps(lot_id=lot_id)
        if not detected_steps:
            detected_steps = list(set([s["step_name"] for s in lot_steps_data if s.get("step_name")]))

        if not detected_steps:
            return []

        # 2. Identify affected cohort (all lots with low yield or matching defect signature)
        all_lots = self.repo.get_all_lots()
        affected_lot_ids = set()
        normal_lot_ids = set()

        for l in all_lots:
            lid = l.get("lot_id")
            if not lid or l.get("status") == "in_progress":
                continue
            yld = l.get("final_yield_pct")
            if yld is not None and yld < self.low_yield_threshold:
                affected_lot_ids.add(lid)
            elif yld is not None:
                normal_lot_ids.add(lid)

        # Ensure current lot is included in affected cohort for ranking
        affected_lot_ids.add(lot_id)
        total_affected = len(affected_lot_ids)

        # 3. Parameter-level evaluation narrowed strictly by detected process steps
        candidate_results: List[CandidateCause] = []

        # Group lot parameters by (step_name, tool_id, parameter_name)
        target_params = {}
        for s in lot_steps_data:
            step_name = s.get("step_name")
            # Enforce step narrowing: prioritize parameters from detected steps
            if step_name not in detected_steps:
                continue
            key = (step_name, s.get("tool_id", "UNKNOWN"), s.get("parameter_name", "UNKNOWN"))
            target_params[key] = s

        # For each parameter in the relevant process steps, analyze historical distribution
        for (step_name, tool_id, param_name), current_step in target_params.items():
            curr_val = current_step.get("value")
            if curr_val is None:
                continue

            spec_min = current_step.get("spec_min")
            spec_max = current_step.get("spec_max")

            # Fetch historical readings for this (tool_id, parameter_name)
            tool_param_history = self.repo.get_process_steps(
                step_name=step_name, tool_id=tool_id, parameter_name=param_name
            )

            all_values = [p["value"] for p in tool_param_history if p.get("value") is not None]
            if len(all_values) < 2:
                continue

            # Compute baseline mean and std using normal (high-yield) lots or spec targets
            normal_vals = [
                p["value"]
                for p in tool_param_history
                if p.get("value") is not None and p.get("lot_id") in normal_lot_ids
            ]
            if len(normal_vals) >= 2:
                baseline_mean = float(np.mean(normal_vals))
                baseline_std = float(np.std(normal_vals, ddof=1)) or 1e-6
            elif spec_min is not None and spec_max is not None and spec_max > spec_min:
                baseline_mean = (spec_min + spec_max) / 2.0
                baseline_std = (spec_max - spec_min) / 6.0
            else:
                baseline_mean = float(np.mean(all_values))
                baseline_std = float(np.std(all_values, ddof=1)) or 1e-6

            pop_mean = float(np.mean(all_values))
            pop_std = float(np.std(all_values, ddof=1)) if len(all_values) > 1 else 1e-6
            if pop_std <= 1e-12:
                pop_std = 1e-6

            # Compute Cpk and Western Electric violations across historical series
            cpk = calculate_cpk(all_values, spec_min, spec_max)
            we_violations = detect_western_electric_violations(all_values, mean=pop_mean, std_dev=pop_std)

            # Current reading z-score relative to normal operating baseline
            z_score = (curr_val - baseline_mean) / baseline_std
            abs_z = abs(z_score)

            # Spec limit excursion
            spec_violation_ratio = 0.0
            if spec_min is not None and spec_max is not None and spec_max > spec_min:
                spec_range = spec_max - spec_min
                if curr_val > spec_max:
                    spec_violation_ratio = (curr_val - spec_max) / spec_range
                elif curr_val < spec_min:
                    spec_violation_ratio = (spec_min - curr_val) / spec_range
            elif spec_max is not None and curr_val > spec_max:
                spec_violation_ratio = (curr_val - spec_max) / (abs(spec_max) + 1e-6)
            elif spec_min is not None and curr_val < spec_min:
                spec_violation_ratio = (spec_min - curr_val) / (abs(spec_min) + 1e-6)

            # A. Calculate deviation_score (0 to 1)
            # Combines z-score severity, spec excursion, Cpk degradation, and WE rules
            z_comp = min(1.0, abs_z / 3.0)  # 3.0 sigma scales to 1.0
            spec_comp = 1.0 if spec_violation_ratio > 0 else min(1.0, abs_z / 3.0)
            cpk_comp = max(0.0, (1.33 - cpk) / 1.33) if cpk is not None else 0.20
            cpk_comp = min(1.0, max(0.0, cpk_comp))
            we_comp = 0.30 if we_violations.has_violations else 0.0

            deviation_score = float(
                0.40 * z_comp + 0.30 * spec_comp + 0.20 * cpk_comp + 0.10 * we_comp
            )
            deviation_score = float(np.clip(deviation_score, 0.01, 0.98))

            # B. Calculate frequency_across_lots (0 to 1)
            # How many affected lots exhibited an abnormality (|z| > 1.5 or out of spec) in this param
            abnormal_affected_count = 0
            normal_affected_count = 0

            for h in tool_param_history:
                hlid = h.get("lot_id")
                hval = h.get("value")
                if hval is None:
                    continue
                hz = abs((hval - pop_mean) / pop_std)
                is_abnormal = hz >= 1.5 or (spec_max is not None and hval > spec_max) or (spec_min is not None and hval < spec_min)

                if hlid in affected_lot_ids:
                    if is_abnormal:
                        abnormal_affected_count += 1
                elif hlid in normal_lot_ids:
                    if is_abnormal:
                        normal_affected_count += 1

            # Frequency among affected lots
            freq_across_affected = (
                float(abnormal_affected_count / total_affected)
                if total_affected > 0
                else 0.50
            )
            freq_across_affected = float(np.clip(freq_across_affected, 0.05, 1.0))

            # Confounding check: if normal lots also show this abnormality at high frequency, penalize
            normal_rate = (
                float(normal_affected_count / len(normal_lot_ids))
                if len(normal_lot_ids) > 0
                else 0.0
            )
            specificity_factor = max(0.20, 1.0 - normal_rate)

            # C. Calculate confidence (0 to 0.95, accounting for sample size)
            # Sample size factor: n / (n + 4.0), approaches 1 asymptotically
            sample_size = abnormal_affected_count if abnormal_affected_count > 0 else 1
            sample_size_factor = float(sample_size / (sample_size + 4.0))

            # SPC corroboration boost
            spc_support = 0.15 if (cpk is not None and cpk < 1.33) or we_violations.has_violations else 0.0

            # Base correlation consistency
            consistency = freq_across_affected * specificity_factor

            # Raw confidence calculation
            confidence = (consistency * 0.70 + spc_support) * sample_size_factor + 0.15 * z_comp
            # Strictly bound confidence: never claim 100% certainty (correlation is not causation)
            confidence = float(np.clip(confidence, 0.10, 0.92))

            # D. Dynamic Evidence String
            direction = "above" if z_score > 0 else "below"
            evidence_parts = []
            evidence_parts.append(
                f"{param_name.replace('_', ' ').capitalize()} was {abs_z:.1f} sigma {direction} target"
            )
            evidence_parts.append(
                f"on {abnormal_affected_count} of {total_affected} affected lots"
            )
            if cpk is not None:
                evidence_parts.append(f"Cpk {cpk:.2f}")
            if we_violations.rule1_beyond_3sigma:
                evidence_parts.append("WE Rule 1 (point > 3σ) violated")
            elif we_violations.rule2_two_of_three_beyond_2sigma:
                evidence_parts.append("WE Rule 2 (2-of-3 > 2σ) violated")
            elif we_violations.rule4_eight_on_one_side:
                evidence_parts.append("WE Rule 4 (8 on one side) violated")

            if spatial_sig != "random":
                evidence_parts.append(f"associated with {spatial_sig} defects at {step_name}")

            evidence_str = "; ".join(evidence_parts) + "."

            # Composite score for ranking
            composite_score = deviation_score * freq_across_affected * confidence

            candidate_results.append(
                CandidateCause(
                    step=step_name,
                    tool_id=tool_id,
                    parameter=param_name,
                    spatial_signature=spatial_sig,
                    deviation_score=round(deviation_score, 4),
                    confidence=round(confidence, 4),
                    sample_size=sample_size,
                    evidence=evidence_str,
                    probability=round(composite_score, 4),
                    risk_score=round(composite_score, 4),
                    confidence_basis="composite_heuristic_v1",
                )
            )

        # Sort candidates by composite_score (probability/risk_score) descending
        candidate_results.sort(
            key=lambda c: (c.deviation_score * c.confidence),
            reverse=True,
        )

        return candidate_results
