"""
copilot/recommender.py  —  Step 4: Recommendation Generator (§5.2)

Generates domain-grounded corrective action recommendations per root-cause category.

Logic:
  1. Hard-coded lookup table maps (step, parameter) → root-cause category + standard actions.
  2. LLM phrases the recommendation naturally (tool-specific, contextual wording).

Source: §5.2 of S1_FINAL_Implementation_Plan_v3.md
"""

from typing import Any

from .config import (
    get_llm_client,
    LLM_PROVIDER,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    DOE_CAVEAT_STRING,
    GROQ_API_KEY,
    GROQ_MODEL,
)


# ---------------------------------------------------------------------------
# Domain knowledge lookup table (§5.2 — hard-coded, never LLM-generated)
# ---------------------------------------------------------------------------

DOMAIN_LOOKUP: dict[tuple[str, str], dict] = {
    # Etch step
    ("etch", "chamber_pressure"): {
        "category": "Pressure drift / chamber seal",
        "standard_actions": [
            "Perform PM inspection of chamber seal and O-ring integrity on affected tool",
            "Requalify etch recipe on the tool after PM",
            "Review pressure trace logs for drift pattern (sustained vs. transient)",
            "Gate lots on this tool until chamber seal is cleared",
        ],
    },
    ("etch", "rf_power_forward"): {
        "category": "RF generator / matching network fault",
        "standard_actions": [
            "Run RF power calibration check on the generator and matching network",
            "Inspect RF transmission line and cable connectors for degradation",
            "Perform PM on RF generator if power oscillation is sustained",
            "Compare RF power forward vs. reflected trace to isolate impedance mismatch",
        ],
    },
    # Litho step
    ("litho", "focus_offset"): {
        "category": "Lens aberration / stage drift",
        "standard_actions": [
            "Run lens alignment calibration procedure on the scanner",
            "Perform stage leveling and z-sensor recalibration",
            "Inspect autofocus system for sensor drift",
            "Run focus-exposure matrix (FEM) wafer to characterize current aberration extent",
        ],
    },
    ("litho", "exposure_energy"): {
        "category": "Light source degradation / dose instability",
        "standard_actions": [
            "Run energy calibration and dose stability check on the light source",
            "Inspect lamp or laser source for end-of-life indicators",
            "Check dose uniformity across slit using a monitor wafer",
            "Schedule bulb/source replacement if output variance exceeds spec",
        ],
    },
    # CVD step
    ("cvd", "deposition_temp"): {
        "category": "Heater degradation / gas flow anomaly",
        "standard_actions": [
            "Inspect and verify pedestal heater operation and temperature profile",
            "Re-validate temperature uniformity across wafer with thermocouple mapping",
            "Check gas flow controllers (MFCs) for drift or clogging",
            "Run a deposition qualification wafer before releasing production lots",
        ],
    },
    # CMP step
    ("cmp", "head_downforce"): {
        "category": "Polishing head mechanical wear",
        "standard_actions": [
            "Inspect polishing head for mechanical wear, membrane degradation, or retainer ring damage",
            "Schedule head replacement or refurbishment",
            "Re-condition pad after head replacement",
            "Run within-wafer uniformity (WIW-U) test after head service",
        ],
    },
    ("cmp", "slurry_flow_rate"): {
        "category": "Slurry delivery clogging / flow meter drift",
        "standard_actions": [
            "Flush slurry delivery lines to clear partial blockages",
            "Calibrate slurry flow meter against reference standard",
            "Inspect mixing system for particle agglomeration",
            "Verify slurry temperature stability and expiry date",
        ],
    },
    # Implant step
    ("implant", "beam_current"): {
        "category": "Ion source degradation / beam instability",
        "standard_actions": [
            "Perform ion source maintenance (filament or indirectly-heated cathode inspection)",
            "Re-calibrate beam current measurement against Faraday cup reference",
            "Check beam scan uniformity with a dosimetry wafer",
            "Inspect acceleration column for contamination causing beam perturbation",
        ],
    },
}

# Fallback for unknown (step, parameter) pairs
_FALLBACK = {
    "category": "General process deviation",
    "standard_actions": [
        "Review SPC charts for the flagged parameter across recent lots",
        "Inspect the tool for mechanical or sensor anomalies",
        "Perform a tool qualification run before releasing additional lots",
        "Escalate to process engineering for root-cause investigation",
    ],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _lookup_domain(step: str, parameter: str) -> dict:
    """Return the domain lookup entry for (step, parameter), or fallback."""
    key = (step.lower(), parameter.lower())
    return DOMAIN_LOOKUP.get(key, _FALLBACK)


def _build_recommendation_prompt(
    cause: dict,
    domain: dict,
    lot_id: str,
) -> str:
    """Build the LLM prompt to phrase the recommendations naturally."""
    step = cause.get("step", "unknown")
    tool_id = cause.get("tool_id", "unknown")
    parameter = cause.get("parameter", "unknown")
    category = domain["category"]
    actions = domain["standard_actions"]
    actions_str = "\n".join(f"  - {a}" for a in actions)

    evidence = cause.get("evidence", "")
    sample_size = cause.get("sample_size", "unknown")

    return f"""You are a semiconductor fab yield engineering assistant.
A root-cause analysis for lot {lot_id} has identified the following leading candidate:

- Process step: {step}
- Tool: {tool_id}
- Parameter: {parameter}
- Root-cause category: {category}
- Evidence: {evidence}
- Sample size: {sample_size} lots

Standard corrective actions for this category:
{actions_str}

Task: Write a single, concise paragraph (3–5 sentences) addressed to a yield engineer.
- Use the tool ID ({tool_id}) specifically.
- Reference the root-cause category ({category}).
- Incorporate the top 2–3 standard actions naturally.
- Be direct and actionable — no preamble like "I recommend..." or "Based on the analysis...".
- Do NOT say "confirmed root cause" — say "leading candidate" or "most likely contributor".

Write only the recommendation paragraph."""


def _generate_fallback_recommendation(candidate_cause: dict, domain: dict, lot_id: str) -> str:
    """Generate deterministic domain recommendation when LLM quota is exhausted or unavailable."""
    step = candidate_cause.get("step", "unknown")
    param = candidate_cause.get("parameter", "unknown")
    tool_id = candidate_cause.get("tool_id", "unknown")
    category = domain.get("category", "Process Parameter Deviation")
    actions = domain.get("standard_actions", ["Review tool telemetry and requalify."])
    primary_action = actions[0] if actions else "Perform preventive maintenance and recipe requalification."
    return (
        f"The leading candidate cause for lot {lot_id} is {category} on {tool_id} "
        f"({step} step, parameter: {param}). "
        f"Recommended primary corrective action: {primary_action}. "
        f"{DOE_CAVEAT_STRING}"
    )


def _call_llm_for_recommendation(
    prompt: str,
    client: Any,
    candidate_cause: dict = None,
    domain: dict = None,
    lot_id: str = "UNKNOWN",
) -> str:
    """Dispatch LLM call with Groq failover and deterministic fallback."""
    provider = LLM_PROVIDER.lower()

    try:
        if provider == "gemini":
            from google.genai import types as genai_types
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=LLM_TEMPERATURE,
                    max_output_tokens=LLM_MAX_TOKENS,
                ),
            )
            return response.text.strip()

        elif provider == "groq":
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            return response.choices[0].message.content.strip()

        elif provider == "openai":
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            return response.choices[0].message.content.strip()

        elif provider == "anthropic":
            response = client.messages.create(
                model=LLM_MODEL,
                max_tokens=LLM_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()

        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'")

    except Exception as exc:
        # If primary is Gemini and failed (e.g. 429 quota exhausted), attempt Groq failover
        if provider != "groq" and GROQ_API_KEY:
            try:
                from groq import Groq
                groq_client = Groq(api_key=GROQ_API_KEY)
                res = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=LLM_TEMPERATURE,
                    max_tokens=LLM_MAX_TOKENS,
                )
                return res.choices[0].message.content.strip()
            except Exception:
                pass

        if candidate_cause is not None and domain is not None:
            return _generate_fallback_recommendation(candidate_cause, domain, lot_id)
        raise exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_recommendations(candidate_cause: dict, client: Any = None, lot_id: str = "UNKNOWN") -> dict:
    """
    Generate corrective action recommendations for a single candidate cause.

    Args:
        candidate_cause: A single cause dict from root_cause_findings["candidate_causes"].
        client:          Optional pre-built LLM client. If None, get_llm_client() is called.
        lot_id:          Lot ID for context in the LLM prompt.

    Returns:
        {
            "step": "etch",
            "tool_id": "ETCH-07",
            "parameter": "chamber_pressure",
            "category": "Pressure drift / chamber seal",
            "recommended_actions": ["...", "...", "..."],
            "phrased_recommendation": "Immediate PM inspection of ETCH-07 chamber seal..."
        }
    """
    if client is None:
        client = get_llm_client()

    step = candidate_cause.get("step", "unknown")
    parameter = candidate_cause.get("parameter", "unknown")
    tool_id = candidate_cause.get("tool_id", "unknown")

    domain = _lookup_domain(step, parameter)
    prompt = _build_recommendation_prompt(candidate_cause, domain, lot_id)
    phrased = _call_llm_for_recommendation(
        prompt, client, candidate_cause=candidate_cause, domain=domain, lot_id=lot_id
    )

    return {
        "step": step,
        "tool_id": tool_id,
        "parameter": parameter,
        "category": domain["category"],
        "recommended_actions": domain["standard_actions"],
        "phrased_recommendation": phrased,
    }
