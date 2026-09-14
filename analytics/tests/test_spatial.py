"""Unit tests for Spatial Signature Classifier."""

import unittest
from analytics.spatial import (
    classify_spatial_signature,
    analyze_spatial_signature,
    SpatialConfig,
)
from analytics.tests.fixtures import (
    generate_edge_ring_points,
    generate_center_cluster_points,
    generate_scratch_points,
    generate_donut_points,
    generate_random_points,
)


class TestSpatialClassifier(unittest.TestCase):

    def test_edge_ring_detection(self):
        pts = generate_edge_ring_points(n=45, seed=10)
        sig = classify_spatial_signature(pts)
        self.assertEqual(sig, "edge-ring")

    def test_center_cluster_detection(self):
        pts = generate_center_cluster_points(n=40, seed=20)
        sig = classify_spatial_signature(pts)
        self.assertEqual(sig, "center-cluster")

    def test_scratch_detection(self):
        pts = generate_scratch_points(n=35, seed=30)
        sig = classify_spatial_signature(pts)
        self.assertEqual(sig, "scratch")

    def test_donut_detection(self):
        pts = generate_donut_points(n=45, seed=40)
        sig = classify_spatial_signature(pts)
        self.assertEqual(sig, "donut")

    def test_random_detection(self):
        pts = generate_random_points(n=30, seed=50)
        sig = classify_spatial_signature(pts)
        self.assertEqual(sig, "random")

    def test_insufficient_points_fallback(self):
        # < 4 points should fall back to random
        self.assertEqual(classify_spatial_signature([]), "random")
        self.assertEqual(classify_spatial_signature([(0.1, 0.2)]), "random")
        self.assertEqual(classify_spatial_signature([(0.1, 0.2), (0.2, 0.3)]), "random")

    def test_detailed_analysis_diagnostics(self):
        pts = generate_scratch_points(n=30, seed=99)
        result = analyze_spatial_signature(pts)
        self.assertEqual(result.signature, "scratch")
        self.assertGreater(result.confidence, 0.5)
        self.assertIn("pca_linearity_ratio", result.diagnostics)
        self.assertGreaterEqual(result.diagnostics["pca_linearity_ratio"], 0.85)


if __name__ == "__main__":
    unittest.main()
