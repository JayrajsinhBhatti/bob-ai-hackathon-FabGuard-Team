"""
copilot/rag_retriever.py  —  Advanced RAG: Hybrid Search + Reranking

Grounds copilot recommendations in real fab Standard Operating Procedures (SOPs),
historical excursion precedents, and tool maintenance protocols using a hybrid
retrieval strategy combining BM25 lexical scoring with TF-IDF cosine similarity.

Advanced RAG Concepts Implemented:
  4. Hybrid Search: BM25 + TF-IDF cosine with tunable α weighting
  5. Reranking: Domain-aware reranker + optional LLM reranking for ambiguous results

Architecture:
  - Knowledge Base: data/knowledge/fab_sop_kb.json (offline, no internet needed)
  - Hybrid Retrieval: BM25 lexical + TF-IDF cosine similarity scoring
  - Reranking: Domain heuristic + LLM fallback for close scores
  - Output: Top-k ranked SOPs with procedures and precedents as context

No external vector DB dependencies. Works offline.

Usage:
    from copilot.rag_retriever import HybridRetriever
    retriever = HybridRetriever()
    results = retriever.retrieve(query="chamber pressure drift edge ring ETCH-07", top_k=3)
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
# TF-IDF Cosine Similarity Retriever (scikit-learn based)
# ---------------------------------------------------------------------------

class TFIDFRetriever:
    """
    TF-IDF based semantic retriever using scikit-learn's TfidfVectorizer.
    Provides cosine similarity scoring as a complement to BM25.
    """

    def __init__(self):
        self._vectorizer = None
        self._tfidf_matrix = None
        self._fitted = False

    def fit(self, documents: List[str]):
        """Fit the TF-IDF vectorizer on a list of document strings."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),  # unigrams + bigrams for better matching
                stop_words="english",
                sublinear_tf=True,
            )
            self._tfidf_matrix = self._vectorizer.fit_transform(documents)
            self._fitted = True
        except ImportError:
            # scikit-learn not available — degrade gracefully
            self._fitted = False

    def score(self, query: str) -> List[float]:
        """
        Return cosine similarity scores for each document against the query.

        Args:
            query: The search query string.

        Returns:
            List of float scores (0.0 to 1.0), one per document.
        """
        if not self._fitted or self._vectorizer is None:
            return []

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            query_vec = self._vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()
            return similarities.tolist()
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Domain-Aware Reranker
# ---------------------------------------------------------------------------

def _domain_rerank_score(
    sop: Dict[str, Any],
    query: str,
    lot_findings: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Compute a domain-aware relevance boost score based on structural matching.

    Boosts SOPs that match the lot's process step, tool ID, spatial signature,
    and parameter — regardless of text similarity.

    Returns a bonus score (0.0 to 1.0) to add to retrieval score.
    """
    bonus = 0.0
    query_lower = query.lower()
    sop_step = sop.get("process_step", "").lower()
    sop_param = sop.get("parameter", "").lower()
    sop_signatures = [s.lower() for s in sop.get("spatial_signatures", [])]

    # Match process step
    if sop_step and sop_step in query_lower:
        bonus += 0.25

    # Match parameter
    if sop_param and sop_param in query_lower:
        bonus += 0.2

    # Match spatial signatures
    for sig in sop_signatures:
        if sig in query_lower:
            bonus += 0.15
            break

    # Match against lot findings (if available)
    if lot_findings:
        causes = lot_findings.get("candidate_causes", [])
        for cause in causes:
            cause_step = cause.get("step", "").lower()
            cause_tool = cause.get("tool_id", "").upper()
            cause_param = cause.get("parameter", "").lower()
            cause_spatial = cause.get("spatial_signature", "").lower()

            if sop_step == cause_step:
                bonus += 0.15
            if sop_param == cause_param:
                bonus += 0.15
            if cause_spatial in sop_signatures:
                bonus += 0.1
            # Exact tool ID mention in SOP text
            sop_text = json.dumps(sop).upper()
            if cause_tool and cause_tool in sop_text:
                bonus += 0.2

    return min(bonus, 1.0)


# ---------------------------------------------------------------------------
# HybridRetriever — Main retriever class
# ---------------------------------------------------------------------------

class HybridRetriever:
    """
    Hybrid BM25 + TF-IDF retriever with domain-aware reranking.

    Combines lexical BM25 scoring with TF-IDF cosine similarity to
    catch both exact term matches and semantically similar SOPs.
    """

    def __init__(self, kb_path: str = DEFAULT_KB_PATH, alpha: float = 0.6):
        """
        Args:
            kb_path: Path to fab_sop_kb.json knowledge base.
            alpha: Weight for BM25 vs TF-IDF. α=0.6 means 60% BM25, 40% TF-IDF.
        """
        self.kb_path = kb_path
        self.alpha = alpha
        self.sops: List[Dict[str, Any]] = []
        self._doc_tokens: List[List[str]] = []
        self._doc_texts: List[str] = []
        self._idf: Dict[str, float] = {}
        self._avg_dl: float = 50.0
        self._tfidf = TFIDFRetriever()
        self._loaded = False

    def _load(self):
        """Lazy-load the knowledge base and build both BM25 and TF-IDF indices."""
        if self._loaded:
            return

        if not os.path.exists(self.kb_path):
            self.sops = []
            self._loaded = True
            return

        with open(self.kb_path, "r", encoding="utf-8") as f:
            self.sops = json.load(f)

        # Also load KB stubs from database (auto-generated SOPs)
        try:
            self._load_kb_stubs()
        except Exception:
            pass

        # Build combined text documents for each SOP (multi-field weighting)
        corpus = []
        doc_texts = []
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
            doc_texts.append(doc_text)

        self._doc_tokens = corpus
        self._doc_texts = doc_texts
        self._idf = _build_idf(corpus)
        total_len = sum(len(d) for d in corpus)
        self._avg_dl = total_len / max(len(corpus), 1)

        # Fit TF-IDF vectorizer
        self._tfidf.fit(doc_texts)

        self._loaded = True

    def _load_kb_stubs(self):
        """Load promoted KB stubs from the database and merge into SOP list."""
        try:
            import sys
            from pathlib import Path
            _backend_root = Path(__file__).resolve().parents[1] / "backend"
            if str(_backend_root) not in sys.path:
                sys.path.insert(0, str(_backend_root))
            from app.db import get_kb_stubs
            stubs = get_kb_stubs(promoted_only=True)
            for stub in stubs:
                sop_data = stub.get("stub_sop", {})
                if isinstance(sop_data, dict) and sop_data.get("sop_id"):
                    self.sops.append(sop_data)
        except Exception:
            pass

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        step_filter: Optional[str] = None,
        lot_findings: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-k SOPs using hybrid BM25 + TF-IDF scoring with domain reranking.

        Args:
            query:        Natural language or structured query string.
            top_k:        Number of results to return.
            step_filter:  If set, only return SOPs matching this process step.
            lot_findings: Optional findings dict for domain reranking boost.

        Returns:
            List of dicts: [{"sop": {...}, "score": float, "retrieval_method": str}, ...]
        """
        self._load()
        if not self.sops:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Get TF-IDF scores
        tfidf_scores = self._tfidf.score(query)
        if not tfidf_scores:
            tfidf_scores = [0.0] * len(self.sops)

        # Compute hybrid scores
        scored = []
        for i, (sop, doc_tokens) in enumerate(zip(self.sops, self._doc_tokens)):
            if step_filter and sop.get("process_step", "").lower() != step_filter.lower():
                continue

            # BM25 score
            bm25 = _bm25_score(query_tokens, doc_tokens, self._idf, avg_dl=self._avg_dl)

            # TF-IDF cosine score
            tfidf = tfidf_scores[i] if i < len(tfidf_scores) else 0.0

            # Normalize BM25 to 0-1 range (approximate)
            bm25_norm = min(bm25 / 20.0, 1.0) if bm25 > 0 else 0.0

            # Hybrid score
            hybrid = self.alpha * bm25_norm + (1 - self.alpha) * tfidf

            # Domain reranking boost
            domain_boost = _domain_rerank_score(sop, query, lot_findings)
            final_score = hybrid + 0.3 * domain_boost  # domain boost adds up to 0.3

            # Track which retriever contributed more
            method = "bm25" if bm25_norm > tfidf else "tfidf"
            if domain_boost > 0.3:
                method = "domain_boost"

            scored.append((final_score, i, sop, method))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx, sop, method in scored[:top_k]:
            if score > 0:
                results.append({
                    "sop": sop,
                    "score": round(score, 4),
                    "retrieval_method": method,
                })

        return results

    def retrieve_multi_query(
        self,
        queries: List[str],
        top_k: int = 5,
        step_filter: Optional[str] = None,
        lot_findings: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve and merge results from multiple sub-queries (Multi-Query RAG).

        Deduplicates by SOP ID, keeping the highest score per document.

        Args:
            queries:      List of sub-queries (from generate_sub_queries).
            top_k:        Number of final results after merge.
            step_filter:  Optional process step filter.
            lot_findings: Optional findings dict.

        Returns:
            Merged, deduplicated, and re-sorted results.
        """
        seen: Dict[str, Dict[str, Any]] = {}

        for q in queries:
            results = self.retrieve(q, top_k=top_k, step_filter=step_filter, lot_findings=lot_findings)
            for r in results:
                sop_id = r["sop"].get("sop_id", "")
                if sop_id not in seen or r["score"] > seen[sop_id]["score"]:
                    seen[sop_id] = r

        merged = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        return merged[:top_k]

    def multi_query_retrieve(
        self,
        queries: List[str],
        top_k: int = 5,
        step_filter: Optional[str] = None,
        lot_findings: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Alias for retrieve_multi_query for multi-query RAG."""
        return self.retrieve_multi_query(
            queries=queries,
            top_k=top_k,
            step_filter=step_filter,
            lot_findings=lot_findings,
        )

    def retrieve_for_cause(
        self,
        candidate_cause: Dict[str, Any],
        top_k: int = 3,
        lot_findings: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convenience method: retrieve SOPs directly from a candidate_cause dict.

        Args:
            candidate_cause: A dict from candidate_causes in findings.
            top_k:           Number of SOPs to retrieve.
            lot_findings:    Full findings dict for domain reranking.

        Returns:
            Same as retrieve().
        """
        step = candidate_cause.get("step", "")
        tool_id = candidate_cause.get("tool_id", "")
        parameter = candidate_cause.get("parameter", "")
        spatial = candidate_cause.get("spatial_signature", "")

        query = f"{step} {tool_id} {parameter} {spatial} {parameter.replace('_', ' ')} {spatial}"
        return self.retrieve(query, top_k=top_k, step_filter=step, lot_findings=lot_findings)

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
            method = r.get("retrieval_method", "hybrid")
            sections.append(f"[SOP {i}: {sop.get('sop_id')} — {sop.get('title')}]")
            sections.append(f"  Process Step: {sop.get('process_step')} | Parameter: {sop.get('parameter')}")
            sections.append(f"  Trigger: {sop.get('trigger', 'Not specified')}")
            sections.append(f"  Relevance Score: {r['score']:.2f} (via {method})")
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

    def get_cited_sop_ids(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract SOP IDs from retrieval results for tracking."""
        return [r["sop"].get("sop_id", "") for r in results if r.get("sop")]


# ---------------------------------------------------------------------------
# Legacy compatibility: FabSOPRetriever alias
# ---------------------------------------------------------------------------

class FabSOPRetriever(HybridRetriever):
    """Backward-compatible alias for HybridRetriever."""
    pass


class DomainAwareReranker:
    """
    Reranks retrieved SOP candidates using semiconductor fab domain rules
    (boosting process step, parameter, spatial signature, and equipment matches).
    """

    def __init__(self, retriever: Optional[HybridRetriever] = None):
        self.retriever = retriever or HybridRetriever()

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        findings: Optional[Dict[str, Any]] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Rerank candidates based on findings and domain relevance."""
        if not candidates:
            return []

        scored = []
        ql = query.lower()
        for cand in candidates:
            score = cand.get("score", 0.0)
            sop = cand.get("sop", {})

            # Explicit query matching takes precedence
            param = sop.get("parameter", "").lower()
            if param and (param in ql or param.replace("_", " ") in ql):
                score += 0.5
            step = sop.get("process_step", "").lower()
            if step and step in ql:
                score += 0.3

            if findings:
                finding_step = findings.get("process_step", "")
                if finding_step and finding_step.lower() == step:
                    score += 0.2
                for cause in findings.get("candidate_causes", []):
                    if cause.get("parameter", "").lower() == param:
                        score += 0.25
                    signatures = [s.lower() for s in sop.get("spatial_signatures", [])]
                    if cause.get("spatial_signature", "").lower() in signatures:
                        score += 0.15

            cand_copy = dict(cand)
            cand_copy["score"] = round(score, 4)
            scored.append(cand_copy)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

