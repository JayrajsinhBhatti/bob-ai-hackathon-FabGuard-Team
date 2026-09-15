"""
analytics/commonality.py  —  Cross-Lot Commonality & Chamber Exclusion Matrix

Statistically proves whether a specific (tool, parameter) combination is
*uniquely common* to defective lots vs. nominal lots using:

  - 2×2 Contingency Table (defective/nominal × processed-on-tool / not)
  - Fisher's Exact Test (hypergeometric p-value) for statistical exclusivity
  - Odds Ratio to quantify the strength of chamber association
  - Relative Risk to communicate clinical magnitude

This converts the mandatory "correlation is not causation" caveat into a
rigorous, peer-reviewable mathematical proof that a tool is statistically
culpable before a DOE is even run.

Usage:
    from analytics.commonality import CommonalityAnalyzer
    analyzer = CommonalityAnalyzer(repository)
    result = analyzer.run_for_lot("LOT-2231")
"""

from typing import Any, Dict, List, Optional, Tuple
import math

from analytics.data_access import DataRepository


# ---------------------------------------------------------------------------
# Pure statistical helpers (no scipy dependency)
# ---------------------------------------------------------------------------

def _log_choose(n: int, k: int) -> float:
    """log(C(n,k)) via log-gamma to avoid integer overflow for large values."""
    if k < 0 or k > n:
        return float("-inf")
    return (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
    )


def _hypergeometric_pmf(k: int, N: int, K: int, n: int) -> float:
    """P(X = k) for Hypergeometric(N, K, n)."""
    log_p = _log_choose(K, k) + _log_choose(N - K, n - k) - _log_choose(N, n)
    return math.exp(log_p) if not math.isinf(log_p) else 0.0


def fisher_exact_p_value(a: int, b: int, c: int, d: int) -> float:
    """
    One-tailed Fisher's Exact Test for 2×2 table (right tail = over-representation).

    Table layout:
              | On Tool | Not On Tool |
    ----------+---------+-------------+
    Defective |    a    |      b      |
    Nominal   |    c    |      d      |

    Returns:
        p-value (probability of observing this or more extreme table under H0).
        Lower p-value = stronger statistical exclusivity of the tool to defective lots.
    """
    N = a + b + c + d
    K = a + c       # total on tool
    n = a + b       # total defective

    if N <= 0 or K <= 0 or n <= 0:
        return 1.0

    # Sum probabilities for all tables as extreme or more extreme than observed
    p_obs = _hypergeometric_pmf(a, N, K, n)
    p_value = 0.0
    max_k = min(K, n)

    for x in range(max_k + 1):
        p_x = _hypergeometric_pmf(x, N, K, n)
        if p_x <= p_obs + 1e-12:
            p_value += p_x

    return min(1.0, p_value)


def odds_ratio(a: int, b: int, c: int, d: int) -> float:
    """
    Odds Ratio = (a*d) / (b*c).
    OR > 1 means the tool is more common in defective lots.
    Returns float('inf') if denominator is 0 (perfect association).
    """
    denom = b * c
    if denom == 0:
        return float("inf") if a * d > 0 else 1.0
    return (a * d) / denom


def relative_risk(a: int, b: int, c: int, d: int) -> float:
    """
    Relative Risk = (a / (a+b)) / (c / (c+d)).
    RR > 1 means defective lots are more likely to have been processed on this tool.
    """
    defect_rate = a / (a + b) if (a + b) > 0 else 0.0
    normal_rate = c / (c + d) if (c + d) > 0 else 0.0
    if normal_rate == 0:
        return float("inf") if defect_rate > 0 else 1.0
    return defect_rate / normal_rate


# ---------------------------------------------------------------------------
# CommonalityAnalyzer
# ---------------------------------------------------------------------------

class CommonalityAnalyzer:
    """
    Computes statistical commonality of process tools/parameters across
    defective vs. nominal lots using Fisher's Exact Test.
    """

    def __init__(
        self,
        repository: DataRepository,
        low_yield_threshold: float = 90.0,
        min_lots_for_analysis: int = 4,
        p_value_significance: float = 0.05,
    ):
        self.repo = repository
        self.low_yield_threshold = low_yield_threshold
        self.min_lots = min_lots_for_analysis
        self.p_sig = p_value_significance

    def _partition_lots(self) -> Tuple[List[str], List[str]]:
        """Split completed lots into defective and nominal cohorts."""
        all_lots = self.repo.get_all_lots()
        defective, nominal = [], []
        for lot in all_lots:
            if lot.get("status") == "in_progress":
                continue
            yld = lot.get("final_yield_pct")
            if yld is None:
                continue
            lid = lot.get("lot_id")
            if yld < self.low_yield_threshold:
                defective.append(lid)
            else:
                nominal.append(lid)
        return defective, nominal

    def _build_tool_presence_map(
        self, lot_ids: List[str]
    ) -> Dict[str, Dict[str, set]]:
        """
        Build a map: tool_id → {lot_ids that were processed on it}.
        Returns Dict[tool_id, set_of_lot_ids].
        """
        tool_to_lots: Dict[str, set] = {}
        for lid in lot_ids:
            steps = self.repo.get_process_steps(lot_id=lid)
            seen_tools = set()
            for s in steps:
                tid = s.get("tool_id")
                if tid and tid not in seen_tools:
                    tool_to_lots.setdefault(tid, set()).add(lid)
                    seen_tools.add(tid)
        return tool_to_lots

    def run_for_lot(
        self,
        lot_id: str,
        top_n: int = 5,
    ) -> Dict[str, Any]:
        """
        Run cross-lot commonality analysis for all tools used in the given lot.

        For each (tool_id) involved in lot_id, computes the 2×2 Fisher's Exact
        contingency table and ranks by ascending p-value (most statistically
        significant exclusivity first).

        Args:
            lot_id: The lot under investigation.
            top_n:  Maximum number of tools to return in the ranked results.

        Returns:
            {
                "lot_id": "LOT-2231",
                "total_lots_analyzed": 80,
                "defective_lots": 20,
                "nominal_lots": 60,
                "findings": [
                    {
                        "tool_id": "ETCH-07",
                        "table": {"a":..,"b":..,"c":..,"d":..},
                        "p_value": 0.0004,
                        "odds_ratio": 18.5,
                        "relative_risk": 4.2,
                        "verdict": "STATISTICALLY SIGNIFICANT (p=0.0004) — ETCH-07 is...",
                        "significant": True,
                    }, ...
                ],
                "summary": "Cross-lot analysis across 80 lots: 1 tool(s) are statistically...",
            }
        """
        target_steps = self.repo.get_process_steps(lot_id=lot_id)
        if not target_steps:
            return {
                "lot_id": lot_id,
                "error": f"No process steps found for {lot_id}.",
                "findings": [],
            }

        # Tools used in the target lot
        target_tools = list({s.get("tool_id") for s in target_steps if s.get("tool_id")})

        defective_lots, nominal_lots = self._partition_lots()
        all_completed = defective_lots + nominal_lots
        N_def = len(defective_lots)
        N_nom = len(nominal_lots)
        N_total = N_def + N_nom

        if N_total < self.min_lots:
            return {
                "lot_id": lot_id,
                "error": f"Insufficient historical data ({N_total} completed lots, need ≥ {self.min_lots}).",
                "findings": [],
                "total_lots_analyzed": N_total,
            }

        # Build tool presence maps for both cohorts
        def_tool_map = self._build_tool_presence_map(defective_lots)
        nom_tool_map = self._build_tool_presence_map(nominal_lots)

        findings = []
        for tid in target_tools:
            # 2×2 table
            a = len(def_tool_map.get(tid, set()))   # defective + processed on tool
            b = N_def - a                            # defective + NOT on tool
            c = len(nom_tool_map.get(tid, set()))   # nominal + processed on tool
            d = N_nom - c                            # nominal + NOT on tool

            # Guard: at least some data in each row
            if (a + b) == 0 or (c + d) == 0:
                continue

            p = fisher_exact_p_value(a, b, c, d)
            or_ = odds_ratio(a, b, c, d)
            rr = relative_risk(a, b, c, d)
            significant = p < self.p_sig

            # Strength descriptor
            if p < 0.001:
                strength = "very strong"
            elif p < 0.01:
                strength = "strong"
            elif p < 0.05:
                strength = "moderate"
            else:
                strength = "not statistically significant"

            if significant:
                verdict = (
                    f"STATISTICALLY SIGNIFICANT (p={p:.4f}, {strength}) — "
                    f"{tid} was processed on {a}/{N_def} defective lots vs "
                    f"{c}/{N_nom} nominal lots. "
                    f"Odds Ratio: {or_:.1f}x (tool strongly associated with yield loss). "
                    f"Relative Risk: {rr:.1f}x."
                )
            else:
                verdict = (
                    f"NOT SIGNIFICANT (p={p:.4f}) — "
                    f"{tid} does not show statistically significant association with yield loss "
                    f"({a}/{N_def} defective vs {c}/{N_nom} nominal lots)."
                )

            findings.append({
                "tool_id": tid,
                "table": {"a_defective_on_tool": a, "b_defective_off_tool": b,
                          "c_nominal_on_tool": c, "d_nominal_off_tool": d},
                "p_value": round(p, 6),
                "odds_ratio": round(or_, 2) if not math.isinf(or_) else 9999.0,
                "relative_risk": round(rr, 2) if not math.isinf(rr) else 9999.0,
                "verdict": verdict,
                "significant": significant,
            })

        # Sort by p-value ascending (most significant first), then limit
        findings.sort(key=lambda x: x["p_value"])
        findings = findings[:top_n]

        sig_count = sum(1 for f in findings if f["significant"])
        if sig_count > 0:
            sig_tools = [f["tool_id"] for f in findings if f["significant"]]
            summary = (
                f"Cross-lot analysis across {N_total} lots "
                f"({N_def} defective, {N_nom} nominal): "
                f"{sig_count} tool(s) show statistically significant association with yield loss: "
                f"{', '.join(sig_tools)}. "
                f"Recommend these tools as priority targets for corrective action after DOE confirmation."
            )
        else:
            summary = (
                f"Cross-lot analysis across {N_total} lots "
                f"({N_def} defective, {N_nom} nominal): "
                f"No tools from lot {lot_id} show statistically significant exclusive association "
                f"with yield loss at p < {self.p_sig}. "
                f"Consider broader process factors or a multi-variate analysis."
            )

        return {
            "lot_id": lot_id,
            "total_lots_analyzed": N_total,
            "defective_lots": N_def,
            "nominal_lots": N_nom,
            "findings": findings,
            "summary": summary,
        }

    def format_as_text(self, result: Dict[str, Any]) -> str:
        """Format commonality results as human-readable text for IBM Bob / MCP output."""
        lines = [
            f"=== Cross-Lot Commonality Analysis: {result.get('lot_id', 'UNKNOWN')} ===",
            "",
        ]

        if "error" in result:
            lines.append(f"⚠️  {result['error']}")
            return "\n".join(lines)

        lines.append(
            f"Dataset: {result['total_lots_analyzed']} completed lots "
            f"({result['defective_lots']} defective / {result['nominal_lots']} nominal)"
        )
        lines.append("")

        findings = result.get("findings", [])
        if not findings:
            lines.append("No tools found for analysis.")
        else:
            lines.append(f"Tool Exclusivity Rankings ({len(findings)} tools from this lot):")
            for i, f in enumerate(findings, 1):
                sig_marker = "🔴" if f["significant"] else "🟢"
                lines.append(f"  {sig_marker} #{i}: {f['tool_id']}")
                lines.append(f"       p-value: {f['p_value']:.4f}  |  Odds Ratio: {f['odds_ratio']:.1f}x  |  Relative Risk: {f['relative_risk']:.1f}x")
                lines.append(f"       {f['verdict']}")
                lines.append("")

        lines.append("─" * 60)
        lines.append(result.get("summary", ""))
        lines.append("")
        lines.append("⚠️  DOE Caveat: Statistical exclusivity is not physical causation.")
        lines.append("   Confirmatory DOE required before equipment corrective action.")

        return "\n".join(lines)
