"""Unit tests for SPC Engine (Cpk, Ppk, Western Electric rules)."""

import unittest
import numpy as np
from analytics.spc import (
    calculate_cpk,
    calculate_ppk,
    is_out_of_capability,
    detect_western_electric_violations,
    analyze_parameter_series,
)


class TestSPCEngine(unittest.TestCase):

    def test_cpk_normal_process(self):
        # Centered process with mean=50, std=1.0, limits [44, 56]
        # (56 - 50) / 3 = 2.0 -> Cpk should be approx 2.0
        rng = np.random.default_rng(42)
        vals = rng.normal(50.0, 1.0, 1000).tolist()
        cpk = calculate_cpk(vals, spec_min=44.0, spec_max=56.0)
        self.assertIsNotNone(cpk)
        self.assertAlmostEqual(cpk, 2.0, delta=0.15)
        self.assertFalse(is_out_of_capability(cpk))

    def test_cpk_out_of_capability(self):
        # Process shifted near upper spec limit: mean=54.5, std=1.0, USL=55.0
        # Cpu = (55 - 54.5) / 3 = 0.167 < 1.33
        rng = np.random.default_rng(42)
        vals = rng.normal(54.5, 1.0, 500).tolist()
        cpk = calculate_cpk(vals, spec_min=45.0, spec_max=55.0)
        self.assertIsNotNone(cpk)
        self.assertLess(cpk, 1.33)
        self.assertTrue(is_out_of_capability(cpk))

    def test_single_sided_specs(self):
        vals = [10.0, 10.5, 9.5, 10.2, 9.8]
        # Only USL
        cpk_u = calculate_cpk(vals, spec_min=None, spec_max=15.0)
        self.assertIsNotNone(cpk_u)
        self.assertGreater(cpk_u, 1.33)

        # Only LSL
        cpk_l = calculate_cpk(vals, spec_min=5.0, spec_max=None)
        self.assertIsNotNone(cpk_l)
        self.assertGreater(cpk_l, 1.33)

    def test_cpk_edge_cases(self):
        # Insufficient data
        self.assertIsNone(calculate_cpk([10.0], spec_min=5.0, spec_max=15.0))
        self.assertIsNone(calculate_cpk([], spec_min=5.0, spec_max=15.0))

        # Missing specs
        self.assertIsNone(calculate_cpk([10.0, 11.0, 12.0], spec_min=None, spec_max=None))

        # Zero variance inside limits
        cpk_zero = calculate_cpk([10.0, 10.0, 10.0], spec_min=5.0, spec_max=15.0)
        self.assertIsNotNone(cpk_zero)
        self.assertGreater(cpk_zero, 1.33)

        # Zero variance outside limits
        cpk_zero_out = calculate_cpk([20.0, 20.0, 20.0], spec_min=5.0, spec_max=15.0)
        self.assertEqual(cpk_zero_out, 0.0)

    def test_western_electric_rule1_beyond_3sigma(self):
        # 1 point beyond 3 sigma
        # baseline mean=10, std=1
        vals = [10.0, 10.1, 9.9, 10.0, 10.2, 14.5, 10.1]
        violations = detect_western_electric_violations(vals, mean=10.0, std_dev=1.0)
        self.assertIn(5, violations.rule1_beyond_3sigma)
        self.assertTrue(violations.has_violations)

    def test_western_electric_rule2_two_of_three_beyond_2sigma(self):
        # 2 of 3 points beyond +2 sigma (mean=10, std=1 -> values > 12)
        vals = [10.0, 10.1, 12.5, 10.2, 12.4]
        violations = detect_western_electric_violations(vals, mean=10.0, std_dev=1.0)
        self.assertTrue(len(violations.rule2_two_of_three_beyond_2sigma) > 0)

    def test_western_electric_rule3_four_of_five_beyond_1sigma(self):
        # 4 of 5 points beyond +1 sigma (> 11)
        vals = [10.0, 11.2, 11.5, 11.3, 11.4]
        violations = detect_western_electric_violations(vals, mean=10.0, std_dev=1.0)
        self.assertIn(4, violations.rule3_four_of_five_beyond_1sigma)

    def test_western_electric_rule4_eight_consecutive(self):
        # 8 consecutive points on one side of center line (all > 10.0)
        vals = [10.2, 10.3, 10.1, 10.4, 10.2, 10.5, 10.3, 10.2]
        violations = detect_western_electric_violations(vals, mean=10.0, std_dev=1.0)
        self.assertIn(7, violations.rule4_eight_on_one_side)

    def test_western_electric_insufficient_points(self):
        # Safe execution with tiny sequences
        violations = detect_western_electric_violations([10.0, 10.1])
        self.assertFalse(violations.has_violations)

    def test_analyze_parameter_series(self):
        vals = [50.0, 50.5, 49.8, 51.0, 50.2, 55.0]
        res = analyze_parameter_series(
            step="etch",
            tool_id="ETCH-07",
            parameter="chamber_pressure",
            values=vals,
            spec_min=45.0,
            spec_max=55.0,
        )
        self.assertEqual(res.step, "etch")
        self.assertEqual(res.tool_id, "ETCH-07")
        self.assertEqual(res.parameter, "chamber_pressure")
        self.assertEqual(res.sample_size, 6)


if __name__ == "__main__":
    unittest.main()
