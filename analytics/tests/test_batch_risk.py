"""Unit tests for Batch Risk Predictor."""

import unittest
from analytics.batch_risk import BatchRiskPredictor
from analytics.data_access import InMemoryRepository
from analytics.tests.fixtures import get_benchmark_fixtures


class TestBatchRiskPredictor(unittest.TestCase):

    def setUp(self):
        self.repo = get_benchmark_fixtures()
        self.predictor = BatchRiskPredictor(repository=self.repo)

    def test_in_progress_lot_prediction(self):
        # LOT-2245 is an in-progress lot with abnormal etch chamber pressure
        at_risk = self.predictor.predict_at_risk_batches()
        self.assertTrue(len(at_risk) > 0)

        flagged = next((b for b in at_risk if b.lot_id == "LOT-2245"), None)
        self.assertIsNotNone(flagged)
        self.assertGreaterEqual(flagged.risk_score, 0.50)
        self.assertLessEqual(flagged.risk_score, 1.0)
        self.assertEqual(flagged.matched_signature, "edge-ring")

    def test_no_in_progress_lots(self):
        empty_repo = InMemoryRepository(lots=[], process_steps=[], defects=[])
        predictor = BatchRiskPredictor(repository=empty_repo)
        results = predictor.predict_at_risk_batches()
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
