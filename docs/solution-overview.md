# 💡 Solution Overview: FabGuard Semiconductor Operations Copilot

---

## 1. What We Built

**FabGuard** is an intelligent, domain-grounded semiconductor fabrication copilot designed to eliminate delayed root-cause analysis and reduce wafer scrap at leading-edge manufacturing nodes. 

Built directly for the **IBM Bob AI Innovation Hackathon**, FabGuard bridges raw fab telemetry and fast engineering resolution by pairing:
1. **Automated Statistical Process Control (SPC) & Spatial Clustering Core:** An automated mathematical engine that classifies spatial wafer defect morphologies (edge-ring, center cluster, scratch, donut) and computes $C_{pk}$ process capability degradation across equipment chambers.
2. **Native Model Context Protocol (MCP) Server for IBM Bob:** An open standard stdio integration that transforms IBM Bob into an active, tool-using fab copilot able to query SQLite fab databases, evaluate lot excursions, and predict batch risks.
3. **Enterprise GenAI Reasoning Powered by IBM watsonx.ai Granite 3.0:** Synthesizes multi-factor statistical evidence into structured, executive-ready engineering briefings with calibrated probabilities and targeted Design of Experiments (DOE) recommendations.
4. **Interactive 3D / 2D Wafer Visualization Dashboard:** A high-performance React + Vite web interface featuring Three.js 3D wafer inspection, real-time yield trend tracking, root-cause attribution bars, and an interactive "Ask Bob" conversational interface.

---

## 2. How It Works

FabGuard operates through a closed-loop diagnostic and predictive workflow:

```
[Fab Telemetry: MES / FDC / Defect Maps]
                   │
                   ▼
       [Automated Analytics Core]
   ┌────────────────────────────────┐
   │ • DBSCAN Spatial Clustering    │
   │ • Western Electric SPC Rules   │
   │ • Cpk Degradation Tracking     │
   │ • Vector Drift Fingerprinting  │
   └────────────────────────────────┘
                   │
                   ▼
      [Normalized Findings JSON]
                   │
                   ▼
  [Native IBM Bob MCP Server (stdio)]  ◄──►  [IBM Bob IDE / Chat]
                   │
                   ▼
    [IBM watsonx.ai Granite 3.0]
                   │
                   ▼
[Actionable Engineering Briefing & DOE Plan]
```

### Step-by-Step Diagnostic Journey

1. **Telemetry & Defect Ingestion:**
   - Raw inspection coordinates $(x, y)$, lot routing histories, and FDC sensor parameters (RF power, chamber pressure, gas flows, electrostatic chuck temperature) are ingested and structured into relational schema (`bob_fab.db`).
2. **Spatial Pattern Recognition (DBSCAN & Geometry Classification):**
   - The analytics engine isolates defect clusters using Density-Based Spatial Clustering of Applications with Noise (DBSCAN), computing radial and angular moments to accurately classify wafer-level signatures into:
     - **Edge-Ring:** Typical of chamber seal breakdown, focus ring wear, or edge-exclusion clamp degradation.
     - **Center-Cluster:** Typical of showerhead gas delivery clogging or center nozzle hot-spots.
     - **Scratch:** Characteristic of wafer handling end-effector mechanical scraping.
     - **Donut:** Signature of non-uniform plasma density distribution during reactive ion etch.
3. **Statistical Root-Cause Attribution & Calibrated Ranking:**
   - For every process step traversed by the lot, the engine evaluates Western Electric rules (points beyond $3\sigma$, consecutive runs beyond $2\sigma$) and historical chamber capability ($C_{pk}$).
   - Suspect chambers and recipe parameters are ranked by calibrated posterior probabilities, preventing coincidental correlation from masking true root causes.
4. **Active Tool Calling via IBM Bob MCP Server:**
   - When a process engineer asks IBM Bob *"Why did lot LOT-2231 experience an excursion?"*, IBM Bob autonomously invokes the registered `analyze_lot` or `get_root_cause_findings` MCP tools over standard JSON-RPC.
5. **GenAI Reasoning & Briefing Generation (watsonx.ai Granite 3.0):**
   - The MCP tool payload is fed into **IBM watsonx.ai Granite 3.0 8B Instruct**. Granite formats a structured diagnostic briefing including:
     - Root-Cause Summary with calibrated confidence.
     - Physical anomaly mechanism (e.g., RF bias generator drift causing plasma instability).
     - Recommended Immediate Containment (e.g., place Chamber B on engineering hold).
     - Standard Operating Procedure (SOP) with targeted Design of Experiments (DOE) confirmation steps.
6. **Proactive In-Progress Batch Risk Assessment:**
   - While in-line lots are still in progress, the engine fingerprints ongoing FDC telemetry vectors against known excursion profiles, flagging high-risk lots (`predict_batch_risk`) before physical defect inspection.

---

## 3. Architecture Diagram

> For complete data flows, sequence diagrams, and module interactions, refer to [`docs/architecture.md`](architecture.md).

```
┌────────────────────────────────────────────────────────────────────────┐
│                          USER TOUCHPOINTS                              │
│       IBM Bob CLI / IDE Chat (MCP)   │   FabGuard Web Dashboard (UI)   │
└───────────────────────┬───────────────────────────────┬────────────────┘
                        │ stdio (JSON-RPC)              │ REST API
┌───────────────────────▼───────────────────────────────▼────────────────┐
│                       FABGUARD MCP SERVER & BACKEND                    │
│    • analyze_lot          • get_root_cause_findings                    │
│    • predict_batch_risk   • ask_fab_copilot                            │
└───────────────────────┬────────────────────────────────────────────────┘
                        │
      ┌─────────────────┴─────────────────┐
      ▼                                   ▼
┌───────────────────────────┐       ┌────────────────────────────────────┐
│    GENAI REASONING CORE   │       │       ANALYTICS ENGINE             │
│ • IBM watsonx.ai Granite  │       │ • DBSCAN Spatial Wafer Classifier  │
│ • Multi-Tier LLM Failover │       │ • SPC Rules & Cpk Capability       │
│ • Deterministic Fallback  │       │ • Multi-Factor Root Cause Ranker   │
└───────────────────────────┘       │ • Parameter Drift Fingerprinting   │
                                    └─────────────────┬──────────────────┘
                                                      │
                                                      ▼
                                    ┌────────────────────────────────────┐
                                    │      FAB STORAGE: bob_fab.db       │
                                    │ Wafer Lots | Defect Maps | FDC Log │
                                    └────────────────────────────────────┘
```

---

## 4. Key Design Decisions

| Decision | Alternative Considered | Rationale |
|---|---|---|
| **Model Context Protocol (MCP) as Primary Interface** | Standalone custom REST API / webhook | MCP is open, standardized, and turns IBM Bob into a truly native, tool-calling participant capable of executing fab queries directly from the engineer's environment. |
| **Calibrated Statistical Probabilities** | Ad-hoc heuristic scoring (0–100) | In semiconductor fabs, arbitrary scores lose credibility with veteran process engineers. Calibrated Bayesian probabilities reflect real statistical confidence and sample size. |
| **Strict DOE Framing (Design of Experiments)** | Definitive "Confirmed Root Cause" assertions | Correlation never guarantees physical causality in complex multi-step fabs. Recommending targeted 2-level factorial DOEs conforms to rigorous SEMI fab operational protocols. |
| **Multi-Tier GenAI Resilience Layer** | Single-provider LLM API call | High-volume fabs cannot tolerate downtime. If watsonx.ai experiences network or quota limits, the copilot automatically falls back across Google Gemini, Groq, and finally an offline deterministic domain engine. |
| **Hybrid 3D + 2D Wafer Defect Visualization** | Pure static 2D scatter plots | Interactive 3D wafer maps (Three.js / React Three Fiber) allow engineers to rotate, zoom, and physically inspect multi-die defect clustering patterns alongside the chat copilot. |

---

## 5. IBM Technologies Used

FabGuard deeply integrates IBM technologies into its core architecture:

### 1. IBM Bob
- **Role:** The primary engineering interface.
- **Implementation:** Integrated via the **Model Context Protocol (MCP)** using Python `mcp` SDK over `stdio`. IBM Bob registers four specialized fab tools:
  - `analyze_lot(lot_id)`: Generates complete end-to-end yield and excursion diagnostics.
  - `get_root_cause_findings(lot_id)`: Returns structured JSON findings with suspect equipment rankings and spatial cluster metrics.
  - `predict_batch_risk()`: Scans in-progress lots and returns chamber drift risk scores.
  - `ask_fab_copilot(query, lot_id)`: Free-form conversational reasoning grounded in real fab telemetry.

### 2. IBM watsonx.ai
- **Role:** Enterprise-grade foundation model reasoning engine.
- **Implementation:** Uses the `ibm-watsonx-ai` SDK connecting to **IBM Granite 3.0 8B Instruct** (`ibm/granite-3-8b-instruct`). Granite processes normalized statistical telemetry vectors and formats actionable, domain-accurate engineering containment briefings.

### 3. IBM Granite 3.0
- **Role:** Domain-specific synthesis and engineering SOP recommendation.
- **Implementation:** Structured system prompting guarantees adherence to fab engineering standards, avoiding generic conversational filler and providing specific equipment, chamber, and DOE containment actions.
