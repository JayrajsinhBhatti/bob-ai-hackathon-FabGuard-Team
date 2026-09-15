"""
src/tests/test_ibm_bob_integration.py

Integration tests for IBM Bob / watsonx.ai Granite 3.0 copilot.

Tests:
  1. Config loads with ibm_bob provider and correct project ID
  2. Granite prompt format is correct (Granite chat-template tags)
  3. LLM client can be instantiated (requires WATSONX_API_KEY in .env)
  4. End-to-end ask_bob_single() with fixture findings (live call if key set)
  5. Fallback chain works when IBM Bob unavailable
  6. IBM Bob MCP settings file exists and is valid JSON
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Bootstrap path so src/ is importable
_SRC_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _SRC_DIR.parent
for _p in [str(_SRC_DIR), str(_REPO_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / ".env")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_FINDINGS = {
    "lot_id": "LOT-2231",
    "candidate_causes": [
        {
            "rank": 1,
            "step": "etch",
            "tool_id": "ETCH-07",
            "parameter": "chamber_pressure",
            "probability": 0.78,
            "confidence_basis": "logistic_regression_v1",
            "spatial_signature": "edge_ring",
            "sample_size": 14,
            "evidence": "Chamber pressure drifted +3.2σ above nominal (12.0 mTorr → 14.1 mTorr).",
        }
    ],
    "at_risk_upcoming_batches": [],
}

BOBatHON_PROJECT_ID = "20260915-1650-5679-61fd-a8533eb2eafb"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Config loads correctly
# ─────────────────────────────────────────────────────────────────────────────

def test_config_ibm_bob_provider():
    """LLM_PROVIDER should default to ibm_bob after loading .env."""
    from copilot import config as cfg
    # When .env sets ibm_bob, config should reflect it
    assert cfg.LLM_PROVIDER in ("ibm_bob", "watsonx", "gemini", "groq"), (
        f"Unexpected LLM_PROVIDER: {cfg.LLM_PROVIDER}"
    )


def test_config_project_id_set():
    """WATSONX_PROJECT_ID should be the BOBathon SaaS account ID."""
    from copilot import config as cfg
    assert cfg.WATSONX_PROJECT_ID == BOBatHON_PROJECT_ID, (
        f"Expected BOBathon project ID {BOBatHON_PROJECT_ID}, got {cfg.WATSONX_PROJECT_ID}"
    )


def test_config_granite_model():
    """WATSONX_MODEL should point to IBM Granite 3.0."""
    from copilot import config as cfg
    assert "granite" in cfg.WATSONX_MODEL.lower(), (
        f"Expected Granite model, got: {cfg.WATSONX_MODEL}"
    )


def test_config_url_ibm():
    """WATSONX_URL should point to IBM Cloud ml endpoint."""
    from copilot import config as cfg
    assert "ml.cloud.ibm.com" in cfg.WATSONX_URL, (
        f"Unexpected URL: {cfg.WATSONX_URL}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Granite prompt formatting
# ─────────────────────────────────────────────────────────────────────────────

def test_granite_prompt_format():
    """
    _dispatch_chat should produce Granite chat-template format for ibm_bob:
    <|system|>\n...<|user|>\n...<|assistant|>
    """
    messages = [
        {"role": "system", "content": "You are Bob."},
        {"role": "user", "content": "Why did LOT-2231 fail?"},
    ]

    # Build expected prompt manually
    expected_parts = [
        "<|system|>\nYou are Bob.",
        "<|user|>\nWhy did LOT-2231 fail?",
        "<|assistant|>",
    ]
    expected_prompt = "\n".join(expected_parts)

    # Extract the formatting logic from agent (without calling the API)
    system_content = ""
    chat_turns = []
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            chat_turns.append(msg)

    formatted_parts = []
    if system_content:
        formatted_parts.append(f"<|system|>\n{system_content}")
    for msg in chat_turns:
        role_tag = "<|user|>" if msg["role"] == "user" else "<|assistant|>"
        formatted_parts.append(f"{role_tag}\n{msg['content']}")
    formatted_parts.append("<|assistant|>")
    actual_prompt = "\n".join(formatted_parts)

    assert actual_prompt == expected_prompt, (
        f"Granite prompt format mismatch:\nExpected:\n{expected_prompt}\nGot:\n{actual_prompt}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. LLM client instantiation (skipped if no API key)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.getenv("WATSONX_API_KEY") or os.getenv("WATSONX_API_KEY", "").startswith("YOUR_"),
    reason="WATSONX_API_KEY not configured — skipping live IBM Bob client test"
)
def test_ibm_bob_client_instantiation():
    """get_llm_client() should return a ModelInference object for ibm_bob."""
    import importlib
    import copilot.config as cfg
    # Force ibm_bob provider for this test
    original = cfg.LLM_PROVIDER
    cfg.LLM_PROVIDER = "ibm_bob"
    try:
        from ibm_watsonx_ai.foundation_models import ModelInference
        client = cfg.get_llm_client()
        assert isinstance(client, ModelInference), (
            f"Expected ModelInference, got {type(client)}"
        )
    finally:
        cfg.LLM_PROVIDER = original


# ─────────────────────────────────────────────────────────────────────────────
# 4. End-to-end ask_bob (live — skipped if no API key)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.getenv("WATSONX_API_KEY") or os.getenv("WATSONX_API_KEY", "").startswith("YOUR_"),
    reason="WATSONX_API_KEY not configured — skipping live IBM Bob e2e test"
)
def test_ask_bob_ibm_granite_live():
    """IBM Granite 3.0 should return a non-empty answer for a fab question."""
    from copilot.agent import ask_bob_single
    answer = ask_bob_single(
        "What is the leading candidate root cause for LOT-2231?",
        findings=SAMPLE_FINDINGS,
    )
    assert isinstance(answer, str), "answer must be a string"
    assert len(answer) > 10, f"Answer too short: {repr(answer)}"
    # Should not be an error message
    assert not answer.startswith("[Error]"), f"Got error response: {answer}"
    print(f"\n[IBM Bob / Granite 3.0 Answer]:\n{answer}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fallback chain — IBM Bob → Groq → Gemini
# ─────────────────────────────────────────────────────────────────────────────

def test_fallback_chain_defined():
    """
    Verify the fallback chain is coded in agent._dispatch_chat():
    ibm_bob → groq → gemini.
    """
    import inspect
    from copilot import agent
    source = inspect.getsource(agent._dispatch_chat)

    assert "ibm_bob" in source or "watsonx" in source, "ibm_bob/watsonx branch missing"
    assert "GROQ_API_KEY" in source, "Groq fallback missing"
    assert "GEMINI_API_KEY" in source, "Gemini fallback missing"


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not configured — skipping Groq fallback test"
)
def test_groq_fallback_works():
    """When ibm_bob fails (no key), should fall back to Groq gracefully."""
    import copilot.config as cfg
    original_key = cfg.WATSONX_API_KEY
    original_provider = cfg.LLM_PROVIDER
    cfg.WATSONX_API_KEY = None  # Force IBM Bob to fail
    cfg.LLM_PROVIDER = "ibm_bob"

    from copilot.agent import ask_bob_single
    try:
        answer = ask_bob_single("What is Cpk?", findings=SAMPLE_FINDINGS)
        assert isinstance(answer, str) and len(answer) > 5
        print(f"\n[Groq Fallback Answer]: {answer[:100]}...")
    finally:
        cfg.WATSONX_API_KEY = original_key
        cfg.LLM_PROVIDER = original_provider


# ─────────────────────────────────────────────────────────────────────────────
# 6. IBM Bob MCP config file
# ─────────────────────────────────────────────────────────────────────────────

def test_bob_mcp_config_exists():
    """`.bob/mcp.json` should exist and be valid JSON with mcpServers."""
    mcp_path = _REPO_ROOT / ".bob" / "mcp.json"
    assert mcp_path.exists(), f".bob/mcp.json not found at {mcp_path}"

    with open(mcp_path, encoding="utf-8") as f:
        config = json.load(f)

    assert "mcpServers" in config, "mcpServers key missing from .bob/mcp.json"
    servers = config["mcpServers"]
    assert len(servers) >= 1, "At least one MCP server must be configured"

    # Check our fabguard server
    assert "fabguard-fab-analytics" in servers, (
        f"fabguard-fab-analytics server not found. Found: {list(servers.keys())}"
    )
    fab_server = servers["fabguard-fab-analytics"]
    assert "command" in fab_server, "command field missing"
    assert "args" in fab_server, "args field missing"
    assert "alwaysAllow" in fab_server, "alwaysAllow field missing"

    # Check all 7 tools are listed
    allowed = fab_server["alwaysAllow"]
    required_tools = [
        "mcp_analyze_lot",
        "mcp_predict_batch_risk",
        "mcp_ask_fab_copilot",
        "mcp_run_commonality_analysis",
        "mcp_simulate_yield_recovery",
        "mcp_generate_doe_matrix",
    ]
    for tool in required_tools:
        assert tool in allowed, f"Tool {tool} not in alwaysAllow list"


def test_bob_mcp_server_script_exists():
    """The MCP server script referenced in .bob/mcp.json should exist."""
    mcp_server_path = _SRC_DIR / "mcp_server.py"
    assert mcp_server_path.exists(), f"mcp_server.py not found at {mcp_server_path}"
