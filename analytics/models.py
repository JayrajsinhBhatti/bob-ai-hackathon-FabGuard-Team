"""Data models and contract definitions for Bob Fab Analytics Core."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class CandidateCause:
    """Represents a ranked root cause candidate for an affected lot."""
    step: str
    tool_id: str
    parameter: str
    spatial_signature: str
    deviation_score: float
    confidence: float
    sample_size: int
    evidence: str
    probability: Optional[float] = None
    risk_score: Optional[float] = None
    confidence_basis: Optional[str] = None

    def to_dict(self, include_v3_fields: bool = False) -> Dict[str, Any]:
        """Convert to dict conforming strictly to the contract."""
        data: Dict[str, Any] = {
            "step": self.step,
            "tool_id": self.tool_id,
            "parameter": self.parameter,
            "spatial_signature": self.spatial_signature,
            "deviation_score": round(self.deviation_score, 4),
            "confidence": round(self.confidence, 4),
            "sample_size": int(self.sample_size),
            "evidence": self.evidence,
        }
        if include_v3_fields:
            data["probability"] = round(self.probability, 4) if self.probability is not None else None
            data["risk_score"] = round(self.risk_score, 4) if self.risk_score is not None else None
            data["confidence_basis"] = self.confidence_basis
        return data


@dataclass
class AtRiskBatch:
    """Represents an upcoming in-progress lot flagged for yield risk."""
    lot_id: str
    risk_score: float
    matched_signature: str
    probability: Optional[float] = None

    def to_dict(self, include_v3_fields: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "lot_id": self.lot_id,
            "risk_score": round(self.risk_score, 4),
            "matched_signature": self.matched_signature,
        }
        if include_v3_fields and self.probability is not None:
            data["probability"] = round(self.probability, 4)
        return data


@dataclass
class RootCauseFindings:
    """The official findings contract shared with Person C and Person D."""
    lot_id: str
    candidate_causes: List[CandidateCause] = field(default_factory=list)
    at_risk_upcoming_batches: List[AtRiskBatch] = field(default_factory=list)

    def to_dict(self, include_v3_fields: bool = False) -> Dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "candidate_causes": [c.to_dict(include_v3_fields=include_v3_fields) for c in self.candidate_causes],
            "at_risk_upcoming_batches": [b.to_dict(include_v3_fields=include_v3_fields) for b in self.at_risk_upcoming_batches],
        }


@dataclass
class WesternElectricViolations:
    """Detected Western Electric rules violations."""
    rule1_beyond_3sigma: List[int] = field(default_factory=list)  # indices of points > 3 sigma
    rule2_two_of_three_beyond_2sigma: List[int] = field(default_factory=list)  # indices
    rule3_four_of_five_beyond_1sigma: List[int] = field(default_factory=list)  # indices
    rule4_eight_on_one_side: List[int] = field(default_factory=list)  # indices

    @property
    def has_violations(self) -> bool:
        return any([
            self.rule1_beyond_3sigma,
            self.rule2_two_of_three_beyond_2sigma,
            self.rule3_four_of_five_beyond_1sigma,
            self.rule4_eight_on_one_side,
        ])

    @property
    def total_violation_count(self) -> int:
        return (
            len(self.rule1_beyond_3sigma)
            + len(self.rule2_two_of_three_beyond_2sigma)
            + len(self.rule3_four_of_five_beyond_1sigma)
            + len(self.rule4_eight_on_one_side)
        )


@dataclass
class SPCResult:
    """Statistical Process Control summary for a parameter."""
    step: str
    tool_id: str
    parameter: str
    mean: float
    std_dev: float
    sample_size: int
    spec_min: Optional[float]
    spec_max: Optional[float]
    cpk: Optional[float]
    ppk: Optional[float]
    is_out_of_capability: bool
    violations: WesternElectricViolations
    latest_z_score: float = 0.0
    latest_value: float = 0.0
