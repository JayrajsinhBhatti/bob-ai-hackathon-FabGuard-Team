"""Unit tests for Validation Harness."""

import unittest
from analytics.validate import validate_ranker
from analytics.tests.fixtures import get_benchmark_fixtures


class TestValidationHarness(unittest.TestCase):

    def setUp(self):
        self.repo = get_benchmark_fixtures()

    def test_validation_gate_passes(self):
        report = validate_ranker(repository=self.repo)

        self.assertEqual(report["status"], "completed")
        self.assertGreater(report["total_evaluated"], 0)
        self.assertGreaterEqual(report["top1_accuracy"], 0.70)
        self.assertGreaterEqual(report["top3_accuracy"], report["top1_accuracy"])
        self.assertTrue(report["gate_passed"])


if __name__ == "__main__":
    unittest.main()
