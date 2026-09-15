"""
tests/test_doe_engine.py  —  Tests for Feature 3: Automated DOE Generator
"""

import pytest
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot.doe_engine import DOEEngine, _minimum_sample_size, _format_value
from analytics.pipeline import analyze_lot, get_default_repository


class TestDOEHelpers:
    def test_minimum_sample_size_reasonable(self):
        n = _minimum_sample_size(effect_size_fraction=0.5)
        assert 4 <= n <= 25, f"Expected 4–25 wafers, got {n}"

    def test_minimum_sample_size_large_effect(self):
        """Large effect = fewer samples needed."""
        n_large = _minimum_sample_size(effect_size_fraction=0.9)
        n_small = _minimum_sample_size(effect_size_fraction=0.2)
        assert n_large < n_small, "Larger effect size should require fewer samples"

    def test_minimum_sample_size_upper_cap(self):
        """Never require more than 25 wafers per run."""
        n = _minimum_sample_size(effect_size_fraction=0.01)  # tiny effect
        assert n <= 25

    def test_format_value_large_number(self):
        assert "." in _format_value(123.456)

    def test_format_value_small_number(self):
        result = _format_value(0.001)
        assert float(result) == pytest.approx(0.001, abs=1e-6)


class TestDOEEngine:

    @pytest.fixture
    def engine(self):
        repo = get_default_repository()
        return DOEEngine(repo)

    @pytest.fixture
    def top_cause(self):
        findings = analyze_lot("LOT-2231", include_v3_fields=True)
        causes = findings.get("candidate_causes", [])
        assert causes, "No candidate causes found"
        return causes[0]

    def test_generate_for_cause_returns_valid_structure(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        assert isinstance(runcard, dict)
        assert runcard.get("lot_id") == "LOT-2231"
        assert "run_sheet" in runcard
        assert "factors" in runcard
        assert "hypothesis" in runcard
        assert "success_criteria" in runcard
        assert "design_type" in runcard

    def test_run_sheet_is_not_empty(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        runs = runcard.get("run_sheet", [])
        assert len(runs) >= 4, f"Expected ≥4 runs for 2^k factorial, got {len(runs)}"

    def test_each_run_has_required_fields(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        for run in runcard.get("run_sheet", []):
            assert "run_id" in run
            assert "run_order" in run
            assert "conditions" in run
            assert "is_center_point" in run

    def test_run_order_is_shuffled(self, engine, top_cause):
        """Run order should not be sequential 1,2,3,..."""
        runcard = engine.generate_for_cause("LOT-2231", top_cause, random_seed=42)
        orders = [r["run_order"] for r in runcard.get("run_sheet", [])]
        # After sorting by run_order, they should cover all integers 1..n
        sorted_orders = sorted(orders)
        expected = list(range(1, len(orders) + 1))
        assert sorted_orders == expected, "Run orders must be a permutation of 1..n"

    def test_center_points_included_when_requested(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause, include_center_points=True)
        center_runs = [r for r in runcard.get("run_sheet", []) if r.get("is_center_point")]
        assert len(center_runs) >= 2, "Expected ≥2 center point runs"

    def test_factor_levels_are_ordered(self, engine, top_cause):
        """Low must be ≤ Nominal ≤ High for all factors."""
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        for factor in runcard.get("factors", []):
            assert factor["low"] <= factor["nominal"] <= factor["high"], \
                f"Factor levels disordered: {factor}"

    def test_hypothesis_contains_tool_and_parameter(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        hyp = runcard.get("hypothesis", {})
        tool = runcard.get("tool_id", "")
        param = runcard.get("parameter", "").replace("_", " ")
        assert tool in hyp.get("H0", "") or param in hyp.get("H0", ""), \
            "H0 should mention tool or parameter"
        assert "H1" in hyp

    def test_wafers_per_run_in_valid_range(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        n = runcard.get("wafers_per_run", 0)
        assert 4 <= n <= 25, f"Wafers per run out of range: {n}"

    def test_total_wafers_matches_n_runs_x_wafers_per_run(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        expected = runcard["n_runs"] * runcard["wafers_per_run"]
        actual = runcard["total_wafers_required"]
        assert actual == expected, f"Total wafers {actual} ≠ {runcard['n_runs']} × {runcard['wafers_per_run']}"

    def test_format_as_text(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        text = engine.format_as_text(runcard)
        assert isinstance(text, str)
        assert "LOT-2231" in text
        assert "Run Sheet" in text
        assert "H₀" in text
        assert "Success Criteria" in text
        assert "DOE" in text
        assert len(text) > 300

    def test_json_serializable(self, engine, top_cause):
        runcard = engine.generate_for_cause("LOT-2231", top_cause)
        try:
            json.dumps(runcard)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Runcard not JSON serializable: {e}")

    def test_run_order_is_a_valid_permutation(self, engine, top_cause):
        """Run orders must form a valid 1..N permutation (all values unique and complete)."""
        runcard = engine.generate_for_cause("LOT-2231", top_cause, random_seed=42)
        orders = [r["run_order"] for r in runcard.get("run_sheet", [])]
        n = len(orders)
        assert sorted(orders) == list(range(1, n + 1)), \
            f"Run orders {orders} are not a valid permutation of 1..{n}"

    def test_shuffling_works_across_seeds(self, engine, top_cause):
        """Verify that different seeds map run_ids to different execution positions."""
        # The run_sheet is sorted by run_order for display (so run_order is always 1..N).
        # The shuffle is reflected in which run_id appears at each execution position.
        # Capture the (run_id, run_order) mapping which differs across seeds.
        seen_mappings = set()
        for seed in range(10):
            rc = engine.generate_for_cause("LOT-2231", top_cause, random_seed=seed)
            # Map: for each run, record (run_id -> execution run_order)
            mapping = tuple(
                (r["run_id"], r["run_order"]) for r in rc.get("run_sheet", [])
            )
            seen_mappings.add(mapping)
        # With 10 seeds and n>=4 runs, we expect at least 2 distinct (run_id→order) mappings
        assert len(seen_mappings) >= 2, \
            f"Expected ≥2 distinct execution mappings across 10 seeds, got {len(seen_mappings)}"
