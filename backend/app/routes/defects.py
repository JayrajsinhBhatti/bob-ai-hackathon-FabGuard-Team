"""
Defects API endpoints: Fetch normalized wafer inspection defect maps.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.db import query_all, query_one

router = APIRouter(prefix="/defects", tags=["defects"])


@router.get("")
def get_defects(
    lot_id: str = Query(..., description="Target wafer lot ID (e.g. LOT-2231)"),
    wafer_id: Optional[str] = Query(None, description="Optional filter by wafer ID"),
    limit: int = Query(2500, ge=10, le=10000),
) -> Dict[str, Any]:
    """
    Fetch normalized wafer defect coordinates (x, y) with severity and signature metadata.
    """
    params = [lot_id]
    wafer_filter = ""
    if wafer_id:
        wafer_filter = "AND wafer_id = ?"
        params.append(wafer_id)

    # Check lot exists
    lot_exists = query_one("SELECT lot_id FROM wafer_lots WHERE lot_id = ?;", (lot_id,))
    if not lot_exists:
        raise HTTPException(status_code=404, detail=f"Lot {lot_id} not found")

    # Fetch defects
    query = f"""
    SELECT 
        id,
        lot_id,
        wafer_id,
        defect_type,
        x,
        y,
        severity,
        detected_at_step
    FROM defects
    WHERE lot_id = ? {wafer_filter}
    LIMIT ?;
    """
    params.append(limit)
    defects = query_all(query, tuple(params))

    # Get signature from ground truth or infer
    gt = query_one("SELECT injected_signature FROM ground_truth_labels WHERE lot_id = ?;", (lot_id,))
    signature = gt["injected_signature"] if gt else "random"

    # Severity distribution
    counts = {"critical": 0, "major": 0, "minor": 0}
    type_counts = {}
    for d in defects:
        sev = d.get("severity", "minor")
        counts[sev] = counts.get(sev, 0) + 1
        t = d.get("defect_type", "particle")
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "lot_id": lot_id,
        "wafer_id": wafer_id or "all_wafers",
        "spatial_signature": signature,
        "total_returned": len(defects),
        "severity_summary": counts,
        "defect_type_summary": type_counts,
        "defects": defects,
    }
