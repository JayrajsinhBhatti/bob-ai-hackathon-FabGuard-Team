"""
src/mcp_server.py  —  IBM Bob MCP Server (Model Context Protocol)

Exposes the Fab Yield & Defect Analysis tools directly to IBM Bob via the
standard MCP stdio JSON-RPC transport.

IBM Bob can call these tools conversationally, e.g.:
    "@bob analyze LOT-2231 and tell me if ETCH-07 is the cause"
    "@bob what batches are at risk?"

Tools exposed:
    - analyze_lot(lot_id)              -> Human-readable diagnostic briefing
    - get_root_cause_findings(lot_id)  -> Raw JSON findings dict (for Bob to reason over)
    - predict_batch_risk()             -> List of at-risk upcoming batches
    - ask_fab_copilot(query, lot_id?)  -> Conversational answer from the Bob Copilot
    - run_commonality_analysis(lot_id) -> Fisher's Exact cross-lot tool exclusivity matrix
    - simulate_yield_recovery(lot_id)  -> Counterfactual yield & financial recovery estimate
    - generate_doe_matrix(lot_id)      -> Statistical DOE runcard for confirmatory experiment

All stdout is reserved for MCP JSON-RPC messages.
All logging/debug output goes to stderr to avoid protocol corruption.

MCP SDK Reference: https://github.com/modelcontextprotocol/python-sdk
"""

import json
import os
import sys
import traceback
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Path bootstrap — ensure repo root and src are importable regardless of cwd
# ---------------------------------------------------------------------------
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SRC_DIR)
for _p in [_REPO_ROOT, _SRC_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# Internal imports (analytics + copilot layers)
# ---------------------------------------------------------------------------

def _get_analytics():
    """Lazy-import analytics to avoid heavy startup cost for health checks."""
    try:
        from analytics.pipeline import analyze_lot as _analyze_lot
        return _analyze_lot
    except ImportError as e:
        print(f"[mcp_server] WARNING: analytics.pipeline unavailable: {e}", file=sys.stderr)
        return None


def _get_batch_predictor():
    try:
        from analytics.pipeline import get_default_repository
        from analytics.batch_risk import BatchRiskPredictor
        repo = get_default_repository()
        return BatchRiskPredictor(repository=repo)
    except Exception as e:
        print(f"[mcp_server] WARNING: BatchRiskPredictor unavailable: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# MCP Tool Implementations (pure functions — usable standalone for tests)
# ---------------------------------------------------------------------------

def analyze_lot(lot_id: str) -> str:
    """
    Run root-cause analysis on a wafer lot and return a human-readable
    diagnostic briefing for IBM Bob.

    Args:
        lot_id: Wafer lot identifier, e.g. "LOT-2231".

    Returns:
        A formatted string briefing with ranked candidate causes, evidence
        summary, and DOE caveat. IBM Bob displays this directly to the engineer.
    """
    _analyze = _get_analytics()
    if _analyze is None:
        return f"[Error] Analytics pipeline not available. Cannot analyze {lot_id}."

    try:
        findings = _analyze(lot_id, include_v3_fields=True)
    except Exception as e:
        return f"[Error] Failed to analyze {lot_id}: {e}"

    # Build human-readable briefing
    causes = findings.get("candidate_causes", [])
    at_risk = findings.get("at_risk_upcoming_batches", [])

    lines = [f"=== Fab Diagnostic Briefing: {lot_id} ===", ""]

    if not causes:
        lines.append("No candidate root causes identified for this lot.")
    else:
        lines.append(f"Ranked Root Cause Candidates ({len(causes)} total):")
        for i, c in enumerate(causes, 1):
            basis = c.get("confidence_basis", "unknown")
            prob = c.get("probability")
            risk = c.get("risk_score")

            if basis == "logistic_regression_v1" and prob is not None:
                score_str = f"{int(round(prob * 100))}% probability (ML model)"
            elif basis == "composite_heuristic_v1" and risk is not None:
                score_str = f"risk score {risk:.2f} (heuristic — not a probability)"
            else:
                score_str = f"prob={prob}, risk={risk}"

            lines.append(
                f"  #{i}: Step={c.get('step')}  Tool={c.get('tool_id')}  "
                f"Param={c.get('parameter')}  Spatial={c.get('spatial_signature')}"
            )
            lines.append(f"       Confidence: {score_str}  |  n={c.get('sample_size')}")
            lines.append(f"       Evidence: {c.get('evidence', 'N/A')}")

    lines.append("")
    if at_risk:
        lines.append(f"At-Risk Upcoming Batches ({len(at_risk)}):")
        for b in at_risk:
            prob = b.get("probability")
            risk = b.get("risk_score")
            if prob is not None:
                s = f"{int(round(prob * 100))}% probability"
            elif risk is not None:
                s = f"risk score {risk:.2f}"
            else:
                s = "risk unquantified"
            lines.append(f"  - {b.get('lot_id')}: {s}  sig={b.get('matched_signature')}")
    else:
        lines.append("At-Risk Batches: None flagged.")

    lines.append("")
    lines.append("⚠️  DOE Caveat: All root-cause rankings are statistical candidates.")
    lines.append("   Confirmatory Design-of-Experiment (DOE) runs are REQUIRED before")
    lines.append("   any corrective action is taken on production equipment.")

    return "\n".join(lines)


def get_root_cause_findings(lot_id: str) -> str:
    """
    Return the raw root_cause_findings JSON for a lot.

    IBM Bob can use this to reason deeply over structured data fields
    (candidate_causes, at_risk_upcoming_batches, etc.).

    Args:
        lot_id: Wafer lot identifier, e.g. "LOT-2231".

    Returns:
        JSON string of the root_cause_findings contract dict.
    """
    _analyze = _get_analytics()
    if _analyze is None:
        return json.dumps({"error": "Analytics pipeline not available.", "lot_id": lot_id})

    try:
        findings = _analyze(lot_id, include_v3_fields=True)
        return json.dumps(findings, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "lot_id": lot_id})


def predict_batch_risk() -> str:
    """
    Scan all in-progress lots and return a risk summary of upcoming batches.

    IBM Bob calls this to proactively surface which lots are at risk of yield
    loss before they complete — enabling early intervention.

    Returns:
        Human-readable string listing at-risk batches, or a nominal status message.
    """
    predictor = _get_batch_predictor()
    if predictor is None:
        return "[Error] Batch risk predictor not available."

    try:
        at_risk = predictor.predict_at_risk_batches()
    except Exception as e:
        return f"[Error] Batch risk prediction failed: {e}"

    if not at_risk:
        return "Batch Risk Assessment: All in-progress lots are within nominal risk thresholds."

    lines = [f"=== Batch Risk Assessment ({len(at_risk)} at-risk lots) ===", ""]
    for b in at_risk:
        # Handle both AtRiskBatch dataclass objects and plain dicts
        if hasattr(b, "probability"):
            prob = b.probability
            risk = b.risk_score
            lot = b.lot_id
            sig = b.matched_signature
        else:
            prob = b.get("probability")
            risk = b.get("risk_score")
            lot = b.get("lot_id")
            sig = b.get("matched_signature")

        if prob is not None:
            s = f"{int(round(prob * 100))}% probability of yield excursion"
        elif risk is not None:
            s = f"risk score {risk:.2f}"
        else:
            s = "risk level unquantified"
        lines.append(f"  LOT {lot}: {s}  |  matched_signature={sig}")

    lines.append("")
    lines.append("Recommendation: Prioritize inspection for lots listed above.")
    return "\n".join(lines)


def ask_fab_copilot(query: str, lot_id: str = None) -> str:
    """
    Ask the Fab Copilot (Bob) a natural-language question, optionally grounded
    in the findings for a specific lot.

    IBM Bob delegates domain-specific reasoning here, for example:
        "Is ETCH-07 the likely cause of LOT-2231's yield loss?"
        "What DOE should we run before taking corrective action?"

    Args:
        query:  The engineer's natural-language question.
        lot_id: Optional lot identifier to ground the answer in real findings.

    Returns:
        Bob's natural-language answer.
    """
    try:
        from copilot.agent import ask_bob_single, create_bob_session, ask_bob
        from copilot.config import get_llm_client

        client = get_llm_client()
        findings = None

        if lot_id:
            _analyze = _get_analytics()
            if _analyze:
                try:
                    findings = _analyze(lot_id, include_v3_fields=True)
                except Exception as e:
                    print(f"[mcp_server] WARNING: Could not load findings for {lot_id}: {e}", file=sys.stderr)

        answer = ask_bob_single(query, findings=findings, client=client)
        return answer

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"[Error] Copilot unavailable: {e}"


def run_commonality_analysis(lot_id: str) -> str:
    """
    Run cross-lot commonality analysis for a lot using Fisher's Exact Test.

    Statistically proves whether specific tools are uniquely common to
    defective lots vs. nominal lots (p-value, odds ratio, relative risk).

    Args:
        lot_id: Wafer lot identifier.

    Returns:
        Human-readable commonality report with tool exclusivity rankings.
    """
    try:
        from analytics.commonality import CommonalityAnalyzer
        from analytics.pipeline import get_default_repository
        repo = get_default_repository()
        analyzer = CommonalityAnalyzer(repo)
        result = analyzer.run_for_lot(lot_id)
        return analyzer.format_as_text(result)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"[Error] Commonality analysis failed for {lot_id}: {e}"


def simulate_yield_recovery(lot_id: str) -> str:
    """
    Simulate counterfactual yield recovery and financial impact for a lot.

    Computes what yield percentage and dollar value would be recovered by
    fixing each identified process excursion.

    Args:
        lot_id: Wafer lot identifier.

    Returns:
        Yield recovery simulation with per-lot financial estimates.
    """
    try:
        from analytics.counterfactual import CounterfactualSimulator
        from analytics.pipeline import analyze_lot as _al, get_default_repository
        repo = get_default_repository()
        findings = _al(lot_id, include_v3_fields=True)
        sim = CounterfactualSimulator(repo)
        result = sim.simulate_recovery_for_lot(lot_id, findings)
        return sim.format_as_text(result)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"[Error] Yield recovery simulation failed for {lot_id}: {e}"


def generate_doe_matrix(lot_id: str) -> str:
    """
    Generate a statistical DOE runcard for the top candidate root cause of a lot.

    Creates a complete 2^k factorial experiment matrix with factor levels,
    randomized run order, and confirmatory success criteria.

    Args:
        lot_id: Wafer lot identifier.

    Returns:
        Formatted DOE runcard with run sheet and hypothesis statement.
    """
    try:
        from analytics.pipeline import analyze_lot as _al, get_default_repository
        from copilot.doe_engine import DOEEngine
        repo = get_default_repository()
        findings = _al(lot_id, include_v3_fields=True)
        causes = findings.get("candidate_causes", [])
        if not causes:
            return f"[DOE Generator] No candidate causes found for {lot_id}. Cannot design experiment."
        engine = DOEEngine(repo)
        runcard = engine.generate_for_cause(lot_id, causes[0])
        return engine.format_as_text(runcard)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"[Error] DOE generation failed for {lot_id}: {e}"


# ---------------------------------------------------------------------------
# MCP Server Registration (stdio JSON-RPC via mcp SDK)
# ---------------------------------------------------------------------------

def run_mcp_server():
    """
    Start the MCP stdio server and register all Fab tools with IBM Bob.

    This function is the entry point when IBM Bob connects via MCP.
    All stdout is used exclusively for JSON-RPC messages.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print(
            "[mcp_server] ERROR: 'mcp' package not installed. "
            "Run: pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp = FastMCP("fab-analytics")

    @mcp.tool()
    def mcp_analyze_lot(lot_id: str) -> str:
        """Run root-cause analysis on a wafer lot and return a diagnostic briefing."""
        return analyze_lot(lot_id)

    @mcp.tool()
    def mcp_get_root_cause_findings(lot_id: str) -> str:
        """Return raw root_cause_findings JSON for a lot."""
        return get_root_cause_findings(lot_id)

    @mcp.tool()
    def mcp_predict_batch_risk() -> str:
        """Scan all in-progress lots and return a risk summary."""
        return predict_batch_risk()

    @mcp.tool()
    def mcp_ask_fab_copilot(query: str, lot_id: str = "") -> str:
        """Ask the Fab Copilot a natural-language question, optionally grounded in a lot's findings."""
        return ask_fab_copilot(query, lot_id=lot_id if lot_id else None)

    @mcp.tool()
    def mcp_run_commonality_analysis(lot_id: str) -> str:
        """Run cross-lot Fisher's Exact Test to prove statistical tool exclusivity for a lot."""
        return run_commonality_analysis(lot_id)

    @mcp.tool()
    def mcp_simulate_yield_recovery(lot_id: str) -> str:
        """Simulate counterfactual yield recovery and financial impact for a lot's excursions."""
        return simulate_yield_recovery(lot_id)

    @mcp.tool()
    def mcp_generate_doe_matrix(lot_id: str) -> str:
        """Generate a statistical 2^k factorial DOE runcard for confirming the top root cause."""
        return generate_doe_matrix(lot_id)

    print("[mcp_server] IBM Bob Fab Analytics MCP server starting on stdio...", file=sys.stderr)
    mcp.run(transport="stdio")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_mcp_server()
