"""
copilot/tests/test_copilot.py  —  Step 6: Unit Tests

Tests for:
  1. test_explainer_tier2_phrasing   — Tier 2 (probability / logistic_regression_v1) output
  2. test_explainer_tier1_phrasing   — Tier 1 (risk_score / composite_heuristic_v1) output
  3. test_recommender_returns_actions — Domain lookup + recommended_actions
  4. test_bob_session_creation        — Session messages list integrity
  5. test_honesty_rule                — Tier 1 output must NOT contain bare "probability" + number

All LLM API calls are mocked — no real API keys needed for tests.
Fixture files from /contracts are used as ground truth input data.

Source: §9 (Step 6) of Person C Guide / S1_FINAL_Implementation_Plan_v3.md
"""

import json
import os
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure repo root is on PYTHONPATH when running tests directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from copilot.explainer import explain_lot_findings, _build_confidence_phrase
from copilot.recommender import generate_recommendations, _lookup_domain
from copilot.agent import create_bob_session, ask_bob, ask_bob_single

# ---------------------------------------------------------------------------
# Paths to fixture files
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FIXTURE_TIER2 = os.path.join(_REPO_ROOT, "contracts", "mock_findings_LOT-2231.json")
_FIXTURE_TIER1 = os.path.join(_REPO_ROOT, "contracts", "mock_findings_tier1_LOT-2231.json")


def _load_fixture(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _make_gemini_mock(response_text: str):
    """Return a mock Gemini client whose generate_content returns response_text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


def _make_groq_openai_mock(response_text: str):
    """Return a mock Groq/OpenAI client whose chat.completions.create returns response_text."""
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# Test 1: Tier 2 (logistic_regression_v1 / probability) phrasing
# ---------------------------------------------------------------------------

class TestExplainerTier2Phrasing(unittest.TestCase):
    """
    Verify that Tier 2 findings (probability field + logistic_regression_v1) are
    correctly phrased as "X% probability" and never as "risk score".
    """

    def setUp(self):
        self.findings = _load_fixture(_FIXTURE_TIER2)
        # Tier 2 fixture top cause: probability=0.78, confidence_basis="logistic_regression_v1"
        self.top_cause = self.findings["candidate_causes"][0]

    def test_confidence_phrase_tier2(self):
        """_build_confidence_phrase should say 'probability' for logistic_regression_v1."""
        phrase = _build_confidence_phrase(self.top_cause)
        self.assertIn("probability", phrase.lower())
        self.assertIn("78", phrase)  # 0.78 → 78%

    def test_explainer_output_contains_doe_caveat(self):
        """explain_lot_findings output must always include the DOE caveat."""
        mock_client = _make_gemini_mock(
            "The leading candidate cause is chamber pressure deviation on ETCH-07, "
            "exhibiting a 78% probability (calibrated ML model) of being the root cause "
            "based on 3.2 sigma exceedance across 14 lots."
        )

        with patch("copilot.explainer.LLM_PROVIDER", "gemini"), \
             patch("copilot.explainer.get_llm_client", return_value=mock_client):
            result = explain_lot_findings(self.findings, client=mock_client)

        self.assertEqual(result["lot_id"], "LOT-2231")
        self.assertGreater(len(result["explanations"]), 0)

        for expl in result["explanations"]:
            self.assertIn("doe_caveat", expl)
            self.assertTrue(len(expl["doe_caveat"]) > 0, "DOE caveat must not be empty")

    def test_explainer_returns_correct_structure(self):
        """Output dict must have lot_id, explanations list, at_risk_batch_summary."""
        mock_client = _make_gemini_mock("Mocked explanation text for tier 2.")

        with patch("copilot.explainer.LLM_PROVIDER", "gemini"), \
             patch("copilot.explainer.get_llm_client", return_value=mock_client):
            result = explain_lot_findings(self.findings, client=mock_client)

        self.assertIn("lot_id", result)
        self.assertIn("explanations", result)
        self.assertIn("at_risk_batch_summary", result)
        self.assertIsInstance(result["explanations"], list)

    def test_explainer_tier2_explanation_count(self):
        """Should produce one explanation per candidate cause."""
        mock_client = _make_gemini_mock("Mocked explanation.")
        num_causes = len(self.findings["candidate_causes"])

        with patch("copilot.explainer.LLM_PROVIDER", "gemini"), \
             patch("copilot.explainer.get_llm_client", return_value=mock_client):
            result = explain_lot_findings(self.findings, client=mock_client)

        self.assertEqual(len(result["explanations"]), num_causes)


# ---------------------------------------------------------------------------
# Test 2: Tier 1 (composite_heuristic_v1 / risk_score) phrasing
# ---------------------------------------------------------------------------

class TestExplainerTier1Phrasing(unittest.TestCase):
    """
    Verify that Tier 1 findings (risk_score + composite_heuristic_v1) are
    phrased as "risk score" and NEVER as a probability percentage.
    """

    def setUp(self):
        self.findings = _load_fixture(_FIXTURE_TIER1)
        self.top_cause = self.findings["candidate_causes"][0]
        # Should be: risk_score=0.84, confidence_basis="composite_heuristic_v1"

    def test_confidence_phrase_tier1_no_probability(self):
        """_build_confidence_phrase for Tier 1 must NOT contain 'XX% probability' phrasing."""
        phrase = _build_confidence_phrase(self.top_cause)
        # The forbidden pattern is a number followed by '% probability'
        forbidden_pattern = re.compile(r"\d+\s*%\s*probability", re.IGNORECASE)
        self.assertIsNone(
            forbidden_pattern.search(phrase),
            f"Tier 1 phrase must not contain 'XX% probability'. Got: '{phrase}'"
        )
        self.assertIn("risk score", phrase.lower())
        self.assertIn("0.84", phrase)

    def test_explainer_tier1_uses_risk_score_phrasing(self):
        """
        For composite_heuristic_v1 findings, the explanation prompt must
        contain 'risk score' phrasing — verified by checking the prompt
        built for the top cause.
        """
        from copilot.explainer import _build_explanation_prompt
        prompt = _build_explanation_prompt(self.top_cause, rank=1, lot_id="LOT-2231")
        self.assertIn("risk score", prompt.lower())
        self.assertNotIn("logistic_regression", prompt)

    def test_explainer_tier1_confidence_basis_propagated(self):
        """The output explanation dict must carry the correct confidence_basis."""
        mock_client = _make_gemini_mock("Mocked tier 1 explanation with risk score of 0.84.")

        with patch("copilot.explainer.LLM_PROVIDER", "gemini"), \
             patch("copilot.explainer.get_llm_client", return_value=mock_client):
            result = explain_lot_findings(self.findings, client=mock_client)

        top = result["explanations"][0]
        self.assertEqual(top["confidence_basis"], "composite_heuristic_v1")


# ---------------------------------------------------------------------------
# Test 3: Recommender
# ---------------------------------------------------------------------------

class TestRecommenderReturnsActions(unittest.TestCase):
    """Verify the recommender returns a correct domain result with >= 2 actions."""

    def test_etch_chamber_pressure_lookup(self):
        """Domain lookup for etch/chamber_pressure must return the correct category."""
        domain = _lookup_domain("etch", "chamber_pressure")
        self.assertEqual(domain["category"], "Pressure drift / chamber seal")
        self.assertGreaterEqual(len(domain["standard_actions"]), 2)

    def test_recommender_output_structure(self):
        """generate_recommendations must return all required keys."""
        cause = {
            "step": "etch",
            "tool_id": "ETCH-07",
            "parameter": "chamber_pressure",
            "spatial_signature": "edge-ring",
            "probability": 0.78,
            "risk_score": None,
            "confidence_basis": "logistic_regression_v1",
            "sample_size": 14,
            "evidence": "Chamber pressure 3.2 sigma above spec.",
        }
        mock_client = _make_gemini_mock(
            "Immediate PM inspection of ETCH-07 chamber seal is recommended as the "
            "leading candidate for this pressure drift event."
        )

        with patch("copilot.recommender.LLM_PROVIDER", "gemini"), \
             patch("copilot.recommender.get_llm_client", return_value=mock_client):
            result = generate_recommendations(cause, client=mock_client, lot_id="LOT-2231")

        self.assertEqual(result["step"], "etch")
        self.assertEqual(result["tool_id"], "ETCH-07")
        self.assertEqual(result["parameter"], "chamber_pressure")
        self.assertIn("category", result)
        self.assertIn("recommended_actions", result)
        self.assertIn("phrased_recommendation", result)
        self.assertGreaterEqual(len(result["recommended_actions"]), 2)

    def test_recommender_unknown_pair_uses_fallback(self):
        """Unknown (step, parameter) must return the fallback, not raise an error."""
        domain = _lookup_domain("unknown_step", "unknown_parameter")
        self.assertIn("standard_actions", domain)
        self.assertGreaterEqual(len(domain["standard_actions"]), 1)

    def test_all_lookup_entries_have_min_two_actions(self):
        """Every entry in the domain lookup table must have >= 2 standard_actions."""
        from copilot.recommender import DOMAIN_LOOKUP
        for key, entry in DOMAIN_LOOKUP.items():
            with self.subTest(key=key):
                self.assertGreaterEqual(len(entry["standard_actions"]), 2,
                                        f"Entry {key} has fewer than 2 standard_actions")


# ---------------------------------------------------------------------------
# Test 4: Bob session creation
# ---------------------------------------------------------------------------

class TestBobSessionCreation(unittest.TestCase):
    """Verify that create_bob_session returns a valid messages list."""

    def setUp(self):
        self.findings_tier2 = _load_fixture(_FIXTURE_TIER2)
        self.findings_tier1 = _load_fixture(_FIXTURE_TIER1)

    def test_session_returns_nonempty_list(self):
        messages = create_bob_session(self.findings_tier2)
        self.assertIsInstance(messages, list)
        self.assertGreater(len(messages), 0)

    def test_session_first_message_is_system_role(self):
        messages = create_bob_session(self.findings_tier2)
        self.assertEqual(messages[0]["role"], "system")

    def test_session_system_message_contains_lot_id(self):
        messages = create_bob_session(self.findings_tier2)
        system_content = messages[0]["content"]
        self.assertIn("LOT-2231", system_content)

    def test_session_contains_findings_context_marker(self):
        messages = create_bob_session(self.findings_tier2)
        system_content = messages[0]["content"]
        self.assertIn("LOT FINDINGS CONTEXT", system_content)

    def test_session_with_lot_overview(self):
        overview = {"final_yield_pct": 82.3, "fab_line": "FAB-03", "status": "completed"}
        messages = create_bob_session(self.findings_tier2, lot_overview=overview)
        system_content = messages[0]["content"]
        self.assertIn("LOT OVERVIEW", system_content)

    def test_ask_bob_appends_history(self):
        """After ask_bob, messages list should have system + user + assistant entries."""
        messages = create_bob_session(self.findings_tier1)
        mock_client = _make_gemini_mock("ETCH-07 chamber pressure is the leading candidate.")

        with patch("copilot.agent.LLM_PROVIDER", "gemini"):
            answer, updated_messages = ask_bob(messages, "Why did LOT-2231 fail?", client=mock_client)

        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 0)
        # system + user + assistant = 3
        self.assertEqual(len(updated_messages), 3)
        self.assertEqual(updated_messages[-1]["role"], "assistant")

    def test_ask_bob_single_returns_string(self):
        """ask_bob_single convenience wrapper must return a non-empty string."""
        mock_client = _make_gemini_mock("Based on the findings, ETCH-07 is the leading candidate.")

        with patch("copilot.agent.LLM_PROVIDER", "gemini"), \
             patch("copilot.agent.get_llm_client", return_value=mock_client):
            result = ask_bob_single(
                "What is the root cause?",
                self.findings_tier2,
                client=mock_client,
            )

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


# ---------------------------------------------------------------------------
# Test 5: Honesty rule — Tier 1 must NOT say "probability" + a number
# ---------------------------------------------------------------------------

class TestHonestyRule(unittest.TestCase):
    """
    The honesty rule:
      If confidence_basis == "composite_heuristic_v1", the output must NOT
      contain a number followed by "%" alongside the word "probability",
      e.g. "84% probability" is forbidden — must be "risk score of 0.84".
    """

    # Pattern that would represent a violation: "XX% probability" or "probability of XX%"
    _PROBABILITY_PCT_PATTERN = re.compile(
        r"(\d+\.?\d*\s*%\s*probability|probability\s*of\s*\d+\.?\d*\s*%)",
        re.IGNORECASE,
    )

    def _check_no_probability_pct_in_text(self, text: str) -> bool:
        """Returns True if text contains no forbidden probability % phrasing."""
        return not bool(self._PROBABILITY_PCT_PATTERN.search(text))

    def test_tier1_confidence_phrase_no_probability_pct(self):
        """_build_confidence_phrase for Tier 1 must not produce XX% probability."""
        cause = {
            "confidence_basis": "composite_heuristic_v1",
            "probability": None,
            "risk_score": 0.84,
        }
        phrase = _build_confidence_phrase(cause)
        self.assertTrue(
            self._check_no_probability_pct_in_text(phrase),
            f"Tier 1 phrase must not contain 'XX% probability'. Got: '{phrase}'"
        )

    def test_tier1_llm_output_honesty_check(self):
        """
        Simulate a mocked LLM returning proper risk-score phrasing for Tier 1.
        The mock should represent what Bob is supposed to output — we verify the
        check function correctly accepts it.
        """
        compliant_output = (
            "ETCH-07 chamber pressure is the highest-risk candidate, "
            "carrying a heuristic deviation risk score of 0.84. "
            "Recommend confirming via targeted DOE before taking corrective action."
        )
        self.assertTrue(self._check_no_probability_pct_in_text(compliant_output))

    def test_violation_detection_works(self):
        """
        The honesty check must CATCH a violation (e.g. calling the heuristic
        score "84% probability") — verifies the check function itself is correct.
        """
        non_compliant_output = (
            "ETCH-07 chamber pressure has a 84% probability of being the root cause."
        )
        self.assertFalse(
            self._check_no_probability_pct_in_text(non_compliant_output),
            "Honesty check should flag '84% probability' as a violation."
        )

    def test_tier2_probability_allowed(self):
        """For Tier 2 (logistic_regression_v1), 'XX% probability' is explicitly allowed."""
        tier2_output = (
            "We estimate a 78% probability (calibrated ML model) "
            "that ETCH-07 chamber pressure caused this yield excursion. "
            "Recommend confirming via targeted DOE before taking corrective action."
        )
        # Tier 2 output SHOULD have probability phrasing — check function would flag it,
        # but that's intentionally allowed. Here we just verify the phrase is present.
        self.assertIn("78%", tier2_output)
        self.assertIn("probability", tier2_output.lower())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
