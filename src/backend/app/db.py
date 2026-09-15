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


def init_chat_tables(db_path: Optional[Path] = None) -> None:
    """Ensure the chat_messages table exists in SQLite database."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                citations_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_lot_id ON chat_messages(lot_id);")
        conn.commit()
    finally:
        conn.close()


def save_chat_message(lot_id: str, sender: str, message: str, citations: Optional[List[Dict[str, Any]]] = None) -> int:
    """Save a chat message from either user or bob into the database."""
    import json
    citations_json = json.dumps(citations) if citations else None
    return execute_write(
        """
        INSERT INTO chat_messages (lot_id, sender, message, citations_json)
        VALUES (?, ?, ?, ?);
        """,
        (lot_id, sender, message, citations_json),
    )


def get_chat_history(lot_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve chat history for a lot ordered chronologically."""
    import json
    rows = query_all(
        """
        SELECT id, lot_id, sender, message, citations_json, created_at
        FROM chat_messages
        WHERE lot_id = ?
        ORDER BY id ASC
        LIMIT ?;
        """,
        (lot_id, limit),
    )
    results = []
    for r in rows:
        citations = []
        if r.get("citations_json"):
            try:
                citations = json.loads(r["citations_json"])
            except Exception:
                citations = []
        results.append({
            "id": r["id"],
            "lot_id": r["lot_id"],
            "sender": r["sender"],
            "message": r["message"],
            "citations": citations,
            "created_at": r["created_at"],
        })
    return results


def clear_chat_history(lot_id: str) -> None:
    """Clear chat history for a given lot."""
    execute_write("DELETE FROM chat_messages WHERE lot_id = ?;", (lot_id,))


# Auto-initialize chat tables on import
try:
    init_chat_tables()
except Exception:
    pass

