"""
Database connection and query helpers for the FastAPI backend.
Connects directly to Person A's SQLite database (bob_fab.db).
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

# Root bob_fab.db path
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "bob_fab.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return a configured SQLite connection with row factory enabled."""
    target_path = db_path or DEFAULT_DB_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Database file not found at {target_path}")
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def query_all(query: str, params: tuple = (), db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Execute a query and return all results as dictionaries."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def query_one(query: str, params: tuple = (), db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Execute a query and return a single result as a dictionary, or None."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def execute_write(query: str, params: tuple = (), db_path: Optional[Path] = None) -> int:
    """Execute an INSERT/UPDATE/DELETE query and commit changes."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def execute_many(query: str, params_list: List[tuple], db_path: Optional[Path] = None) -> None:
    """Execute batch writes with executemany and commit."""
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.executemany(query, params_list)
        conn.commit()
    finally:
        conn.close()

