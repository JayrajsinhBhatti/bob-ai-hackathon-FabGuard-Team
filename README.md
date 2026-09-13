# Bob Fab Copilot
## S1: Wafer Yield Root Cause & Defect Pattern Analyser
### IBM BoB AI Innovation Hackathon 2026 — 4-Person Team

[![Team Collaboration Repo](https://img.shields.io/badge/GitHub-BOBathon--collab-blue)](https://github.com/Yashgohel018/BOBathon-collab)
[![Submission Repo](https://img.shields.io/badge/GitHub-BOBathon--S1--submission-green)](https://github.com/Yashgohel018/BOBathon-S1-submission)

---

## 1. Overview
In semiconductor manufacturing (3nm/5nm fab operations), a 1% yield drop costs tens of millions of dollars per month. **Bob Fab Copilot** rapidly isolates root causes across multi-step physical and chemical processes using real semiconductor statistical process control (SPC), spatial defect signature classification, calibrated machine learning probabilities, and an intelligent GenAI conversational copilot.

## 2. Core Capabilities
1. **Defect Pattern & SPC Violation Detection**: Continuous monitoring of FDC sensor telemetry against Western Electric rules & Cpk < 1.33, coupled with spatial wafer defect signature extraction (*edge-ring*, *center-cluster*, *scratch*, *donut*, *random*).
2. **Calibrated Root Cause Probability Ranking**: Ranks candidate equipment parameters by true calibrated probability $P(\text{root cause})$ with confidence intervals, sample sizes, and DOE-confirmation caveats.
3. **Automated Corrective Actions**: Context-aware recommendations (PM check, requalification, quarantine).
4. **Predictive Batch Risk**: Identifies upcoming in-progress wafer lots exhibiting early sensor drift matching known failure fingerprints.
5. **Ground-Truth Validation Gate**: An integrated validation harness measuring Top-1 & Top-3 accuracy against known injected fab failure scenarios.

## 3. Architecture & Repository Structure
```
BOBathon/
├── /contracts        # Shared schemas, DDL, and mock fixtures (Hour 0 freeze)
├── /data             # Person A: Synthetic FDC/MES generator & ground-truth injection
├── /analytics        # Person B: SPC engine, spatial classifier, ML ranker, validation harness
├── /copilot          # Person C: GenAI explanation, recommendation engine, conversational Bob
├── /backend          # Person D: FastAPI endpoints (/lots, /defects, /rootcause, /validate, /chat)
├── /frontend         # Person D: Dashboard (yield trends, wafer heatmaps, validation panel)
└── /docs             # Implementation plans, SEMI standards notes, and demo scripts
```

## 4. Team Roles
- **Person A (Data Engineering & Contracts)**: Synthetic dataset generator, FDC/MES simulation, 5 injected ground-truth fault scenarios, SQLite database seeding.
- **Person B (Analytics Core)**: SPC Western Electric engine, wafer spatial signature classifier, Tier 2 calibrated logistic regression ranker, validation harness.
- **Person C (GenAI Copilot)**: Explanation generator, DOE-caveat phrasing, recommendation generator, conversational tool-calling agent.
- **Person D (Fullstack Integration)**: FastAPI backend, modern responsive frontend dashboard, live validation panel, demo flow.
