"""
Lots API endpoints: Fetch wafer lots, yield metrics, and timelines.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.db import query_all, query_one

router = APIRouter(prefix="/lots", tags=["lots"])


@router.get("")
def get_lots(
    fab_line: Optional[str] = Query(None, description="Filter by fab line (e.g. LINE-01-FAB12)"),
    product_id: Optional[str] = Query(None, description="Filter by product ID (e.g. PROD-3NM-SOC)"),
    status: Optional[str] = Query(None, description="Filter by status ('completed', 'in_progress', 'at_risk')"),
    limit: int = Query(150, ge=1, le=500),
) -> Dict[str, Any]:
    """Retrieve wafer lots with aggregate defect counts and primary signatures."""
    conditions = []
    params = []

    if fab_line:
        conditions.append("l.fab_line = ?")
        params.append(fab_line)
    if product_id:
        conditions.append("l.product_id = ?")
        params.append(product_id)
    if status:
        conditions.append("l.status = ?")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
    SELECT 
        l.lot_id,
        l.product_id,
        l.start_time,
        l.fab_line,
        l.final_yield_pct,
        l.status,
        COUNT(d.id) AS defect_count,
        COALESCE(gt.injected_signature, 'random') AS primary_signature
    FROM wafer_lots l
    LEFT JOIN defects d ON l.lot_id = d.lot_id
    LEFT JOIN ground_truth_labels gt ON l.lot_id = gt.lot_id
    {where_clause}
    GROUP BY l.lot_id
    ORDER BY l.start_time ASC
    LIMIT ?;
    """
    params.append(limit)
    rows = query_all(query, tuple(params))

    # Calculate aggregate summary KPIs
    completed_yields = [r["final_yield_pct"] for r in rows if r["final_yield_pct"] is not None]
    avg_yield = round(sum(completed_yields) / len(completed_yields), 2) if completed_yields else 95.0
    at_risk_count = sum(1 for r in rows if r["status"] == "at_risk")
    excursion_count = sum(1 for r in rows if r["final_yield_pct"] is not None and r["final_yield_pct"] < 90.0)

    return {
        "summary": {
            "total_lots": len(rows),
            "average_yield_pct": avg_yield,
            "target_yield_pct": 95.0,
            "at_risk_count": at_risk_count,
            "excursion_count": excursion_count,
        },
        "lots": rows,
    }


@router.get("/{lot_id}")
def get_lot_detail(lot_id: str) -> Dict[str, Any]:
    """Retrieve deep-dive metadata and FDC parameters for a single lot."""
    lot = query_one(
        """
        SELECT 
            l.lot_id,
            l.product_id,
            l.start_time,
            l.fab_line,
            l.final_yield_pct,
            l.status,
            COUNT(d.id) as defect_count,
            COALESCE(gt.injected_signature, 'random') as primary_signature
        FROM wafer_lots l
        LEFT JOIN defects d ON l.lot_id = d.lot_id
        LEFT JOIN ground_truth_labels gt ON l.lot_id = gt.lot_id
        WHERE l.lot_id = ?
        GROUP BY l.lot_id;
        """,
        (lot_id,),
    )

    if not lot:
        raise HTTPException(status_code=404, detail=f"Lot {lot_id} not found")

    # Get process step sensor telemetry readings
    steps = query_all(
        """
        SELECT step_name, tool_id, parameter_name, value, spec_min, spec_max, timestamp
        FROM process_steps
        WHERE lot_id = ?
        ORDER BY timestamp ASC;
        """,
        (lot_id,),
    )

    return {
        "lot": lot,
        "process_steps": steps,
    }


from pydantic import BaseModel, Field
import math
import random
from datetime import datetime
from app.db import execute_write, execute_many


class IngestLotRequest(BaseModel):
    lot_id: str = Field(..., description="Unique Lot identifier, e.g. LOT-3001")
    product_id: str = Field("PROD-3NM-SOC", description="Product family, e.g. PROD-3NM-SOC")
    fab_line: str = Field("LINE-01-FAB12", description="Fab production line")
    final_yield_pct: Optional[float] = Field(71.4, description="Final test yield percentage (e.g. <90% for failed/excursion lot)")
    signature: str = Field("edge-ring", description="Wafer defect spatial signature: edge-ring, center-cluster, scratch, donut, random")
    defect_count: int = Field(850, ge=50, le=5000, description="Number of metrology defect coordinates to simulate")
    suspect_tool: str = Field("ETCH-02", description="Suspect equipment tool ID")
    suspect_step: str = Field("etch", description="Process step name")
    suspect_parameter: str = Field("rf_power_forward", description="Out of control sensor parameter")
    z_score_drift: float = Field(3.8, description="Sensor deviation z-score above 3-sigma")


@router.post("/ingest")
def ingest_new_lot(body: IngestLotRequest) -> Dict[str, Any]:
    """
    Ingest a new wafer lot with custom failure telemetry, simulated defect coordinates,
    and FDC sensor signatures into the cleanroom database.
    """
    lot_id = body.lot_id.strip().upper()
    now_str = datetime.utcnow().isoformat()
    status = "completed" if body.final_yield_pct is not None else "in_progress"

    # 1. Clean existing records if overwriting same test lot
    execute_write("DELETE FROM defects WHERE lot_id = ?;", (lot_id,))
    execute_write("DELETE FROM process_steps WHERE lot_id = ?;", (lot_id,))
    execute_write("DELETE FROM ground_truth_labels WHERE lot_id = ?;", (lot_id,))
    execute_write("DELETE FROM wafer_lots WHERE lot_id = ?;", (lot_id,))

    # 2. Insert into wafer_lots
    execute_write(
        """
        INSERT INTO wafer_lots (lot_id, product_id, start_time, fab_line, final_yield_pct, status)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (lot_id, body.product_id, now_str, body.fab_line, body.final_yield_pct, status),
    )

    # 3. Generate defect coordinates matching spatial signature
    defects_data = []
    wafer_ids = [f"W-{i:02d}" for i in range(1, 26)]
    severities = ["critical", "major", "minor"]
    sev_weights = [0.35, 0.45, 0.20] if (body.final_yield_pct or 100) < 90 else [0.05, 0.25, 0.70]

    for i in range(body.defect_count):
        wafer_id = random.choice(wafer_ids)
        severity = random.choices(severities, weights=sev_weights, k=1)[0]
        defect_type = random.choice(["particle", "bridging", "scratch", "void"])

        # Spatial coordinate generation
        sig = body.signature.lower()
        if sig == "edge-ring":
            theta = random.uniform(0, 2 * math.pi)
            r = random.uniform(0.75, 0.96)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
        elif sig == "center-cluster":
            theta = random.uniform(0, 2 * math.pi)
            r = random.uniform(0.02, 0.38)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
        elif sig == "donut":
            theta = random.uniform(0, 2 * math.pi)
            r = random.uniform(0.45, 0.72)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
        elif sig == "scratch":
            t = random.uniform(-0.85, 0.85)
            x = t + random.gauss(0, 0.04)
            y = t * 0.75 + random.gauss(0, 0.04)
        else: # random
            theta = random.uniform(0, 2 * math.pi)
            r = math.sqrt(random.uniform(0, 0.92))
            x = r * math.cos(theta)
            y = r * math.sin(theta)

        # Clamp to wafer unit circle
        dist = math.hypot(x, y)
        if dist > 0.98:
            x /= (dist / 0.97)
            y /= (dist / 0.97)

        defects_data.append((lot_id, wafer_id, defect_type, round(x, 4), round(y, 4), severity, body.suspect_step))

    execute_many(
        """
        INSERT INTO defects (lot_id, wafer_id, defect_type, x, y, severity, detected_at_step)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        defects_data,
    )

    # 4. Insert baseline and anomalous process steps
    steps = [
        ("litho", "LITHO-01", "focus_offset", 0.0, -15.0, 15.0),
        ("etch", "ETCH-01", "rf_power_forward", 450.0, 420.0, 480.0),
        ("cmp", "CMP-01", "head_downforce", 2.5, 2.0, 3.0),
        ("implant", "IMP-01", "beam_current_ma", 12.0, 10.0, 14.0),
    ]

    process_step_rows = []
    for step_name, tool_id, param, nominal, s_min, s_max in steps:
        val = nominal + random.gauss(0, (s_max - s_min) * 0.05)
        process_step_rows.append((lot_id, step_name, tool_id, param, round(val, 2), s_min, s_max, now_str))

    # Add the injected anomalous tool parameter
    spec_range = 30.0
    nominal_val = 450.0
    drift_val = nominal_val + (body.z_score_drift * (spec_range / 3.0))
    process_step_rows.append((
        lot_id,
        body.suspect_step,
        body.suspect_tool,
        body.suspect_parameter,
        round(drift_val, 2),
        nominal_val - spec_range,
        nominal_val + spec_range,
        now_str,
    ))

    execute_many(
        """
        INSERT INTO process_steps (lot_id, step_name, tool_id, parameter_name, value, spec_min, spec_max, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        process_step_rows,
    )

    # 5. Insert ground truth benchmark label
    execute_write(
        """
        INSERT INTO ground_truth_labels (lot_id, injected_cause_step, injected_cause_tool_id, injected_cause_parameter, injected_signature)
        VALUES (?, ?, ?, ?, ?);
        """,
        (lot_id, body.suspect_step, body.suspect_tool, body.suspect_parameter, body.signature),
    )

    return {
        "status": "success",
        "message": f"Successfully ingested {lot_id} into semiconductor cleanroom database",
        "lot_id": lot_id,
        "product_id": body.product_id,
        "defects_generated": len(defects_data),
        "primary_signature": body.signature,
        "final_yield_pct": body.final_yield_pct,
    }

