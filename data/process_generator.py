"""
Process step simulation & FDC (Fault Detection and Classification) telemetry generator.
Simulates SECS/GEM parameter data streams for Litho, Etch, CVD, CMP, and Implant steps.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from data.config import TOOL_POOLS, PROCESS_SPECS

STEP_SEQUENCE = ["litho", "etch", "cvd", "cmp", "implant"]


def generate_lot_process_telemetry(
    lot_id: str,
    start_time: datetime,
    injected_scenario: Optional[Dict[str, Any]] = None,
    is_in_progress: bool = False,
    in_progress_drift: bool = False,
) -> List[Dict[str, Any]]:
    """
    Generate telemetry records for all process steps associated with a single wafer lot.
    
    If injected_scenario is provided, the designated (step, tool_id, parameter) receives
    a calibrated shift past specification limits (e.g. +3.4 sigma), simulating physical drift.
    
    If is_in_progress is True, only the first 2 or 3 steps are completed.
    """
    process_records: List[Dict[str, Any]] = []
    current_time = start_time

    # Determine how many steps to execute
    if is_in_progress:
        # In-progress lots have only completed 2 or 3 steps
        num_steps_to_run = 2 if in_progress_drift else random.choice([2, 3])
        active_steps = STEP_SEQUENCE[:num_steps_to_run]
    else:
        active_steps = STEP_SEQUENCE

    for step_name in active_steps:
        # Step processing duration: 45 to 80 minutes
        current_time += timedelta(minutes=random.randint(45, 80))
        tool_pool = TOOL_POOLS[step_name]

        # Check if this step is subject to an injected fault
        is_fault_step = (
            injected_scenario is not None and injected_scenario["step"] == step_name
        ) or (
            is_in_progress and in_progress_drift and step_name == "etch"
        )

        if is_fault_step:
            if injected_scenario is not None:
                assigned_tool = injected_scenario["tool_id"]
                drift_param = injected_scenario["parameter"]
                drift_sigma = injected_scenario["drift_sigma"]
            else:
                # In-progress active drift (Scenario 1 mimic: ETCH-07 chamber_pressure)
                assigned_tool = "ETCH-07"
                drift_param = "chamber_pressure"
                drift_sigma = 3.2
        else:
            # Assign normal tool from pool
            assigned_tool = random.choice(tool_pool)
            drift_param = None
            drift_sigma = 0.0

        # Generate telemetry for each parameter of this step
        specs = PROCESS_SPECS[step_name]
        for param_name, param_meta in specs.items():
            mean = param_meta["mean"]
            sigma = param_meta["sigma"]
            spec_min = param_meta["spec_min"]
            spec_max = param_meta["spec_max"]

            if is_fault_step and param_name == drift_param:
                # Apply deliberate drift (+3.0 to +3.8 sigma)
                noise = random.gauss(0, 0.25 * sigma)
                val = mean + (drift_sigma * sigma) + noise
            else:
                # Normal variation within specification (+/- 1.5 sigma)
                # Keep mostly within specs (Cpk > 1.33)
                val = random.gauss(mean, sigma * 0.85)

            # Round to sensible precision
            val = round(val, 4)

            process_records.append({
                "lot_id": lot_id,
                "step_name": step_name,
                "tool_id": assigned_tool,
                "parameter_name": param_name,
                "value": val,
                "spec_min": spec_min,
                "spec_max": spec_max,
                "timestamp": current_time.isoformat(),
            })

    return process_records
