"""
copilot/agent.py  —  Step 5: Conversational "Ask Bob" Agent (§5.3)

Implements a multi-turn conversational assistant ("Bob") over a lot's findings JSON.
Bob is a Fab Yield & Defect Analysis assistant with enforced honesty rules:
  - NEVER says "probability" for heuristic risk scores (composite_heuristic_v1)
  - ALWAYS cites evidence (sigma, Cpk, sample size, spatial signature)
  - ALWAYS appends DOE caveat in root-cause answers
  - NEVER claims a cause is "confirmed" — always "leading candidate"

The system prompt from config.py is injected into every session.

Source: §5.3 of S1_FINAL_Implementation_Plan_v3.md
"""

import json
from typing import Any

from .config import (
    get_llm_client,
    SYSTEM_PROMPT_BOB,
    LLM_PROVIDER,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
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

def _serialize_findings_context(findings: dict, lot_overview: dict = None) -> str:
    """
    Produce the structured context string that gets injected as Bob's
    initial knowledge about the lot. JSON-serialized with human-readable
    labels so the LLM can reliably reference specific fields.
    """
    context_parts = []

    lot_id = findings.get("lot_id", "UNKNOWN")
    context_parts.append(f"=== LOT FINDINGS CONTEXT: {lot_id} ===\n")

    if lot_overview:
        context_parts.append("LOT OVERVIEW:")
        context_parts.append(json.dumps(lot_overview, indent=2))
        context_parts.append("")

    causes = findings.get("candidate_causes", [])
    context_parts.append(f"CANDIDATE ROOT CAUSES ({len(causes)} total):")
    for i, cause in enumerate(causes, 1):
        basis = cause.get("confidence_basis", "unknown")
        prob = cause.get("probability")
        risk = cause.get("risk_score")

        if basis == "logistic_regression_v1" and prob is not None:
            confidence_str = f"probability={int(round(prob*100))}% (calibrated ML model — you may say 'X% probability')"
        elif basis == "composite_heuristic_v1" and risk is not None:
            confidence_str = f"risk_score={risk:.2f} (heuristic composite — say 'risk score of {risk:.2f}', NEVER say 'probability')"
        else:
            confidence_str = f"raw value: prob={prob}, risk={risk}, basis={basis}"

        context_parts.append(
            f"  Rank #{i}: step={cause.get('step')}, tool={cause.get('tool_id')}, "
            f"parameter={cause.get('parameter')}, spatial_signature={cause.get('spatial_signature')}, "
            f"{confidence_str}, sample_size={cause.get('sample_size')}, "
            f"evidence=\"{cause.get('evidence', '')}\""
        )

    at_risk = findings.get("at_risk_upcoming_batches", [])
    if at_risk:
        context_parts.append(f"\nAT-RISK UPCOMING BATCHES ({len(at_risk)} total):")
        for batch in at_risk:
            prob = batch.get("probability")
            risk = batch.get("risk_score")
            basis = batch.get("confidence_basis", "")
            if basis == "logistic_regression_v1" and prob is not None:
                score_str = f"{int(round(prob*100))}% probability"
            elif prob is not None:
                score_str = f"{int(round(prob*100))}% probability"
            elif risk is not None:
                score_str = f"risk score {risk:.2f}"
            else:
                score_str = "risk unquantified"
            context_parts.append(
                f"  {batch.get('lot_id')} — {score_str}, matched_signature={batch.get('matched_signature')}"
            )

    context_parts.append("\n=== END CONTEXT ===")
    return "\n".join(context_parts)


def _dispatch_chat(messages: list, client: Any) -> str:
    """
    Send the messages list to the configured LLM and return the response string.
    Handles the different API shapes for Gemini, Groq, OpenAI, Anthropic.
    """
    provider = LLM_PROVIDER.lower()

    try:
        if provider == "gemini":
            from google.genai import types as genai_types

            # Gemini uses a different message format — convert from OpenAI style
            # System prompt → first user turn with explicit instruction wrapper
            gemini_contents = []
            system_msg = None
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                elif msg["role"] == "user":
                    if system_msg and not gemini_contents:
                        # Prepend system to first user message for Gemini
                        gemini_contents.append(
                            genai_types.Content(
                                role="user",
                                parts=[genai_types.Part(text=f"[SYSTEM INSTRUCTIONS]\n{system_msg}\n\n[USER]\n{msg['content']}")]
                            )
                        )
                        system_msg = None
                    else:
                        gemini_contents.append(
                            genai_types.Content(
                                role="user",
                                parts=[genai_types.Part(text=msg["content"])]
                            )
                        )
                elif msg["role"] == "assistant":
                    gemini_contents.append(
                        genai_types.Content(
                            role="model",
                            parts=[genai_types.Part(text=msg["content"])]
                        )
                    )

            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=gemini_contents,
                config=genai_types.GenerateContentConfig(
                    temperature=LLM_TEMPERATURE,
                    max_output_tokens=LLM_MAX_TOKENS,
                ),
            )
            return response.text.strip()

        elif provider == "watsonx":
            # Format messages for watsonx Granite instruction format
            formatted_prompt = ""
            for msg in messages:
                formatted_prompt += f"\n[{msg['role'].upper()}]:\n{msg['content']}\n"
            formatted_prompt += "\n[ASSISTANT]:\n"
            if hasattr(client, "generate_text"):
                return client.generate_text(prompt=formatted_prompt).strip()
            elif hasattr(client, "generate"):
                res = client.generate(prompt=formatted_prompt)
                return res.get("results", [{}])[0].get("generated_text", "").strip()
            return str(client(formatted_prompt)).strip()

        elif provider in ("groq", "openai"):
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            return response.choices[0].message.content.strip()

        elif provider == "anthropic":
            # Anthropic separates system from messages
            system_content = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                else:
                    chat_messages.append(msg)

            response = client.messages.create(
                model=LLM_MODEL,
                max_tokens=LLM_MAX_TOKENS,
                system=system_content,
                messages=chat_messages,
            )
            return response.content[0].text.strip()

        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'")

    except Exception as exc:
        # Fallover 1: Attempt watsonx if configured and was not primary
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
                formatted_prompt = ""
                for msg in messages:
                    formatted_prompt += f"\n[{msg['role'].upper()}]:\n{msg['content']}\n"
                formatted_prompt += "\n[ASSISTANT]:\n"
                return wx_model.generate_text(prompt=formatted_prompt).strip()
            except Exception:
                pass

        # Fallover 2: Attempt Groq if configured
        if provider != "groq" and GROQ_API_KEY:
            try:
                from groq import Groq
                groq_client = Groq(api_key=GROQ_API_KEY)
                res = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    temperature=LLM_TEMPERATURE,
                    max_tokens=LLM_MAX_TOKENS,
                )
                return res.choices[0].message.content.strip()
            except Exception:
                pass
        raise exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_bob_session(findings: dict = None, lot_overview: dict = None) -> list:
    """
    Initialize a new conversation session with Bob.

    Injects the lot's findings JSON as structured context into the system message,
    and returns the initial messages list for use with ask_bob().

    Args:
        findings:     Optional root_cause_findings dict for the lot.
        lot_overview: Optional additional lot metadata (yield %, dates, etc.).

    Returns:
        messages list (OpenAI-style) with one system role message containing
        the Bob persona + operational rules + lot context.
    """
    if findings:
        findings_context = _serialize_findings_context(findings, lot_overview)
        system_content = (
            SYSTEM_PROMPT_BOB
            + "\n\n"
            + "You have been provided the following lot analysis findings. "
            + "Answer all questions strictly based on this data — do not invent metrics.\n\n"
            + findings_context
        )
    else:
        system_content = SYSTEM_PROMPT_BOB

    return [{"role": "system", "content": system_content}]


def ask_bob(messages: list, user_question: str, client: Any = None) -> tuple[str, list]:
    """
    Send a user question to Bob and get a response, maintaining conversation history.

    Args:
        messages:      Current conversation messages list (from create_bob_session or prior ask_bob).
        user_question: The engineer's natural-language question.
        client:        Optional pre-built LLM client. If None, get_llm_client() is called.

    Returns:
        Tuple of (answer_string, updated_messages_list).
        The returned messages list can be passed back to the next ask_bob() call for multi-turn.
    """
    if client is None:
        client = get_llm_client()

    # Append user's question
    updated_messages = messages + [{"role": "user", "content": user_question}]

    answer = _dispatch_chat(updated_messages, client)

    # Append Bob's answer to keep history
    updated_messages = updated_messages + [{"role": "assistant", "content": answer}]

    return answer, updated_messages


def ask_bob_single(user_question: str, findings: dict = None, client: Any = None) -> str:
    """
    One-shot convenience wrapper — creates a fresh session and asks one question.

    Supports calling as ask_bob_single(user_question, findings) or
    ask_bob_single(findings, user_question) for maximum ergonomics.

    Args:
        user_question: The engineer's question (or findings dict if swapped).
        findings:      The root_cause_findings dict for the lot (or question if swapped).
        client:        Optional pre-built LLM client.

    Returns:
        Bob's answer as a string.
    """
    # Allow arguments to be passed in either order
    if isinstance(user_question, dict) and isinstance(findings, str):
        user_question, findings = findings, user_question

    if client is None:
        client = get_llm_client()

    messages = create_bob_session(findings)
    answer, _ = ask_bob(messages, user_question, client)
    return answer
