"""Validation Harness for Root Cause Ranking Accuracy.

Evaluates Top-1 and Top-3 accuracy against injected ground-truth fault scenarios.
Hard gate check: Top-1 accuracy must be >= 70%.
"""

from typing import Any, Dict, List, Optional
from analytics.data_access import DataRepository
from analytics.pipeline import get_default_repository
from analytics.root_cause import RootCauseRanker


def validate_ranker(
    repository: Optional[DataRepository] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Run validation against all ground-truth labeled lots in the repository.

    Returns:
        Summary dict containing top1_accuracy, top3_accuracy, total_evaluated, and scenario_breakdown.
    """
    repo = repository or get_default_repository(db_path)
    labels = repo.get_ground_truth_labels()

    if not labels:
        return {
            "status": "skipped",
            "message": "No ground_truth_labels found in dataset",
            "total_evaluated": 0,
            "top1_accuracy": 0.0,
            "top3_accuracy": 0.0,
            "gate_passed": False,
        }

    ranker = RootCauseRanker(repository=repo)

    top1_matches = 0
    top3_matches = 0
    evaluated_count = 0
    details: List[Dict[str, Any]] = []

    for label in labels:
        lot_id = label.get("lot_id")
        if not lot_id:
            continue

        true_step = label.get("injected_cause_step")
        true_tool = label.get("injected_cause_tool_id")
        true_param = label.get("injected_cause_parameter")

        candidates = ranker.rank_causes_for_lot(lot_id)
        evaluated_count += 1

        top1_hit = False
        top3_hit = False

        if candidates:
            # Check Top 1
            c0 = candidates[0]
            if (
                c0.step == true_step
                and c0.tool_id == true_tool
                and c0.parameter == true_param
            ):
                top1_hit = True
                top1_matches += 1

            # Check Top 3
            top3 = candidates[:3]
            for c in top3:
                if (
                    c.step == true_step
                    and c.tool_id == true_tool
                    and c.parameter == true_param
                ):
                    top3_hit = True
                    top3_matches += 1
                    break

        details.append({
            "lot_id": lot_id,
            "true_cause": f"{true_step}:{true_tool}:{true_param}",
            "top_candidate": f"{candidates[0].step}:{candidates[0].tool_id}:{candidates[0].parameter}" if candidates else None,
            "top1_hit": top1_hit,
            "top3_hit": top3_hit,
        })

    top1_acc = float(top1_matches / evaluated_count) if evaluated_count > 0 else 0.0
    top3_acc = float(top3_matches / evaluated_count) if evaluated_count > 0 else 0.0
    gate_passed = top1_acc >= 0.70

    return {
        "status": "completed",
        "total_evaluated": evaluated_count,
        "top1_matches": top1_matches,
        "top1_accuracy": round(top1_acc, 4),
        "top3_matches": top3_matches,
        "top3_accuracy": round(top3_acc, 4),
        "gate_passed": gate_passed,
        "gate_threshold": 0.70,
        "details": details,
    }


if __name__ == "__main__":
    result = validate_ranker()
    print("=" * 60)
    print("ANALYTICS ROOT CAUSE RANKER VALIDATION GATE REPORT")
    print("=" * 60)
    print(f"Total Evaluated: {result['total_evaluated']}")
    print(f"Top-1 Accuracy:  {result['top1_accuracy'] * 100:.1f}% (Gate Target >= 70%)")
    print(f"Top-3 Accuracy:  {result['top3_accuracy'] * 100:.1f}%")
    print(f"Gate Status:     {'PASSED' if result['gate_passed'] else 'FAILED'}")
    print("=" * 60)
