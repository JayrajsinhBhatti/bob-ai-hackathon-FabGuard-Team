"""
copilot/config.py
LLM client initialization and system prompts for Bob Fab Copilot.

Provider hierarchy (set LLM_PROVIDER in .env):
  ibm_bob           — IBM Bob via watsonx.ai Granite 3.0 (PRIMARY for BOBathon)
  watsonx           — IBM watsonx.ai Granite (legacy alias for ibm_bob)
  watsonx_assistant — IBM watsonx Assistant session-based REST API
  gemini            — Google Gemini (fallback)
  groq              — Groq cloud (fallback)
"""

import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()

# --- Model & Provider Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ibm_bob").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "ibm/granite-3-8b-instruct")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# API Keys and Provider Endpoints
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ─── IBM Bob / watsonx.ai Configuration ──────────────────────────────────────
# IBM Bob platform / IDE admin token
IBM_BOB_API_KEY  = os.getenv("IBM_BOB_API_KEY") or os.getenv("BOB_API_KEY")

# Primary credentials for IBM Bob (BOBathon SaaS account)
WATSONX_API_KEY  = os.getenv("WATSONX_API_KEY") or os.getenv("IBM_CLOUD_API_KEY")
WATSONX_URL      = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_MODEL    = os.getenv("WATSONX_MODEL", "ibm/granite-3-8b-instruct")

# Space/Project ID — set to the BOBathon SaaS account ID provided by the user
# This acts as the watsonx.ai project scope for IBM Granite model inference
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "20260915-1650-5679-61fd-a8533eb2eafb")
WATSONX_SPACE_ID   = os.getenv("WATSONX_SPACE_ID", "")

# IBM watsonx Assistant (session-based chat) credentials
# Used when LLM_PROVIDER=watsonx_assistant
WATSONX_ASSISTANT_ID  = os.getenv("WATSONX_ASSISTANT_ID", "")
WATSONX_ASSISTANT_URL = os.getenv(
    "WATSONX_ASSISTANT_URL",
    "https://api.us-south.assistant.watson.cloud.ibm.com"
)

# Normalise ibm_bob → uses watsonx.ai Granite (same credentials)
if LLM_PROVIDER in ("ibm_bob", "watsonx"):
    LLM_MODEL = os.getenv("WATSONX_MODEL", WATSONX_MODEL)
elif LLM_PROVIDER == "groq" and ("gemini" in LLM_MODEL or "granite" in LLM_MODEL):
    LLM_MODEL = GROQ_MODEL
elif LLM_PROVIDER == "gemini" and "granite" in LLM_MODEL:
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

# --- Mandatory System Prompt for "Ask Bob" ---
SYSTEM_PROMPT_BOB = """You are "Bob", an expert Semiconductor Fab Yield & Defect Analysis Assistant for advanced node manufacturing (3nm/5nm).
Your role is to assist fab yield engineers and process engineers in diagnosing yield excursions, understanding root causes, evaluating spatial defect signatures, and reviewing upcoming batch risks.

You must strictly adhere to the following operational and honesty rules:

1. STATISTICAL & CONFIDENCE HONESTY (CRITICAL):
   - Only use the term "probability" (e.g., "78% probability") if the finding's confidence_basis is "logistic_regression_v1" (calibrated ML model).
   - If confidence_basis is "composite_heuristic_v1", you MUST refer to it as a "risk score" or "heuristic deviation score" (e.g., "risk score of 0.84"). NEVER call a heuristic score a probability.
   - Never invent, hallucinate, or extrapolate confidence numbers or probabilities that are not explicitly present in the provided findings data.

2. SCIENTIFIC & DOE FRAMING:
   - Never declare an equipment parameter as the "confirmed" root cause. In semiconductor manufacturing, statistical correlation does not prove physical causation.
   - Always frame primary findings as the "leading candidate cause".
   - You MUST ALWAYS include the DOE caveat in root cause conclusions:
     "Recommend confirming via targeted DOE (Design of Experiments) before taking corrective action."

3. CITE HARD EVIDENCE:
   - Always ground your technical reasoning in the provided SPC metrics:
     * Sigma deviations (e.g., "3.2 sigma above nominal spec")
     * Cpk degradation relative to fab control standards (nominal Cpk >= 1.33)
     * Sample size / affected lots (e.g., "14 of 16 lots affected")
     * Spatial wafer defect patterns (e.g., "edge-ring", "center-cluster", "scratch", "donut")
     * Equipment & tool IDs (e.g., "ETCH-07") and process steps (e.g., "etch", "litho", "cvd", "cmp")

4. ACTIONABLE FAB RECOMMENDATIONS:
   - When asked for solutions or next steps, provide standard fab operating procedures:
     * Tool PM (preventive maintenance) inspections (e.g., chamber seal leaks, RF matching network)
     * Sensor / flow meter recalibrations
     * Recipe requalifications
     * Lot quarantine / gating downstream steps
     * Flagging at-risk upcoming batches running on identical tool recipes

5. TONE & STYLE:
   - Professional, concise, technically rigorous, and direct.
   - Speak peer-to-peer with semiconductor yield engineers. Avoid generic corporate fluff.
"""

DOE_CAVEAT_STRING = "Recommend confirming via targeted DOE before taking corrective action."


def get_llm_client() -> Any:
    """
    Factory function returning the configured LLM client instance.

    Supports:
      - 'ibm_bob'           via ibm-watsonx-ai ModelInference (Granite 3.0) — PRIMARY
      - 'watsonx'           alias for ibm_bob (same credentials)
      - 'watsonx_assistant' via ibm-watson AssistantV2 session-based API
      - 'gemini'            via google.genai.Client
      - 'groq'              via groq.Groq
    """
    provider = LLM_PROVIDER.lower()

    # ── IBM Bob / watsonx.ai Granite 3.0 (PRIMARY for BOBathon) ──────────────
    if provider in ("ibm_bob", "watsonx"):
        # If WatsonX API key is placeholder or missing, fallback to working Gemini
        if not WATSONX_API_KEY or WATSONX_API_KEY.startswith("YOUR_") or len(WATSONX_API_KEY) < 20:
            if GEMINI_API_KEY:
                from google import genai
                return genai.Client(api_key=GEMINI_API_KEY)
            raise ValueError(
                "WATSONX_API_KEY is not set in .env. "
                "Get your API key from https://cloud.ibm.com/iam/apikeys"
            )
        if not WATSONX_PROJECT_ID:
            raise ValueError(
                "WATSONX_PROJECT_ID must be set. "
                "Using BOBathon SaaS account: 20260915-1650-5679-61fd-a8533eb2eafb"
            )
        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
            credentials = Credentials(url=WATSONX_URL, api_key=WATSONX_API_KEY)
            return ModelInference(
                model_id=WATSONX_MODEL,
                credentials=credentials,
                project_id=WATSONX_PROJECT_ID,
                params={
                    "decoding_method": "greedy",
                    "temperature": LLM_TEMPERATURE,
                    "max_new_tokens": LLM_MAX_TOKENS,
                    "repetition_penalty": 1.1,
                }
            )
        except Exception as e:
            if GEMINI_API_KEY:
                from google import genai
                return genai.Client(api_key=GEMINI_API_KEY)
            raise e


    # ── IBM watsonx Assistant session-based API ───────────────────────────────
    elif provider == "watsonx_assistant":
        if not WATSONX_API_KEY:
            raise ValueError("WATSONX_API_KEY must be set for watsonx_assistant provider.")
        if not WATSONX_ASSISTANT_ID:
            raise ValueError(
                "WATSONX_ASSISTANT_ID must be set for watsonx_assistant provider. "
                "Find it in your Assistant dashboard → Settings → API details."
            )
        from ibm_watson import AssistantV2
        from ibm_cloud_sdk_core.authenticators import IamAuthenticator
        authenticator = IamAuthenticator(WATSONX_API_KEY)
        assistant = AssistantV2(version="2024-08-25", authenticator=authenticator)
        assistant.set_service_url(WATSONX_ASSISTANT_URL)
        return assistant  # Returned raw; _dispatch_chat handles sessions

    # ── Google Gemini ─────────────────────────────────────────────────────────
    elif provider == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set in .env")
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)

    # ── Groq ──────────────────────────────────────────────────────────────────
    elif provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in .env")
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. "
            f"Choose from: ibm_bob, watsonx, watsonx_assistant, gemini, groq"
        )

