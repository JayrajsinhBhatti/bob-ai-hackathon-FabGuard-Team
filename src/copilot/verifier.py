"""
copilot/verifier.py  —  Feature 5: Dual-Pass Evidence Grounding Verifier

Intercepts all LLM-generated briefings before they reach IBM Bob and
audits every quantitative claim against the underlying findings contract.

In semiconductor manufacturing, an LLM exaggerating a sigma value, misquoting
a Cpk, or inventing a tool ID can trigger misdirected equipment maintenance
costing thousands of dollars. This verifier is the last line of defense.

Two-pass verification:
  Pass 1 — Entity Extraction:
    Extracts all quantitative claims from LLM text:
      - Sigma values  (e.g., "3.2 sigma", "2.8σ")
      - Cpk values    (e.g., "Cpk 0.82", "Cpk=1.21")
      - Tool IDs      (e.g., "ETCH-07", "LITHO-03")
      - Probabilities (e.g., "78%", "82% probability")
      - Risk scores   (e.g., "risk score 0.73")

  Pass 2 — Grounding Check:
    Each extracted entity is cross-checked against the findings contract.
    Entities not grounded in the contract are flagged as UNGROUNDED.
    Grounded entities are CONFIRMED.

Output:
    A VerificationResult with:
      - passed: bool (all claims grounded)
      - confirmed: List of grounded claims
      - ungrounded: List of suspicious claims
      - corrected_text: Optional corrected text (inserts [UNVERIFIED] markers)
      - audit_summary: Human-readable audit report

Usage:
    from copilot.verifier import GroundingVerifier, verify_text_against_findings
    result = verify_text_against_findings(llm_text, findings)
    if not result.passed:
        print(result.audit_summary)
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Regex patterns for entity extraction
# ---------------------------------------------------------------------------

# Sigma values: "3.2 sigma", "3.2σ", "2-sigma", "+3.2 sigma"
_SIGMA_PATTERN = re.compile(
    r"[+-]?\s*(\d+\.?\d*)\s*(?:sigma|σ|[-–]\s*sigma)",
    re.IGNORECASE,
)

# Cpk values: "Cpk 0.82", "Cpk=1.21", "Cpk of 0.9"
_CPK_PATTERN = re.compile(
    r"(?:Cpk|cpk|C_pk)\s*(?:of\s*|=\s*|:\s*)?(\d+\.?\d*)",
    re.IGNORECASE,
)

# Tool IDs: ETCH-07, LITHO-03, CVD-11, CMP-02, IMPLANT-05 (ignore SOP- and PM- prefixes)
_TOOL_PATTERN = re.compile(
    r"(?<!SOP-)(?<!PM-)(?<!sop-)(?<!pm-)\b((?:ETCH|LITHO|CVD|CMP|IMPLANT|etch|litho|cvd|cmp|implant)-\d{2})\b",
    re.IGNORECASE,
)

# Probabilities: "78%", "82% probability", "78 percent" (excluding decimals like 80.34%)
_PROB_PATTERN = re.compile(
    r"(?<![\.\d])(\d{1,3})\s*%(?:\s+probability)?",
    re.IGNORECASE,
)

# Risk scores: "risk score 0.73", "score of 0.82"
_RISK_SCORE_PATTERN = re.compile(
    r"(?:risk\s+score|score)\s+(?:of\s+)?(\d+\.?\d*)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ClaimCheck:
    entity_type: str        # "sigma", "cpk", "tool_id", "probability", "risk_score"
    extracted_value: str    # The raw extracted string
    numeric_value: Optional[float]  # Parsed float if applicable
    grounded: bool          # Whether found in findings contract
    context: str            # Surrounding text snippet


@dataclass
class VerificationResult:
    passed: bool
    confirmed: List[ClaimCheck] = field(default_factory=list)
    ungrounded: List[ClaimCheck] = field(default_factory=list)
    corrected_text: Optional[str] = None
    audit_summary: str = ""
    grounding_rate: float = 1.0


# ---------------------------------------------------------------------------
# GroundingVerifier
# ---------------------------------------------------------------------------

class GroundingVerifier:
    """
    Dual-pass evidence grounding verifier for LLM-generated fab briefings.
    Extracts all quantitative claims and checks them against the findings contract.
    """

    def __init__(self, tolerance_sigma: float = 0.5, tolerance_numeric: float = 0.05):
        """
        Args:
            tolerance_sigma:   Max allowed deviation between claimed and actual sigma (±σ).
            tolerance_numeric: Max allowed relative deviation for Cpk, risk score, probability.
        """
        self.tol_sigma = tolerance_sigma
        self.tol_numeric = tolerance_numeric

    # -----------------------------------------------------------------------
    # Reference value extraction from findings contract
    # -----------------------------------------------------------------------

    def _extract_reference_sigmas(self, findings: Dict[str, Any]) -> List[float]:
        """Pull all sigma values referenced in the findings evidence strings."""
        sigmas = []
        for cause in findings.get("candidate_causes", []):
            evidence = cause.get("evidence", "")
            for m in _SIGMA_PATTERN.finditer(evidence):
                try:
                    sigmas.append(float(m.group(1)))
                except ValueError:
                    pass
        return sigmas

    def _extract_reference_cpks(self, findings: Dict[str, Any]) -> List[float]:
        """Pull all Cpk values from findings evidence."""
        cpks = []
        for cause in findings.get("candidate_causes", []):
            evidence = cause.get("evidence", "")
            for m in _CPK_PATTERN.finditer(evidence):
                try:
                    cpks.append(float(m.group(1)))
                except ValueError:
                    pass
        return cpks

    def _extract_reference_tool_ids(self, findings: Dict[str, Any]) -> List[str]:
        """Pull all tool IDs referenced in findings, equipment routing, and active fab inventory."""
        tools = set()
        for cause in findings.get("candidate_causes", []):
            tid = cause.get("tool_id")
            if tid:
                tools.add(tid.upper())
        for eq in findings.get("equipment_used", []):
            if isinstance(eq, str):
                tools.add(eq.upper())
            elif isinstance(eq, dict) and eq.get("tool_id"):
                tools.add(eq.get("tool_id").upper())
        for tool in findings.get("all_fab_tools", []):
            tools.add(str(tool).upper())

        # Pull actual fab tool IDs from database if present
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bob_fab.db")
            if not os.path.exists(db_path):
                db_path = "src/bob_fab.db"
            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as conn:
                    for r in conn.cursor().execute("SELECT DISTINCT tool_id FROM process_steps;").fetchall():
                        if r[0]:
                            tools.add(r[0].upper())
        except Exception:
            pass

        # Pull historical fab tools from SOP knowledge base if present
        try:
            import json
            kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "knowledge", "fab_sop_kb.json")
            if not os.path.exists(kb_path):
                kb_path = "src/data/knowledge/fab_sop_kb.json"
            if os.path.exists(kb_path):
                with open(kb_path, "r", encoding="utf-8") as f:
                    kb_data = json.load(f)
                    for sop in kb_data:
                        for prec in sop.get("root_cause_precedents", []):
                            for tm in _TOOL_PATTERN.finditer(prec):
                                tools.add(tm.group(1).upper())
        except Exception:
            pass

        return list(tools)

    def _extract_reference_probabilities(self, findings: Dict[str, Any]) -> List[float]:
        """Pull all probability/risk score values from findings."""
        probs = []
        for cause in findings.get("candidate_causes", []):
            p = cause.get("probability")
            r = cause.get("risk_score")
            if p is not None:
                probs.append(float(p) * 100)  # Convert 0-1 to 0-100 for % comparison
            if r is not None:
                probs.append(float(r) * 100)
        return probs

    def _extract_reference_risk_scores(self, findings: Dict[str, Any]) -> List[float]:
        """Pull all 0-1 risk scores from findings."""
        scores = []
        for cause in findings.get("candidate_causes", []):
            r = cause.get("risk_score")
            p = cause.get("probability")
            if r is not None:
                scores.append(float(r))
            if p is not None:
                scores.append(float(p))
        return scores

    # -----------------------------------------------------------------------
    # Grounding check helpers
    # -----------------------------------------------------------------------

    def _is_grounded_numeric(
        self, value: float, reference_values: List[float], tolerance: float
    ) -> bool:
        """Check if a numeric value is within tolerance of any reference value."""
        if not reference_values:
            return True  # Can't disprove — assume grounded
        return any(abs(value - ref) <= tolerance for ref in reference_values)

    def _is_grounded_tool(self, tool_id: str, reference_tools: List[str]) -> bool:
        """Check if a tool ID appears in the findings."""
        if not reference_tools:
            return True  # No reference tools to validate against
        return tool_id.upper() in reference_tools

    def _get_context(self, text: str, match: re.Match, window: int = 50) -> str:
        """Extract surrounding text context for a regex match."""
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        snippet = text[start:end].replace("\n", " ").strip()
        return f"...{snippet}..."

    # -----------------------------------------------------------------------
    # Main verification
    # -----------------------------------------------------------------------

    def verify(self, llm_text: str, findings: Dict[str, Any]) -> VerificationResult:
        """
        Run dual-pass verification of LLM text against findings contract.

        Pass 1: Extract all quantitative entities from the LLM text.
        Pass 2: Cross-check each entity against the findings contract.

        Args:
            llm_text: The LLM-generated explanation/recommendation text.
            findings: The root_cause_findings dict.

        Returns:
            VerificationResult with grounding status for every claim.
        """
        # Build reference data from findings
        ref_sigmas = self._extract_reference_sigmas(findings)
        ref_cpks = self._extract_reference_cpks(findings)
        ref_tools = self._extract_reference_tool_ids(findings)
        ref_probs = self._extract_reference_probabilities(findings)
        ref_scores = self._extract_reference_risk_scores(findings)

        checks: List[ClaimCheck] = []

        # Reference sigmas from findings plus standard fab control limits (1.5, 2.0, 3.0, 6.0)
        valid_sigmas = list(ref_sigmas) + [1.5, 2.0, 3.0, 6.0]
        # --- Extract and check sigma values ---
        for m in _SIGMA_PATTERN.finditer(llm_text):
            try:
                val = float(m.group(1))
            except ValueError:
                continue
            grounded = self._is_grounded_numeric(val, valid_sigmas, self.tol_sigma)
            checks.append(ClaimCheck(
                entity_type="sigma",
                extracted_value=m.group(0),
                numeric_value=val,
                grounded=grounded,
                context=self._get_context(llm_text, m),
            ))

        # --- Extract and check Cpk values ---
        for m in _CPK_PATTERN.finditer(llm_text):
            try:
                val = float(m.group(1))
            except ValueError:
                continue
            grounded = self._is_grounded_numeric(
                val, ref_cpks, max(0.10, val * self.tol_numeric)
            )
            checks.append(ClaimCheck(
                entity_type="cpk",
                extracted_value=m.group(0),
                numeric_value=val,
                grounded=grounded,
                context=self._get_context(llm_text, m),
            ))

        # --- Extract and check tool IDs ---
        for m in _TOOL_PATTERN.finditer(llm_text):
            tid = m.group(1).upper()
            grounded = self._is_grounded_tool(tid, ref_tools)
            checks.append(ClaimCheck(
                entity_type="tool_id",
                extracted_value=tid,
                numeric_value=None,
                grounded=grounded,
                context=self._get_context(llm_text, m),
            ))

        # --- Extract and check probability percentages ---
        for m in _PROB_PATTERN.finditer(llm_text):
            try:
                val = float(m.group(1))
            except ValueError:
                continue
            # Only check if above 1% (filter out incidental percentages like "2% yield")
            if val < 5 or val > 100:
                continue

            ctx = self._get_context(llm_text, m).lower()
            # Only treat as a probability claim if context indicates probability/confidence/likelihood
            # Avoid flagging DOE factor levels (+/-5%), yield values, reductions, or spatial radii
            is_prob_claim = any(kw in ctx for kw in ("probab", "confidence", "likelihood", "chance", "calibrated")) or bool(re.search(r"%\s+probability", m.group(0), re.IGNORECASE))
            if not is_prob_claim:
                continue

            grounded = self._is_grounded_numeric(
                val, ref_probs, max(5.0, val * self.tol_numeric)
            ) if ref_probs else True
            checks.append(ClaimCheck(
                entity_type="probability",
                extracted_value=m.group(0),
                numeric_value=val,
                grounded=grounded,
                context=self._get_context(llm_text, m),
            ))

        # --- Extract and check risk scores ---
        for m in _RISK_SCORE_PATTERN.finditer(llm_text):
            try:
                val = float(m.group(1))
            except ValueError:
                continue
            if val > 1.0:
                continue  # likely a probability in %, skip
            grounded = self._is_grounded_numeric(
                val, ref_scores, max(0.05, val * self.tol_numeric)
            ) if ref_scores else True
            checks.append(ClaimCheck(
                entity_type="risk_score",
                extracted_value=m.group(0),
                numeric_value=val,
                grounded=grounded,
                context=self._get_context(llm_text, m),
            ))

        # Partition results
        confirmed = [c for c in checks if c.grounded]
        ungrounded = [c for c in checks if not c.grounded]
        total = len(checks)
        grounding_rate = (len(confirmed) / total) if total > 0 else 1.0
        passed = len(ungrounded) == 0

        # Build corrected text with [UNVERIFIED] markers
        corrected = llm_text
        if ungrounded:
            for claim in ungrounded:
                val = claim.extracted_value
                if f"[UNVERIFIED: {val}]" in corrected:
                    continue
                # Replace only bare occurrences not already inside [UNVERIFIED: ...]
                pattern = r'(?<!\[UNVERIFIED:\s)(?<!\[UNVERIFIED:)\b' + re.escape(val) + r'\b(?!\s*\])'
                corrected = re.sub(pattern, f"[UNVERIFIED: {val}]", corrected, count=1)

        # Build audit summary
        summary_lines = [
            f"=== Evidence Grounding Audit ===",
            f"Status: {'✅ PASSED' if passed else '⚠️ FLAGGED'}",
            f"Claims audited: {total}  |  Confirmed: {len(confirmed)}  |  Ungrounded: {len(ungrounded)}",
            f"Grounding rate: {grounding_rate:.0%}",
        ]

        if ungrounded:
            summary_lines.append("\nUngrounded claims (not found in findings contract):")
            for claim in ungrounded:
                summary_lines.append(
                    f"  ❌ [{claim.entity_type.upper()}] '{claim.extracted_value}' — "
                    f"not found in findings. Context: {claim.context}"
                )
        if confirmed:
            summary_lines.append("\nConfirmed grounded claims:")
            for claim in confirmed:
                summary_lines.append(
                    f"  ✓ [{claim.entity_type.upper()}] '{claim.extracted_value}'"
                )

        summary_lines.append(
            "\nNote: Grounding check uses ±tolerance matching. "
            "Confirmed does not mean correct — always cross-check with raw findings."
        )

        return VerificationResult(
            passed=passed,
            confirmed=confirmed,
            ungrounded=ungrounded,
            corrected_text=corrected if not passed else llm_text,
            audit_summary="\n".join(summary_lines),
            grounding_rate=round(grounding_rate, 4),
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def verify_text_against_findings(
    llm_text: str,
    findings: Dict[str, Any],
    tolerance_sigma: float = 0.5,
    tolerance_numeric: float = 0.05,
) -> VerificationResult:
    """
    One-shot convenience: verify LLM text against a findings contract.

    Args:
        llm_text:         The LLM-generated text to audit.
        findings:         The root_cause_findings dict.
        tolerance_sigma:  Allowed sigma deviation (±).
        tolerance_numeric: Allowed relative numeric deviation.

    Returns:
        VerificationResult.
    """
    verifier = GroundingVerifier(tolerance_sigma=tolerance_sigma, tolerance_numeric=tolerance_numeric)
    return verifier.verify(llm_text, findings)


# ---------------------------------------------------------------------------
# Retrieval Evaluation & Domain Scope Verification (Concepts 9 & 10)
# ---------------------------------------------------------------------------

@dataclass
class RetrievalEvaluationResult:
    """Quantitative evaluation of retrieval quality and utilization in the generated response."""
    retrieval_precision: float      # Fraction of retrieved docs cited in the response (0.0 to 1.0)
    retrieval_recall: float         # Fraction of key findings entities present in retrieved docs (0.0 to 1.0)
    context_utilization: float      # Lexical / semantic utilization of retrieved context in answer (0.0 to 1.0)
    cited_doc_ids: List[str]        # Doc IDs explicitly cited in the answer
    retrieved_doc_ids: List[str]    # Doc IDs that were fed to the context
    summary: str                    # Human-readable summary of retrieval quality


class RetrievalEvaluator:
    """
    Evaluates retrieval precision, recall, and context utilization
    to provide feedback signals for self-improvement.
    """

    def evaluate(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        answer_text: str,
        findings: Optional[Dict[str, Any]] = None,
    ) -> RetrievalEvaluationResult:
        if not retrieved_docs:
            return RetrievalEvaluationResult(
                retrieval_precision=1.0,
                retrieval_recall=1.0,
                context_utilization=1.0,
                cited_doc_ids=[],
                retrieved_doc_ids=[],
                summary="No retrieval requested or required for this query.",
            )

        retrieved_ids = [
            doc.get("doc_id") or doc.get("id") or str(i)
            for i, doc in enumerate(retrieved_docs)
        ]

        # 1. Retrieval Precision: Docs cited in answer / Total retrieved docs
        cited_ids = []
        answer_upper = answer_text.upper()
        for doc in retrieved_docs:
            doc_id = doc.get("doc_id") or doc.get("id") or ""
            title = doc.get("title", "")
            # Check if doc_id or title is mentioned in the answer
            if doc_id and doc_id.upper() in answer_upper:
                cited_ids.append(doc_id)
            elif title and len(title) > 6 and title.upper() in answer_upper:
                cited_ids.append(doc_id or title)

        precision = len(cited_ids) / max(len(retrieved_docs), 1)
        # Cap at 1.0
        precision = min(1.0, round(precision, 4))

        # 2. Retrieval Recall: Fraction of findings entities captured in retrieved docs
        target_entities = set()
        if findings:
            for suspect in findings.get("suspect_tools", []):
                if isinstance(suspect, dict):
                    tool = suspect.get("tool_id") or suspect.get("tool")
                    if tool:
                        target_entities.add(str(tool).upper())
                elif isinstance(suspect, str):
                    target_entities.add(suspect.upper())

            for param in findings.get("drift_parameters", []):
                if isinstance(param, dict):
                    p_name = param.get("parameter") or param.get("name")
                    if p_name:
                        target_entities.add(str(p_name).upper())
                elif isinstance(param, str):
                    target_entities.add(param.upper())

            step = findings.get("process_step")
            if step:
                target_entities.add(str(step).upper())

        if target_entities:
            # Check how many target entities appear in retrieved doc content
            combined_docs_text = " ".join(
                f"{d.get('title', '')} {d.get('content', '')} {d.get('equipment_type', '')}"
                for d in retrieved_docs
            ).upper()

            matched_entities = sum(
                1 for ent in target_entities if ent in combined_docs_text
            )
            recall = round(matched_entities / len(target_entities), 4)
        else:
            recall = 1.0  # If no specific findings entities to match, neutral 1.0

        # 3. Context Utilization: Overlap between retrieved keywords and answer keywords
        stop_words = {
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
            "with", "by", "from", "is", "are", "was", "were", "this", "that",
            "these", "those", "it", "its", "as", "be", "of", "lot", "bob"
        }
        all_doc_words = set(re.findall(r"\b[A-Za-z0-9_-]{3,}\b", " ".join(
            f"{d.get('title', '')} {d.get('content', '')}" for d in retrieved_docs
        ).lower())) - stop_words

        answer_words = set(re.findall(r"\b[A-Za-z0-9_-]{3,}\b", answer_text.lower())) - stop_words

        if all_doc_words and answer_words:
            overlap = len(all_doc_words.intersection(answer_words))
            # Ratio of retrieved concepts actually incorporated
            utilization = round(min(1.0, overlap / min(len(all_doc_words), 30)), 4)
        else:
            utilization = 0.5

        summary = (
            f"Retrieval Evaluation: Precision={precision*100:.1f}% ({len(cited_ids)}/{len(retrieved_docs)} cited), "
            f"Recall={recall*100:.1f}%, Context Utilization={utilization*100:.1f}%."
        )

        return RetrievalEvaluationResult(
            retrieval_precision=precision,
            retrieval_recall=recall,
            context_utilization=utilization,
            cited_doc_ids=cited_ids,
            retrieved_doc_ids=retrieved_ids,
            summary=summary,
        )


class DomainScopeGate:
    """
    Enforces that copilot queries and responses stay strictly within
    semiconductor fab operations, yield analysis, process engineering, and DOE.
    Hard-blocks off-topic queries (cooking, gaming, general coding, politics, etc.).
    """

    OUT_OF_SCOPE_TERMS = {
        "recipe", "cook", "bake", "weather in", "football", "soccer", "basketball",
        "movie", "celebrity", "crypto", "bitcoin", "horoscope", "dating", "restaurant",
        "translate to french", "translate to spanish", "write a poem about love",
        "president of", "capital of", "who won", "song lyrics", "video game"
    }

    FAB_KEYWORDS = {
        "lot", "wafer", "fab", "etch", "litho", "cmp", "cvd", "pvd", "implant",
        "cpk", "sigma", "yield", "doe", "defect", "recipe", "chamber", "spc",
        "parameter", "drift", "excursion", "disposition", "scrap", "rework",
        "semiconductor", "inspection", "metrology", "cleanroom", "rf", "gas",
        "pressure", "temperature", "focus", "exposure", "overlay", "critical dimension"
    }

    @classmethod
    def check_query_scope(cls, query: str) -> Tuple[bool, str]:
        """Returns (in_scope, message)."""
        q_lower = query.lower().strip()
        for term in cls.OUT_OF_SCOPE_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", q_lower):
                return (
                    False,
                    "I am FabGuard Copilot ('Ask Bob'), specialized strictly in semiconductor "
                    "manufacturing, yield engineering, fab operations, and process DOE. "
                    "I cannot assist with topics outside this domain."
                )
        return True, ""

    @classmethod
    def check_response_scope(cls, text: str) -> Tuple[bool, str]:
        """Checks if generated response inadvertently veered into out-of-scope domain."""
        t_lower = text.lower()
        for term in cls.OUT_OF_SCOPE_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", t_lower):
                return (
                    False,
                    "Response flagged by Domain Scope Gate: generated text strayed outside "
                    "semiconductor domain."
                )
        return True, ""

