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


def init_copilot_feedback_tables(db_path: Optional[Path] = None) -> None:
    """Ensure copilot_feedback and kb_stubs tables exist for self-improving RAG."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS copilot_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT,
                query TEXT NOT NULL,
                rewritten_query TEXT,
                route TEXT,
                retrieved_doc_ids TEXT,
                answer TEXT,
                grounding_rate REAL,
                retrieval_precision REAL,
                retrieval_recall REAL,
                context_utilization REAL,
                user_feedback TEXT,
                was_regenerated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kb_stubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_step TEXT NOT NULL,
                parameter TEXT NOT NULL,
                stub_sop TEXT NOT NULL,
                source_query TEXT,
                times_cited INTEGER DEFAULT 0,
                promoted BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_lot ON copilot_feedback(lot_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_route ON copilot_feedback(route);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stubs_step_param ON kb_stubs(process_step, parameter);")
        conn.commit()
    finally:
        conn.close()


def save_copilot_feedback(
    lot_id: str,
    query: str,
    answer: str,
    rewritten_query: str = None,
    route: str = None,
    retrieved_doc_ids: List[str] = None,
    grounding_rate: float = None,
    retrieval_precision: float = None,
    retrieval_recall: float = None,
    context_utilization: float = None,
    was_regenerated: bool = False,
) -> int:
    """Store a copilot interaction's quality metrics for self-improvement."""
    import json
    doc_ids_json = json.dumps(retrieved_doc_ids) if retrieved_doc_ids else None
    return execute_write(
        """
        INSERT INTO copilot_feedback
            (lot_id, query, rewritten_query, route, retrieved_doc_ids, answer,
             grounding_rate, retrieval_precision, retrieval_recall,
             context_utilization, was_regenerated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (lot_id, query, rewritten_query, route, doc_ids_json, answer,
         grounding_rate, retrieval_precision, retrieval_recall,
         context_utilization, 1 if was_regenerated else 0),
    )


def save_user_feedback(feedback_id: int, feedback: str) -> None:
    """Store explicit user thumbs-up/down for a copilot response."""
    execute_write(
        "UPDATE copilot_feedback SET user_feedback = ? WHERE id = ?;",
        (feedback, feedback_id),
    )


def get_gold_examples(limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve high-quality past interactions for few-shot prompting."""
    return query_all(
        """
        SELECT query, answer, grounding_rate, route
        FROM copilot_feedback
        WHERE grounding_rate >= 0.95
          AND context_utilization >= 0.6
          AND (user_feedback IS NULL OR user_feedback = 'positive')
          AND was_regenerated = 0
        ORDER BY created_at DESC
        LIMIT ?;
        """,
        (limit,),
    )


def get_feedback_stats() -> Dict[str, Any]:
    """Get aggregate feedback statistics for self-improvement tuning."""
    row = query_one(
        """
        SELECT COUNT(*) as total,
               AVG(grounding_rate) as avg_grounding,
               AVG(retrieval_precision) as avg_precision,
               AVG(retrieval_recall) as avg_recall,
               AVG(context_utilization) as avg_utilization,
               SUM(CASE WHEN was_regenerated = 1 THEN 1 ELSE 0 END) as regenerated_count,
               SUM(CASE WHEN user_feedback = 'positive' THEN 1 ELSE 0 END) as positive_count,
               SUM(CASE WHEN user_feedback = 'negative' THEN 1 ELSE 0 END) as negative_count
        FROM copilot_feedback;
        """
    )
    return dict(row) if row else {}


def save_kb_stub(process_step: str, parameter: str, stub_sop: dict, source_query: str = None) -> int:
    """Store an auto-generated SOP stub for a knowledge gap."""
    import json
    return execute_write(
        """
        INSERT INTO kb_stubs (process_step, parameter, stub_sop, source_query)
        VALUES (?, ?, ?, ?);
        """,
        (process_step, parameter, json.dumps(stub_sop), source_query),
    )


def get_kb_stubs(promoted_only: bool = False) -> List[Dict[str, Any]]:
    """Retrieve knowledge base stubs, optionally only promoted ones."""
    import json
    where = "WHERE promoted = 1" if promoted_only else ""
    rows = query_all(f"SELECT * FROM kb_stubs {where} ORDER BY times_cited DESC;")
    for r in rows:
        if r.get("stub_sop"):
            try:
                r["stub_sop"] = json.loads(r["stub_sop"])
            except Exception:
                pass
    return rows


def increment_stub_citation(stub_id: int) -> None:
    """Increment the citation count for a KB stub."""
    execute_write("UPDATE kb_stubs SET times_cited = times_cited + 1 WHERE id = ?;", (stub_id,))


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


# Auto-initialize tables on import
try:
    init_chat_tables()
except Exception:
    pass

try:
    init_copilot_feedback_tables()
except Exception:
    pass

