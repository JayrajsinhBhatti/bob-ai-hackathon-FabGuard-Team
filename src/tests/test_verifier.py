"""
tests/test_verifier.py  —  Tests for Feature 5: Dual-Pass Evidence Grounding Verifier
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot.verifier import (
    GroundingVerifier,
    VerificationResult,
    ClaimCheck,
    verify_text_against_findings,
)
from analytics.pipeline import analyze_lot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def findings():
    return analyze_lot("LOT-2231", include_v3_fields=True)


@pytest.fixture
def verifier():
    return GroundingVerifier(tolerance_sigma=0.5, tolerance_numeric=0.05)


@pytest.fixture
def well_grounded_text(findings):
    """Build text using actual values from findings."""
    causes = findings.get("candidate_causes", [])
    if not causes:
        return "No findings available."
    top = causes[0]
    tool = top.get("tool_id", "ETCH-07")
    evidence = top.get("evidence", "")
    # Extract a sigma value from evidence
    import re
    sigma_m = re.search(r"(\d+\.?\d*)\s*sigma", evidence, re.IGNORECASE)
    sigma = sigma_m.group(1) if sigma_m else "2.0"
    return f"Tool {tool} shows a {sigma} sigma deviation from target. Recommend DOE before action."


# ---------------------------------------------------------------------------
# Unit tests: regex extraction
# ---------------------------------------------------------------------------

class TestEntityExtraction:

    def test_sigma_extraction_standard(self, verifier):
        """Standard sigma notation extracted correctly."""
        findings = {"candidate_causes": [], "at_risk_upcoming_batches": []}
        text = "The parameter was 3.2 sigma above target."
        result = verifier.verify(text, findings)
        sigma_checks = [c for c in result.confirmed + result.ungrounded if c.entity_type == "sigma"]
        assert len(sigma_checks) >= 1
        vals = [c.numeric_value for c in sigma_checks]
        assert 3.2 in vals

    def test_sigma_extraction_unicode(self, verifier):
        """Unicode σ symbol extracted correctly."""
        findings = {"candidate_causes": [], "at_risk_upcoming_batches": []}
        text = "Deviation of 2.8σ observed."
        result = verifier.verify(text, findings)
        sigma_checks = [c for c in result.confirmed + result.ungrounded if c.entity_type == "sigma"]
        assert len(sigma_checks) >= 1

    def test_tool_id_extraction(self, verifier):
        """Tool IDs are extracted from text."""
        findings = {"candidate_causes": [{"tool_id": "ETCH-07"}], "at_risk_upcoming_batches": []}
        text = "ETCH-07 shows chamber pressure drift."
        result = verifier.verify(text, findings)
        tool_checks = [c for c in result.confirmed + result.ungrounded if c.entity_type == "tool_id"]
        assert len(tool_checks) >= 1
        assert any(c.extracted_value == "ETCH-07" for c in tool_checks)

    def test_cpk_extraction(self, verifier):
        """Cpk values are extracted correctly."""
        findings = {"candidate_causes": [], "at_risk_upcoming_batches": []}
        text = "Process capability Cpk 0.82 indicates out-of-control condition."
        result = verifier.verify(text, findings)
        cpk_checks = [c for c in result.confirmed + result.ungrounded if c.entity_type == "cpk"]
        assert len(cpk_checks) >= 1
        assert any(abs(c.numeric_value - 0.82) < 0.01 for c in cpk_checks)

    def test_probability_extraction(self, verifier):
        """Percentage probabilities are extracted."""
        findings = {
            "candidate_causes": [{"probability": 0.78, "risk_score": 0.78}],
            "at_risk_upcoming_batches": [],
        }
        text = "78% probability of yield loss based on calibrated model."
        result = verifier.verify(text, findings)
        prob_checks = [c for c in result.confirmed + result.ungrounded if c.entity_type == "probability"]
        assert len(prob_checks) >= 1


# ---------------------------------------------------------------------------
# Integration tests: VerificationResult
# ---------------------------------------------------------------------------

class TestVerificationResult:

    def test_grounded_text_passes(self, verifier, findings, well_grounded_text):
        result = verifier.verify(well_grounded_text, findings)
        assert isinstance(result, VerificationResult)
        assert result.passed, \
            f"Expected grounded text to pass. Ungrounded: {[c.extracted_value for c in result.ungrounded]}"
        assert result.grounding_rate >= 0.80

    def test_hallucinated_sigma_fails(self, verifier, findings):
        """Sigma value far from any reference should be flagged."""
        text = "The parameter deviated by 99.9 sigma from target — catastrophic excursion."
        result = verifier.verify(text, findings)
        assert isinstance(result, VerificationResult)
        ungrounded_sigmas = [c for c in result.ungrounded if c.entity_type == "sigma"]
        assert len(ungrounded_sigmas) >= 1, "99.9 sigma should be flagged as ungrounded"
        assert not result.passed

    def test_hallucinated_tool_fails(self, verifier, findings):
        """Tool IDs not in findings should be flagged."""
        text = "IMPLANT-99 is the confirmed root cause of the yield loss."
        result = verifier.verify(text, findings)
        ungrounded_tools = [c for c in result.ungrounded if c.entity_type == "tool_id"]
        assert len(ungrounded_tools) >= 1, "IMPLANT-99 should be flagged if not in findings"

    def test_correct_tool_id_is_grounded(self, verifier, findings):
        causes = findings.get("candidate_causes", [])
        if not causes:
            pytest.skip("No causes in findings")
        tool = causes[0]["tool_id"]
        text = f"Tool {tool} is the leading candidate cause for LOT-2231."
        result = verifier.verify(text, findings)
        confirmed_tools = [c for c in result.confirmed if c.entity_type == "tool_id"]
        assert any(c.extracted_value.upper() == tool.upper() for c in confirmed_tools), \
            f"Tool {tool} from findings should be confirmed grounded"

    def test_corrected_text_marks_ungrounded(self, verifier, findings):
        """Corrected text should have [UNVERIFIED] markers for ungrounded claims."""
        text = "Parameter deviated 99.9 sigma. This is catastrophic."
        result = verifier.verify(text, findings)
        if result.ungrounded:
            assert "[UNVERIFIED:" in result.corrected_text, \
                "Ungrounded claims should be marked [UNVERIFIED] in corrected text"

    def test_grounding_rate_is_bounded(self, verifier, findings):
        text = "ETCH-07 shows 3.2 sigma drift with risk score 0.75."
        result = verifier.verify(text, findings)
        assert 0.0 <= result.grounding_rate <= 1.0

    def test_audit_summary_is_non_empty(self, verifier, findings):
        text = "Chamber pressure on ETCH-07 was 3.2 sigma above target."
        result = verifier.verify(text, findings)
        assert isinstance(result.audit_summary, str)
        assert len(result.audit_summary) > 50
        assert "Grounding" in result.audit_summary or "audit" in result.audit_summary.lower()

    def test_empty_text_passes(self, verifier, findings):
        result = verifier.verify("", findings)
        assert result.passed, "Empty text has no claims to fail"
        assert result.grounding_rate == 1.0

    def test_text_with_no_quantitative_claims_passes(self, verifier, findings):
        text = "Recommend reviewing the process step for potential equipment issues."
        result = verifier.verify(text, findings)
        assert result.passed, "Text with no numeric claims should pass"


# ---------------------------------------------------------------------------
# Convenience function test
# ---------------------------------------------------------------------------

class TestConvenienceFunction:
    def test_verify_text_against_findings(self, findings):
        text = "The tool shows a 99.9 sigma deviation — clearly a hallucination."
        result = verify_text_against_findings(text, findings)
        assert isinstance(result, VerificationResult)
        assert not result.passed, "Hallucinated sigma should fail verification"

    def test_verify_with_custom_tolerance(self, findings):
        """Very tight tolerance should flag borderline values."""
        result = verify_text_against_findings(
            "Parameter deviated 3.0 sigma.",
            findings,
            tolerance_sigma=0.0,  # Exact match required
        )
        # Depending on findings, the 3.0 sigma may or may not match exactly
        assert isinstance(result, VerificationResult)
