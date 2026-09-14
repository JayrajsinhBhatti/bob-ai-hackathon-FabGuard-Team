"""Batch Risk Predictor for upcoming in-progress wafer lots.

Identifies in-progress lots exhibiting early process parameter drift matching
historical low-yield failure fingerprints using normalized parameter vector similarity.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from analytics.data_access import DataRepository
from analytics.models import AtRiskBatch
from analytics.spatial import classify_spatial_signature


class BatchRiskPredictor:
    """Predicts yield risk for upcoming batches currently in-progress."""

    def __init__(
        self,
        repository: DataRepository,
        low_yield_threshold: float = 90.0,
        risk_flag_threshold: float = 0.50,
    ):
        self.repo = repository
        self.low_yield_threshold = low_yield_threshold
        self.risk_flag_threshold = risk_flag_threshold

    def predict_at_risk_batches(self) -> List[AtRiskBatch]:
        """Predict yield risk for all in-progress lots.

        Returns:
            List of AtRiskBatch objects sorted by risk_score descending.
        """
        in_progress_lots = self.repo.get_all_lots(status="in_progress")
        if not in_progress_lots:
            return []

        all_lots = self.repo.get_all_lots()
        completed_low_yield_lots = [
            lot for lot in all_lots
            if lot.get("status") != "in_progress"
            and lot.get("final_yield_pct") is not None
            and lot.get("final_yield_pct") < self.low_yield_threshold
        ]

        if not completed_low_yield_lots:
            return []

        # 1. Compute baseline means and standard deviations using normal lots or spec limits
        normal_lots = {
            l["lot_id"] for l in all_lots
            if l.get("status") != "in_progress"
            and l.get("final_yield_pct") is not None
            and l.get("final_yield_pct") >= self.low_yield_threshold
        }

        all_steps = self.repo.get_process_steps()
        param_stats: Dict[str, Tuple[float, float]] = {}
        grouped_normal_vals: Dict[str, List[float]] = {}
        grouped_all_vals: Dict[str, List[float]] = {}
        param_specs: Dict[str, Tuple[Optional[float], Optional[float]]] = {}

        for step in all_steps:
            val = step.get("value")
            if val is None:
                continue
            key = f"{step.get('step_name')}_{step.get('tool_id')}_{step.get('parameter_name')}"
            grouped_all_vals.setdefault(key, []).append(float(val))
            if step.get("lot_id") in normal_lots:
                grouped_normal_vals.setdefault(key, []).append(float(val))
            if key not in param_specs:
                param_specs[key] = (step.get("spec_min"), step.get("spec_max"))

        for key, all_vals in grouped_all_vals.items():
            norm_vals = grouped_normal_vals.get(key, [])
            s_min, s_max = param_specs.get(key, (None, None))
            if len(norm_vals) >= 2:
                param_stats[key] = (float(np.mean(norm_vals)), float(np.std(norm_vals, ddof=1)) or 1e-6)
            elif s_min is not None and s_max is not None and s_max > s_min:
                param_stats[key] = ((s_min + s_max) / 2.0, (s_max - s_min) / 6.0)
            elif len(all_vals) >= 2:
                param_stats[key] = (float(np.mean(all_vals)), float(np.std(all_vals, ddof=1)) or 1e-6)
            else:
                param_stats[key] = (float(all_vals[0]), 1.0)

        # 2. Build parameter fingerprints and spatial signatures for historical low-yield lots
        historical_fingerprints: List[Dict[str, Any]] = []

        for hist_lot in completed_low_yield_lots:
            hlid = hist_lot["lot_id"]
            hsteps = self.repo.get_process_steps(lot_id=hlid)
            if not hsteps:
                continue

            z_vector: Dict[str, float] = {}
            for s in hsteps:
                key = f"{s.get('step_name')}_{s.get('tool_id')}_{s.get('parameter_name')}"
                val = s.get("value")
                if val is not None and key in param_stats:
                    mean, std = param_stats[key]
                    z_vector[key] = (float(val) - mean) / std

            # Determine historical spatial signature if defects exist
            hdefects = self.repo.get_defects(lot_id=hlid)
            hsig = "random"
            if hdefects:
                coords = [(d["x"], d["y"]) for d in hdefects if "x" in d and "y" in d]
                hsig = classify_spatial_signature(coords)

            historical_fingerprints.append({
                "lot_id": hlid,
                "z_vector": z_vector,
                "signature": hsig,
                "yield": hist_lot.get("final_yield_pct", 0.0),
            })

        if not historical_fingerprints:
            return []

        # 3. For each in-progress lot, evaluate similarity to low-yield fingerprints
        at_risk_results: List[AtRiskBatch] = []

        for in_lot in in_progress_lots:
            in_lid = in_lot["lot_id"]
            in_steps = self.repo.get_process_steps(lot_id=in_lid)
            if not in_steps:
                continue

            in_z: Dict[str, float] = {}
            for s in in_steps:
                key = f"{s.get('step_name')}_{s.get('tool_id')}_{s.get('parameter_name')}"
                val = s.get("value")
                if val is not None and key in param_stats:
                    mean, std = param_stats[key]
                    in_z[key] = (float(val) - mean) / std

            if not in_z:
                continue

            # Compare against each historical low-yield fingerprint over shared observed parameters
            max_similarity = 0.0
            best_matched_signature = "random"

            for hfp in historical_fingerprints:
                hz = hfp["z_vector"]
                shared_keys = set(in_z.keys()).intersection(set(hz.keys()))
                if not shared_keys:
                    continue

                diffs = []
                abnormal_count = 0
                for k in shared_keys:
                    diff = in_z[k] - hz[k]
                    diffs.append(diff**2)
                    if abs(in_z[k]) >= 1.5:
                        abnormal_count += 1

                rmse = np.sqrt(np.mean(diffs))
                # High similarity to historical low-yield fingerprint
                sim = float(np.exp(-rmse / 2.0))

                # If the batch exhibits active parameter excursion, elevate risk to full similarity
                if abnormal_count > 0:
                    adjusted_sim = sim
                else:
                    adjusted_sim = sim * 0.20

                if adjusted_sim > max_similarity:
                    max_similarity = adjusted_sim
                    best_matched_signature = hfp["signature"]

            risk_score = float(np.clip(max_similarity, 0.05, 0.96))

            if risk_score >= self.risk_flag_threshold:
                at_risk_results.append(
                    AtRiskBatch(
                        lot_id=in_lid,
                        risk_score=round(risk_score, 4),
                        matched_signature=best_matched_signature,
                        probability=round(risk_score, 4),
                    )
                )

        at_risk_results.sort(key=lambda b: b.risk_score, reverse=True)
        return at_risk_results
