"""
Lot lifecycle, wafer batch simulation, and defect synthesis coordinator.
Produces complete relational datasets matching the BOBathon S1 data contracts.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

from data.config import (
    PRODUCT_LINES,
    FAB_LINES,
    SCENARIOS_CONFIG,
    NORMAL_LOTS_CONFIG,
    IN_PROGRESS_LOTS_CONFIG,
)
from data.process_generator import generate_lot_process_telemetry
from data.spatial_patterns import generate_spatial_defects

WAFERS_PER_LOT = 25


def generate_scenario_lots(
    scenario: Dict[str, Any],
    base_timestamp: datetime,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate all lots, process steps, defects, and ground-truth labels for an injected scenario."""
    lots: List[Dict[str, Any]] = []
    process_steps: List[Dict[str, Any]] = []
    defects: List[Dict[str, Any]] = []
    ground_truth: List[Dict[str, Any]] = []

    prefix = scenario["lot_prefix"]
    start_num = scenario["start_lot_num"]
    count = scenario["num_lots"]
    min_yield, max_yield = scenario["nominal_yield_range"]
    min_defects, max_defects = scenario["defects_per_wafer_range"]

    for i in range(count):
        lot_id = f"{prefix}{start_num + i:02d}"
        lot_start = base_timestamp + timedelta(hours=i * 6 + random.randint(10, 50))
        product_id = random.choice(PRODUCT_LINES)
        fab_line = random.choice(FAB_LINES)
        final_yield = round(random.uniform(min_yield, max_yield), 2)

        # 1. Wafer lot record
        lots.append({
            "lot_id": lot_id,
            "product_id": product_id,
            "start_time": lot_start.isoformat(),
            "fab_line": fab_line,
            "final_yield_pct": final_yield,
            "status": "completed",
        })

        # 2. Ground-truth label record (for validation harness)
        ground_truth.append({
            "lot_id": lot_id,
            "injected_cause_step": scenario["step"],
            "injected_cause_tool_id": scenario["tool_id"],
            "injected_cause_parameter": scenario["parameter"],
            "injected_signature": scenario["signature"],
        })

        # 3. Process telemetry records
        telemetry = generate_lot_process_telemetry(
            lot_id=lot_id,
            start_time=lot_start,
            injected_scenario=scenario,
        )
        process_steps.extend(telemetry)

        # 4. Defect inspection records for 25 wafers
        for w_idx in range(1, WAFERS_PER_LOT + 1):
            wafer_id = f"{lot_id}-W{w_idx:02d}"
            # ~80% of wafers in an affected lot clearly exhibit the signature pattern
            if random.random() < 0.82:
                sig = scenario["signature"]
                n_def = random.randint(min_defects, max_defects)
            else:
                # 18% have lower background defects
                sig = "random"
                n_def = random.randint(15, 35)

            w_defects = generate_spatial_defects(
                signature=sig,
                total_defects=n_def,
                defect_type_weights=scenario["defect_types"],
                step_detected=scenario["step"],
                lot_id=lot_id,
                wafer_id=wafer_id,
            )
            defects.extend(w_defects)

    return lots, process_steps, defects, ground_truth


def generate_normal_lots(
    base_timestamp: datetime,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate clean baseline wafer lots operating under nominal Six Sigma control."""
    lots: List[Dict[str, Any]] = []
    process_steps: List[Dict[str, Any]] = []
    defects: List[Dict[str, Any]] = []

    prefix = NORMAL_LOTS_CONFIG["lot_prefix"]
    start_num = NORMAL_LOTS_CONFIG["start_lot_num"]
    count = NORMAL_LOTS_CONFIG["num_lots"]
    min_yield, max_yield = NORMAL_LOTS_CONFIG["nominal_yield_range"]
    min_defects, max_defects = NORMAL_LOTS_CONFIG["defects_per_wafer_range"]

    for i in range(count):
        lot_id = f"{prefix}{start_num + i:02d}"
        lot_start = base_timestamp + timedelta(hours=i * 4 + random.randint(5, 30))
        product_id = random.choice(PRODUCT_LINES)
        fab_line = random.choice(FAB_LINES)
        final_yield = round(random.uniform(min_yield, max_yield), 2)

        lots.append({
            "lot_id": lot_id,
            "product_id": product_id,
            "start_time": lot_start.isoformat(),
            "fab_line": fab_line,
            "final_yield_pct": final_yield,
            "status": "completed",
        })

        telemetry = generate_lot_process_telemetry(
            lot_id=lot_id,
            start_time=lot_start,
            injected_scenario=None,
        )
        process_steps.extend(telemetry)

        for w_idx in range(1, WAFERS_PER_LOT + 1):
            wafer_id = f"{lot_id}-W{w_idx:02d}"
            n_def = random.randint(min_defects, max_defects)
            w_defects = generate_spatial_defects(
                signature="random",
                total_defects=n_def,
                defect_type_weights={"particle": 0.70, "void": 0.20, "bridging": 0.10},
                step_detected=random.choice(["litho", "etch", "cvd", "cmp"]),
                lot_id=lot_id,
                wafer_id=wafer_id,
            )
            defects.extend(w_defects)

    return lots, process_steps, defects


def generate_in_progress_lots(
    base_timestamp: datetime,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate in-progress lots currently being processed on the fab floor."""
    lots: List[Dict[str, Any]] = []
    process_steps: List[Dict[str, Any]] = []
    defects: List[Dict[str, Any]] = []

    prefix = IN_PROGRESS_LOTS_CONFIG["lot_prefix"]
    start_num = IN_PROGRESS_LOTS_CONFIG["start_lot_num"]
    count = IN_PROGRESS_LOTS_CONFIG["num_lots"]
    at_risk_indices = set(IN_PROGRESS_LOTS_CONFIG["at_risk_indices"])

    for i in range(1, count + 1):
        lot_id = f"{prefix}{start_num + i - 1:02d}"
        lot_start = base_timestamp + timedelta(hours=80 + i * 2)
        product_id = random.choice(PRODUCT_LINES)
        fab_line = random.choice(FAB_LINES)
        is_at_risk = i in at_risk_indices

        lots.append({
            "lot_id": lot_id,
            "product_id": product_id,
            "start_time": lot_start.isoformat(),
            "fab_line": fab_line,
            "final_yield_pct": None,  # In-progress lots do not have final yield yet
            "status": "at_risk" if is_at_risk else "in_progress",
        })

        telemetry = generate_lot_process_telemetry(
            lot_id=lot_id,
            start_time=lot_start,
            is_in_progress=True,
            in_progress_drift=is_at_risk,
        )
        process_steps.extend(telemetry)

        # Intermediate inspection defects for the executed steps
        for w_idx in range(1, WAFERS_PER_LOT + 1):
            wafer_id = f"{lot_id}-W{w_idx:02d}"
            if is_at_risk:
                sig = "edge-ring" if random.random() < 0.70 else "random"
                n_def = random.randint(50, 110)
                step_det = "etch"
            else:
                sig = "random"
                n_def = random.randint(10, 25)
                step_det = "litho"

            w_defects = generate_spatial_defects(
                signature=sig,
                total_defects=n_def,
                defect_type_weights={"particle": 0.65, "void": 0.25, "scratch": 0.10},
                step_detected=step_det,
                lot_id=lot_id,
                wafer_id=wafer_id,
            )
            defects.extend(w_defects)

    return lots, process_steps, defects


def generate_full_synthetic_dataset(seed: int = 42) -> Dict[str, List[Dict[str, Any]]]:
    """Master generation function synthesizing the complete fab dataset."""
    random.seed(seed)
    base_time = datetime(2026, 3, 1, 6, 0, 0)

    all_lots: List[Dict[str, Any]] = []
    all_process_steps: List[Dict[str, Any]] = []
    all_defects: List[Dict[str, Any]] = []
    all_ground_truth: List[Dict[str, Any]] = []

    # 1. Generate normal baseline lots
    n_lots, n_steps, n_defects = generate_normal_lots(base_time)
    all_lots.extend(n_lots)
    all_process_steps.extend(n_steps)
    all_defects.extend(n_defects)

    # 2. Generate 5 injected scenarios
    for sc in SCENARIOS_CONFIG:
        sc_lots, sc_steps, sc_defects, sc_gt = generate_scenario_lots(sc, base_time)
        all_lots.extend(sc_lots)
        all_process_steps.extend(sc_steps)
        all_defects.extend(sc_defects)
        all_ground_truth.extend(sc_gt)

    # 3. Generate in-progress lots
    ip_lots, ip_steps, ip_defects = generate_in_progress_lots(base_time)
    all_lots.extend(ip_lots)
    all_process_steps.extend(ip_steps)
    all_defects.extend(ip_defects)

    # Sort lots by start_time for chronological order
    all_lots.sort(key=lambda l: l["start_time"])

    return {
        "wafer_lots": all_lots,
        "process_steps": all_process_steps,
        "defects": all_defects,
        "ground_truth_labels": all_ground_truth,
    }
