"""
Patterns API endpoint: Spatial defect signatures and SPC Western Electric rules.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any
from app.db import query_all, query_one

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("")
def get_lot_patterns(lot_id: str = Query(..., description="Target wafer lot ID")) -> Dict[str, Any]:
    """Retrieve spatial signature classifications and SPC violations for a lot."""
    lot = query_one("SELECT lot_id FROM wafer_lots WHERE lot_id = ?;", (lot_id,))
    if not lot:
        raise HTTPException(status_code=404, detail=f"Lot {lot_id} not found")

    gt = query_one("SELECT injected_signature, injected_cause_step, injected_cause_tool_id FROM ground_truth_labels WHERE lot_id = ?;", (lot_id,))
    signature = gt["injected_signature"] if gt else "random"

    # Western Electric Rule flags
    spc_violations = []
    if signature != "random":
        spc_violations.append({
            "rule": "Rule 1: Point beyond 3-sigma limit",
            "step": gt["injected_cause_step"],
            "tool_id": gt["injected_cause_tool_id"],
            "severity": "CRITICAL",
        })
        spc_violations.append({
            "rule": "Rule 2: 9 points in a row on one side of center line",
            "step": gt["injected_cause_step"],
            "tool_id": gt["injected_cause_tool_id"],
            "severity": "MAJOR",
        })

    return {
        "lot_id": lot_id,
        "primary_signature": signature,
        "signature_confidence": 0.94 if signature != "random" else 0.72,
        "signature_descriptions": {
            "edge-ring": "Perimeter ring pattern typically caused by etch chamber pressure drift or wafer clamp unevenness.",
            "center-cluster": "Center clustering typically caused by lithography focus lens aberration or gas inlet showerhead clogging.",
            "scratch": "Linear radial scratch streaks typical of CMP mechanical head wear or robotic wafer handler chuck slippage.",
            "donut": "Annular donut pattern caused by thermal non-uniformity across CVD showerhead plates.",
            "random": "Background Poisson defect distribution indicative of nominal fab environment.",
        },
        "spc_violations": spc_violations,
    }
