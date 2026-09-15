"""
copilot/rag_retriever.py  —  Feature 4: RAG Fab SOP & Historical Incident Retriever

Grounds copilot recommendations in real fab Standard Operating Procedures (SOPs),
historical excursion precedents, and tool maintenance protocols using BM25-style
term frequency retrieval over a local JSON knowledge base.

This replaces generic LLM hallucinations ("clean the chamber") with specific,
authoritative fab procedures:
  "Per SOP-ETCH-402 (RF Power Excursion): inspect RF match network capacitor C2,
   measure reflected power ratio (target < 2%). Historical precedent (2024-Q2 ETCH-07):
   degraded C2 capacitor caused 12% power loss at center."

Architecture:
  - Knowledge Base: data/knowledge/fab_sop_kb.json (offline, no internet needed)
  - Retrieval: TF-IDF / BM25-style scoring with multi-field weighting
  - Output: Top-k ranked SOPs with their procedures and precedents as context

No external dependencies beyond the stdlib. Works offline.

Usage:
    from copilot.rag_retriever import FabSOPRetriever
    retriever = FabSOPRetriever()
    results = retriever.retrieve(query="chamber pressure drift edge ring ETCH-07", top_k=2)
    context = retriever.format_context_for_llm(results)
"""

import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Default Knowledge Base Path
# ---------------------------------------------------------------------------

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_MODULE_DIR)
DEFAULT_KB_PATH = os.path.join(_REPO_ROOT, "data", "knowledge", "fab_sop_kb.json")


# ---------------------------------------------------------------------------
# BM25-style Retrieval (pure Python, no external dependencies)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, split into tokens."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s_/]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def _build_idf(corpus: List[List[str]]) -> Dict[str, float]:
    """Compute IDF (Inverse Document Frequency) for a corpus of token lists."""
    N = len(corpus)
    df: Dict[str, int] = {}
    for doc_tokens in corpus:
        for tok in set(doc_tokens):
            df[tok] = df.get(tok, 0) + 1
    return {tok: math.log((N - freq + 0.5) / (freq + 0.5) + 1.0)
            for tok, freq in df.items()}


def _bm25_score(
    query_tokens: List[str],
    doc_tokens: List[str],
    idf: Dict[str, float],
    k1: float = 1.5,
    b: float = 0.75,
    avg_dl: float = 50.0,
) -> float:
    """Compute BM25 relevance score for a document against a query."""
    dl = len(doc_tokens)
    tf_map: Dict[str, int] = {}
    for tok in doc_tokens:
        tf_map[tok] = tf_map.get(tok, 0) + 1

    score = 0.0
    for qt in query_tokens:
        if qt not in idf:
            continue
        tf = tf_map.get(qt, 0)
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * dl / avg_dl)
        score += idf[qt] * (numerator / denominator if denominator > 0 else 0)
    return score


# ---------------------------------------------------------------------------
# FabSOPRetriever
# ---------------------------------------------------------------------------

class FabSOPRetriever:
    """
    BM25-based retriever over the local fab SOP knowledge base.

    Retrieves the most relevant Standard Operating Procedures and historical
    incident precedents for a given query (tool ID, parameter, spatial signature).
    """

    def __init__(self, kb_path: str = DEFAULT_KB_PATH):
        self.kb_path = kb_path
        self.sops: List[Dict[str, Any]] = []
        self._doc_tokens: List[List[str]] = []
        self._idf: Dict[str, float] = {}
        self._avg_dl: float = 50.0
        self._loaded = False

    def _load(self):
        """Lazy-load the knowledge base and build the index."""
        if self._loaded:
            return

        if not os.path.exists(self.kb_path):
            self.sops = []
            self._loaded = True
            return

        with open(self.kb_path, "r", encoding="utf-8") as f:
            self.sops = json.load(f)

        # Build a combined text document for each SOP (multi-field weighting)
        corpus = []
        for sop in self.sops:
            doc_text = " ".join([
                sop.get("title", "") * 3,              # title gets 3x weight
                sop.get("process_step", "") * 3,       # step gets 3x weight
                sop.get("parameter", "") * 2,          # parameter gets 2x weight
                " ".join(sop.get("spatial_signatures", [])) * 2,
                " ".join(sop.get("keywords", [])) * 2,
                " ".join(sop.get("procedures", [])),
                " ".join(sop.get("root_cause_precedents", [])),
                sop.get("trigger", ""),
                sop.get("sop_id", ""),
            ])
            corpus.append(_tokenize(doc_text))

        self._doc_tokens = corpus
        self._idf = _build_idf(corpus)
        total_len = sum(len(d) for d in corpus)
        self._avg_dl = total_len / max(len(corpus), 1)
        self._loaded = True

    def retrieve(
        self,
        query: str,
        top_k: int = 2,
        step_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the top-k most relevant SOPs for a query.

        Args:
            query:       Natural language or structured query string.
                         Include tool IDs, parameter names, spatial signatures.
            top_k:       Number of results to return.
            step_filter: If set, only return SOPs matching this process step.

        Returns:
            List of dicts: [{"sop": {...sop_dict}, "score": float}, ...]
        """
        self._load()
        if not self.sops:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored = []
        for i, (sop, doc_tokens) in enumerate(zip(self.sops, self._doc_tokens)):
            if step_filter and sop.get("process_step", "").lower() != step_filter.lower():
                continue
            score = _bm25_score(query_tokens, doc_tokens, self._idf, avg_dl=self._avg_dl)
            scored.append((score, i, sop))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx, sop in scored[:top_k]:
            if score > 0:
                results.append({"sop": sop, "score": round(score, 4)})

        return results

    def retrieve_for_cause(
        self,
        candidate_cause: Dict[str, Any],
        top_k: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Convenience method: retrieve SOPs directly from a candidate_cause dict.

        Args:
            candidate_cause: A dict from candidate_causes in findings.
            top_k:           Number of SOPs to retrieve.

        Returns:
            Same as retrieve().
        """
        step = candidate_cause.get("step", "")
        tool_id = candidate_cause.get("tool_id", "")
        parameter = candidate_cause.get("parameter", "")
        spatial = candidate_cause.get("spatial_signature", "")

        query = f"{step} {tool_id} {parameter} {spatial} {parameter.replace('_', ' ')} {spatial}"
        return self.retrieve(query, top_k=top_k, step_filter=step)

    def format_context_for_llm(
        self,
        results: List[Dict[str, Any]],
        max_procedures: int = 5,
        max_precedents: int = 2,
    ) -> str:
        """
        Format retrieved SOPs as structured context for LLM injection.

        Args:
            results:        Output from retrieve() or retrieve_for_cause().
            max_procedures: Limit number of procedures to include.
            max_precedents: Limit number of historical incidents to include.

        Returns:
            A formatted string ready to be injected into an LLM system prompt.
        """
        if not results:
            return "No matching SOP procedures found in knowledge base."

        sections = ["=== RETRIEVED FAB SOP PROCEDURES (cite these in your response) ===\n"]

        for i, r in enumerate(results, 1):
            sop = r["sop"]
            sections.append(f"[SOP {i}: {sop.get('sop_id')} — {sop.get('title')}]")
            sections.append(f"  Process Step: {sop.get('process_step')} | Parameter: {sop.get('parameter')}")
            sections.append(f"  Trigger: {sop.get('trigger', 'Not specified')}")
            sections.append(f"  Relevance Score: {r['score']:.2f}")
            sections.append("")
            sections.append("  Standard Procedures (follow in order):")
            for proc in sop.get("procedures", [])[:max_procedures]:
                sections.append(f"    {proc}")
            sections.append("")

            precedents = sop.get("root_cause_precedents", [])[:max_precedents]
            if precedents:
                sections.append("  Historical Incident Precedents (reference these explicitly):")
                for prec in precedents:
                    sections.append(f"    ▸ {prec}")
                sections.append("")

        sections.append("=== END RETRIEVED SOPs ===\n")
        sections.append(
            "INSTRUCTION: When answering, cite the SOP ID (e.g., 'Per SOP-ETCH-402') "
            "and reference the historical precedent year and tool ID when relevant. "
            "Do NOT recommend procedures not listed in the retrieved SOPs above."
        )

        return "\n".join(sections)

    def format_as_text(
        self,
        results: List[Dict[str, Any]],
        max_procedures: int = 6,
        max_precedents: int = 2,
    ) -> str:
        """
        Format retrieved SOPs as human-readable text for IBM Bob chat panel.

        Args:
            results: Output from retrieve() or retrieve_for_cause().

        Returns:
            Formatted string for display in Bob.
        """
        if not results:
            return "=== SOP Knowledge Base ===\nNo matching procedures found for this excursion.\n"

        lines = ["=== Fab SOP & Historical Incident Knowledge Base ===", ""]

        for i, r in enumerate(results, 1):
            sop = r["sop"]
            lines.append(f"📋 {sop.get('sop_id')}: {sop.get('title')}")
            lines.append(f"   Step: {sop.get('process_step')}  |  Parameter: {sop.get('parameter')}")
            lines.append(f"   Trigger: {sop.get('trigger', 'N/A')}")
            lines.append("")
            lines.append("   Standard Procedures:")
            for proc in sop.get("procedures", [])[:max_procedures]:
                lines.append(f"     {proc}")
            lines.append("")
            precedents = sop.get("root_cause_precedents", [])[:max_precedents]
            if precedents:
                lines.append("   Historical Precedents:")
                for prec in precedents:
                    lines.append(f"     ▸ {prec}")
            lines.append("")
            lines.append("─" * 60)
            lines.append("")

        lines.append(
            "⚠️  All SOP procedures must be authorized by the process module owner "
            "before execution on production equipment."
        )
        return "\n".join(lines)
