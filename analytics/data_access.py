"""Data Access Layer for Bob Fab Analytics Core.

Provides clean repository interface for reading wafer lots, process steps,
defects, and ground-truth validation labels from SQLite or in-memory fixtures.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Protocol, Tuple


class DataRepository(Protocol):
    """Protocol defining data access requirements for the Analytics Core."""

    def get_lot(self, lot_id: str) -> Optional[Dict[str, Any]]:
        ...

    def get_all_lots(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        ...

    def get_process_steps(
        self,
        lot_id: Optional[str] = None,
        step_name: Optional[str] = None,
        tool_id: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    def get_defects(self, lot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        ...

    def get_ground_truth_labels(self) -> List[Dict[str, Any]]:
        ...


class SQLiteRepository:
    """SQLite data repository reading fab tables populated by Person A."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_lot(self, lot_id: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM wafer_lots WHERE lot_id = ?", (lot_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_lots(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM wafer_lots WHERE status = ?", (status,))
            else:
                cursor.execute("SELECT * FROM wafer_lots")
            return [dict(row) for row in cursor.fetchall()]

    def get_process_steps(
        self,
        lot_id: Optional[str] = None,
        step_name: Optional[str] = None,
        tool_id: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return []
        query = "SELECT * FROM process_steps WHERE 1=1"
        params: List[Any] = []
        if lot_id:
            query += " AND lot_id = ?"
            params.append(lot_id)
        if step_name:
            query += " AND step_name = ?"
            params.append(step_name)
        if tool_id:
            query += " AND tool_id = ?"
            params.append(tool_id)
        if parameter_name:
            query += " AND parameter_name = ?"
            params.append(parameter_name)
        query += " ORDER BY timestamp ASC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_defects(self, lot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return []
        query = "SELECT * FROM defects"
        params: List[Any] = []
        if lot_id:
            query += " WHERE lot_id = ?"
            params.append(lot_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def get_ground_truth_labels(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if ground_truth_labels table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ground_truth_labels'")
            if not cursor.fetchone():
                return []
            cursor.execute("SELECT * FROM ground_truth_labels")
            return [dict(row) for row in cursor.fetchall()]


class InMemoryRepository:
    """In-memory data repository for testing, fixtures, and standalone analytics execution."""

    def __init__(
        self,
        lots: Optional[List[Dict[str, Any]]] = None,
        process_steps: Optional[List[Dict[str, Any]]] = None,
        defects: Optional[List[Dict[str, Any]]] = None,
        ground_truth_labels: Optional[List[Dict[str, Any]]] = None,
    ):
        self.lots: List[Dict[str, Any]] = lots or []
        self.process_steps: List[Dict[str, Any]] = process_steps or []
        self.defects: List[Dict[str, Any]] = defects or []
        self.ground_truth_labels: List[Dict[str, Any]] = ground_truth_labels or []

    def get_lot(self, lot_id: str) -> Optional[Dict[str, Any]]:
        for lot in self.lots:
            if lot.get("lot_id") == lot_id:
                return dict(lot)
        return None

    def get_all_lots(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status:
            return [dict(lot) for lot in self.lots if lot.get("status") == status]
        return [dict(lot) for lot in self.lots]

    def get_process_steps(
        self,
        lot_id: Optional[str] = None,
        step_name: Optional[str] = None,
        tool_id: Optional[str] = None,
        parameter_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for step in self.process_steps:
            if lot_id and step.get("lot_id") != lot_id:
                continue
            if step_name and step.get("step_name") != step_name:
                continue
            if tool_id and step.get("tool_id") != tool_id:
                continue
            if parameter_name and step.get("parameter_name") != parameter_name:
                continue
            results.append(dict(step))
        return results

    def get_defects(self, lot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if lot_id:
            return [dict(d) for d in self.defects if d.get("lot_id") == lot_id]
        return [dict(d) for d in self.defects]

    def get_ground_truth_labels(self) -> List[Dict[str, Any]]:
        return [dict(lbl) for lbl in self.ground_truth_labels]
