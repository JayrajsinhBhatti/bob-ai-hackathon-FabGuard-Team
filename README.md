# 🚀 FabGuard: Semiconductor Yield Risk & Root-Cause Copilot with IBM Bob

FabGuard is an intelligent semiconductor fab operations copilot that connects an automated Statistical Process Control (SPC) and spatial defect clustering analytics core directly to **IBM Bob** via the **Model Context Protocol (MCP)**, powered by **IBM watsonx.ai Granite 3.0**.

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | FabGuard Team |
| **Track** | AI |
| **Team Lead** | Jayrajsinh Bhatti — jayrajsinhbhatti9687@gmail.com |
| **Members** | Jayrajsinh Bhatti, Yash Gohel |

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
git clone https://github.com/Yashgohel018/BOBathon-collab.git
cd BOBathon-collab

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
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo Status | [See demo/live-demo-url.txt](demo/live-demo-url.txt) (NOT DEPLOYED) |
| 📊 Screenshots | [See demo/screenshots/](demo/screenshots/) |

---

## 🏆 What We're Most Proud Of

Making IBM Bob an active, load-bearing participant via the Model Context Protocol (MCP). Rather than just a passive conversational agent, IBM Bob directly invokes our analytics tools over stdio to query fab sensor databases, classify spatial defect patterns, evaluate chamber drift, and formulate statistically rigorous explanations with strict Design of Experiments (DOE) caveats.

---

## ⚠️ Known Limitations

- Ingestion currently connects to a SQLite fab database schema rather than a live streaming SECS/GEM or OPC-UA fab bus.
- DBSCAN clustering parameters are calibrated for 300mm wafer coordinate geometries and would require retuning for 200mm wafers.
