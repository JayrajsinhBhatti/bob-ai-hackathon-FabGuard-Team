"""
tests/test_advanced_rag.py — Comprehensive tests for all 10 Advanced RAG concepts
and the Self-Improving Feedback Loop.
"""

import os
import sys
import pytest

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot.query_intelligence import (
    QueryRouter,
    QueryRewriter,
    MultiQueryGenerator,
    QueryRoute,
    FAB_ABBREVIATIONS,
)
from copilot.rag_retriever import HybridRetriever, DomainAwareReranker
from copilot.adaptive_rag import (
    grade_retrieval_relevance,
    self_assess_response,
    select_strategy,
    CRAGResult,
)
from copilot.verifier import GroundingVerifier, RetrievalEvaluator, DomainScopeGate
from copilot.feedback_store import CopilotFeedbackStore
from copilot.agent import ask_bob_advanced


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_findings():
    return {
        "lot_id": "LOT-2231",
        "process_step": "etch",
        "candidate_causes": [
            {
                "tool_id": "ETCH-07",
                "step": "etch",
                "parameter": "chamber_pressure",
                "spatial_signature": "edge-ring",
                "probability": 0.82,
                "confidence_basis": "logistic_regression_v1",
                "sample_size": 45,
                "cpk": 0.88,
                "evidence": "Chamber pressure drifted +3.2 sigma with edge-ring signature",
            }
        ],
        "suspect_tools": [{"tool_id": "ETCH-07"}],
        "drift_parameters": [{"parameter": "chamber_pressure"}],
    }


# ---------------------------------------------------------------------------
# 1. Concept 1: Query Routing
# ---------------------------------------------------------------------------

class TestQueryRouting:
    def test_routes_greetings(self):
        router = QueryRouter()
        assert router.route("hello").target == QueryRoute.GREETING
        assert router.route("hey bob").target == QueryRoute.GREETING

    def test_routes_doe(self):
        router = QueryRouter()
        res = router.route("design a 2^k DOE for the chamber pressure excursion")
        assert res.target == QueryRoute.DOE_GENERATION

    def test_routes_sop(self):
        router = QueryRouter()
        res = router.route("what SOP procedure should I follow for chamber cleaning?")
        assert res.target == QueryRoute.SOP_RETRIEVAL

    def test_routes_findings(self, sample_findings):
        router = QueryRouter()
        res = router.route("why did LOT-2231 fail?", lot_context=sample_findings)
        assert res.target == QueryRoute.FINDINGS_GROUNDED

    def test_routes_out_of_scope(self):
        router = QueryRouter()
        res = router.route("what is the weather in Tokyo?")
        assert res.target == QueryRoute.OUT_OF_SCOPE


# ---------------------------------------------------------------------------
# 2. Concept 2: Query Rewriting
# ---------------------------------------------------------------------------

class TestQueryRewriting:
    def test_expands_abbreviations(self):
        rewriter = QueryRewriter()
        rewritten = rewriter.rewrite("check cp and rf on etch chamber")
        assert "chamber_pressure" in rewritten
        assert "rf_power_forward" in rewritten

    def test_injects_findings_context(self, sample_findings):
        rewriter = QueryRewriter()
        rewritten = rewriter.rewrite("why did it fail?", findings=sample_findings)
        assert "LOT-2231" in rewritten
        assert "ETCH-07" in rewritten
        assert "chamber_pressure" in rewritten


# ---------------------------------------------------------------------------
# 3. Concept 3: Multi-Query Generation
# ---------------------------------------------------------------------------

class TestMultiQuery:
    def test_generates_diverse_angles(self, sample_findings):
        gen = MultiQueryGenerator()
        queries = gen.generate("why did LOT-2231 fail?", findings=sample_findings)
        assert len(queries) >= 2
        # Original query is included
        assert queries[0] == "why did LOT-2231 fail?"
        # Equipment/symptom angles generated
        combined = " ".join(queries)
        assert "ETCH-07" in combined or "chamber_pressure" in combined


# ---------------------------------------------------------------------------
# 4. Concepts 4 & 5: Hybrid Search & Reranking
# ---------------------------------------------------------------------------

class TestHybridRetrievalAndReranking:
    def test_hybrid_search_finds_sop(self):
        retriever = HybridRetriever()
        results = retriever.retrieve("chamber pressure drift edge ring ETCH-07", top_k=3)
        assert len(results) > 0
        assert results[0]["score"] > 0.0
        # Verify SOP structure
        assert "sop" in results[0]
        assert "sop_id" in results[0]["sop"]

    def test_domain_reranker_boosts_matching_cause(self, sample_findings):
        retriever = HybridRetriever()
        candidates = retriever.retrieve("pressure drift", top_k=5)
        reranker = DomainAwareReranker(retriever)
        reranked = reranker.rerank("pressure drift", candidates, findings=sample_findings, top_k=3)
        assert len(reranked) <= 3
        # Top result should match etch step or chamber_pressure parameter
        top_sop = reranked[0]["sop"]
        assert top_sop.get("process_step") == "etch" or "pressure" in top_sop.get("parameter", "").lower()


# ---------------------------------------------------------------------------
# 5. Concept 6: CRAG (Corrective RAG)
# ---------------------------------------------------------------------------

class TestCRAG:
    def test_grades_relevant_document(self, sample_findings):
        retriever = HybridRetriever()
        docs = retriever.retrieve("ETCH-07 chamber pressure drift", top_k=2)
        crag = grade_retrieval_relevance("ETCH-07 chamber pressure drift", docs, sample_findings)
        assert crag.overall_grade in ("RELEVANT", "PARTIAL")
        assert len(crag.relevant_docs) > 0

    def test_flags_irrelevant_query(self, sample_findings):
        # When docs have very low overlap
        irrelevant_docs = [
            {"score": 0.01, "sop": {"process_step": "implant", "parameter": "beam_current", "keywords": ["beam"]}}
        ]
        crag = grade_retrieval_relevance("baking recipe pizza oven", irrelevant_docs, sample_findings)
        assert crag.overall_grade == "IRRELEVANT"
        assert crag.fallback_to_findings is True


# ---------------------------------------------------------------------------
# 6. Concept 7: Self-RAG
# ---------------------------------------------------------------------------

class TestSelfRAG:
    def test_passes_valid_answer(self, sample_findings):
        answer = (
            "Based on LOT-2231 telemetry, the leading candidate cause is chamber_pressure drift "
            "on ETCH-07. Recommend confirming via targeted DOE before taking corrective action."
        )
        assessment = self_assess_response(answer, "Why did LOT-2231 fail?", sample_findings)
        assert assessment.overall_pass is True
        assert assessment.should_regenerate is False

    def test_flags_invented_tool(self, sample_findings):
        answer = (
            "We detected an excursion on ETCH-99 causing the defect. Confirm with DOE."
        )
        assessment = self_assess_response(answer, "Why did LOT-2231 fail?", sample_findings)
        assert assessment.passes_grounding is False
        assert assessment.should_regenerate is True

    def test_flags_missing_doe_caveat(self, sample_findings):
        answer = (
            "The root cause is chamber_pressure drift on ETCH-07. Immediate tool shutdown required."
        )
        assessment = self_assess_response(answer, "What is the root cause?", sample_findings)
        assert assessment.passes_completeness is False
        assert assessment.should_regenerate is True


# ---------------------------------------------------------------------------
# 7. Concept 8: Adaptive Strategy Selection
# ---------------------------------------------------------------------------

class TestAdaptiveStrategy:
    def test_simple_lookup_for_status(self):
        strategy = select_strategy(QueryRoute.STATUS, "what is current yield?")
        assert strategy.name == "direct_lookup"
        assert strategy.needs_retrieval is False

    def test_agentic_rag_for_complex_inquiry(self):
        strategy = select_strategy(
            QueryRoute.FINDINGS_GROUNDED,
            "Analyze and explain root cause and recommend actions"
        )
        assert strategy.name == "agentic_rag"
        assert strategy.needs_multi_query is True


# ---------------------------------------------------------------------------
# 8. Concepts 9 & 10: Retrieval Evaluation & Domain Scope Gate
# ---------------------------------------------------------------------------

class TestVerifierAndEvaluator:
    def test_domain_scope_blocks_out_of_scope(self):
        in_scope, msg = DomainScopeGate.check_query_scope("what is your favorite pasta recipe?")
        assert in_scope is False
        assert "semiconductor" in msg.lower()

    def test_domain_scope_allows_fab_queries(self):
        in_scope, msg = DomainScopeGate.check_query_scope("What caused the etch yield loss on LOT-2231?")
        assert in_scope is True

    def test_retrieval_evaluator_metrics(self, sample_findings):
        evaluator = RetrievalEvaluator()
        retrieved_docs = [
            {"doc_id": "SOP-ETCH-401", "title": "Etch Chamber Maintenance", "equipment_type": "ETCH-07", "content": "chamber_pressure"}
        ]
        answer = "Following SOP-ETCH-401 for ETCH-07 chamber_pressure recalibration."
        res = evaluator.evaluate("ETCH-07 chamber_pressure", retrieved_docs, answer, sample_findings)
        assert res.retrieval_precision == 1.0
        assert res.retrieval_recall > 0.0
        assert res.context_utilization > 0.0


# ---------------------------------------------------------------------------
# 9. Self-Improving Feedback Store
# ---------------------------------------------------------------------------

class TestFeedbackStore:
    def test_records_and_retrieves_feedback(self):
        store = CopilotFeedbackStore()
        rec_id = store.record_interaction(
            query="Test query about ETCH-07",
            answer="Grounded answer about ETCH-07",
            lot_id="LOT-2231",
            route="findings_grounded",
            grounding_rate=1.0,
            retrieval_precision=1.0,
        )
        assert rec_id is not None

        # Record user thumbs up
        success = store.record_user_feedback(rec_id, "positive")
        assert success is True

        # Check metrics summary
        metrics = store.get_metrics_summary()
        assert metrics["total_interactions"] >= 1
        assert metrics["avg_grounding_rate"] > 0.0


# ---------------------------------------------------------------------------
# 10. End-to-End ask_bob_advanced Pipeline
# ---------------------------------------------------------------------------

class TestAskBobAdvanced:
    def test_handles_out_of_scope_gracefully(self, sample_findings):
        res = ask_bob_advanced("Tell me how to bake bread", findings=sample_findings)
        assert res["route"] == "out_of_scope"
        assert res["is_out_of_scope"] is True
        assert res["citations"] == []
        assert "semiconductor" in res["response"].lower()

    def test_handles_fab_query_with_grounding_and_citations(self, sample_findings):
        res = ask_bob_advanced(
            "Why did LOT-2231 have a yield drop?",
            findings=sample_findings,
            fast_mode=True,
        )
        assert res["route"] in ("findings_grounded", "sop_retrieval", "general_fab")
        assert res["grounding_rate"] >= 0.0
        assert len(res["citations"]) > 0
        assert "ETCH-07" in res["response"] or "chamber_pressure" in res["response"] or "LOT-2231" in res["response"]
