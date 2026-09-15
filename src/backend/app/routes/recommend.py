"""
Recommendations API endpoint: Returns corrective engineering recommendations.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any
from app.db import query_one
from app.routes.rootcause import get_root_cause

router = APIRouter(prefix="/recommend", tags=["recommendations"])


@router.get("")
def get_recommendations(lot_id: str = Query(..., description="Target wafer lot ID")) -> Dict[str, Any]:
    """Retrieve structured engineering recommendations and DOE validation steps for a lot."""
    findings = get_root_cause(lot_id, tier="tier2")
    candidates = findings.get("candidate_causes", [])

    if not candidates:
        return {
            "lot_id": lot_id,
            "actions": [],
            "doe_matrix": None,
            "status": "NOMINAL",
        }

    top = candidates[0]
    return {
        "lot_id": lot_id,
        "suspect_tool": top["tool_id"],
        "suspect_step": top["step"],
        "suspect_parameter": top["parameter"],
        "calibrated_probability": top["probability"],
        "actions": [
            {
                "priority": "P0 - Immediate",
                "action": f"Hardware Interlock {top['tool_id']}",
                "description": f"Prevent automatic wafer dispatch to {top['tool_id']} until chamber manometer is re-zeroed.",
            },
            {
                "priority": "P1 - Verification",
                "action": "Execute 2-Wafer Split DOE",
                "description": f"Perform a 2-wafer test comparing nominal {top['parameter']} vs current recipe drift.",
            },
            {
                "priority": "P2 - Preventive",
                "action": "Inspect Upstream RF Generator / Gas Line",
                "description": "Verify impedance matchbox capacitors and gas line mass flow controllers (MFC).",
            },
        ],
        "doe_matrix": {
            "title": f"DOE Verification Matrix for {top['tool_id']}",
            "runs": [
                {"run_id": "DOE-1", "wafer_id": "W-TEST-01", "offset": "-5% target", "expected_outcome": "Baseline recovery"},
                {"run_id": "DOE-2", "wafer_id": "W-TEST-02", "offset": "Nominal target", "expected_outcome": "Defect density < 0.5/cm²"},
            ],
            "caveat": "Mandatory cleanroom protocol: Do not modify standard production recipe without DOE sign-off.",
        },
    }
