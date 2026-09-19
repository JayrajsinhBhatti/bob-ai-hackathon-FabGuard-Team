"""
copilot/query_intelligence.py — Advanced RAG: Query Routing, Rewriting & Multi-Query

Implements the first 3 advanced RAG concepts for FabGuard:
  1. Query Routing: Classifies queries into routing targets (findings, SOP, DOE, risk, general, out-of-scope)
  2. Query Rewriting: Expands abbreviations, injects lot context, normalizes terminology
  3. Multi-Query: Generates diverse sub-queries for improved retrieval recall

All functions are stateless and work with the existing LLM provider hierarchy.
"""

"""first-stage intelligence layer of FabGuard's Advanced RAG. It handles the first 3 advanced RAG concepts:

1.Query Routing → decides where the question should go
2.Query Rewriting → makes the question more precise
3.Multi-Query → creates multiple search versions to improve retrieval"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple



# ---------------------------------------------------------------------------
# Fab Domain Abbreviation Dictionary (expands over time via self-improvement)
# ---------------------------------------------------------------------------

FAB_ABBREVIATIONS: Dict[str, str] = {
    "cp": "chamber_pressure",
    "rf": "rf_power_forward",
    "rf power": "rf_power_forward",
    "fo": "focus_offset",
    "focus": "focus_offset",
    "cd": "critical_dimension",
    "dep temp": "deposition_temp",
    "dep": "deposition",
    "hd": "head_downforce",
    "slurry": "slurry_flow_rate",
    "beam": "beam_current",
    "ee": "exposure_energy",
    "pm": "preventive_maintenance",
    "fem": "focus_exposure_matrix",
    "mfc": "mass_flow_controller",
    "oes": "optical_emission_spectroscopy",
    "apc": "advanced_process_control",
    "fdc": "fault_detection_classification",
    "wiw": "within_wafer_uniformity",
}

# Fab process steps for normalization
FAB_STEPS = {"etch", "litho", "lithography", "cvd", "cmp", "implant", "deposition"}

# Tool ID pattern
_TOOL_PATTERN = re.compile(r"\b([A-Z]{2,7}-\d{2,3})\b", re.IGNORECASE)

# Spatial signature vocabulary
SPATIAL_SIGNATURES = {
    "edge-ring", "center-cluster", "donut", "scratch",
    "uniform", "radial", "hotspot", "random",
}


# ---------------------------------------------------------------------------
# 1. Query Routing
# ---------------------------------------------------------------------------

class QueryRoute:
    """Enum-like routing targets."""
    FINDINGS_GROUNDED = "findings_grounded"
    SOP_RETRIEVAL = "sop_retrieval"
    DOE_GENERATION = "doe_generation"
    BATCH_RISK = "batch_risk"
    GENERAL_FAB = "general_fab"
    OUT_OF_SCOPE = "out_of_scope"
    GREETING = "greeting"
    HELP = "help"
    STATUS = "status"
    FINANCIAL_IMPACT = "financial_impact"
    COMMONALITY = "commonality"
    DATA_RETRIEVAL = "data_retrieval"


# Keywords mapped to routes (ordered by priority)
_ROUTE_RULES: List[Tuple[str, List[str]]] = [
    (QueryRoute.GREETING, [
        "hi", "hii", "hiii", "hello", "hey", "heyy", "greetings",
        "good morning", "good afternoon", "good evening", "howdy",
        "sup", "yo", "bob", "test", "ping",
    ]),
    (QueryRoute.HELP, [
        "who are you", "what can you do", "help", "capabilities", "menu",
        "what do you know", "how can you help",
    ]),
    (QueryRoute.FINANCIAL_IMPACT, [
        "financial", "savings", "dollar", "how much yield could potentially be recovered",
        "how much yield could we recover", "how much yield", "yield could we recover",
        "recover", "recovery", "recovered", "recoverable", "cost", "revenue", "roi",
        "counterfactual", "economic", "if we fix", "fix the",
    ]),
    (QueryRoute.DOE_GENERATION, [
        "doe", "design a doe", "design of experiment", "split test", "experiment matrix",
        "test wafer", "factorial", "2^k", "2k factorial", "runcard",
        "confirmatory experiment", "validate whether", "validate if",
    ]),
    (QueryRoute.COMMONALITY, [
        "commonality", "fisher", "odds ratio", "contingency",
        "commonly associated", "associated with failed", "associated with other failed",
        "associated with", "appear significantly more often",
        "linking this equipment", "compare lot", "common factors",
        "across these failed lots", "responsible for the defect",
        "cross-lot", "cross lot",
    ]),
    (QueryRoute.BATCH_RISK, [
        "at risk", "upcoming batch", "risk predict", "batch risk",
        "in-progress lots", "flag batch", "risk assessment", "why is lot-2240",
        "similar to previously failed", "putting this batch at risk",
    ]),
    (QueryRoute.DATA_RETRIEVAL, [
        "equipment was used", "which equipment is associated",
        "process steps were used", "what process steps", "defects were detected",
        "what defects", "what data is available", "data available for",
    ]),
    (QueryRoute.STATUS, [
        "status of", "status", "how is lot", "yield of", "what yield", "current yield",
        "overview", "summary of lot",
    ]),
    (QueryRoute.SOP_RETRIEVAL, [
        "sop", "procedure", "standard operating", "containment",
        "interlock", "pm inspection", "preventive maintenance",
        "what should i check", "check first", "action plan",
        "corrective action", "recommend", "fix", "prevent",
        "investigate next",
    ]),
    (QueryRoute.FINDINGS_GROUNDED, [
        "why", "fail", "drop", "excursion", "defect", "root cause", "cause",
        "cpk", "sigma", "z score", "zscore", "drift", "spec", "telemetry",
        "sensor", "spatial", "pattern", "wafer map", "yield loss",
        "probability", "risk score", "evidence", "candidate", "abnormal",
        "outside their normal", "abnormalities", "biggest deviation",
        "acceptable range", "chamber pressure abnormal", "defect pattern is present",
        "defect pattern mean",
    ]),
]

# Out-of-scope blocklist — topics Bob should refuse
_OUT_OF_SCOPE_KEYWORDS = [
    "weather", "sports", "recipe", "cooking", "movie", "music",
    "stock", "bitcoin", "crypto", "politics", "election",
    "write code", "python script", "javascript", "html",
    "poem", "story", "joke", "game", "homework",
    "personal", "relationship", "dating",
]


def route_query(query: str, lot_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Classify a user query into a routing target.

    Uses keyword matching with priority ordering. Falls back to
    GENERAL_FAB for domain-adjacent queries.

    Args:
        query: The user's raw question.
        lot_context: Optional dict with lot_id, findings, etc.

    Returns:
        A QueryRoute string constant.
    """
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", query.lower()).strip()
    words = set(clean.split())

    # Check greetings (short messages only)
    if len(words) <= 3:
        greeting_words = set(_ROUTE_RULES[0][1])
        if words & greeting_words:
            return QueryRoute.GREETING

    # Check out-of-scope first
    for kw in _OUT_OF_SCOPE_KEYWORDS:
        if kw in clean:
            return QueryRoute.OUT_OF_SCOPE

    # Check domain routes in priority order (skip greeting, already handled)
    for route, keywords in _ROUTE_RULES[1:]:
        for kw in keywords:
            if kw in clean:
                return route

    # If query mentions a tool ID or process step, route to findings
    if _TOOL_PATTERN.search(query):
        return QueryRoute.FINDINGS_GROUNDED

    for step in FAB_STEPS:
        if step in clean:
            return QueryRoute.FINDINGS_GROUNDED

    # Default: general fab knowledge (still domain-constrained)
    return QueryRoute.GENERAL_FAB


# ---------------------------------------------------------------------------
# 2. Query Rewriting
# ---------------------------------------------------------------------------

def rewrite_query(
    query: str,
    lot_id: str = None,
    findings: Dict[str, Any] = None,
) -> str:
    """
    Rewrite a vague user query into a precise, retrieval-optimized fab query.

    Transforms:
    - Expands abbreviations: "CP" → "chamber_pressure"
    - Injects lot context: "why did it fail" → "why did LOT-2231 fail — suspect ETCH-07 chamber_pressure edge-ring"
    - Normalizes tool IDs and process steps

    Args:
        query: The user's raw question.
        lot_id: Current lot identifier.
        findings: Optional root_cause_findings dict.

    Returns:
        The rewritten, retrieval-optimized query string.
    """
    rewritten = query

    # Expand abbreviations (case-insensitive word boundary replacement)
    for abbr, expansion in FAB_ABBREVIATIONS.items():
        pattern = re.compile(r"\b" + re.escape(abbr) + r"\b", re.IGNORECASE)
        rewritten = pattern.sub(expansion, rewritten)

    # Normalize "lithography" → "litho" for consistency
    rewritten = re.sub(r"\blithography\b", "litho", rewritten, flags=re.IGNORECASE)

    # Inject lot context ONLY for truly vague queries that lack specific tool/parameter targets
    if findings and lot_id:
        vague_patterns = [
            r"\bit\b", r"\bthis lot\b", r"\bthe lot\b",
            r"\bwhy did it\b", r"\bwhat happened\b", r"\bwhat went wrong\b",
        ]
        is_vague = any(re.search(p, rewritten, re.IGNORECASE) for p in vague_patterns)
        has_specific_target = bool(re.search(r"\b(etch|litho|cmp|cvd|imp|implant)-\d{1,2}\b|\b(chamber[-_ ]pressure|focus[-_ ]offset|rf[-_ ]power|pressure|throttle)\b", rewritten, re.IGNORECASE))

        if is_vague and not has_specific_target:
            causes = findings.get("candidate_causes", [])
            if causes:
                top = causes[0]
                context_suffix = (
                    f" — lot {lot_id}, suspect tool {top.get('tool_id', '')}, "
                    f"parameter {top.get('parameter', '')}, "
                    f"spatial signature {top.get('spatial_signature', '')}, "
                    f"process step {top.get('step', '')}"
                )
                rewritten = rewritten.rstrip("?.! ") + context_suffix

    # Normalize tool IDs to uppercase
    def _upper_tool(m):
        return m.group(0).upper()
    rewritten = _TOOL_PATTERN.sub(_upper_tool, rewritten)

    return rewritten.strip()


# ---------------------------------------------------------------------------
# 3. Multi-Query Generation
# ---------------------------------------------------------------------------

def generate_sub_queries(
    query: str,
    lot_id: str = None,
    findings: Dict[str, Any] = None,
    max_queries: int = 3,
) -> List[str]:
    """
    Generate diverse sub-queries from different retrieval angles.

    For complex questions, creates 2-3 sub-queries that approach the
    information need from equipment, symptom, and historical perspectives.

    Args:
        query: The rewritten query (output of rewrite_query).
        lot_id: Current lot identifier.
        findings: Optional root_cause_findings dict.
        max_queries: Maximum sub-queries to generate.

    Returns:
        List of sub-query strings (always includes the original).
    """
    sub_queries = [query]  # Always include original

    if not findings or not findings.get("candidate_causes"):
        return sub_queries[:max_queries]

    top_cause = findings["candidate_causes"][0]
    step = top_cause.get("step", "")
    tool_id = top_cause.get("tool_id", "")
    parameter = top_cause.get("parameter", "")
    spatial = top_cause.get("spatial_signature", "")

    # Angle 1: Equipment-focused
    equipment_query = f"{tool_id} {parameter} {step} SOP procedures maintenance calibration"
    if equipment_query not in sub_queries:
        sub_queries.append(equipment_query)

    # Angle 2: Symptom-focused
    symptom_query = f"yield drop {spatial} defect pattern {step} step {parameter.replace('_', ' ')} drift"
    if symptom_query not in sub_queries:
        sub_queries.append(symptom_query)

    # Angle 3: Historical-focused
    historical_query = f"prior incident {parameter.replace('_', ' ')} {step} chamber tool precedent root cause"
    if historical_query not in sub_queries:
        sub_queries.append(historical_query)

    return sub_queries[:max_queries]


# ---------------------------------------------------------------------------
# Domain scope enforcement
# ---------------------------------------------------------------------------

OUT_OF_SCOPE_RESPONSE = (
    "I appreciate your question, but I can only assist with **semiconductor fab operations "
    "and yield analysis**.\n\n"
    "Here are some things I can help with:\n"
    "- 🔬 **Root cause analysis** for wafer lot yield excursions\n"
    "- 📋 **SOP procedures** for equipment maintenance and calibration\n"
    "- 📊 **Cpk/sigma analysis** of process parameters\n"
    "- 🧪 **DOE design** for confirmatory experiments\n"
    "- ⚠️ **Batch risk assessment** for in-progress lots\n\n"
    "Please ask me a question about your fab operations!"
)


def get_out_of_scope_response() -> str:
    """Return the standard domain-scope rejection message."""
    return OUT_OF_SCOPE_RESPONSE


# ---------------------------------------------------------------------------
# Object-Oriented Interfaces (for clean dependency injection)
# ---------------------------------------------------------------------------

@dataclass
class RoutingResult:
    target: str
    confidence: float = 1.0
    matched_keywords: List[str] = field(default_factory=list)


class QueryRouter:
    """Class wrapper for Query Routing."""
    def route(self, query: str, lot_context: Optional[Dict[str, Any]] = None) -> RoutingResult:
        target = route_query(query, lot_context)
        return RoutingResult(target=target)


class QueryRewriter:
    """Class wrapper for Query Rewriting."""
    def rewrite(self, query: str, findings: Optional[Dict[str, Any]] = None, lot_id: Optional[str] = None) -> str:
        eff_lot = lot_id or (findings.get("lot_id") if findings else None)
        return rewrite_query(query, lot_id=eff_lot, findings=findings)


class MultiQueryGenerator:
    """Class wrapper for Multi-Query Generation."""
    def generate(
        self,
        query: str,
        routing_result: Optional[RoutingResult] = None,
        findings: Optional[Dict[str, Any]] = None,
        max_queries: int = 3,
    ) -> List[str]:
        return generate_sub_queries(query, findings=findings, max_queries=max_queries)


