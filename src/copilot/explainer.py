"""
copilot/explainer.py  —  Step 3: Explanation Generator (§5.1)

Generates plain-English, evidence-grounded root-cause explanations for
a lot's findings JSON produced by the Analytics Core.

Honesty rules (mandated by §2, §5.1 of the Implementation Plan):
  • confidence_basis == "logistic_regression_v1"  → say "X% probability"
  • confidence_basis == "composite_heuristic_v1"  → say "risk score of X.XX"
  • Always append the DOE confirmation caveat.
  • Never invent a number not present in the findings data.

Supports Gemini (google-genai) and Groq provider clients.
"""

import json
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
    WATSONX_API_KEY,
    WATSONX_PROJECT_ID,
    WATSONX_URL,
    WATSONX_MODEL,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_confidence_phrase(cause: dict) -> str:
    """
    Return the correctly-phrased confidence string for a candidate cause,
    based on which field is non-null and what confidence_basis says.
    """
    basis = cause.get("confidence_basis", "")
    prob = cause.get("probability")
    risk = cause.get("risk_score")

    if basis == "logistic_regression_v1" and prob is not None:
        return f"a {int(round(prob * 100))}% probability (calibrated ML model, logistic regression)"
    elif basis == "composite_heuristic_v1" and risk is not None:
        return f"a heuristic deviation risk score of {risk:.2f} (composite heuristic score — use 'risk score' phrasing only)"
    elif prob is not None:
        # Fallback: model present but basis unknown — be conservative
        return f"a confidence estimate of {int(round(prob * 100))}%"
    elif risk is not None:
        return f"a risk score of {risk:.2f}"
    return "an unquantified confidence level"


def _build_explanation_prompt(cause: dict, rank: int, lot_id: str) -> str:
    """
    Build the LLM prompt for a single candidate cause explanation.
    All relevant SPC evidence is injected so the LLM cites real data.
    """
    confidence_phrase = _build_confidence_phrase(cause)
    step = cause.get("step", "unknown")
    tool_id = cause.get("tool_id", "unknown")
    parameter = cause.get("parameter", "unknown")
    spatial = cause.get("spatial_signature", "unknown")
    evidence = cause.get("evidence", "No evidence details provided.")
    sample_size = cause.get("sample_size", "unknown")

    return f"""You are a semiconductor fab yield engineering assistant.
Write a 2-3 sentence plain-English explanation of the following root-cause candidate for lot {lot_id}.
Rank: #{rank}

Facts (cite these exactly — do not invent or alter numbers):
- Process step: {step}
- Tool ID: {tool_id}
- Parameter: {parameter}
- Spatial wafer defect signature: {spatial}
- Confidence: {confidence_phrase}
- Evidence: {evidence}
- Sample size: {sample_size} affected lots

Rules:
1. Phrase confidence exactly as stated (use the confidence phrase verbatim if it contains a percentage or score).
2. Reference the spatial signature ({spatial}) to explain the wafer-level impact.
3. Do NOT say "confirmed root cause" — say "leading candidate".
4. Keep it under 80 words. Be direct and technical.

Write only the explanation paragraph (no headings, no bullet points)."""


def _generate_fallback_explanation(cause: dict, rank: int, lot_id: str) -> str:
    """Generate deterministic domain explanation when LLM quota is exhausted or unavailable."""
    if not cause:
        return f"Yield excursion identified on lot {lot_id}. {DOE_CAVEAT_STRING}"
    step = cause.get("step", "unknown")
    tool_id = cause.get("tool_id", "unknown")
    param = cause.get("parameter", "unknown")
    spatial = cause.get("spatial_signature", "unknown")
    evidence = cause.get("evidence", "Sensor telemetry deviations observed.")
    conf_phrase = _build_confidence_phrase(cause)
    return (
        f"The #{rank} leading candidate cause for lot {lot_id} is {param} on tool {tool_id} "
        f"during the {step} step, exhibiting {conf_phrase}. "
        f"Wafer defect maps correlate with a {spatial} spatial signature. "
        f"{evidence} {DOE_CAVEAT_STRING}"
    )


def _call_llm_for_explanation(
    prompt: str,
    client: Any,
    cause: dict = None,
    rank: int = 1,
    lot_id: str = "UNKNOWN",
) -> str:
    """
    Dispatch LLM call based on provider with automatic Groq failover and
    deterministic fallback when quotas are exhausted.
    """
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

        elif provider == "watsonx":
            if hasattr(client, "generate_text"):
                return client.generate_text(prompt=prompt).strip()
            elif hasattr(client, "generate"):
                res = client.generate(prompt=prompt)
                return res.get("results", [{}])[0].get("generated_text", "").strip()
            return str(client(prompt)).strip()

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
        # Fallover 1: Attempt watsonx if credentials present and was not primary
        if provider != "watsonx" and WATSONX_API_KEY and WATSONX_PROJECT_ID:
            try:
                from ibm_watsonx_ai import Credentials
                from ibm_watsonx_ai.foundation_models import ModelInference
                cred = Credentials(url=WATSONX_URL, api_key=WATSONX_API_KEY)
                wx_model = ModelInference(
                    model_id=WATSONX_MODEL,
                    credentials=cred,
                    project_id=WATSONX_PROJECT_ID,
                    params={"temperature": LLM_TEMPERATURE, "max_new_tokens": LLM_MAX_TOKENS}
                )
                return wx_model.generate_text(prompt=prompt).strip()
            except Exception:
                pass

        # Fallover 2: Attempt Groq if configured
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

        # Final resilient fallback: domain template conforming strictly to rules
        if cause is not None:
            return _generate_fallback_explanation(cause, rank, lot_id)
        raise exc


def _build_batch_summary(findings: dict) -> str:
    """Build a concise at-risk batch summary string from findings."""
    at_risk = findings.get("at_risk_upcoming_batches", [])
    if not at_risk:
        return "No upcoming batches currently flagged as at-risk."

    parts = []
    for batch in at_risk:
        lot = batch.get("lot_id", "unknown")
        sig = batch.get("matched_signature", "unknown")
        prob = batch.get("probability")
        risk = batch.get("risk_score")
        basis = batch.get("confidence_basis", "")

        if basis == "logistic_regression_v1" and prob is not None:
            score_str = f"{int(round(prob * 100))}% probability"
        elif prob is not None:
            score_str = f"{int(round(prob * 100))}% probability"
        elif risk is not None:
            score_str = f"risk score {risk:.2f}"
        else:
            score_str = "risk unquantified"

        parts.append(f"{lot} ({score_str}, matched signature: {sig})")

    return f"{len(at_risk)} upcoming lot(s) at risk: " + "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_lot_findings(findings: dict, client: Any = None) -> dict:
    """
    Generate plain-English explanations for each candidate cause in findings.

    Args:
        findings: The root_cause_findings dict (from analytics or fixture JSON).
        client:   Optional pre-built LLM client. If None, get_llm_client() is called.

    Returns:
        {
            "lot_id": "LOT-2231",
            "explanations": [
                {
                    "rank": 1,
                    "step": "etch",
                    "tool_id": "ETCH-07",
                    "parameter": "chamber_pressure",
                    "confidence_basis": "logistic_regression_v1",
                    "explanation": "...",
                    "doe_caveat": "Recommend confirming via targeted DOE..."
                },
                ...
            ],
            "at_risk_batch_summary": "2 upcoming lots at risk: ..."
        }
    """
    if client is None:
        client = get_llm_client()

    lot_id = findings.get("lot_id", "UNKNOWN")
    causes = findings.get("candidate_causes", [])

    explanations = []
    for rank, cause in enumerate(causes, start=1):
        prompt = _build_explanation_prompt(cause, rank, lot_id)
        explanation_text = _call_llm_for_explanation(
            prompt, client, cause=cause, rank=rank, lot_id=lot_id
        )

        explanations.append({
            "rank": rank,
            "step": cause.get("step"),
            "tool_id": cause.get("tool_id"),
            "parameter": cause.get("parameter"),
            "confidence_basis": cause.get("confidence_basis"),
            "explanation": explanation_text,
            "doe_caveat": DOE_CAVEAT_STRING,
        })

    return {
        "lot_id": lot_id,
        "explanations": explanations,
        "at_risk_batch_summary": _build_batch_summary(findings),
    }
