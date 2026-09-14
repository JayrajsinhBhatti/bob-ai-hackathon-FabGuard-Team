# 🏗️ Technical Architecture: FabGuard System Design

This document details the end-to-end technical architecture, component responsibilities, data flow, and integration pathways for **FabGuard**.

---

## 1. System Architecture Diagram

```mermaid
flowchart TD
    subgraph USER_LAYER["User Interaction Layer"]
        A["Fab Yield / Process Engineer"]
        B["IBM Bob IDE & CLI Chat"]
    end

    subgraph MCP_LAYER["Model Context Protocol (MCP) Server"]
        C["stdio Transport Listener"]
        D["MCP Tool Registry<br/>• analyze_lot<br/>• get_root_cause_findings<br/>• predict_batch_risk<br/>• ask_fab_copilot"]
    end

    subgraph COPILOT_LAYER["GenAI Reasoning & Copilot Core"]
        E["Copilot Pipeline Orchestrator"]
        F["Statistical Explainer"]
        G["Action Recommender"]
        H["Conversational Agent & Guardrails"]
    end

    subgraph LLM_PROVIDERS["Foundation Model Providers"]
        I["IBM watsonx.ai<br/>(Granite 3.0 8B Instruct)"]
        J["Google Gemini 2.5 Flash"]
        K["Groq (Qwen 3.8 / LLaMA 3.3)"]
        L["Deterministic Domain Engine (Fallback)"]
    end

    subgraph ANALYTICS_LAYER["Analytics Core (Person B)"]
        M["SPC Rules Engine<br/>(Western Electric / Nelson)"]
        N["Spatial Defect Classifier<br/>(DBSCAN Wafer Clustering)"]
        O["Root Cause Ranker<br/>(Cpk & Multi-Factor Likelihood)"]
        P["Batch Risk Predictor<br/>(Vector Drift Fingerprinting)"]
    end

    subgraph DATA_LAYER["Fab Storage Layer"]
        Q[("bob_fab.db (SQLite)")]
        R["Sensor Telemetry<br/>(RF Power, Pressure, Temp, Flow)"]
        S["Wafer Defect Coordinate Maps"]
        T["Historical Yield & Ground Truth"]
    end

    %% Connections
    A -->|Natural Language Prompt| B
    B -->|stdio JSON-RPC Protocol| C
    C --> D
    D --> E
    D --> P
    E --> F
    E --> G
    E --> H

    F -->|Provider Call / Failover| I
    F -.->|Failover 1| J
    F -.->|Failover 2| K
    F -.->|Fallback| L

    H -->|Chat Stream| I
    H -.->|Failover| J
    H -.->|Failover| K

    E <-->|Findings Contract JSON| M
    E <-->|Findings Contract JSON| N
    E <-->|Findings Contract JSON| O
    P <-->|Active Batch Telemetry| Q

    M <--> Q
    N <--> Q
    O <--> Q
    Q --- R
    Q --- S
    Q --- T

    D -->|Markdown Briefing / JSON| C
    C -->|JSON-RPC Response| B
    B -->|Rendered Briefing| A
```

---

## 2. Component Responsibility Matrix

| Component | Technology | Primary Responsibility |
|---|---|---|
| **IBM Bob Interface** | IBM Bob IDE / Bob Shell | Provides native developer/engineer conversational workspace. Emits MCP JSON-RPC tool calls. |
| **MCP Server** | Python `mcp` SDK (2.x/1.x) | Exposes standard MCP tools over `stdio`, handling parameter deserialization and structured markdown output formatting. Strictly writes logs to `stderr`. |
| **Copilot Orchestrator** | Python (`copilot/pipeline.py`) | Coordinates calls between the analytics engine, explainer, recommender, and agent session state. |
| **Statistical Explainer** | Python (`copilot/explainer.py`) | Transforms quantitative deviations ($Z$-scores, Cpk drops, spatial clusters) into peer-to-peer technical briefings. |
| **Action Recommender** | Python (`copilot/recommender.py`) | Maps (step, parameter) findings to established fab standard operating procedures (tool PM, recipe requalification, sensor recalibration). |
| **Conversational Agent** | Python (`copilot/agent.py`) | Maintains multi-turn conversation context; enforces operational honesty rules and the mandatory DOE caveat. |
| **watsonx.ai Granite** | `ibm-watsonx-ai` SDK | Primary enterprise foundation model (`ibm/granite-3-8b-instruct`) providing high-precision semiconductor technical reasoning. |
| **Analytics Core** | NumPy, SciPy, Scikit-learn | Executes Western Electric SPC rules, DBSCAN spatial clustering on wafer defect coordinates, and multi-factor Bayesian attribution. |
| **Data Repository** | SQLite3 (`bob_fab.db`) | Relational fab database containing lots, equipment, steps, sensor logs, wafer inspection coordinates, and ground truth labels. |

---

## 3. End-to-End Data Flow

1. **Tool Invocation**:
   When a user in IBM Bob types `@bob analyze LOT-2231`, Bob inspects its MCP server registry and dispatches a JSON-RPC `tools/call` message for `analyze_lot` with arguments `{"lot_id": "LOT-2231"}` to `src/mcp_server.py`.
2. **Analytics Ingestion & Feature Extraction**:
   - `analytics.pipeline.analyze_lot` queries `bob_fab.db` for all process steps, sensor measurements, and defect coordinates associated with `LOT-2231`.
   - `analytics.spc` checks parameters against control limits ($UCL$, $LCL$) and historical sigma baselines.
   - `analytics.spatial` clusters inspection coordinates using DBSCAN to identify geometric defect signatures (e.g. edge-ring, center-cluster).
   - `analytics.root_cause` calculates capability index degradation ($\Delta C_{pk}$) and p-values to score candidate causes.
3. **LLM Synthesis & Guardrail Enforcement**:
   - The analytics findings are serialized into structured JSON conforming to the contract schema.
   - `copilot.explainer` prompts `ibm-watsonx-ai` Granite 3.0 to formulate a technical explanation adhering strictly to statistical confidence rules (only calibrated models report "probability").
   - `copilot.recommender` injects hard-coded domain SOP actions.
   - The mandatory DOE caveat is automatically appended: *"Recommend confirming via targeted DOE before taking corrective action."*
4. **Response Delivery**:
   The briefing is formatted into rich GitHub-flavored markdown and returned over `stdio` to IBM Bob, which displays the interactive report directly in the chat panel.

---

## 4. Security, Resilience & Scalability Notes

- **Credential Hygiene**: API keys (`WATSONX_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`) are managed strictly via environment variables (`.env`) which are excluded in `.gitignore`.
- **Fault-Tolerant Provider Failover**: If watsonx or Gemini encounters rate limiting (HTTP 429), the system automatically falls back to Groq or deterministic domain templates without halting fab operations.
- **STDIO Purity**: All MCP server debug messages and runtime traces write strictly to `sys.stderr`, preventing corruption of standard JSON-RPC data streams.
- **Stateless MCP Execution**: Tools are designed to be idempotent and thread-safe, allowing horizontal scaling across multiple tool-calling instances.
