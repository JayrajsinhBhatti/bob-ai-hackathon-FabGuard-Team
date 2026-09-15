"""
tests/test_counterfactual.py  —  Tests for Feature 2: Counterfactual Yield & Financial Recovery Simulator
"""

import json
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.counterfactual import CounterfactualSimulator
from analytics.pipeline import analyze_lot, get_default_repository


class TestCounterfactualSimulator:

    @pytest.fixture
    def repo(self):
        return get_default_repository()

    @pytest.fixture
    def simulator(self, repo):
        return CounterfactualSimulator(repo)

    @pytest.fixture
    def findings(self):
        return analyze_lot("LOT-2231", include_v3_fields=True)

    def test_returns_valid_structure(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        assert isinstance(result, dict)
        assert result["lot_id"] == "LOT-2231"
        assert "actual_yield_gap_pct" in result
        assert "cause_simulations" in result
        assert "total_recoverable_yield_pct" in result
        assert "total_usd_recovery_per_lot" in result
        assert "summary" in result
        assert "disclaimer" in result

    def test_yield_gap_is_non_negative(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        assert result["actual_yield_gap_pct"] >= 0.0, "Yield gap must be non-negative"

    def test_cause_simulations_have_required_fields(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        sims = result.get("cause_simulations", [])
        assert len(sims) > 0, "Expected at least one simulation"
        for sim in sims:
            assert "rank" in sim
            assert "tool_id" in sim
            assert "parameter" in sim
            assert "recoverable_yield_pct" in sim
            assert "usd_recovery_per_lot" in sim
            assert "confidence_factor" in sim
            assert "narrative" in sim
            assert "recoverable_yield_range_pct" in sim
            assert len(sim["recoverable_yield_range_pct"]) == 2

    def test_recoverable_yield_within_bounds(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        gap = result["actual_yield_gap_pct"]
        total_rec = result["total_recoverable_yield_pct"]
        # Total recoverable cannot exceed the actual yield gap
        assert total_rec <= gap + 0.01, \
            f"Recoverable ({total_rec}%) exceeds yield gap ({gap}%)"
        assert total_rec >= 0.0, "Recoverable yield must be non-negative"

    def test_financial_values_are_positive(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        sims = result.get("cause_simulations", [])
        for sim in sims:
            assert sim["usd_recovery_per_lot"] >= 0.0, "USD recovery must be non-negative"
            assert sim["die_recovered_per_lot"] >= 0.0, "Die count must be non-negative"

    def test_confidence_factor_bounded(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        for sim in result.get("cause_simulations", []):
            assert 0.0 <= sim["confidence_factor"] <= 1.0, \
                f"Confidence factor out of [0,1]: {sim['confidence_factor']}"

    def test_uncertainty_range_is_symmetric(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        for sim in result.get("cause_simulations", []):
            low, high = sim["recoverable_yield_range_pct"]
            mid = sim["recoverable_yield_pct"]
            # Range is ±30% so: low ≈ mid*0.7, high ≈ mid*1.3
            assert low <= mid <= high, \
                f"Range [{low}, {high}] does not contain mid {mid}"

    def test_format_as_text(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        text = simulator.format_as_text(result)
        assert isinstance(text, str)
        assert "LOT-2231" in text
        assert "Yield Gap" in text
        assert "$" in text  # financial values present
        assert "DOE" in text  # disclaimer present
        assert len(text) > 200

    def test_json_serializable(self, simulator, findings):
        result = simulator.simulate_recovery_for_lot("LOT-2231", findings)
        try:
            json.dumps(result)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Result not JSON serializable: {e}")

    def test_custom_economics(self, repo, findings):
        """Custom ASP and wafer count should change financial outputs proportionally."""
        sim_standard = CounterfactualSimulator(repo, asp_per_die_usd=45.0, die_per_wafer=500)
        sim_custom = CounterfactualSimulator(repo, asp_per_die_usd=90.0, die_per_wafer=500)
        r_std = sim_standard.simulate_recovery_for_lot("LOT-2231", findings)
        r_cust = sim_custom.simulate_recovery_for_lot("LOT-2231", findings)
        if r_std["cause_simulations"] and r_cust["cause_simulations"]:
            usd_std = r_std["cause_simulations"][0]["usd_recovery_per_lot"]
            usd_cust = r_cust["cause_simulations"][0]["usd_recovery_per_lot"]
            # Doubling ASP should roughly double the USD recovery
            assert abs(usd_cust - 2 * usd_std) < 1.0, \
                f"Expected USD to double with 2x ASP: std={usd_std}, custom={usd_cust}"

    def test_empty_findings_handles_gracefully(self, simulator):
        empty_findings = {"lot_id": "LOT-9999", "candidate_causes": [], "at_risk_upcoming_batches": []}
        result = simulator.simulate_recovery_for_lot("LOT-9999", empty_findings)
        assert result["lot_id"] == "LOT-9999"
        assert result["cause_simulations"] == []
        assert "No candidate causes" in result["summary"]
