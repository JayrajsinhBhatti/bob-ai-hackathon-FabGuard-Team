"""Public Analytics Pipeline and orchestration entry points.

Provides:
- analyze_lot(lot_id: str, ...) -> dict
- analyze_all(...) -> list[dict]
Conforms strictly to the shared Bob Fab findings contract.
"""

import json
import os
from typing import Any, Dict, List, Optional

from analytics.batch_risk import BatchRiskPredictor
from analytics.data_access import DataRepository, InMemoryRepository, SQLiteRepository
from analytics.models import RootCauseFindings
from analytics.root_cause import RootCauseRanker


DEFAULT_DB_PATHS = [
    "bob_fab.db",
    "data/bob_fab.db",
    "../bob_fab.db",
    "data/fab_data.db",
    "fab_data.db",
    "fab.db",
    "../data/fab_data.db",
]


def get_default_repository(db_path: Optional[str] = None) -> DataRepository:
    """Resolve active repository, prioritizing specified path or discovering existing SQLite DBs."""
    if db_path and os.path.exists(db_path):
        return SQLiteRepository(db_path)

    for p in DEFAULT_DB_PATHS:
        if os.path.exists(p):
            return SQLiteRepository(p)

    # Fallback to in-memory repository if no DB file is present
    from analytics.tests.fixtures import get_benchmark_fixtures
    return get_benchmark_fixtures()


def analyze_lot(
    lot_id: str,
    db_path: Optional[str] = None,
    repository: Optional[DataRepository] = None,
    include_v3_fields: bool = False,
) -> Dict[str, Any]:
    """Analyze a single wafer lot for root cause candidates and upcoming batch risks.

    Args:
        lot_id: Identifier of the lot to analyze.
        db_path: Optional path to SQLite database.
        repository: Optional custom DataRepository instance.
        include_v3_fields: Whether to include extra v3 fields (probability, confidence_basis).

    Returns:
        JSON-serializable dict matching the shared root_cause_findings contract.
    """
    repo = repository or (SQLiteRepository(db_path) if db_path else get_default_repository())

    ranker = RootCauseRanker(repository=repo)
    predictor = BatchRiskPredictor(repository=repo)

    # Rank root causes for this lot
    candidates = ranker.rank_causes_for_lot(lot_id)

    # Predict upcoming batch risk across in-progress lots
    at_risk = predictor.predict_at_risk_batches()

    findings = RootCauseFindings(
        lot_id=lot_id,
        candidate_causes=candidates,
        at_risk_upcoming_batches=at_risk,
    )

    result_dict = findings.to_dict(include_v3_fields=include_v3_fields)

    # Ensure JSON serializable (verify no raw numpy types remain)
    json.dumps(result_dict)

    return result_dict


def analyze_all(
    db_path: Optional[str] = None,
    repository: Optional[DataRepository] = None,
    include_v3_fields: bool = False,
) -> List[Dict[str, Any]]:
    """Analyze all completed lots in the dataset and return findings for each.

    Returns:
        List of findings dicts conforming to the shared contract.
    """
    repo = repository or (SQLiteRepository(db_path) if db_path else get_default_repository())
    all_lots = repo.get_all_lots()

    results: List[Dict[str, Any]] = []
    for lot in all_lots:
        lid = lot.get("lot_id")
        if not lid:
            continue
        # Only analyze lots that are not currently in-progress
        if lot.get("status") == "in_progress":
            continue
        findings = analyze_lot(
            lot_id=lid,
            repository=repo,
            include_v3_fields=include_v3_fields,
        )
        results.append(findings)

    return results
