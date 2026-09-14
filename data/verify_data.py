"""
Automated Data Validation & Verification Suite for Bob Fab Dataset.
Verifies relational integrity, Six Sigma SPC drift, spatial defect boundaries,
and ground-truth scenario clarity before handoff to Person B (Analytics Core).

Usage:
    python -m data.verify_data
    python -m data.verify_data --db-path bob_fab.db
"""

import argparse
import math
import sqlite3
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from data.db import DEFAULT_DB_PATH, get_connection
from data.config import SCENARIOS_CONFIG, NORMAL_LOTS_CONFIG, IN_PROGRESS_LOTS_CONFIG


def run_verification(db_path: Path) -> bool:
    print("=" * 70)
    print("      BOB FAB DATA VERIFICATION SUITE — CHECKPOINT 1 GATE         ")
    print("=" * 70)
    print(f"[*] Validating Database: {db_path.resolve()}\n")

    if not db_path.exists():
        print(f"[FAIL] Database file not found at {db_path}")
        return False

    conn = get_connection(db_path)
    all_passed = True

    try:
        # Check 1: Row Counts
        print("[Check 1/5] Checking table row counts and completeness...")
        cur = conn.cursor()
        counts = {}
        for table in ["wafer_lots", "process_steps", "defects", "ground_truth_labels"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
            print(f"  -> {table:22s}: {counts[table]:7d} rows")

        expected_lots = (
            sum(s["num_lots"] for s in SCENARIOS_CONFIG)
            + NORMAL_LOTS_CONFIG["num_lots"]
            + IN_PROGRESS_LOTS_CONFIG["num_lots"]
        )
        expected_gt = sum(s["num_lots"] for s in SCENARIOS_CONFIG)

        if counts["wafer_lots"] != expected_lots:
            print(f"  [!] MISMATCH: Expected {expected_lots} lots, got {counts['wafer_lots']}")
            all_passed = False
        else:
            print(f"  [PASS] wafer_lots count matches expected: {expected_lots}")

        if counts["ground_truth_labels"] != expected_gt:
            print(f"  [!] MISMATCH: Expected {expected_gt} ground-truth labels, got {counts['ground_truth_labels']}")
            all_passed = False
        else:
            print(f"  [PASS] ground_truth_labels count matches expected: {expected_gt}")

        # Check 2: Physical Wafer Boundary Check (x^2 + y^2 <= 1.0)
        print("\n[Check 2/5] Verifying physical wafer disk boundary (x^2 + y^2 <= 1.0)...")
        cur.execute("SELECT COUNT(*) FROM defects WHERE (x*x + y*y) > 1.0001;")
        out_of_bounds = cur.fetchone()[0]
        if out_of_bounds > 0:
            print(f"  [!] FAILED: Found {out_of_bounds} defects outside physical wafer disk!")
            all_passed = False
        else:
            print(f"  [PASS] 100% of {counts['defects']} defects strictly within unit disk (r <= 1.0)")

        # Check 3: Relational Foreign Key Integrity
        print("\n[Check 3/5] Verifying Foreign Key referential integrity...")
        cur.execute("PRAGMA foreign_key_check;")
        fk_violations = cur.fetchall()
        if fk_violations:
            print(f"  [!] FAILED: Found {len(fk_violations)} foreign key violations!")
            all_passed = False
        else:
            print("  [PASS] Zero foreign key violations. Relational integrity intact.")

        # Check 4: Injected Scenario Statistical Separation & SPC Degradation
        print("\n[Check 4/5] Verifying statistical signal separation for 5 injected scenarios...")
        steps_df = pd.read_sql_query("SELECT * FROM process_steps", conn)
        gt_df = pd.read_sql_query("SELECT * FROM ground_truth_labels", conn)

        for sc in SCENARIOS_CONFIG:
            sc_id = sc["scenario_id"]
            step = sc["step"]
            tool = sc["tool_id"]
            param = sc["parameter"]
            sig = sc["signature"]

            # Filter telemetry for this specific (step, tool, param)
            subset = steps_df[
                (steps_df["step_name"] == step)
                & (steps_df["tool_id"] == tool)
                & (steps_df["parameter_name"] == param)
            ]

            affected_lots = set(gt_df[gt_df["injected_cause_tool_id"] == tool]["lot_id"])
            injected_vals = subset[subset["lot_id"].isin(affected_lots)]["value"]

            # Baseline values across other lots
            baseline_vals = steps_df[
                (steps_df["step_name"] == step)
                & (steps_df["parameter_name"] == param)
                & (~steps_df["lot_id"].isin(affected_lots))
            ]["value"]

            inj_mean = injected_vals.mean()
            base_mean = baseline_vals.mean()
            base_std = baseline_vals.std()
            shift_sigmas = abs(inj_mean - base_mean) / base_std if base_std > 0 else 0

            # Cpk on injected lots
            spec_min = sc.get("spec_min", subset["spec_min"].iloc[0])
            spec_max = sc.get("spec_max", subset["spec_max"].iloc[0])
            inj_std = injected_vals.std() if len(injected_vals) > 1 else 0.01
            cpk_upper = (spec_max - inj_mean) / (3 * inj_std) if inj_std > 0 else 99
            cpk_lower = (inj_mean - spec_min) / (3 * inj_std) if inj_std > 0 else 99
            cpk = min(cpk_upper, cpk_lower)

            status = "PASS" if (shift_sigmas >= 2.5 and cpk < 1.33) else "WARN"
            print(
                f"  [{status}] Scenario {sc_id} ({tool} - {param}): "
                f"Shift = {shift_sigmas:.2f} sigma | Cpk = {cpk:.2f} (Target < 1.33) | Pattern: {sig}"
            )

            if shift_sigmas < 2.0 or cpk >= 1.33:
                print(f"      [WARNING] Signal strength may be low for Scenario {sc_id}")

        # Check 5: In-Progress Lots Check
        print("\n[Check 5/5] Verifying In-Progress & At-Risk upcoming lots...")
        cur.execute("SELECT lot_id, status, final_yield_pct FROM wafer_lots WHERE status IN ('in_progress', 'at_risk');")
        ip_rows = cur.fetchall()
        at_risk_count = sum(1 for r in ip_rows if r["status"] == "at_risk")
        normal_ip_count = sum(1 for r in ip_rows if r["status"] == "in_progress")
        null_yields = all(r["final_yield_pct"] is None for r in ip_rows)

        print(f"  -> Found {len(ip_rows)} in-progress lots ({at_risk_count} at_risk, {normal_ip_count} normal)")
        if not null_yields:
            print("  [!] FAILED: Some in-progress lots have non-null final_yield_pct!")
            all_passed = False
        else:
            print("  [PASS] All in-progress lots have NULL final_yield_pct as specified in Section 7.1")

    finally:
        conn.close()

    print("\n" + "=" * 70)
    if all_passed:
        print("GATE CHECKPOINT 1 PASSED: Dataset is 100% verified and ready for Person B!")
    else:
        print("GATE CHECKPOINT 1 FAILED: Please inspect errors above.")
    print("=" * 70)

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Bob Fab data verification suite")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to SQLite database")
    args = parser.parse_args()
    success = run_verification(args.db_path)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
