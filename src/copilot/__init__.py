"""
Bob Fab Copilot Package.
GenAI Copilot for Fab Engineers:
- Explanation Generator (plain-English root cause explanations)
- Recommendation Generator (domain-grounded corrective actions)
- Ask Bob (conversational Q&A assistant)
"""

__version__ = "0.2.0"

from .agent import ask_bob, ask_bob_single, ask_bob_advanced, create_bob_session
from .query_intelligence import QueryRouter, QueryRewriter, MultiQueryGenerator, QueryRoute
from .rag_retriever import HybridRetriever, DomainAwareReranker, FabSOPRetriever
from .adaptive_rag import grade_retrieval_relevance, self_assess_response, select_strategy
from .verifier import GroundingVerifier, RetrievalEvaluator, DomainScopeGate
from .feedback_store import CopilotFeedbackStore

__all__ = [
    "ask_bob",
    "ask_bob_single",
    "ask_bob_advanced",
    "create_bob_session",
    "QueryRouter",
    "QueryRewriter",
    "MultiQueryGenerator",
    "QueryRoute",
    "HybridRetriever",
    "DomainAwareReranker",
    "FabSOPRetriever",
    "grade_retrieval_relevance",
    "self_assess_response",
    "select_strategy",
    "GroundingVerifier",
    "RetrievalEvaluator",
    "DomainScopeGate",
    "CopilotFeedbackStore",
]

