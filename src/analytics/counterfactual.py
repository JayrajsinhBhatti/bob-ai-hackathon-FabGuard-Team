"""
analytics/counterfactual.py  —  Counterfactual Yield & Financial Recovery Simulator

Answers the question every fab manager asks:
  "If we fix this tool excursion, how much yield do we recover — and what is it worth?"

Uses the root_cause_findings from the analytics pipeline to compute:

  1. Baseline Yield Impact Score:
     Derived from the candidate cause's deviation score and frequency across lots.
     ΔYield_estimate = deviation_score × frequency × empirical_yield_gap

  2. Counterfactual Recovery Estimate:
     What yield percentage is recoverable if the drifted parameter is re-centered
     to its nominal baseline value.

  3. Financial Recovery Value:
     ΔYield × Wafers per Lot × Die per Wafer × Average Selling Price per Die

All estimates are clearly labeled as *estimates* with explicit uncertainty ranges.
No hallucinated numbers — all inputs come from the findings contract and config.

Usage:
    from analytics.counterfactual import CounterfactualSimulator
    sim = CounterfactualSimulator(repository)
    result = sim.simulate_recovery_for_lot("LOT-2231", findings)
"""

from typing import Any, Dict, List, Optional, Tuple
import math

from analytics.data_access import DataRepository


# ---------------------------------------------------------------------------
# Default fab economics (configurable, clearly labeled as assumptions)
# ---------------------------------------------------------------------------

DEFAULT_WAFERS_PER_LOT = 25          # Standard production lot size (SEMI SPEC)
DEFAULT_DIE_PER_WAFER = 500          # Approximate die count for 3nm/5nm node, ~26mm² die
DEFAULT_ASP_PER_DIE_USD = 45.0       # Average Selling Price per die (~$45 for advanced node SoC)
DEFAULT_YIELD_GAP_PCT = 12.0         # Typical yield gap in excursion conditions (%)


class CounterfactualSimulator:
    """
    Simulates counterfactual yield recovery and financial impact of fixing
    process excursions identified by the Analytics Core.
    """

    def __init__(
        self,
        repository: DataRepository,
        wafers_per_lot: int = DEFAULT_WAFERS_PER_LOT,
        die_per_wafer: int = DEFAULT_DIE_PER_WAFER,
        asp_per_die_usd: float = DEFAULT_ASP_PER_DIE_USD,
        low_yield_threshold: float = 90.0,
    ):
        self.repo = repository
        self.wafers_per_lot = wafers_per_lot
        self.die_per_wafer = die_per_wafer
        self.asp_per_die_usd = asp_per_die_usd
        self.low_yield_threshold = low_yield_threshold

    def _compute_yield_gap(self, lot_id: str) -> float:
        """
        Compute the actual yield gap for the target lot vs. the nominal population.
        Returns the yield gap in percentage points (e.g., 8.5 means lot yield is 8.5% below avg).
        Falls back to DEFAULT_YIELD_GAP_PCT if data is insufficient.
        """
        lot = self.repo.get_lot(lot_id)
        if lot is None:
            return DEFAULT_YIELD_GAP_PCT

        lot_yield = lot.get("final_yield_pct")
        if lot_yield is None:
            return DEFAULT_YIELD_GAP_PCT

        # Compute mean yield of normal lots
        all_lots = self.repo.get_all_lots()
        normal_yields = [
            l.get("final_yield_pct")
            for l in all_lots
            if l.get("status") != "in_progress"
            and l.get("final_yield_pct") is not None
            and l.get("final_yield_pct") >= self.low_yield_threshold
        ]
        if not normal_yields:
            return DEFAULT_YIELD_GAP_PCT

        avg_normal_yield = sum(normal_yields) / len(normal_yields)
        gap = avg_normal_yield - lot_yield
        return max(0.0, gap)

    def _estimate_cause_yield_impact(
        self,
        cause: Dict[str, Any],
        yield_gap: float,
    ) -> Tuple[float, float, float]:
        """
        Estimate the yield impact attributable to this specific candidate cause.

        Returns:
            (attributed_yield_loss_pct, recoverable_yield_pct, confidence_factor)

        Logic:
            Each cause's composite deviation_score × confidence represents its
            relative contribution to the total yield gap. For the top-ranked cause,
            we attribute a portion of the yield gap proportional to its score.
        """
        deviation_score = cause.get("deviation_score", 0.0) or 0.0
        confidence = cause.get("confidence", 0.0) or 0.0
        risk_score = cause.get("risk_score") or cause.get("probability") or 0.0

        # Attribution factor: how much of the yield gap is driven by this cause
        # Conservative: score-weighted fraction, capped at 80% (never blame single cause for all)
        attribution_factor = min(0.80, deviation_score * confidence)

        # Recoverable yield = attribution × total yield gap × slight discount for model uncertainty
        confidence_factor = min(0.90, confidence + 0.10)  # slight upward prior from sample data
        attributed_loss = yield_gap * attribution_factor
        recoverable = attributed_loss * confidence_factor

        return round(attributed_loss, 2), round(recoverable, 2), round(confidence_factor, 2)

    def _compute_financial_impact(self, recoverable_yield_pct: float) -> Dict[str, Any]:
        """
        Translate a yield recovery percentage into dollars and die counts.

        Args:
            recoverable_yield_pct: Percentage points of yield recovered (e.g., 4.8 = 4.8%).

        Returns:
            Dict with die_count_recovered, dollar_recovery_per_lot, and assumptions.
        """
        # Die recovered per lot = (yield_pct/100) × wafers × die_per_wafer
        die_per_lot = (recoverable_yield_pct / 100.0) * self.wafers_per_lot * self.die_per_wafer
        usd_per_lot = die_per_lot * self.asp_per_die_usd

        return {
            "die_recovered_per_lot": round(die_per_lot, 0),
            "usd_recovery_per_lot": round(usd_per_lot, 2),
            "assumptions": {
                "wafers_per_lot": self.wafers_per_lot,
                "die_per_wafer": self.die_per_wafer,
                "asp_per_die_usd": self.asp_per_die_usd,
            },
        }

    def simulate_recovery_for_lot(
        self,
        lot_id: str,
        findings: Dict[str, Any],
        max_causes: int = 3,
    ) -> Dict[str, Any]:
        """
        Run counterfactual yield & financial recovery simulation for a lot.

        Args:
            lot_id:     The lot identifier.
            findings:   root_cause_findings dict from analytics pipeline.
            max_causes: Limit to top N candidate causes (default 3).

        Returns:
            {
                "lot_id": "LOT-2231",
                "actual_yield_gap_pct": 8.5,
                "cause_simulations": [
                    {
                        "rank": 1,
                        "tool_id": "ETCH-07",
                        "parameter": "chamber_pressure",
                        "attributed_yield_loss_pct": 5.1,
                        "recoverable_yield_pct": 4.3,
                        "die_recovered_per_lot": 537.5,
                        "usd_recovery_per_lot": 24187.5,
                        "confidence_factor": 0.72,
                        "narrative": "...",
                    }, ...
                ],
                "total_recoverable_yield_pct": 5.8,
                "total_usd_recovery_per_lot": 32625.0,
                "summary": "Fixing ETCH-07 pressure could recover ~4.3% yield...",
            }
        """
        yield_gap = self._compute_yield_gap(lot_id)
        causes = findings.get("candidate_causes", [])[:max_causes]

        cause_sims = []
        total_recoverable = 0.0
        total_usd = 0.0

        for rank, cause in enumerate(causes, 1):
            attr_loss, recoverable, conf_factor = self._estimate_cause_yield_impact(
                cause, yield_gap
            )
            financials = self._compute_financial_impact(recoverable)

            tool_id = cause.get("tool_id", "UNKNOWN")
            parameter = cause.get("parameter", "unknown")
            step = cause.get("step", "unknown")
            spatial = cause.get("spatial_signature", "random")
            evidence = cause.get("evidence", "")

            # Uncertainty bounds (±30% of estimate, reflecting model uncertainty)
            low_est = round(recoverable * 0.70, 2)
            high_est = round(recoverable * 1.30, 2)
            usd_low = round(financials["usd_recovery_per_lot"] * 0.70, 2)
            usd_high = round(financials["usd_recovery_per_lot"] * 1.30, 2)

            narrative = (
                f"If {parameter.replace('_', ' ')} on {tool_id} ({step} step) is re-centered "
                f"to nominal operating conditions, the estimated recoverable yield is "
                f"~{recoverable:.1f}% (range: {low_est}–{high_est}%). "
                f"This translates to approximately ${financials['usd_recovery_per_lot']:,.0f} "
                f"per lot (range: ${usd_low:,.0f}–${usd_high:,.0f}). "
                f"Confidence factor: {conf_factor:.0%}. "
                f"The {spatial} spatial defect signature supports this attribution. "
                f"These are simulation estimates — confirmatory DOE required before action."
            )

            cause_sims.append({
                "rank": rank,
                "tool_id": tool_id,
                "parameter": parameter,
                "step": step,
                "attributed_yield_loss_pct": attr_loss,
                "recoverable_yield_pct": recoverable,
                "recoverable_yield_range_pct": [low_est, high_est],
                "die_recovered_per_lot": financials["die_recovered_per_lot"],
                "usd_recovery_per_lot": financials["usd_recovery_per_lot"],
                "usd_recovery_range": [usd_low, usd_high],
                "confidence_factor": conf_factor,
                "financial_assumptions": financials["assumptions"],
                "narrative": narrative,
            })

            total_recoverable += recoverable
            total_usd += financials["usd_recovery_per_lot"]

        # Cap total to actual yield gap (can't recover more than lost)
        total_recoverable = min(total_recoverable, yield_gap)
        total_recoverable = round(total_recoverable, 2)
        total_usd = round(total_usd, 2)

        if cause_sims:
            top = cause_sims[0]
            summary = (
                f"Counterfactual simulation for {lot_id}: "
                f"Actual yield gap vs. nominal: {yield_gap:.1f}%. "
                f"Top intervention — fix {top['parameter'].replace('_', ' ')} on {top['tool_id']}: "
                f"estimated +{top['recoverable_yield_pct']:.1f}% yield recovery "
                f"(~${top['usd_recovery_per_lot']:,.0f}/lot). "
                f"Combined recovery from top {len(cause_sims)} interventions: "
                f"+{total_recoverable:.1f}% yield (~${total_usd:,.0f}/lot). "
                f"All estimates subject to ±30% uncertainty and require DOE confirmation."
            )
        else:
            summary = f"No candidate causes found for {lot_id}. Cannot simulate recovery."

        return {
            "lot_id": lot_id,
            "actual_yield_gap_pct": round(yield_gap, 2),
            "cause_simulations": cause_sims,
            "total_recoverable_yield_pct": total_recoverable,
            "total_usd_recovery_per_lot": total_usd,
            "summary": summary,
            "disclaimer": (
                "All yield and financial figures are simulation estimates based on "
                "statistical attribution from the analytics model. "
                "Assumptions: {wafers}/lot, {die} die/wafer, ${asp:.0f}/die ASP. "
                "Confirmatory DOE runs are required before taking corrective action."
            ).format(
                wafers=self.wafers_per_lot,
                die=self.die_per_wafer,
                asp=self.asp_per_die_usd,
            ),
        }

    def format_as_text(self, result: Dict[str, Any]) -> str:
        """Format simulation results as human-readable text for IBM Bob / MCP output."""
        lines = [
            f"=== Counterfactual Yield & Financial Recovery Simulation: {result.get('lot_id')} ===",
            "",
            f"Actual Yield Gap vs. Nominal Population: {result.get('actual_yield_gap_pct', 0):.1f}%",
            "",
        ]

        cause_sims = result.get("cause_simulations", [])
        if not cause_sims:
            lines.append("No candidate causes available for simulation.")
        else:
            lines.append("Recovery Scenarios (per corrective action):")
            for sim in cause_sims:
                lines.append(
                    f"  #{sim['rank']}: Fix {sim['parameter'].replace('_',' ')} on {sim['tool_id']} ({sim['step']} step)"
                )
                lines.append(
                    f"       Recoverable Yield:  ~+{sim['recoverable_yield_pct']:.1f}%  "
                    f"(range: {sim['recoverable_yield_range_pct'][0]}–{sim['recoverable_yield_range_pct'][1]}%)"
                )
                lines.append(
                    f"       Financial Recovery: ~${sim['usd_recovery_per_lot']:,.0f}/lot  "
                    f"(range: ${sim['usd_recovery_range'][0]:,.0f}–${sim['usd_recovery_range'][1]:,.0f})"
                )
                lines.append(f"       Confidence Factor: {sim['confidence_factor']:.0%}")
                lines.append("")

        lines.append("─" * 60)
        lines.append(
            f"Combined Total Recovery (all interventions): "
            f"+{result.get('total_recoverable_yield_pct', 0):.1f}% yield  "
            f"| ~${result.get('total_usd_recovery_per_lot', 0):,.0f}/lot"
        )
        lines.append("")
        lines.append(f"Summary: {result.get('summary', '')}")
        lines.append("")
        lines.append(f"⚠️  {result.get('disclaimer', '')}")

        return "\n".join(lines)
