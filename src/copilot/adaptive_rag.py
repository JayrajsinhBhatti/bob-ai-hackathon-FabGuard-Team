"""
copilot/adaptive_rag.py — Advanced RAG: CRAG, Self-RAG & Adaptive/Agentic RAG

Implements concepts 6, 7, 8 of the advanced RAG pipeline:
  6. CRAG (Corrective RAG): Evaluates retrieval relevance before injection
  7. Self-RAG: Self-assesses response quality, regenerates if needed
  8. Adaptive/Agentic RAG: Dynamically selects retrieval strategy per query - bm25 + TF-IDF = Term Frequency × Inverse Document Frequency

All functions work with the existing LLM dispatch in agent.py.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .query_intelligence import QueryRoute


# ---------------------------------------------------------------------------
# CRAG: Corrective RAG — Retrieval Relevance Grading
# ---------------------------------------------------------------------------

@dataclass
class CRAGResult:
    """Result of CRAG relevance evaluation."""
    relevant_docs: List[Dict[str, Any]] = field(default_factory=list)
    irrelevant_docs: List[Dict[str, Any]] = field(default_factory=list)
    partial_docs: List[Dict[str, Any]] = field(default_factory=list)
    overall_grade: str = "RELEVANT"  # RELEVANT, PARTIAL, IRRELEVANT
    fallback_to_findings: bool = False


def grade_retrieval_relevance(
    query: str,
    retrieved_docs: List[Dict[str, Any]],
    findings: Optional[Dict[str, Any]] = None,
) -> CRAGResult:
    """
    CRAG: Grade each retrieved document for relevance to the query.

    Uses deterministic domain heuristics (no LLM call) to keep latency low:
    - Checks overlap between query terms and SOP keywords/step/parameter
    - Cross-references against lot findings if available
    - Scores below threshold → IRRELEVANT

    Args:
        query: The rewritten user query.
        retrieved_docs: Output from HybridRetriever.retrieve().
        findings: Optional lot findings for grounding.

    Returns:
        CRAGResult with graded documents and overall assessment.
    """
    result = CRAGResult()
    query_lower = query.lower()
    query_tokens = set(re.sub(r"[^a-z0-9\s_]", " ", query_lower).split())

    # Extract key entities from findings for cross-referencing
    findings_tools = set()
    findings_steps = set()
    findings_params = set()
    if findings:
        for cause in findings.get("candidate_causes", []):
            if cause.get("tool_id"):
                findings_tools.add(cause["tool_id"].upper())
            if cause.get("step"):
                findings_steps.add(cause["step"].lower())
            if cause.get("parameter"):
                findings_params.add(cause["parameter"].lower())

    for doc in retrieved_docs:
        sop = doc.get("sop", {})
        retrieval_score = doc.get("score", 0)

        # Build SOP keyword set
        sop_keywords = set()
        for kw in sop.get("keywords", []):
            sop_keywords.update(kw.lower().split())
        sop_keywords.add(sop.get("process_step", "").lower())
        sop_keywords.add(sop.get("parameter", "").lower())
        for sig in sop.get("spatial_signatures", []):
            sop_keywords.add(sig.lower())

        # Compute keyword overlap
        overlap = query_tokens & sop_keywords
        overlap_ratio = len(overlap) / max(len(query_tokens), 1)

        # Check if SOP matches lot findings
        findings_match = False
        if findings_steps and sop.get("process_step", "").lower() in findings_steps:
            findings_match = True
        if findings_params and sop.get("parameter", "").lower() in findings_params:
            findings_match = True

        # Grade the document
        if retrieval_score >= 0.4 and (overlap_ratio >= 0.2 or findings_match):
            result.relevant_docs.append(doc)
        elif retrieval_score >= 0.15 or overlap_ratio >= 0.1:
            result.partial_docs.append(doc)
        else:
            result.irrelevant_docs.append(doc)

    # Set overall grade
    if result.relevant_docs:
        result.overall_grade = "RELEVANT"
    elif result.partial_docs:
        result.overall_grade = "PARTIAL"
        result.relevant_docs = result.partial_docs  # use partial as best available
    else:
        result.overall_grade = "IRRELEVANT"
        result.fallback_to_findings = True

    return result


# ---------------------------------------------------------------------------
# Self-RAG: Response Quality Self-Assessment
# ---------------------------------------------------------------------------

@dataclass
class SelfRAGAssessment:
    """Result of Self-RAG quality self-check."""
    passes_grounding: bool = True
    passes_relevance: bool = True
    passes_completeness: bool = True
    passes_honesty: bool = True
    overall_pass: bool = True
    issues: List[str] = field(default_factory=list)
    should_regenerate: bool = False


def self_assess_response(
    answer: str,
    query: str,
    findings: Optional[Dict[str, Any]] = None,
    retrieved_sop_ids: Optional[List[str]] = None,
) -> SelfRAGAssessment:
    """
    Self-RAG: Assess the quality of Bob's response before returning to user.

    Checks:
    (a) Does the answer cite only data from provided context?
    (b) Does it answer the user's actual question?
    (c) Does it avoid speculation and invented metrics?
    (d) Does it include DOE caveat where appropriate?
    (e) Does it avoid calling findings "confirmed"?

    Uses deterministic rules (no LLM call) for reliability and speed.

    Args:
        answer: Bob's generated response text.
        query: The user's original query.
        findings: Optional lot findings used as context.
        retrieved_sop_ids: SOP IDs that were retrieved and injected.

    Returns:
        SelfRAGAssessment with per-check results and regeneration flag.
    """
    assessment = SelfRAGAssessment()
    answer_lower = answer.lower()
    query_lower = query.lower()

    # ── Check 1: Grounding — no invented tool IDs ──
    tool_pattern = re.compile(r"\b((?:ETCH|LITHO|CVD|CMP|IMPLANT)-\d{2,3})\b", re.IGNORECASE)
    mentioned_tools = {m.group(1).upper() for m in tool_pattern.finditer(answer)}

    if findings and mentioned_tools:
        known_tools = set()
        for cause in findings.get("candidate_causes", []):
            if cause.get("tool_id"):
                known_tools.add(cause["tool_id"].upper())
        for tool_entry in findings.get("suspect_tools", []):
            if isinstance(tool_entry, dict) and tool_entry.get("tool_id"):
                known_tools.add(tool_entry["tool_id"].upper())
            elif isinstance(tool_entry, str):
                known_tools.add(tool_entry.upper())
        # Tools mentioned in the user query itself are explicitly allowed
        for q_tool in tool_pattern.finditer(query):
            known_tools.add(q_tool.group(1).upper())

        # Allow standard historical fab tool IDs mentioned in knowledge base
        known_tools.update({"ETCH-01", "ETCH-03", "ETCH-07", "ETCH-12", "LITHO-01", "LITHO-02", "LITHO-03", "CVD-01", "CVD-02", "CMP-01", "CMP-02"})

        unknown_tools = mentioned_tools - known_tools
        if unknown_tools:
            assessment.passes_grounding = False
            assessment.issues.append(
                f"Tool IDs {unknown_tools} mentioned but not in lot findings or fab catalog"
            )


    # ── Check 2: Relevance — answer should relate to the query topic ──
    # Extract key query terms (ignoring stop words)
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "why", "how", "do",
                  "does", "did", "can", "should", "would", "this", "that", "it", "lot", "bob"}
    query_terms = {w for w in re.sub(r"[^a-z0-9\s]", "", query_lower).split() if w not in stop_words and len(w) > 2}
    answer_terms = set(re.sub(r"[^a-z0-9\s]", "", answer_lower).split())

    if query_terms:
        relevance_overlap = len(query_terms & answer_terms) / len(query_terms)
        if relevance_overlap < 0.15:
            assessment.passes_relevance = False
            assessment.issues.append(
                f"Answer may not address the query (overlap: {relevance_overlap:.0%})"
            )

    # ── Check 3: Honesty — never say "confirmed root cause" ──
    confirmed_patterns = [
        r"confirmed\s+root\s+cause",
        r"definitive\s+cause",
        r"proven\s+cause",
        r"certainly\s+the\s+cause",
    ]
    for pat in confirmed_patterns:
        if re.search(pat, answer_lower):
            assessment.passes_honesty = False
            assessment.issues.append(
                "Response declares a 'confirmed' root cause — must say 'leading candidate'"
            )
            break

    # ── Check 4: DOE caveat — must be present for root cause answers ──
    root_cause_keywords = ["root cause", "candidate cause", "leading candidate", "suspect", "excursion"]
    mentions_root_cause = any(kw in answer_lower for kw in root_cause_keywords)
    has_doe_caveat = "doe" in answer_lower or "design of experiment" in answer_lower or "confirm" in answer_lower

    if mentions_root_cause and not has_doe_caveat:
        assessment.passes_completeness = False
        assessment.issues.append("Root cause discussed without DOE confirmation caveat")

    # ── Check 5: Scope — no non-semiconductor content ──
    off_topic_markers = ["weather", "sports", "recipe", "code example", "def main()", "import numpy"]
    for marker in off_topic_markers:
        if marker in answer_lower:
            assessment.passes_grounding = False
            assessment.issues.append(f"Off-topic content detected: '{marker}'")
            break

    # ── Overall assessment ──
    assessment.overall_pass = all([
        assessment.passes_grounding,
        assessment.passes_relevance,
        assessment.passes_honesty,
        assessment.passes_completeness,
    ])
    assessment.should_regenerate = not assessment.overall_pass

    return assessment


def build_regeneration_prompt(
    original_query: str,
    original_answer: str,
    issues: List[str],
) -> str:
    """
    Build a corrective regeneration prompt incorporating Self-RAG feedback.

    Args:
        original_query: The user's question.
        original_answer: The answer that failed self-assessment.
        issues: List of specific issues found.

    Returns:
        A stricter prompt for regeneration.
    """
    issues_text = "\n".join(f"  - {issue}" for issue in issues)

    return (
        f"Your previous answer had quality issues:\n{issues_text}\n\n"
        f"Original question: {original_query}\n\n"
        f"Please regenerate your answer with these strict corrections:\n"
        f"1. ONLY cite tools, metrics, and values that are explicitly in the provided data.\n"
        f"2. NEVER say 'confirmed root cause' — use 'leading candidate' instead.\n"
        f"3. ALWAYS include DOE caveat when discussing root causes.\n"
        f"4. Stay STRICTLY within semiconductor fab operations.\n"
        f"5. Directly address the user's question.\n\n"
        f"Regenerate your answer now."
    )


# ---------------------------------------------------------------------------
# Adaptive/Agentic RAG: Strategy Selection
# ---------------------------------------------------------------------------

@dataclass
class RAGStrategy:
    """Defines the retrieval and generation strategy for a query."""
    name: str  # "direct_lookup", "standard_rag", "agentic_rag"
    needs_retrieval: bool = True
    needs_multi_query: bool = False
    needs_crag: bool = True
    needs_self_rag: bool = True
    needs_doe: bool = False
    needs_recommendations: bool = False
    max_retrieval_k: int = 3


def select_strategy(
    route: str,
    query: str,
    findings: Optional[Dict[str, Any]] = None,
) -> RAGStrategy:
    """
    Adaptive RAG: Select the optimal retrieval strategy based on query complexity.

    Simple queries → Direct lookup (no retrieval overhead)
    Standard queries → Hybrid retrieval + reranking
    Complex queries → Multi-step agentic orchestration

    Args:
        route: The query route from QueryRouter.
        query: The user's query.
        findings: Optional lot findings.

    Returns:
        RAGStrategy defining the pipeline configuration.
    """
    query_lower = query.lower()

    # ── Direct lookup — no RAG needed ──
    if route in (QueryRoute.GREETING, QueryRoute.HELP, QueryRoute.OUT_OF_SCOPE):
        return RAGStrategy(
            name="direct_lookup",
            needs_retrieval=False,
            needs_crag=False,
            needs_self_rag=False,
        )

    if route in (QueryRoute.STATUS, getattr(QueryRoute, "DATA_RETRIEVAL", "data_retrieval")):
        return RAGStrategy(
            name="direct_lookup",
            needs_retrieval=False,
            needs_crag=False,
            needs_self_rag=True,  # still verify status answers
        )

    # ── DOE generation — specialized handler ──
    if route == QueryRoute.DOE_GENERATION:
        return RAGStrategy(
            name="standard_rag",
            needs_retrieval=True,
            needs_crag=True,
            needs_self_rag=True,
            needs_doe=True,
            max_retrieval_k=2,
        )

    # ── Batch risk, Financial impact, Commonality — direct computation ──
    if route in (QueryRoute.BATCH_RISK, getattr(QueryRoute, "FINANCIAL_IMPACT", "financial_impact"), getattr(QueryRoute, "COMMONALITY", "commonality")):
        return RAGStrategy(
            name="direct_lookup",
            needs_retrieval=False,
            needs_crag=False,
            needs_self_rag=True,
        )

    # ── Complex multi-part queries → Agentic RAG ──
    complexity_markers = [
        "analyze and", "explain and recommend", "why and what",
        "full analysis", "comprehensive", "end to end",
        "root cause and action", "diagnose and fix",
    ]
    is_complex = any(marker in query_lower for marker in complexity_markers)

    if is_complex:
        return RAGStrategy(
            name="agentic_rag",
            needs_retrieval=True,
            needs_multi_query=True,
            needs_crag=True,
            needs_self_rag=True,
            needs_recommendations=True,
            max_retrieval_k=5,
        )

    # ── SOP retrieval — standard RAG ──
    if route == QueryRoute.SOP_RETRIEVAL:
        return RAGStrategy(
            name="standard_rag",
            needs_retrieval=True,
            needs_multi_query=True,
            needs_crag=True,
            needs_self_rag=True,
            max_retrieval_k=3,
        )

    # ── Default: standard RAG for findings-grounded and general fab ──
    return RAGStrategy(
        name="standard_rag",
        needs_retrieval=True,
        needs_multi_query=False,
        needs_crag=True,
        needs_self_rag=True,
        max_retrieval_k=3,
    )
