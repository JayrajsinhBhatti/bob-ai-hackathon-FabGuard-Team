"""Unit tests for Root Cause Ranker."""

import unittest
from analytics.root_cause import RootCauseRanker
from analytics.tests.fixtures import get_benchmark_fixtures


class TestRootCauseRanker(unittest.TestCase):

    def setUp(self):
        self.repo = get_benchmark_fixtures()
        self.ranker = RootCauseRanker(repository=self.repo)

    def test_case1_etch_chamber_pressure_ranking(self):
        # LOT-2231 has abnormal etch chamber pressure and edge-ring defects at etch
        candidates = self.ranker.rank_causes_for_lot("LOT-2231")
        self.assertTrue(len(candidates) > 0)

        top = candidates[0]
        self.assertEqual(top.step, "etch")
        self.assertEqual(top.tool_id, "ETCH-07")
        self.assertEqual(top.parameter, "chamber_pressure")
        self.assertEqual(top.spatial_signature, "edge-ring")
        self.assertGreater(top.deviation_score, 0.50)
        self.assertGreater(top.confidence, 0.40)
        self.assertLess(top.confidence, 0.95)  # Honest confidence: never 1.0
        self.assertGreater(top.sample_size, 5)
        self.assertIn("sigma above", top.evidence)
        self.assertIn("edge-ring", top.evidence)

    def test_case2_cmp_pad_downforce_ranking(self):
        # LOT-2261 has abnormal CMP pad downforce with scratch defects at cmp
        candidates = self.ranker.rank_causes_for_lot("LOT-2261")
        self.assertTrue(len(candidates) > 0)

        top = candidates[0]
        self.assertEqual(top.step, "cmp")
        self.assertEqual(top.tool_id, "CMP-01")
        self.assertEqual(top.parameter, "pad_downforce")
        self.assertEqual(top.spatial_signature, "scratch")

    def test_case3_cvd_deposition_temp_ranking(self):
        # LOT-2271 has abnormal CVD deposition temp with center-cluster defects at cvd
        candidates = self.ranker.rank_causes_for_lot("LOT-2271")
        self.assertTrue(len(candidates) > 0)

        top = candidates[0]
        self.assertEqual(top.step, "cvd")
        self.assertEqual(top.tool_id, "CVD-03")
        self.assertEqual(top.parameter, "deposition_temp")
        self.assertEqual(top.spatial_signature, "center-cluster")

    def test_step_narrowing_enforcement(self):
        # Verify that candidate causes do not include steps unrelated to the defect's detected step
        candidates = self.ranker.rank_causes_for_lot("LOT-2231")
        # LOT-2231 defects were detected at 'etch'. Non-detected steps like 'litho' should not appear
        candidate_steps = {c.step for c in candidates}
        self.assertIn("etch", candidate_steps)
        self.assertNotIn("litho", candidate_steps)

    def test_missing_lot_graceful_handling(self):
        candidates = self.ranker.rank_causes_for_lot("LOT-NONEXISTENT")
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
