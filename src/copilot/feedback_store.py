"""
copilot/feedback_store.py — Advanced RAG: Self-Improving Feedback Loop

Stores copilot interactions and provides continuous self-improvement signals:
  1. Records interaction performance: route, grounding rate, retrieval metrics, regeneration status
  2. Gold Examples Store: retrieves high-quality past interactions (100% grounded) for dynamic few-shot prompting
  3. Knowledge Gap Detection: flags queries with zero or irrelevant retrieval and creates SOP stub candidates in `kb_stubs`
  4. User Feedback Integration: accepts explicit thumbs-up / thumbs-down ratings
  5. Feedback Consolidation: calculates overall quality metrics, average grounding, and retrieval performance
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.db import get_connection, init_copilot_feedback_tables

logger = logging.getLogger("copilot.feedback_store")


class CopilotFeedbackStore:
    """
    Manages continuous learning and telemetry for FabGuard Copilot.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        # Ensure database tables exist
        try:
            init_copilot_feedback_tables(db_path)
        except Exception as e:
            logger.warning(f"Could not initialize feedback tables: {e}")

    def record_interaction(
        self,
        query: str,
        answer: str,
        lot_id: Optional[str] = None,
        rewritten_query: Optional[str] = None,
        route: Optional[str] = None,
        retrieved_doc_ids: Optional[List[str]] = None,
        grounding_rate: float = 1.0,
        retrieval_precision: float = 1.0,
        retrieval_recall: float = 1.0,
        context_utilization: float = 1.0,
        was_regenerated: bool = False,
    ) -> Optional[int]:
        """
        Records a completed RAG interaction in the SQLite store.
        Returns the inserted record ID.
        """
        conn = get_connection(self.db_path)
        doc_ids_json = json.dumps(retrieved_doc_ids or [])
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO copilot_feedback (
                    lot_id, query, rewritten_query, route, retrieved_doc_ids,
                    answer, grounding_rate, retrieval_precision, retrieval_recall,
                    context_utilization, was_regenerated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    lot_id,
                    query,
                    rewritten_query,
                    route,
                    doc_ids_json,
                    answer,
                    grounding_rate,
                    retrieval_precision,
                    retrieval_recall,
                    context_utilization,
                    1 if was_regenerated else 0,
                ),
            )
            conn.commit()
            record_id = cur.lastrowid

            # Knowledge gap detection: if query was fab/sop-related but retrieved nothing or low recall
            if route in ("sop_retrieval", "findings_grounded") and (not retrieved_doc_ids or retrieval_recall < 0.2):
                self._record_knowledge_gap_candidate(query, lot_id)

            return record_id
        except Exception as e:
            logger.error(f"Failed to record copilot interaction: {e}")
            return None
        finally:
            conn.close()

    def record_user_feedback(self, interaction_id: int, feedback: str) -> bool:
        """
        Updates an interaction with user feedback ('positive' or 'negative').
        """
        if feedback not in ("positive", "negative"):
            return False
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                "UPDATE copilot_feedback SET user_feedback = ? WHERE id = ?",
                (feedback, interaction_id),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to record user feedback: {e}")
            return False
        finally:
            conn.close()

    def get_gold_examples(self, limit: int = 3) -> List[Dict[str, str]]:
        """
        Retrieves top performing past interactions (high grounding and positive/neutral feedback)
        to act as dynamic few-shot learning references.
        """
        conn = get_connection(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT query, answer FROM copilot_feedback
                WHERE grounding_rate >= 0.95
                  AND (user_feedback IS NULL OR user_feedback = 'positive')
                  AND was_regenerated = 0
                  AND length(answer) > 40
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [{"query": row[0], "answer": row[1]} for row in rows]
        except Exception as e:
            logger.warning(f"Failed to fetch gold examples: {e}")
            return []
        finally:
            conn.close()

    def _record_knowledge_gap_candidate(self, query: str, lot_id: Optional[str] = None):
        """
        Creates a draft SOP stub when a fab query could not be grounded by existing documentation.
        """
        conn = get_connection(self.db_path)
        try:
            cur = conn.cursor()
            stub_content = {
                "title": f"Auto-Generated Stub for: {query[:50]}",
                "equipment_type": "Unknown / Pending Triage",
                "action": "Investigate recurring inquiry; author definitive fab SOP.",
                "source_lot": lot_id or "N/A",
                "created_at": datetime.utcnow().isoformat(),
            }
            cur.execute(
                """
                INSERT INTO kb_stubs (process_step, parameter, stub_sop, source_query, times_cited, promoted)
                VALUES (?, ?, ?, ?, 1, 0)
                """,
                ("UNCLASSIFIED", "UNCLASSIFIED", json.dumps(stub_content), query),
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"Could not record knowledge gap stub: {e}")
        finally:
            conn.close()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Aggregates system-wide self-improving RAG evolution metrics.
        """
        conn = get_connection(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM copilot_feedback")
            total_interactions = cur.fetchone()[0] or 0

            if total_interactions == 0:
                return {
                    "total_interactions": 0,
                    "avg_grounding_rate": 1.0,
                    "avg_retrieval_precision": 1.0,
                    "avg_context_utilization": 1.0,
                    "positive_feedback_count": 0,
                    "negative_feedback_count": 0,
                    "regeneration_rate": 0.0,
                    "active_stubs_count": 0,
                }

            cur.execute(
                """
                SELECT
                    AVG(grounding_rate),
                    AVG(retrieval_precision),
                    AVG(context_utilization),
                    SUM(CASE WHEN user_feedback = 'positive' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN user_feedback = 'negative' THEN 1 ELSE 0 END),
                    AVG(CASE WHEN was_regenerated = 1 THEN 1.0 ELSE 0.0 END)
                FROM copilot_feedback
                """
            )
            row = cur.fetchone()

            cur.execute("SELECT COUNT(*) FROM kb_stubs")
            active_stubs = cur.fetchone()[0] or 0

            return {
                "total_interactions": total_interactions,
                "avg_grounding_rate": round(row[0] or 0.0, 4),
                "avg_retrieval_precision": round(row[1] or 0.0, 4),
                "avg_context_utilization": round(row[2] or 0.0, 4),
                "positive_feedback_count": int(row[3] or 0),
                "negative_feedback_count": int(row[4] or 0),
                "regeneration_rate": round(row[5] or 0.0, 4),
                "active_stubs_count": active_stubs,
            }
        except Exception as e:
            logger.error(f"Error calculating feedback metrics: {e}")
            return {}
        finally:
            conn.close()
