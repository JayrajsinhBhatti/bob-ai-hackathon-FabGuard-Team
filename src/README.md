# 📦 FabGuard Source Code (`src/`)

This directory contains the complete source code implementation for **FabGuard: Semiconductor Yield Risk & Root-Cause Copilot with IBM Bob**.

---

## 📁 Directory Layout

```
src/
├── mcp_server.py           # Model Context Protocol (MCP) server for IBM Bob (stdio transport)
├── requirements.txt        # Python dependency manifest
├── .env.example            # Environment configuration template
│
├── analytics/              # Statistical Process Control & ML Pattern Engine
│   ├── spc.py              # Western Electric rules & Cpk process capability calculations
│   ├── spatial.py          # DBSCAN spatial wafer defect clustering & morphology classifier
│   ├── root_cause.py       # Multi-factor calibrated probability root-cause ranking engine
│   ├── batch_risk.py       # Parameter vector drift fingerprinting for in-progress lots
│   ├── pipeline.py         # Unified analytics pipeline generating normalized Findings JSON
│   ├── data_access.py      # SQLite data access layer for fab telemetry
│   ├── models.py           # Typed dataclasses and schemas for findings and metrics
│   └── validate.py         # Statistical validation gate against injected ground truth
│
├── copilot/                # watsonx.ai GenAI Reasoning & Recommendation Engine
│   ├── config.py           # LLM configuration (watsonx.ai, Gemini, Groq, deterministic fallback)
│   ├── explainer.py        # Statistical explanation synthesizer using IBM Granite 3.0
│   ├── recommender.py      # SOP & Design of Experiments (DOE) action generator
│   ├── pipeline.py         # Integrated Copilot pipeline (Analytics → LLM Reasoning → Briefing)
│   └── agent.py            # Conversational fab copilot agent with multi-turn context
│
├── contracts/              # Shared JSON schemas and interface contracts
│   ├── findings_schema.json # JSON Schema for normalized analytics findings
│   ├── schema.sql          # Fab relational database schema (lots, process steps, defects)
│   └── schema.md           # Schema documentation & entity-relationship reference
│
├── data/                   # Data generation, database seeding, and ground-truth validation
│   ├── db.py               # Database connection manager and schema initialization
│   ├── seed.py             # Synthetic fab dataset seeding pipeline
│   ├── lot_generator.py    # Wafer lot synthesizer across 500+ fab steps
│   ├── spatial_patterns.py # Synthetic wafer defect coordinate generator (edge, center, scratch, donut)
│   ├── ground_truth.py     # Ground truth excursion injection and verification labels
│   └── exports/            # Exported reference datasets (CSV / JSON)
│
└── tests/                  # Automated test suite
    ├── test_mcp_server.py  # End-to-end testing of IBM Bob MCP tools
    └── test_submission_template.py # Submission compliance test matching GitHub Actions validator
```

---

## 🚀 Key Entry Points

1. **IBM Bob MCP Server:**
   ```bash
   python src/mcp_server.py
   ```
   Runs the stdio Model Context Protocol server exposing `analyze_lot`, `get_root_cause_findings`, `predict_batch_risk`, and `ask_fab_copilot`.

2. **Unified Pipeline Execution (CLI):**
   ```bash
   python -X utf8 -c "from src.analytics.pipeline import run_pipeline; print(run_pipeline('LOT-2231'))"
   ```

3. **Copilot Briefing Generation:**
   ```bash
   python -X utf8 -c "from src.copilot.pipeline import run_copilot; print(run_copilot('LOT-2231'))"
   ```
