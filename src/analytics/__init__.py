"""Bob Fab Copilot — Analytics Core Package (Person B).

Public Exports:
- analyze_lot: Analyze root causes and batch risks for a lot
- analyze_all: Analyze all lots
- RootCauseRanker: Equipment and parameter root cause ranking
- BatchRiskPredictor: Yield risk prediction for in-progress lots
- classify_spatial_signature: Wafer defect pattern classification
- calculate_cpk: Process capability index calculation
- calculate_ppk: Process performance index calculation
- detect_western_electric_violations: Western Electric rules detection
- validate_ranker: Validation harness against ground-truth scenarios
"""

from analytics.batch_risk import BatchRiskPredictor
from analytics.data_access import DataRepository, InMemoryRepository, SQLiteRepository
from analytics.models import (
    AtRiskBatch,
    CandidateCause,
    RootCauseFindings,
    SPCResult,
    WesternElectricViolations,
)
from analytics.pipeline import analyze_all, analyze_lot
from analytics.root_cause import RootCauseRanker
from analytics.spatial import (
    SpatialClassificationResult,
    SpatialConfig,
    analyze_spatial_signature,
    classify_spatial_signature,
)
from analytics.spc import (
    analyze_parameter_series,
    calculate_cpk,
    calculate_ppk,
    detect_western_electric_violations,
    is_out_of_capability,
)
from analytics.validate import validate_ranker

__all__ = [
    "analyze_lot",
    "analyze_all",
    "RootCauseRanker",
    "BatchRiskPredictor",
    "classify_spatial_signature",
    "analyze_spatial_signature",
    "SpatialConfig",
    "SpatialClassificationResult",
    "calculate_cpk",
    "calculate_ppk",
    "is_out_of_capability",
    "detect_western_electric_violations",
    "analyze_parameter_series",
    "validate_ranker",
    "CandidateCause",
    "AtRiskBatch",
    "RootCauseFindings",
    "SPCResult",
    "WesternElectricViolations",
    "DataRepository",
    "SQLiteRepository",
    "InMemoryRepository",
]
