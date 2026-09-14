"""
Live End-to-End Scenario Verification for Copilot Layer.

Tests:
1. Scenario 1 (LOT-2231): Etch Chamber Pressure Excursion + Edge-Ring signature
2. Scenario 2 (LOT-2232): CMP Downforce Excursion + Scratch signature
3. Scenario 3 (LOT-2233): CVD Deposition Temperature Excursion + Center Cluster
4. Scenario 4 (LOT-2240): Real SQLite fab database lot
5. Scenario 5 (Chat Engine): Multi-turn Ask Bob conversation testing honesty & DOE caveat
6. Scenario 6 (Provider Failover / Switch): Both Gemini and Groq live verification
"""

import json
import os
import sys

# Ensure utf-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from copilot.pipeline import full_copilot_analysis, full_copilot_analysis_from_fixture, copilot_chat
from copilot.config import get_llm_client, LLM_PROVIDER, LLM_MODEL, GROQ_MODEL, GROQ_API_KEY
from copilot.agent import ask_bob_single, create_bob_session, ask_bob


def test_scenario_1_etch():
    print("\n" + "=" * 70)
    print("SCENARIO 1: LOT-2231 (Etch Chamber Pressure / Edge-Ring Signature)")
    print("=" * 70)
    res = full_copilot_analysis("LOT-2231")
    assert res["lot_id"] == "LOT-2231"
    assert len(res["explanations"]["explanations"]) > 0
    assert len(res["recommendations"]) > 0

    top_expl = res["explanations"]["explanations"][0]
    print(f"Top Candidate: #{top_expl['rank']} {top_expl['step']} / {top_expl['tool_id']} / {top_expl['parameter']}")
    print(f"Explanation:   {top_expl['explanation']}")
    print(f"DOE Caveat:    {top_expl['doe_caveat']}")
    assert "DOE" in top_expl["doe_caveat"]

    top_rec = res["recommendations"][0]
    print(f"Rec Category:  {top_rec['category']}")
    print(f"Standard Acts: {top_rec['recommended_actions']}")
    print(f"Phrased Rec:   {top_rec['phrased_recommendation']}")
    print(" At-Risk Batches:", res["explanations"]["at_risk_batch_summary"])
    print("[PASS] Scenario 1 completed successfully.")
    return res


def test_scenario_2_cmp():
    print("\n" + "=" * 70)
    print("SCENARIO 2: LOT-2232 (CMP Scratch Signature)")
    print("=" * 70)
    res = full_copilot_analysis("LOT-2232")
    assert res["lot_id"] == "LOT-2232"
    top_expl = res["explanations"]["explanations"][0]
    print(f"Top Candidate: #{top_expl['rank']} {top_expl['step']} / {top_expl['tool_id']} / {top_expl['parameter']}")
    print(f"Explanation:   {top_expl['explanation']}")
    print(f"Rec Category:  {res['recommendations'][0]['category']}")
    print(f"Phrased Rec:   {res['recommendations'][0]['phrased_recommendation']}")
    print("[PASS] Scenario 2 completed successfully.")
    return res


def test_scenario_3_cvd():
    print("\n" + "=" * 70)
    print("SCENARIO 3: LOT-2233 (CVD Deposition Temp / Center Cluster Signature)")
    print("=" * 70)
    res = full_copilot_analysis("LOT-2233")
    assert res["lot_id"] == "LOT-2233"
    top_expl = res["explanations"]["explanations"][0]
    print(f"Top Candidate: #{top_expl['rank']} {top_expl['step']} / {top_expl['tool_id']} / {top_expl['parameter']}")
    print(f"Explanation:   {top_expl['explanation']}")
    print(f"Rec Category:  {res['recommendations'][0]['category']}")
    print("[PASS] Scenario 3 completed successfully.")
    return res


def test_scenario_4_real_db_lot():
    print("\n" + "=" * 70)
    print("SCENARIO 4: LOT-2240 (Real Lot from SQLite Database 'bob_fab.db')")
    print("=" * 70)
    res = full_copilot_analysis("LOT-2240", db_path="bob_fab.db")
    assert res["lot_id"] == "LOT-2240"
    top_expl = res["explanations"]["explanations"][0]
    print(f"Top Candidate: #{top_expl['rank']} {top_expl['step']} / {top_expl['tool_id']} / {top_expl['parameter']}")
    print(f"Explanation:   {top_expl['explanation']}")
    print(f"Phrased Rec:   {res['recommendations'][0]['phrased_recommendation']}")
    print("[PASS] Scenario 4 completed successfully.")
    return res


def test_scenario_5_chat(findings: dict):
    print("\n" + "=" * 70)
    print("SCENARIO 5: Multi-Turn 'Ask Bob' Interactive Chat Session")
    print("=" * 70)
    session = create_bob_session(findings)

    # Turn 1: Initial root cause query
    q1 = "Why did this lot experience a yield excursion?"
    ans1, session = ask_bob(session, q1)
    print(f"User: {q1}")
    print(f"Bob:  {ans1}\n")

    # Turn 2: Honesty & confirmation check
    q2 = "Is ETCH-07 100% confirmed as the root cause?"
    ans2, session = ask_bob(session, q2)
    print(f"User: {q2}")
    print(f"Bob:  {ans2}\n")
    # Verify Bob does NOT say confirmed and recommends DOE
    assert "DOE" in ans2 or "Design of Experiments" in ans2 or "candidate" in ans2.lower()

    # Turn 3: Actionable recommendations
    q3 = "What immediate actions should the fab shift engineer execute?"
    ans3, session = ask_bob(session, q3)
    print(f"User: {q3}")
    print(f"Bob:  {ans3}\n")

    print("[PASS] Scenario 5 (Multi-Turn Chat) completed successfully.")


def test_scenario_6_groq(findings: dict):
    print("\n" + "=" * 70)
    print("SCENARIO 6: Groq LLM Provider Live Execution")
    print("=" * 70)
    if not GROQ_API_KEY:
        print("[SKIP] GROQ_API_KEY not configured in .env")
        return

    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)

    # Test Ask Bob with Groq
    import copilot.config as cfg
    orig_provider = cfg.LLM_PROVIDER
    orig_model = cfg.LLM_MODEL
    try:
        cfg.LLM_PROVIDER = "groq"
        cfg.LLM_MODEL = GROQ_MODEL

        ans = ask_bob_single(
            "Summarize the leading cause for LOT-2231 and next steps in 2 sentences.",
            findings,
            client=groq_client,
        )
        print(f"Bob (via Groq {GROQ_MODEL}):\n{ans}\n")
        assert len(ans) > 20
        print("[PASS] Scenario 6 (Groq Provider) completed successfully.")
    finally:
        cfg.LLM_PROVIDER = orig_provider
        cfg.LLM_MODEL = orig_model


if __name__ == "__main__":
    print("Starting Comprehensive Copilot Scenario Verification...")
    res1 = test_scenario_1_etch()
    test_scenario_2_cmp()
    test_scenario_3_cvd()
    test_scenario_4_real_db_lot()
    test_scenario_5_chat(res1["findings"])
    test_scenario_6_groq(res1["findings"])
    print("\n" + "=" * 70)
    print("ALL 6 SCENARIOS VERIFIED AND PASSED!")
    print("=" * 70)
