"""
tests/test_mcp_server.py
Unit tests verifying the IBM Bob Model Context Protocol (MCP) server.
"""

import json
import pytest
from src.mcp_server import (
    analyze_lot,
    get_root_cause_findings,
    predict_batch_risk,
    ask_fab_copilot,
)


def test_mcp_predict_batch_risk():
    res = predict_batch_risk()
    assert isinstance(res, str)
    assert len(res) > 0
    # Either lists lots or indicates all batches nominal
    assert "Batch Risk" in res or "nominal" in res.lower()


def test_mcp_get_root_cause_findings():
    res = get_root_cause_findings("LOT-2231")
    assert isinstance(res, str)
    data = json.loads(res)
    assert data.get("lot_id") == "LOT-2231"
    assert "candidate_causes" in data


def test_mcp_analyze_lot():
    res = analyze_lot("LOT-2231")
    assert isinstance(res, str)
    assert "Fab Diagnostic Briefing: LOT-2231" in res
    assert "DOE Caveat" in res or "DOE" in res


def test_mcp_ask_fab_copilot():
    res = ask_fab_copilot("What DOE is recommended before taking corrective action?")
    assert isinstance(res, str)
    assert len(res) > 20
