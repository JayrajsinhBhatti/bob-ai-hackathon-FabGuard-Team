"""
tests/test_commonality.py  —  Tests for Feature 1: Cross-Lot Commonality Engine
"""

import json
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.commonality import (
    CommonalityAnalyzer,
    fisher_exact_p_value,
    odds_ratio,
    relative_risk,
)
from analytics.pipeline import get_default_repository


# ---------------------------------------------------------------------------
# Unit tests: pure statistical functions
# ---------------------------------------------------------------------------

class TestStatisticalFunctions:
    def test_fisher_exact_perfect_association(self):
        """All defective lots processed on tool, zero nominal lots — p should be tiny."""
        # a=10 defective on tool, b=0 defective off, c=0 nominal on, d=10 nominal off
        p = fisher_exact_p_value(10, 0, 0, 10)
        assert p < 0.001, f"Expected p < 0.001 for perfect association, got {p}"

    def test_fisher_exact_no_association(self):
        """Equal proportions across groups — p should be large (not significant)."""
        # a=5 defective on, b=5 off; c=5 nominal on, d=5 nominal off (identical rates)
        p = fisher_exact_p_value(5, 5, 5, 5)
        assert p > 0.3, f"Expected p > 0.3 for no association, got {p}"

    def test_fisher_exact_partial_association(self):
        """Moderate association — p should be in a reasonable range."""
        # 8/10 defective on tool, 2/10 nominal on tool
        p = fisher_exact_p_value(8, 2, 2, 8)
        assert 0.0 < p < 0.1, f"Expected 0 < p < 0.1 for partial association, got {p}"

    def test_odds_ratio_strong(self):
        """OR >> 1 for strongly tool-associated defects."""
        or_ = odds_ratio(10, 0, 0, 10)
        assert or_ > 100 or or_ == 9999.0 or or_ == float("inf"), f"Expected large OR, got {or_}"

    def test_odds_ratio_no_association(self):
        """OR ≈ 1.0 for equal proportions."""
        or_ = odds_ratio(5, 5, 5, 5)
        assert 0.8 < or_ < 1.2, f"Expected OR ≈ 1.0, got {or_}"

    def test_relative_risk_asymmetric(self):
        """RR > 1 when defective lots are more likely to use the tool."""
        rr = relative_risk(8, 2, 2, 8)
        assert rr > 2.0, f"Expected RR > 2.0, got {rr}"

    def test_fisher_edge_zero_cells(self):
        """Fisher test handles zero cells gracefully (returns valid float)."""
        p = fisher_exact_p_value(0, 5, 0, 5)
        assert isinstance(p, float), f"Expected float, got {type(p)}"
        assert 0.0 <= p <= 1.0, f"p-value must be in [0,1], got {p}"


# ---------------------------------------------------------------------------
# Integration tests: CommonalityAnalyzer with real DB
# ---------------------------------------------------------------------------

class TestCommonalityAnalyzerIntegration:
    @pytest.fixture
    def analyzer(self):
        repo = get_default_repository()
        return CommonalityAnalyzer(repo, low_yield_threshold=90.0)

    def test_run_for_lot_returns_valid_structure(self, analyzer):
        result = analyzer.run_for_lot("LOT-2231")
        assert isinstance(result, dict), "Result must be a dict"
        assert "lot_id" in result
        assert result["lot_id"] == "LOT-2231"
        assert "findings" in result
        assert "total_lots_analyzed" in result
        assert "summary" in result

    def test_findings_have_required_fields(self, analyzer):
        result = analyzer.run_for_lot("LOT-2231")
        findings = result.get("findings", [])
        assert len(findings) > 0, "Expected at least one tool finding"
        for f in findings:
            assert "tool_id" in f
            assert "p_value" in f
            assert "odds_ratio" in f
            assert "relative_risk" in f
            assert "verdict" in f
            assert "significant" in f
            assert "table" in f
            # p-value must be a valid probability
            assert 0.0 <= f["p_value"] <= 1.0, f"p-value out of range: {f['p_value']}"

    def test_findings_sorted_by_p_value(self, analyzer):
        result = analyzer.run_for_lot("LOT-2231")
        findings = result.get("findings", [])
        if len(findings) >= 2:
            for i in range(len(findings) - 1):
                assert findings[i]["p_value"] <= findings[i+1]["p_value"], \
                    "Findings must be sorted by ascending p_value"

    def test_format_as_text_output(self, analyzer):
        result = analyzer.run_for_lot("LOT-2231")
        text = analyzer.format_as_text(result)
        assert isinstance(text, str)
        assert "LOT-2231" in text
        assert "p-value" in text
        assert "DOE Caveat" in text
        assert len(text) > 100, "Expected meaningful text output"

    def test_lot_counts_make_sense(self, analyzer):
        result = analyzer.run_for_lot("LOT-2231")
        n_def = result.get("defective_lots", 0)
        n_nom = result.get("nominal_lots", 0)
        n_total = result.get("total_lots_analyzed", 0)
        assert n_total == n_def + n_nom, "Total lots must equal defective + nominal"
        assert n_total > 0, "Must have at least some historical lots"

    def test_summary_is_non_empty_string(self, analyzer):
        result = analyzer.run_for_lot("LOT-2231")
        summary = result.get("summary", "")
        assert isinstance(summary, str)
        assert len(summary) > 20

    def test_json_serializable(self, analyzer):
        result = analyzer.run_for_lot("LOT-2231")
        try:
            json.dumps(result)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Result not JSON serializable: {e}")
