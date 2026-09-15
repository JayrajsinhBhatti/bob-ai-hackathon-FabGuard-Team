"""
Automated Integration Test for Bob Fab Copilot + Backend API
Tests the complete end-to-end integration:
- /health
- /lots
- /rootcause
- /defects
- /predict-risk
- /chat (Multi-turn conversational Bob Copilot)
"""

import sys
import os
import json
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root and backend to sys.path
_repo_root = str(Path(__file__).resolve().parents[1])
_backend_dir = str(Path(__file__).resolve().parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    print("\n[1/6] Testing /health endpoint...")
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data.get("status") == "online"
    print("  PASS: Backend is online and connected to SQLite database.")

def test_lots():
    print("\n[2/6] Testing /lots endpoint...")
    res = client.get("/lots?limit=5")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "lots" in data
    assert "summary" in data
    print(f"  PASS: Retrieved {len(data['lots'])} lots. Fab Avg Yield: {data['summary'].get('average_yield_pct')}%.")

def test_rootcause():
    print("\n[3/6] Testing /rootcause endpoints (query & path params)...")
    # Path param
    res1 = client.get("/rootcause/LOT-2231?tier=tier2")
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
    data1 = res1.json()
    assert data1["lot_id"] == "LOT-2231"
    assert len(data1["candidate_causes"]) > 0

    # Query param
    res2 = client.get("/rootcause?lot_id=LOT-2231&tier=tier2")
    assert res2.status_code == 200
    print(f"  PASS: Leading candidate identified: Tool {data1['candidate_causes'][0]['tool_id']} ({data1['candidate_causes'][0]['parameter']}).")

def test_defects():
    print("\n[4/6] Testing /defects endpoint...")
    res = client.get("/defects/LOT-2231?limit=100")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "defects" in data
    print(f"  PASS: Retrieved {data['total_returned']} defects for LOT-2231 with spatial signature: {data['spatial_signature']}.")

def test_predict_risk():
    print("\n[5/6] Testing /predict-risk endpoint...")
    res = client.get("/predict-risk")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "batches" in data
    print(f"  PASS: Monitoring {data['total_monitored']} batches ({data['high_risk_count']} high risk).")

def test_copilot_chat():
    print("\n[6/7] Testing /chat Copilot greetings & context handling...")

    # Test 1: Greeting "hii" -> should NOT dump full diagnostic summary, NO citations!
    res_greet = client.post("/chat", json={"lot_id": "LOT-2231", "question": "hii"})
    assert res_greet.status_code == 200, f"Expected 200, got {res_greet.status_code}"
    greet_data = res_greet.json()
    assert "Hello" in greet_data["response"] or "Bob" in greet_data["response"]
    assert len(greet_data.get("cited_findings", [])) == 0, "Greetings must NOT have citations attached!"
    assert "Focus offset recorded" not in greet_data["response"], "Greetings must not dump full excursion statistics!"
    print("  PASS: 'hii' greeted properly without dumping full excursion diagnostic.")

    # Test 2: Specific diagnostic inquiry
    req1 = {
        "lot_id": "LOT-2231",
        "question": "Why did LOT-2231 have a yield drop?",
        "conversation_history": []
    }
    res1 = client.post("/chat", json=req1)
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
    ans1 = res1.json()
    
    assert "response" in ans1 and len(ans1["response"]) > 0
    assert "DOE" in ans1["response"] or "Design of Experiments" in ans1["response"], "DOE caveat missing in Copilot response!"
    print("  PASS: Diagnostic inquiry provided grounded cause with DOE caveat.")

    # Test 3: Multi-turn DOE inquiry
    req2 = {
        "lot_id": "LOT-2231",
        "question": "What is the recommended DOE matrix to confirm this?",
        "conversation_history": ans1.get("conversation_history", [])
    }
    res2 = client.post("/chat", json=req2)
    assert res2.status_code == 200, f"Expected 200, got {res2.status_code}"
    ans2 = res2.json()
    print("  PASS: Multi-turn DOE inquiry succeeded.")


def test_database_chat_history():
    print("\n[7/7] Testing database conversation persistence (/chat/history)...")
    res = client.get("/chat/history/LOT-2231")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "history" in data
    assert data["count"] > 0, "Chat history should contain saved messages in SQLite!"
    
    first_msg = data["history"][0]
    assert "sender" in first_msg and "message" in first_msg
    print(f"  PASS: Retrieved {data['count']} persisted chat messages from SQLite database.")

    # Test DELETE /chat/history
    res_del = client.delete("/chat/history/LOT-TEST-TEMP")
    assert res_del.status_code == 200


if __name__ == "__main__":
    print("==================================================================")
    print("RUNNING END-TO-END INTEGRATION TESTS: COPILOT + FASTAPI BACKEND")
    print("==================================================================")
    try:
        test_health()
        test_lots()
        test_rootcause()
        test_defects()
        test_predict_risk()
        test_copilot_chat()
        test_database_chat_history()
        print("\n==================================================================")
        print("ALL 7/7 INTEGRATION TESTS PASSED SUCCESSFULLY! [SUCCESS]")
        print("==================================================================")
    except Exception as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

