"""
Master Seed Script for Bob Fab Synthetic Data Generation.
Synthesizes wafer lots, FDC sensor telemetry, defect maps, and ground-truth labels.
Populates bob_fab.db and exports JSON/CSV dumps to data/exports/.

Usage:
    python -m data.seed
    python -m data.seed --seed 123 --export-dir data/exports
"""

import argparse
import json
import os
from pathlib import Path
import pandas as pd

from data.db import DEFAULT_DB_PATH, init_database, insert_synthetic_data
from data.lot_generator import generate_full_synthetic_dataset


def run_seed(db_path: Path, export_dir: Path, random_seed: int = 42) -> None:
    print("=" * 70)
    print("      BOB FAB COPILOT — SYNTHETIC DATA GENERATOR (PERSON A)       ")
    print("=" * 70)
    print(f"[*] Target SQLite Database: {db_path.resolve()}")
    print(f"[*] Export Directory:       {export_dir.resolve()}")
    print(f"[*] Random Generator Seed:  {random_seed}")

    # 1. Generate full synthetic dataset
    print("\n[1/4] Generating wafer lots, FDC telemetry, and defect maps...")
    data = generate_full_synthetic_dataset(seed=random_seed)

    lots_count = len(data["wafer_lots"])
    steps_count = len(data["process_steps"])
    defects_count = len(data["defects"])
    gt_count = len(data["ground_truth_labels"])

    print(f"  -> Generated {lots_count} wafer lots")
    print(f"  -> Generated {gt_count} injected ground-truth validation labels")
    print(f"  -> Generated {steps_count} FDC sensor telemetry readings")
    print(f"  -> Generated {defects_count} physical wafer defect coordinates")

    # 2. Initialize Database schema
    print("\n[2/4] Initializing SQLite database schema from contracts/schema.sql...")
    init_database(db_path=db_path)

    # 3. Insert into Database
    print("\n[3/4] Ingesting synthetic records into SQLite tables...")
    counts = insert_synthetic_data(data, db_path=db_path)
    for table, count in counts.items():
        print(f"  [+] {table:22s}: {count:7d} records inserted")

    # 4. Export JSON and CSV dumps
    print(f"\n[4/4] Exporting flat JSON and CSV dumps into {export_dir}...")
    export_dir.mkdir(parents=True, exist_ok=True)

    for table_name, records in data.items():
        # JSON export
        json_file = export_dir / f"{table_name}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        # CSV export
        csv_file = export_dir / f"{table_name}.csv"
        df = pd.DataFrame(records)
        df.to_csv(csv_file, index=False)
        print(f"  [+] Exported: {json_file.name} and {csv_file.name}")

    print("\n" + "=" * 70)
    print("SUCCESS: Fab dataset generated and seeded successfully!")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Bob Fab synthetic data seeder")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Output SQLite DB path")
    parser.add_argument("--export-dir", type=Path, default=Path(__file__).parent / "exports", help="Export directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    run_seed(db_path=args.db_path, export_dir=args.export_dir, random_seed=args.seed)


if __name__ == "__main__":
    main()
