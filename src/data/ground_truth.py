"""
Ground-truth query helpers and validation access layer for Person B (Analytics Core).
Provides access to hidden ground-truth labels used exclusively for validation testing.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from data.db import DEFAULT_DB_PATH, get_connection


def get_ground_truth_dataframe(db_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Retrieve all ground-truth scenario records into a pandas DataFrame.
    Used by /analytics/validate.py to compute Top-1 and Top-3 accuracy.
    """
    conn = get_connection(db_path or DEFAULT_DB_PATH)
    try:
        query = """
        SELECT 
            gt.lot_id,
            gt.injected_cause_step,
            gt.injected_cause_tool_id,
            gt.injected_cause_parameter,
            gt.injected_signature,
            l.product_id,
            l.final_yield_pct,
            l.start_time
        FROM ground_truth_labels gt
        JOIN wafer_lots l ON gt.lot_id = l.lot_id;
        """
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()


def get_ground_truth_for_lot(lot_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve injected ground-truth label for a single lot, if one was injected."""
    conn = get_connection(db_path or DEFAULT_DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT injected_cause_step, injected_cause_tool_id, injected_cause_parameter, injected_signature
            FROM ground_truth_labels
            WHERE lot_id = ?;
            """,
            (lot_id,),
        )
        row = cur.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()
