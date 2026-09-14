"""End-to-end integration and JSON contract tests for Analytics Pipeline."""

import json
import unittest
from analytics.pipeline import analyze_lot, analyze_all
from analytics.tests.fixtures import get_benchmark_fixtures


class TestAnalyticsPipeline(unittest.TestCase):

    def setUp(self):
        self.repo = get_benchmark_fixtures()

    def test_analyze_lot_contract_shape(self):
        result = analyze_lot("LOT-2231", repository=self.repo)

        # 1. Check top-level contract keys
        self.assertIn("lot_id", result)
        self.assertIn("candidate_causes", result)
        self.assertIn("at_risk_upcoming_batches", result)
        self.assertEqual(result["lot_id"], "LOT-2231")

        # 2. Check candidate_causes structure
        self.assertTrue(len(result["candidate_causes"]) > 0)
        c0 = result["candidate_causes"][0]
        expected_cause_keys = {
            "step",
            "tool_id",
            "parameter",
            "spatial_signature",
            "deviation_score",
            "confidence",
            "sample_size",
            "evidence",
        }
        self.assertEqual(set(c0.keys()), expected_cause_keys)

        # Field types
        self.assertIsInstance(c0["step"], str)
        self.assertIsInstance(c0["tool_id"], str)
        self.assertIsInstance(c0["parameter"], str)
        self.assertIsInstance(c0["spatial_signature"], str)
        self.assertIsInstance(c0["deviation_score"], float)
        self.assertIsInstance(c0["confidence"], float)
        self.assertIsInstance(c0["sample_size"], int)
        self.assertIsInstance(c0["evidence"], str)

        # 3. Check at_risk_upcoming_batches structure
        self.assertTrue(len(result["at_risk_upcoming_batches"]) > 0)
        b0 = result["at_risk_upcoming_batches"][0]
        expected_batch_keys = {"lot_id", "risk_score", "matched_signature"}
        self.assertEqual(set(b0.keys()), expected_batch_keys)
        self.assertIsInstance(b0["lot_id"], str)
        self.assertIsInstance(b0["risk_score"], float)
        self.assertIsInstance(b0["matched_signature"], str)

        # 4. Strictly verify JSON serializability
        serialized = json.dumps(result)
        self.assertIsInstance(serialized, str)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["lot_id"], "LOT-2231")

    def test_analyze_all(self):
        results = analyze_all(repository=self.repo)
        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        # Ensure all results can be dumped to JSON
        json_str = json.dumps(results)
        self.assertTrue(len(json_str) > 0)


if __name__ == "__main__":
    unittest.main()
