"""
Database initialization, transaction management, and batch ingestion for SQLite.
Reads contracts/schema.sql and provides robust data access for Person B, C, and D.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "bob_fab.db"
SCHEMA_SQL_PATH = Path(__file__).resolve().parent.parent / "contracts" / "schema.sql"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled and row factory set."""
    target_path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(target_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: Optional[Path] = None, schema_file: Optional[Path] = None) -> None:
    """Initialize database tables and indexes from schema.sql."""
    target_db = db_path or DEFAULT_DB_PATH
    target_schema = schema_file or SCHEMA_SQL_PATH

    with open(target_schema, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_connection(target_db)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def insert_synthetic_data(
    data: Dict[str, List[Dict[str, Any]]],
    db_path: Optional[Path] = None,
) -> Dict[str, int]:
    """
    Perform high-speed batch insertion of synthetic dataset inside an explicit transaction.
    Returns record counts per table.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()
    counts: Dict[str, int] = {}

    try:
        # Clear existing data
        cur.execute("DELETE FROM ground_truth_labels;")
        cur.execute("DELETE FROM defects;")
        cur.execute("DELETE FROM process_steps;")
        cur.execute("DELETE FROM wafer_lots;")

        # 1. Insert wafer_lots
        lots_data = [
            (
                l["lot_id"],
                l["product_id"],
                l["start_time"],
                l["fab_line"],
                l["final_yield_pct"],
                l["status"],
            )
            for l in data["wafer_lots"]
        ]
        cur.executemany(
            """
            INSERT INTO wafer_lots (lot_id, product_id, start_time, fab_line, final_yield_pct, status)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            lots_data,
        )
        counts["wafer_lots"] = len(lots_data)

        # 2. Insert ground_truth_labels
        gt_data = [
            (
                g["lot_id"],
                g["injected_cause_step"],
                g["injected_cause_tool_id"],
                g["injected_cause_parameter"],
                g["injected_signature"],
            )
            for g in data["ground_truth_labels"]
        ]
        cur.executemany(
            """
            INSERT INTO ground_truth_labels (lot_id, injected_cause_step, injected_cause_tool_id, injected_cause_parameter, injected_signature)
            VALUES (?, ?, ?, ?, ?);
            """,
            gt_data,
        )
        counts["ground_truth_labels"] = len(gt_data)

        # 3. Insert process_steps
        steps_data = [
            (
                p["lot_id"],
                p["step_name"],
                p["tool_id"],
                p["parameter_name"],
                p["value"],
                p["spec_min"],
                p["spec_max"],
                p["timestamp"],
            )
            for p in data["process_steps"]
        ]
        cur.executemany(
            """
            INSERT INTO process_steps (lot_id, step_name, tool_id, parameter_name, value, spec_min, spec_max, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            steps_data,
        )
        counts["process_steps"] = len(steps_data)

        # 4. Insert defects
        defects_data = [
            (
                d["lot_id"],
                d["wafer_id"],
                d["defect_type"],
                d["x"],
                d["y"],
                d["severity"],
                d["detected_at_step"],
            )
            for d in data["defects"]
        ]
        cur.executemany(
            """
            INSERT INTO defects (lot_id, wafer_id, defect_type, x, y, severity, detected_at_step)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            defects_data,
        )
        counts["defects"] = len(defects_data)

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return counts
