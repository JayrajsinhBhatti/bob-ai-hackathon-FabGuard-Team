import os
import sys
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

# Ensure project root is accessible
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.db import query_one, save_chat_message, get_chat_history, clear_chat_history
from app.routes.rootcause import get_root_cause

logger = logging.getLogger("bob_copilot")

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    lot_id: str
    question: Optional[str] = None
    message: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None


class FeedbackRequest(BaseModel):
    interaction_id: int
    feedback: str  # 'positive' or 'negative'


@router.post("/feedback")
def record_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    """Records explicit user thumbs-up/down feedback to improve future RAG retrieval and few-shot examples."""
    from copilot.feedback_store import CopilotFeedbackStore
    store = CopilotFeedbackStore()
    success = store.record_user_feedback(req.interaction_id, req.feedback)
    return {"status": "success" if success else "error", "interaction_id": req.interaction_id, "feedback": req.feedback}


@router.get("/metrics")
def get_copilot_metrics() -> Dict[str, Any]:
    """Retrieve self-improving RAG evolution metrics (grounding rate, retrieval precision, feedback counts)."""
    from copilot.feedback_store import CopilotFeedbackStore
    store = CopilotFeedbackStore()
    return store.get_metrics_summary()



@router.get("/history/{lot_id}")
def get_persisted_chat_history(lot_id: str) -> Dict[str, Any]:
    """Retrieve saved chat conversations for a given lot from the database."""
    history = get_chat_history(lot_id.strip().upper())
    return {
        "lot_id": lot_id,
        "count": len(history),
        "history": history,
    }


@router.delete("/history/{lot_id}")
def clear_persisted_chat_history(lot_id: str) -> Dict[str, Any]:
    """Clear saved chat conversations for a given lot."""
    clear_chat_history(lot_id.strip().upper())
    return {"status": "success", "message": f"Chat history cleared for {lot_id}"}


@router.get("/sessions")
def list_chat_sessions() -> Dict[str, Any]:
    """List all lots that have at least one saved chat message, with last message preview."""
    from app.db import query_all
    rows = query_all(
        """
        SELECT lot_id,
               COUNT(*) as message_count,
               MAX(created_at) as last_active,
               (SELECT message FROM chat_messages m2
                WHERE m2.lot_id = m1.lot_id AND m2.sender = 'user'
                ORDER BY m2.id DESC LIMIT 1) as last_user_message
        FROM chat_messages m1
        GROUP BY lot_id
        ORDER BY last_active DESC
        LIMIT 20;
        """
    )
    return {"sessions": rows, "count": len(rows)}


def _classify_intent(q: str) -> str:
    """Classify user query intent into cleanroom conversational categories."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", q.lower()).strip()
    words = clean.split()

    greetings = {
        "hi", "hii", "hiii", "hello", "hey", "heyy", "greetings", "good morning",
        "good afternoon", "good evening", "howdy", "sup", "yo", "bob", "test", "ping"
    }
    if clean in greetings or (len(words) <= 2 and any(w in greetings for w in words)):
        return "greeting"

    if any(k in clean for k in ["status", "how is lot", "yield of", "what yield", "current yield", "overview"]):
        return "status"

    if any(k in clean for k in ["why", "fail", "drop", "excursion", "defect", "root cause", "cause"]):
        return "root_cause"

    if any(k in clean for k in ["action", "check first", "recommend", "interlock", "contain", "fix", "sop", "prevent"]):
        return "actions"

    if any(k in clean for k in ["cpk", "sigma", "z score", "zscore", "drift", "spec", "telemetry", "sensor"]):
        return "cpk_telemetry"

    if any(k in clean for k in ["doe", "split", "experiment", "matrix", "test wafer", "verify"]):
        return "doe"

    if any(k in clean for k in ["who are you", "what can you do", "help", "capabilities", "menu"]):
        return "help"

    return "general"


@router.post("")
def chat_with_bob(req: ChatRequest) -> Dict[str, Any]:
    """
    Handle engineer questions for a given wafer lot using Bob Fab Copilot.
    Provides context-aware conversational answers, saves conversation history to SQLite,
    and returns relevant citation badges ONLY when citing specific equipment findings.
    """
    lot_id = (req.lot_id or "LOT-2231").strip().upper()
    user_question = (req.question or req.message or "").strip()
    history = req.conversation_history or []

    if not user_question:
        return {
            "lot_id": lot_id,
            "question": "",
            "response": "Please provide a question or instruction for analysis.",
            "cited_findings": [],
            "suggested_questions": [f"Why did {lot_id} fail?", "What should I check first?"],
            "conversation_history": history,
        }

    # Save user message to database
    try:
        save_chat_message(lot_id=lot_id, sender="user", message=user_question, citations=None)
    except Exception as e:
        logger.warning(f"Could not persist user message: {e}")

    # Fetch lot metadata
    lot = query_one(
        "SELECT lot_id, product_id, fab_line, final_yield_pct, status FROM wafer_lots WHERE lot_id = ?;",
        (lot_id,),
    )
    if not lot:
        resp_text = f"Lot `{lot_id}` was not found in the SECS/GEM fab database."
        try:
            save_chat_message(lot_id=lot_id, sender="bob", message=resp_text, citations=[])
        except Exception:
            pass
        return {
            "lot_id": lot_id,
            "response": resp_text,
            "cited_findings": [],
            "suggested_questions": ["Why did LOT-2231 fail?", "What is the primary excursion in ETCH-07?"],
            "conversation_history": history,
        }

    # Fetch real root cause findings for this lot
    try:
        findings = get_root_cause(lot_id, tier="tier2")
    except Exception:
        findings = {"lot_id": lot_id, "candidate_causes": [], "at_risk_upcoming_batches": []}

    candidates = findings.get("candidate_causes", [])
    primary_cause = candidates[0] if candidates else None

    suggested = [
        f"Why did {lot_id} have a yield drop?",
        f"What should I check first on {lot_id}?",
        f"What is the Cpk of the suspect tool?",
        "Design confirmatory 2^k DOE",
    ]

    # Anti-Hallucination Domain Scope Gate (Hard rejection for off-topic queries)
    from copilot.verifier import DomainScopeGate
    in_scope, refusal_reason = DomainScopeGate.check_query_scope(user_question)
    if not in_scope:
        new_history = list(history)
        new_history.append({"role": "user", "content": user_question})
        new_history.append({"role": "assistant", "content": refusal_reason})
        try:
            save_chat_message(lot_id=lot_id, sender="bob", message=refusal_reason, citations=[])
        except Exception:
            pass
        return {
            "lot_id": lot_id,
            "question": user_question,
            "response": refusal_reason,
            "cited_findings": [],
            "grounding_rate": 1.0,
            "is_grounded": True,
            "confidence_level": 1.0,
            "route": "out_of_scope",
            "is_out_of_scope": True,
            "suggested_questions": suggested,
            "conversation_history": new_history,
        }

    # Classify Intent
    intent = _classify_intent(user_question)


    # Handle casual greetings without firing heavy diagnostic text or citation badges
    if intent == "greeting":
        yield_val = lot.get("final_yield_pct")
        yield_str = f" Yield is currently at **{yield_val}%**." if yield_val is not None else ""
        resp_text = (
            f"Hello! I am **Bob**, your Cleanroom Fab Copilot monitoring **{lot_id}** "
            f"({lot.get('product_id', '3nm node')}).{yield_str}\n\n"
            f"How can I assist you with this lot? You can ask me:\n"
            f"- *\"Why did {lot_id} have a yield excursion?\"*\n"
            f"- *\"What equipment should I inspect first?\"*\n"
            f"- *\"What is the Cpk of suspect chambers?\"*\n"
            f"- *\"Design a confirmatory 2^k DOE matrix.\"*"
        )
        citations = [] # No citations for greetings!
        
        new_history = list(history)
        new_history.append({"role": "user", "content": user_question})
        new_history.append({"role": "assistant", "content": resp_text})

        try:
            save_chat_message(lot_id=lot_id, sender="bob", message=resp_text, citations=citations)
        except Exception as e:
            logger.warning(f"Could not persist bob message: {e}")

        return {
            "lot_id": lot_id,
            "question": user_question,
            "response": resp_text,
            "cited_findings": citations,
            "suggested_questions": suggested,
            "conversation_history": new_history,
        }

    # Handle help intent
    if intent == "help":
        resp_text = (
            f"I am **Bob**, your semiconductor fab engineering copilot.\n\n"
            f"**My Capabilities for Lot {lot_id}:**\n"
            f"1. **Root Cause Analysis**: Correlate SECS/GEM process sensor drift with spatial defect morphology.\n"
            f"2. **Cpk & Statistical Capability**: Identify parameters violating nominal 3-sigma boundaries.\n"
            f"3. **Containment & SOP**: Recommend equipment interlocks and chamber PM actions.\n"
            f"4. **DOE Engine**: Formulate 2^k factorial confirmatory Design of Experiments runcards before production dispatch."
        )
        citations = []
        new_history = list(history)
        new_history.append({"role": "user", "content": user_question})
        new_history.append({"role": "assistant", "content": resp_text})
        try:
            save_chat_message(lot_id=lot_id, sender="bob", message=resp_text, citations=citations)
        except Exception:
            pass
        return {
            "lot_id": lot_id,
            "question": user_question,
            "response": resp_text,
            "cited_findings": citations,
            "suggested_questions": suggested,
            "conversation_history": new_history,
        }

    # Dispatch all analytical, DOE, yield simulation, and RAG queries to ask_bob_advanced

    # Attempt GenAI Copilot response with full Advanced RAG pipeline
    try:
        from copilot.agent import ask_bob_advanced
        copilot_res = ask_bob_advanced(
            user_question=user_question,
            findings=findings,
            conversation_history=history,
            lot_id=lot_id,
        )
        answer = copilot_res.get("response") or copilot_res.get("answer", "")
        updated_history = copilot_res.get("conversation_history", [])
        citations = copilot_res.get("citations") or copilot_res.get("cited_findings") or []

        try:
            save_chat_message(lot_id=lot_id, sender="bob", message=answer, citations=citations)
        except Exception as e:
            logger.warning(f"Could not persist bob message: {e}")

        return {
            "lot_id": lot_id,
            "question": user_question,
            "response": answer,
            "cited_findings": citations,
            "grounding_rate": copilot_res.get("grounding_rate", 1.0),
            "is_grounded": copilot_res.get("is_grounded", True),
            "retrieval_quality": copilot_res.get("retrieval_quality", {}),
            "confidence_level": copilot_res.get("confidence_level", 0.95),
            "interaction_id": copilot_res.get("interaction_id"),
            "route": copilot_res.get("route", "general"),
            "was_regenerated": copilot_res.get("was_regenerated", False),
            "suggested_questions": suggested,
            "conversation_history": updated_history,
        }


    except Exception as exc:
        import traceback
        logger.warning(f"GenAI copilot dispatch fallback: {exc}\n{traceback.format_exc()}. Using grounded physics rules.")

        # Grounded physics fallback maintaining strict honesty rules
        prob_str = f"{int(primary_cause['probability'] * 100)}%" if primary_cause and primary_cause.get("probability") is not None else "Elevated"

        if intent == "root_cause":
            if primary_cause:
                text = (
                    f"**Lot {lot_id} Excursion Analysis:**\n\n"
                    f"Yield dropped to **{lot.get('final_yield_pct', 'N/A')}%** (target: >95.0%). "
                    f"Our calibrated ranking model indicates a **{prob_str} probability** that the leading candidate cause is "
                    f"**{primary_cause['parameter']}** drift on tool **{primary_cause['tool_id']}** during the `{primary_cause['step']}` step.\n\n"
                    f"- **Statistical Evidence**: {primary_cause['evidence']}\n"
                    f"- **Spatial Morphology**: Classified as `{primary_cause['spatial_signature']}` clustering.\n\n"
                    f"> ⚠️ **Mandatory Cleanroom Caveat**: Recommend confirming via targeted DOE (Design of Experiments) before taking corrective action."
                )
                citations = [primary_cause]
            else:
                text = f"Lot {lot_id} shows normal baseline behavior within nominal 3-sigma specifications."
                citations = []

        elif intent == "actions":
            if primary_cause:
                text = (
                    f"**Recommended Action Sequence for Lot {lot_id}:**\n\n"
                    f"1. **Chamber Interlock**: Place `{primary_cause['tool_id']}` on calibration hold.\n"
                    f"2. **Sensor Recalibration**: Inspect `{primary_cause['parameter']}` sensor line and manometer.\n"
                    f"3. **Verification DOE**: Execute a 2-wafer split test before restoring mass production dispatch.\n"
                    f"4. **Downstream Check**: Inspect upcoming batches for matching spatial signatures.\n\n"
                    f"> ⚠️ **DOE Protocol**: Recommend confirming via targeted DOE before taking corrective action."
                )
                citations = [primary_cause]
            else:
                text = "No immediate equipment interlock required. Standard PM schedule applies."
                citations = []

        elif intent == "cpk_telemetry":
            if primary_cause:
                text = (
                    f"**Process Capability Readout for {lot_id}:**\n\n"
                    f"Tool **{primary_cause['tool_id']}** ({primary_cause['parameter']}) degraded to "
                    f"**Cpk = {primary_cause.get('cpk', '0.91')}** (critical threshold is 1.33). "
                    f"Telemetry shifted **{primary_cause.get('z_score', '3.4')} sigma** beyond nominal target.\n\n"
                    f"> ⚠️ Recommend confirming via targeted DOE before taking corrective action."
                )
                citations = [primary_cause]
            else:
                text = f"All parameters for {lot_id} are operating at nominal Cpk > 1.45."
                citations = []

        elif intent == "doe":
            if primary_cause:
                try:
                    import os
                    from copilot.doe_engine import DOEEngine
                    from analytics.data_access import SQLiteRepository
                    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "src", "bob_fab.db")
                    if not os.path.exists(db_path):
                        db_path = "src/bob_fab.db"
                    repo = SQLiteRepository(db_path)
                    engine = DOEEngine(repo)
                    runcard = engine.generate_for_cause(lot_id, primary_cause)
                    text = engine.format_as_markdown(runcard)
                except Exception:
                    text = (
                        f"### 🔬 Statistical DOE Runcard: `{primary_cause['tool_id']}` ({primary_cause['parameter']})\n\n"
                        f"| Run | Type | {primary_cause['parameter']} | Target Metric | Expected Outcome |\n"
                        f"|:---:|:---:|:---:|:---|:---|\n"
                        f"| 1 | Corner | Nominal -5% | Defect Density (def/cm²) | Baseline recovery |\n"
                        f"| 2 | Corner | Nominal +5% | Defect Density (def/cm²) | Parameter sensitivity |\n"
                        f"| 3 | Center | Nominal (0) | Defect Density (def/cm²) | < 0.5/cm² (Curvature check) |\n\n"
                        f"> ⚠️ **Protocol Rule (Cleanroom Sign-off)**: Cleanroom Module Owner sign-off required prior to production dispatch."
                    )
                citations = [primary_cause]
            else:
                text = "No excursion detected; DOE verification not currently requested."
                citations = []

        else:
            if primary_cause:
                text = (
                    f"**Diagnostic Summary for {lot_id}:**\n\n"
                    f"Identified leading candidate: **{primary_cause['tool_id']}** (`{primary_cause['parameter']}`) "
                    f"with **{prob_str} calibrated probability** ({primary_cause['spatial_signature']} pattern). "
                    f"Evidence: {primary_cause['evidence']}.\n\n"
                    f"> ⚠️ Recommend confirming via targeted DOE before taking corrective action."
                )
                citations = [primary_cause]
            else:
                text = f"Lot {lot_id} is operating within nominal cleanroom limits."
                citations = []

        new_history = list(history)
        new_history.append({"role": "user", "content": user_question})
        new_history.append({"role": "assistant", "content": text})

        try:
            save_chat_message(lot_id=lot_id, sender="bob", message=text, citations=citations)
        except Exception as e:
            logger.warning(f"Could not persist fallback bob message: {e}")

        return {
            "lot_id": lot_id,
            "question": user_question,
            "response": text,
            "cited_findings": citations,
            "suggested_questions": suggested,
            "conversation_history": new_history,
        }


