"""
copilot/config.py
LLM client initialization and system prompts for Bob Fab Copilot.
Supports Google Gemini, Groq, OpenAI, and Anthropic.
"""

import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()

# --- Model & Provider Configuration ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

# If provider is groq and model still points to gemini default, switch to groq default
if LLM_PROVIDER == "groq" and ("gemini" in LLM_MODEL or not LLM_MODEL):
    LLM_MODEL = GROQ_MODEL

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

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
      - 'gemini' via google.genai.Client
      - 'groq' via groq.Groq
    """
    provider = LLM_PROVIDER.lower()

    if provider == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set in .env")
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)

    elif provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in .env")
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Choose from: gemini, groq, openai, anthropic")
