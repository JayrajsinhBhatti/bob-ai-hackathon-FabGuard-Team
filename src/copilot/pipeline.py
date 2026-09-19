"""
copilot/pipeline.py  —  Step 7: Integration Entry Point (§6)

Wires the Analytics Core (Person B) to the GenAI Copilot (Person C).
This is the function Person D's backend (/backend) calls for the
/copilot and /chat API endpoints.

Usage (after Person B merges feature/analytics-integrated into dev):
    from copilot.pipeline import full_copilot_analysis
    result = full_copilot_analysis(lot_id="LOT-2231")

Until Person B's analytics are merged, pass pre-loaded findings directly
via full_copilot_analysis_from_findings(findings).

Source: §6 (Step 7) of Person C Guide / S1_FINAL_Implementation_Plan_v3.md
"""

import json
import os
import sys
from typing import Any

# Ensure the repo root is importable when running this module directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot.config import get_llm_client
from copilot.explainer import explain_lot_findings
from copilot.recommender import generate_recommendations
from copilot.agent import ask_bob_single, create_bob_session


# ---------------------------------------------------------------------------
# Primary integration entry point (requires Person B's analytics)
# ---------------------------------------------------------------------------

def full_copilot_analysis(lot_id: str, db_path: str = None) -> dict:
    """
    End-to-end pipeline: run analytics → generate all copilot outputs for a lot.

    Requires: analytics.pipeline.analyze_lot (Person B's feature merged into dev).

    Args:
        lot_id:  The wafer lot identifier (e.g. "LOT-2231").
        db_path: Optional path to the SQLite database. Defaults to analytics default.

    Returns:
        {
            "lot_id": "LOT-2231",
            "findings": { ... raw root_cause_findings ... },
            "explanations": { ... explain_lot_findings output ... },
            "recommendations": [ ... per-cause recommendation dicts ... ],
        }
    """
    try:
        from analytics.pipeline import analyze_lot
    except ImportError:
        raise ImportError(
            "analytics.pipeline is not yet available. "
            "Use full_copilot_analysis_from_findings() with fixture data until "
            "Person B's feature/analytics-integrated branch is merged into dev."
        )

    findings = analyze_lot(lot_id, db_path=db_path, include_v3_fields=True)
    return _run_copilot_on_findings(findings)


# ---------------------------------------------------------------------------
# Fixture / fallback entry point (works without Person B's analytics)
# ---------------------------------------------------------------------------

def full_copilot_analysis_from_findings(findings: dict) -> dict:
    """
    Run all copilot components directly against a pre-loaded findings dict.

    Use this for:
      - Development and testing against contract fixture files.
      - Backend endpoints before analytics integration is complete.
      - Unit tests in copilot/tests/.

    Args:
        findings: A root_cause_findings dict (from fixture JSON or analytics).

    Returns:
        Same structure as full_copilot_analysis().
    """
    return _run_copilot_on_findings(findings)


def full_copilot_analysis_from_fixture(fixture_path: str) -> dict:
    """
    Convenience wrapper to load a fixture JSON file and run the full pipeline.

    Args:
        fixture_path: Absolute or relative path to a findings fixture JSON.

    Returns:
        Same structure as full_copilot_analysis().
    """
    with open(fixture_path, "r", encoding="utf-8") as f:
        findings = json.load(f)
    return full_copilot_analysis_from_findings(findings)


# ---------------------------------------------------------------------------
# Internal shared pipeline logic
# ---------------------------------------------------------------------------

def _run_copilot_on_findings(findings: dict) -> dict:
    """
    Core copilot pipeline — shared by both integration paths.
    Creates one shared LLM client for efficiency (avoids repeated auth calls).
    """
    client = get_llm_client()
    lot_id = findings.get("lot_id", "UNKNOWN")

    # Step 1: Explanation Generator
    explanations = explain_lot_findings(findings, client=client)

    # Step 2: Recommendation Generator (one per candidate cause)
    recommendations = []
    for cause in findings.get("candidate_causes", []):
        rec = generate_recommendations(cause, client=client, lot_id=lot_id)
        recommendations.append(rec)

    return {
        "lot_id": lot_id,
        "findings": findings,
        "explanations": explanations,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Chat endpoint helper
# ---------------------------------------------------------------------------

def copilot_chat(
    user_question: str,
    findings: dict,
    conversation_history: list = None,
    client: Any = None,
) -> dict:
    """
    Chat endpoint helper for Person D's /chat FastAPI route.

    Supports stateless (single-turn) and stateful (multi-turn) modes.

    Args:
        user_question:        The engineer's natural language question.
        findings:             The root_cause_findings dict for the lot.
        conversation_history: Optional messages list from a previous call
                              (enables multi-turn conversation).
        client:               Optional pre-built LLM client.

    Returns:
        {
            "answer": "...",
            "conversation_history": [ updated messages list for next call ]
        }
    """
    from copilot.agent import ask_bob, create_bob_session

    if client is None:
        try:
            client = get_llm_client()
        except Exception:
            client = None

    if conversation_history:
        messages = conversation_history
    else:
        messages = create_bob_session(findings)

    answer, updated_history = ask_bob(messages, user_question, client=client)

    return {
        "answer": answer,
        "conversation_history": updated_history,
    }


# ---------------------------------------------------------------------------
# CLI quick-test (run with: python -m copilot.pipeline)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _FIXTURE = os.path.join(_REPO_ROOT, "contracts", "mock_findings_LOT-2231.json")

    print("=" * 60)
    print("Running copilot pipeline against Tier 2 fixture...")
    print("=" * 60)

    result = full_copilot_analysis_from_fixture(_FIXTURE)

    print(f"\nLot: {result['lot_id']}")
    print(f"\n--- Explanations ---")
    for expl in result["explanations"]["explanations"]:
        print(f"\nRank #{expl['rank']}: {expl['step']} / {expl['tool_id']} / {expl['parameter']}")
        print(f"  {expl['explanation']}")
        print(f"  ⚠️  {expl['doe_caveat']}")

    print(f"\n--- Recommendations ---")
    for rec in result["recommendations"]:
        print(f"\n{rec['tool_id']} / {rec['parameter']} → {rec['category']}")
        print(f"  {rec['phrased_recommendation']}")

    print(f"\n--- At-Risk Batches ---")
    print(f"  {result['explanations']['at_risk_batch_summary']}")

    print("\n--- Ask Bob: Why did LOT-2231 fail? ---")
    answer = ask_bob_single(
        "Why did LOT-2231 fail and what should we do?",
        result["findings"],
    )
    print(f"  Bob: {answer}")
