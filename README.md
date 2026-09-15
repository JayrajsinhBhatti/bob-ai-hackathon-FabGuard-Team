# 🚀 FabGuard: Semiconductor Yield Risk & Root-Cause Copilot with IBM Bob

FabGuard is an intelligent semiconductor fab operations copilot that connects an automated Statistical Process Control (SPC) and spatial defect clustering analytics core directly to **IBM Bob** via the **Model Context Protocol (MCP)**, powered by **IBM watsonx.ai Granite 3.0**.

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | FabGuard Team |
| **Track** | AI |
| **Team Lead** | Jayrajsinh Bhatti — 24ce014@charusat.edu.in |
| **Members** | Jayrajsinh Bhatti, Yash Gohel, Meet Ghori, Kavy Chauhan |

---

## 🎯 Problem Statement

Modern semiconductor fabs generate gigabytes of sensor telemetry per wafer, yet root-cause diagnosis of yield excursions across lithography, etch, and CMP remains a manual, multi-hour process. Process and yield engineers face alert fatigue and delayed mean-time-to-resolution (MTTR), risking millions of dollars in scrapped wafer lots during critical production runs.

---

## 💡 Solution

FabGuard bridges raw fab telemetry and fast engineering resolution by pairing automated statistical process control and spatial defect pattern classification with an active IBM Bob MCP Server and watsonx.ai Granite 3.0 foundation models. Yield engineers can converse directly with IBM Bob to diagnose excursions, identify suspect equipment with statistical rigor, and receive actionable standard operating procedures with strict Design of Experiments (DOE) caveats.

---

## ✨ Key Features

- **Automated SPC & DBSCAN Spatial Wafer Pattern Recognition**: Mathematically identifies edge-ring, center cluster, scratch, and donut signatures from defect coordinate maps.
- **Multi-Factor Statistical Root-Cause Attribution**: Pinpoints suspect equipment, chamber drift, $C_{pk}$ degradation, and sigma deviations without hallucinating correlation as physical causation.
- **Native IBM Bob MCP Server**: Enables IBM Bob to directly call `analyze_lot`, `get_root_cause_findings`, `predict_batch_risk`, and `ask_fab_copilot` over standard JSON-RPC.
- **IBM watsonx.ai Granite 3.0 Integration**: Enterprise-grade LLM reasoning with automated multi-tier failover (watsonx $\to$ Gemini $\to$ Groq $\to$ Deterministic Domain Engine).
- **Proactive In-Progress Batch Risk Assessment**: Uses normalized parameter vector similarity to detect early chamber drift and hold at-risk lots before physical yield loss occurs.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python, SQL |
| **Frameworks** | Model Context Protocol (MCP), ibm-watsonx-ai, scikit-learn, pytest |
| **IBM Technologies** | IBM Bob, watsonx.ai, IBM Granite 3.0, Model Context Protocol (MCP) |
| **Databases** | SQLite (`bob_fab.db`) |
| **Other** | DBSCAN, Groq, Google Gemini, GitHub Actions |

---

## 📁 Repository Structure

```
├── submission.yaml          # Structured submission metadata (validated by GitHub Actions)
├── README.md                # Human-readable project overview
├── CONTRIBUTING.md          # Hackathon submission guidelines
├── src/                     # All source code
│   ├── mcp_server.py        # Model Context Protocol server for IBM Bob
│   ├── analytics/           # SPC rules, DBSCAN clustering, ML root-cause ranker
│   ├── copilot/             # watsonx.ai Granite briefing & recommendation engine
│   ├── contracts/           # Shared JSON schema contracts
│   ├── data/                # Telemetry fixtures & synthetic lots
│   ├── bob_fab.db           # SQLite semiconductor fab telemetry database
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Template environment configuration
│   └── README.md            # Source code layout explanation
├── docs/                    # Technical documentation
│   ├── problem-statement.md # Detailed domain problem & quantified cost
│   ├── solution-overview.md # Conceptual design & differentiation
│   ├── architecture.md      # Mermaid diagram & component specifications
│   └── setup-guide.md       # Exact installation, execution & testing steps
├── demo/                    # Demonstration artifacts
│   ├── demo-video-link.txt  # Video walkthrough URL
│   ├── live-demo-url.txt    # Deployment status
│   └── screenshots/         # App and wafer defect pattern screenshots
└── presentation/            # Slide deck documentation
    └── README.md            # Presentation deck structure
```

---

## ⚡ How to Run

### 1. Clone and Install Dependencies
```bash
git clone https://github.com/JayrajsinhBhatti/bob-ai-hackathon-FabGuard-Team.git
cd bob-ai-hackathon-FabGuard-Team

# Install Python requirements
pip install -r src/requirements.txt
```

### 2. Configure Environment Variables
```bash
cp src/.env.example .env
# Edit .env with your WATSONX_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY
```

### 3. Run the IBM Bob MCP Server
```bash
python src/mcp_server.py
```

### 4. Interactive CLI Tool Verification
```bash
# Predict at-risk in-progress batches
python -X utf8 -c "from src.mcp_server import predict_batch_risk; print(predict_batch_risk())"

# Run complete lot diagnostics briefing
python -X utf8 -c "from src.mcp_server import analyze_lot; print(analyze_lot('LOT-2231'))"

# Query the Fab Copilot
python -X utf8 -c "from src.mcp_server import ask_fab_copilot; print(ask_fab_copilot('Why did lot LOT-2231 fail?', 'LOT-2231'))"
```

### 5. Run Automated Test Suite
```bash
pytest
```

---

## 🖥️ Demo

| Artifact | Link / Path |
|---|---|
| 📹 Demo Video | [▶️ Watch on YouTube](https://youtu.be/wzFjRJUOYY0) |
| 🌐 Live Demo | [🚀 fabguard-team.vercel.app](https://fabguard-team.vercel.app) |
| 📊 Screenshots | [See demo/screenshots/](demo/screenshots/) |

---

## 🏆 What We're Most Proud Of

Our system goes beyond being a conversational semiconductor analytics assistant. **IBM Bob acts as an agentic engineering copilot**, combining MCP-powered analytics, statistical experimentation, counterfactual simulation, evidence verification, and domain-specific RAG to turn raw fab data into **actionable, statistically grounded decisions**.

### 1. 🧪 Automated Statistical DOE Generator

When Bob identifies a candidate root cause, engineers can ask:

> `@bob design a DOE for ETCH-07`

Bob automatically generates a statistically structured **$2^k$ factorial Design of Experiments (DOE)**, including:

* **Factors & Levels** — nominal, low, and high operating conditions.
* **Randomized Run Sheet** — wafer IDs, recipe offsets, test order, and chamber stabilization requirements.
* **Hypothesis & Success Criteria** — explicitly defining $H_0$ and $H_1$ before experimentation.
* **Engineering Constraints** — preserves DOE assumptions and clearly distinguishes correlation from experimentally validated causation.

**Example:**

> **Factor:** Chamber Pressure
> **Nominal:** $12.0$ mTorr
> **Low:** $10.8$ mTorr ($-10%$)
> **High:** $13.2$ mTorr ($+10%$)
> **Success Criterion:** Defect density reduction $\geq 40%$

This transforms Bob from a **diagnostic assistant into an experiment-design assistant**.

---

### 2. 💰 Counterfactual Yield & Financial Recovery Simulator

Bob can estimate what would happen if a suspected process parameter were returned to its nominal operating point.

The simulator:

1. Takes the current out-of-spec parameter.
2. Uses the trained logistic-regression model to estimate the current probability of yield loss.
3. Counterfactually resets the parameter to its nominal value $\mu$ while holding other variables constant.
4. Calculates the expected yield improvement:

$$
\Delta \text{Yield}
=
P(\text{yield loss}\mid\text{current})
-
P(\text{yield loss}\mid\text{nominal})
$$

5. Converts the predicted recovery into an estimated financial impact using lot size, die count, and die value.

**Example output:**

> **Centering ETCH-07 pressure could recover an estimated +4.8% yield, representing approximately $27,000 in potential recovery for LOT-2235.**

This connects **statistical diagnosis → predicted yield → business impact** in a single workflow.

---

### 3. 🔬 Automated Cross-Lot Commonality & Exclusion Analysis

Instead of analyzing an excursion in isolation, Bob automatically searches historical production data for **cross-lot commonality**.

For a suspected tool or chamber, the system constructs a $2\times2$ contingency table:

|                    | Processed on Tool $T$ | Not on Tool $T$ |
| ------------------ | --------------------: | --------------: |
| **Defective Lots** |                   $a$ |             $b$ |
| **Nominal Lots**   |                   $c$ |             $d$ |

It then calculates:

* **Fisher's Exact Test**
* **Odds Ratio**
* **Hypergeometric probability**
* Statistical significance across historical lots

This allows Bob to answer questions such as:

> **“Is this defect disproportionately associated with ETCH-07 across production history?”**

Rather than relying only on the current lot, Bob uses **historical commonality evidence to strengthen or reject a suspected root cause**.

---

### 4. 🛡️ Dual-Pass Evidence Grounding Verifier

LLM-generated engineering reports should never be trusted simply because they sound convincing.

Our **Dual-Pass Evidence Grounding Verifier** acts as a guardrail between the LLM and the engineer.

Before a briefing is delivered, the verifier extracts critical claims such as:

* **Tool IDs** — `ETCH-07`, `CVD-03`, etc.
* **Sigma deviations** — `-3.2σ`, `+2.7 sigma`
* **Probabilities / risk scores** — `78%`, `Risk: 82%`
* Other contract-defined numerical findings

Each extracted claim is matched against the **underlying findings contract**.

If Bob produces a metric that does not exist in the verified evidence:

```text
LLM Draft
    ↓
Claim Extraction
    ↓
Evidence Contract Matching
    ↓
 ┌───────────────┐
 │ Supported?    │
 └───────┬───────┘
       Yes ↓ No
   Deliver    Reject
              ↓
       Deterministic
       Template / Regeneration
```

This creates a **fail-closed architecture** where unsupported numerical claims are blocked instead of being presented to engineers as facts.

---

### 5. 📚 RAG Equipment SOP & Historical Incident Retriever

Bob doesn't stop at identifying **what went wrong**. It can retrieve the relevant **engineering procedure and historical evidence** needed to respond.

A local fab knowledge base contains:

* Equipment SOPs
* Tool maintenance procedures
* Chamber troubleshooting guides
* Historical excursion post-mortems
* Equipment-specific corrective actions

When an anomaly such as:

```text
RF_POWER_DRIFT
CHAMBER_PRESSURE_SPIKE
```

is detected, the retriever searches the knowledge base using **BM25 / lightweight TF-IDF / sentence embeddings** and retrieves the most relevant procedure.

For example:

> **SOP-ETCH-402 — Throttle Valve Inspection & RF Impedance Matching Recalibration**

Bob can then ground its recommendation in the retrieved procedure instead of generating a generic troubleshooting response.

This creates a complete loop:

**Anomaly → Root Cause → Historical Evidence → SOP → Recommended Action**

---

### 🚀 Why These Features Matter

Together, these capabilities make IBM Bob more than an LLM interface:

```text
                    ┌──────────────────────┐
                    │      IBM Bob         │
                    │  Agentic Engineering  │
                    │       Copilot         │
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ↓                      ↓                      ↓
  🔬 Diagnose              📊 Experiment          📚 Retrieve
        │                      │                      │
 Cross-Lot Analysis       DOE Generator          SOP / Incidents
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ↓
                     💰 Counterfactual
                     Yield & Financial
                         Simulation
                               ↓
                       🛡️ Evidence
                       Verification
                               ↓
                    Actionable Engineering
                          Decision
```

The result is a system that can move from **“we detected an anomaly”** to **“here is the evidence, here is the experiment to validate it, here is the expected yield impact, and here is the documented procedure to act on it.”**


---

## ⚠️ Known Limitations

- Ingestion currently connects to a SQLite fab database schema rather than a live streaming SECS/GEM or OPC-UA fab bus.
- DBSCAN clustering parameters are calibrated for 300mm wafer coordinate geometries and would require retuning for 200mm wafers.
