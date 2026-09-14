# GenAI Copilot Layer — Person C: Complete Description

> **Branch:** `feature/copilot`  
> **Package:** `/copilot`  
> **Role in Team:** GenAI Copilot (Person C)  
> **Analytics Integration:** ✅ Merged with Person B's `feature/analytics-integrated`  
> **Unit Test Status:** ✅ 22/22 unit tests passing (100% offline with mocks)  
> **Analytics Test Status:** ✅ 27/27 analytics tests passing  
> **Live Scenario Status:** ✅ All 6 live scenarios verified and passing (Gemini & Groq)  

---

## What This Module Does — High-Level Summary

The `/copilot` package is the **GenAI intelligence layer** of the Bob Fab Copilot system. It sits downstream of the Analytics Core (Person B) and turns raw root-cause findings JSON into three core capabilities:

1. **Plain-English Explanations** — Evidence-grounded, tier-aware explanations of each candidate root cause.
2. **Corrective Action Recommendations** — Domain-grounded, tool-specific recommended actions for fab engineers.
3. **Conversational "Ask Bob"** — A multi-turn natural language assistant that answers fab engineer questions about specific lots, enforces statistical honesty, and grounds reasoning in SPC metrics and physical tool physics.

---

## File-by-File Architecture

### 1. `copilot/config.py` — LLM Client & System Prompts
- Loads API keys and model settings from `.env` using `python-dotenv`.
- Supports multi-provider configuration: Google Gemini (`gemini-2.5-flash`), Groq (`qwen/qwen3.8-27b`), OpenAI, Anthropic.
- Includes dynamic model selection and automatic fallback configuration (`GROQ_MODEL`, `GROQ_API_KEY`).
- Defines `SYSTEM_PROMPT_BOB`:
  * Enforces statistical honesty (Tier 1 heuristic vs. Tier 2 calibrated ML probability).
  * Scientific framing: Correlation ≠ Causation, leading candidates only.
  * Mandatory DOE confirmation caveat string.
  * Hard evidence citation: Sigma deviations, Cpk degradation (nominal $\ge 1.33$), sample size, spatial defect signatures, equipment IDs.
  * Professional peer-to-peer fab engineer tone.

### 2. `copilot/explainer.py` — Root Cause Explanation Generator
- Implements `explain_lot_findings(findings, client=None)`.
- Enforces the **Tier 1 vs Tier 2 phrasing rule**:
  * `basis == "logistic_regression_v1"` $\rightarrow$ `"X% probability"`
  * `basis == "composite_heuristic_v1"` $\rightarrow$ `"heuristic deviation risk score of X.XX (risk score only)"`
- Resilient dispatch: If Gemini rate limits (429 free tier quota) occur, automatically fails over to Groq, or falls back to a deterministic rule-based explanation without failing.
- Appends `doe_caveat` to every explanation.
- Summarizes upcoming at-risk batches.

### 3. `copilot/recommender.py` — Corrective Action Recommender
- Implements `generate_recommendations(candidate_cause, client=None, lot_id="UNKNOWN")`.
- Contains `DOMAIN_LOOKUP`: Hard-coded expert fab engineering domain knowledge table mapping `(step, parameter)` to `category` and actionable SOP steps (`standard_actions`).
- Combines domain-expert actions with natural language LLM phrasing.
- Resilient dispatch with automatic Groq failover and deterministic fallback.

### 4. `copilot/agent.py` — Conversational "Ask Bob"
- Implements `create_bob_session(findings, lot_overview=None)`, `ask_bob(messages, user_question, client=None)`, and `ask_bob_single(question, findings, client=None)`.
- Formats complete lot findings into structured context for the system prompt.
- Maintains multi-turn conversation history.
- Handles provider message conversions (e.g. Gemini Content format vs OpenAI/Groq messages format).

### 5. `copilot/pipeline.py` — Full Integration Pipeline Entry Point
- Wires Person B's Analytics Core directly to the Copilot layer.
- `full_copilot_analysis(lot_id, db_path=None)`: Calls `analytics.pipeline.analyze_lot(lot_id)` and generates explanations + recommendations end-to-end.
- `full_copilot_analysis_from_findings(findings)`: Contract-based execution against pre-computed findings or fixtures.
- `copilot_chat(user_question, findings, conversation_history, client)`: Helper function for Person D's FastAPI `/chat` endpoint.

### 6. `copilot/tests/test_copilot.py` — Unit Test Suite
- 22 comprehensive unit tests verifying:
  * Tier 2 probability phrasing.
  * Tier 1 risk score phrasing (and strict ban on probability percentage phrasing).
  * DOE caveat presence.
  * Recommender domain lookup completeness (at least 2 actionable steps per parameter).
  * Session creation, system message formatting, and history tracking.
  * Honest output validation.

### 7. `copilot/tests/test_live_scenarios.py` — End-to-End Live Verification
- Executes 6 end-to-end scenarios with live API credentials:
  * Scenario 1: `LOT-2231` (Etch chamber pressure excursion with edge-ring signature).
  * Scenario 2: `LOT-2232` (CMP pad downforce with scratch signature).
  * Scenario 3: `LOT-2233` (CVD deposition temperature with center-cluster signature).
  * Scenario 4: `LOT-2240` (Real low-yield lot from SQLite database `bob_fab.db`).
  * Scenario 5: Multi-turn Ask Bob conversation (diagnoses cause, rejects premature confirmation, demands DOE, provides immediate containment & quarantine steps).
  * Scenario 6: Live Groq provider execution (`qwen/qwen3.8-27b`).

---

## Traceability to Project Specifications

| Requirement | Implementation | Status |
|---|---|---|
| Step 0: Git branch setup | `feature/copilot` branched from `dev`, merged with Person B | ✅ Complete |
| Step 1: LLM Config & System Prompt | `copilot/config.py` with `SYSTEM_PROMPT_BOB` | ✅ Complete |
| Step 2: Test Fixtures & Contract | Mock fixtures, contract schemas, SQLite `bob_fab.db` | ✅ Complete |
| Step 3: Explanation Generator | `copilot/explainer.py` with Tier 1/Tier 2 phrasing | ✅ Complete |
| Step 4: Corrective Actions | `copilot/recommender.py` with 11 domain lookup pairs | ✅ Complete |
| Step 5: "Ask Bob" Agent | `copilot/agent.py` multi-turn assistant | ✅ Complete |
| Step 6: Unit Test Suite | `copilot/tests/test_copilot.py` (22/22 pass) | ✅ Complete |
| Step 7: End-to-End Pipeline | `copilot/pipeline.py` connected to `analytics.pipeline` | ✅ Complete |
| Live Verification | `copilot/tests/test_live_scenarios.py` (6/6 pass) | ✅ Complete |
