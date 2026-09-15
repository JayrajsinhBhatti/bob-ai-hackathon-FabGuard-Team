"""
tests/test_rag_retriever.py  —  Tests for Feature 4: RAG SOP Retriever
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot.rag_retriever import FabSOPRetriever, _tokenize, _bm25_score, _build_idf


# ---------------------------------------------------------------------------
# Unit tests: retrieval primitives
# ---------------------------------------------------------------------------

class TestRetrievalPrimitives:
    def test_tokenize_lowercases(self):
        tokens = _tokenize("ETCH-07 Chamber_Pressure")
        assert all(t == t.lower() for t in tokens)

    def test_tokenize_strips_punctuation(self):
        tokens = _tokenize("chamber.pressure, drift!")
        assert "," not in tokens
        assert "." not in tokens
        assert "!" not in tokens

    def test_tokenize_removes_single_chars(self):
        tokens = _tokenize("a b the pressure")
        # 'a' and 'b' are single chars and should be removed
        assert "a" not in tokens
        assert "b" not in tokens
        assert "pressure" in tokens

    def test_idf_computed_for_known_term(self):
        corpus = [["etch", "pressure"], ["litho", "focus"], ["etch", "flow"]]
        idf = _build_idf(corpus)
        # "etch" appears in 2/3 docs — should have lower IDF than "pressure" (1/3)
        assert idf.get("etch", 0) < idf.get("pressure", 0)

    def test_bm25_score_positive_for_matching_query(self):
        idf = {"pressure": 1.5, "chamber": 1.2}
        doc_tokens = ["pressure", "chamber", "etch", "pressure"]
        score = _bm25_score(["pressure", "chamber"], doc_tokens, idf)
        assert score > 0.0

    def test_bm25_score_zero_for_no_match(self):
        idf = {"pressure": 1.5}
        doc_tokens = ["litho", "focus", "exposure"]
        score = _bm25_score(["pressure"], doc_tokens, idf)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Integration tests: FabSOPRetriever
# ---------------------------------------------------------------------------

class TestFabSOPRetriever:

    @pytest.fixture
    def retriever(self):
        return FabSOPRetriever()

    def test_kb_loads_successfully(self, retriever):
        retriever._load()
        assert retriever._loaded
        assert len(retriever.sops) > 0, "Knowledge base should have at least one SOP"

    def test_retrieve_etch_pressure_query(self, retriever):
        results = retriever.retrieve("chamber pressure ETCH-07 edge ring etch step", top_k=2)
        assert isinstance(results, list)
        assert len(results) >= 1, "Expected at least one result for etch pressure query"
        # Top result should relate to etch
        top_sop = results[0]["sop"]
        assert top_sop.get("process_step") == "etch", \
            f"Expected etch step, got {top_sop.get('process_step')}"

    def test_retrieve_rf_power_query(self, retriever):
        results = retriever.retrieve("rf power etch center cluster impedance matching", top_k=2)
        assert len(results) >= 1
        top_sop = results[0]["sop"]
        assert top_sop.get("process_step") == "etch"

    def test_retrieve_litho_focus_query(self, retriever):
        results = retriever.retrieve("focus offset litho center cluster CD uniformity", top_k=2)
        assert len(results) >= 1
        top_sop = results[0]["sop"]
        assert top_sop.get("process_step") == "litho", \
            f"Expected litho step, got {top_sop.get('process_step')}"

    def test_step_filter_works(self, retriever):
        results = retriever.retrieve("process deviation excursion", top_k=5, step_filter="cmp")
        for r in results:
            assert r["sop"].get("process_step") == "cmp", \
                f"Step filter 'cmp' violated: got {r['sop'].get('process_step')}"

    def test_top_k_limits_results(self, retriever):
        results = retriever.retrieve("pressure etch litho chamber flow", top_k=1)
        assert len(results) <= 1

    def test_scores_are_positive(self, retriever):
        results = retriever.retrieve("chamber pressure etch drift sigma", top_k=3)
        for r in results:
            assert r["score"] > 0.0, f"Score should be positive, got {r['score']}"

    def test_results_sorted_by_score(self, retriever):
        results = retriever.retrieve("etch chamber pressure rf power drift", top_k=3)
        if len(results) >= 2:
            for i in range(len(results) - 1):
                assert results[i]["score"] >= results[i+1]["score"], \
                    "Results should be sorted by descending score"

    def test_retrieve_for_cause_returns_results(self, retriever):
        cause = {
            "step": "etch",
            "tool_id": "ETCH-07",
            "parameter": "chamber_pressure",
            "spatial_signature": "edge-ring",
        }
        results = retriever.retrieve_for_cause(cause, top_k=2)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_format_context_for_llm(self, retriever):
        results = retriever.retrieve("chamber pressure etch drift", top_k=2)
        context = retriever.format_context_for_llm(results)
        assert isinstance(context, str)
        assert "SOP" in context
        assert "Procedures" in context
        assert "cite" in context.lower()
        assert len(context) > 100

    def test_format_as_text(self, retriever):
        results = retriever.retrieve("etch rf power center cluster", top_k=2)
        text = retriever.format_as_text(results)
        assert isinstance(text, str)
        assert "SOP" in text
        assert "Procedures" in text or "procedures" in text.lower()
        assert len(text) > 100

    def test_empty_query_returns_empty(self, retriever):
        results = retriever.retrieve("", top_k=2)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_unknown_step_filter_returns_empty(self, retriever):
        results = retriever.retrieve("pressure chamber", top_k=5, step_filter="unknown_step")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_result_sop_has_required_fields(self, retriever):
        results = retriever.retrieve("etch pressure drift excursion", top_k=2)
        for r in results:
            sop = r["sop"]
            assert "sop_id" in sop
            assert "title" in sop
            assert "process_step" in sop
            assert "procedures" in sop
            assert isinstance(sop["procedures"], list)
            assert len(sop["procedures"]) > 0
