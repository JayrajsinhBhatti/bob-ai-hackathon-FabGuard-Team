# Bob Fab Copilot — FINAL Implementation Plan (v3)
## S1: Wafer Yield Root Cause & Defect Pattern Analyser
### IBM BoB AI Innovation Hackathon 2026 — 4-Person Team

> This is the version the team builds against. Changes from v2: root cause scoring is now a
> real calibrated probability (not an ad-hoc composite score), and a mandatory validation gate
> against injected ground-truth causes has been added at Checkpoint 2 (§10, §11).

---

## 1. Requirement Traceability

| # | Requirement (from problem statement) | Where it's built | Status |
|---|---|---|---|
| 1 | Analyse wafer lot data and defect reports to **identify patterns** | Analytics Core → Pattern Engine (§4.2) | Fully specified |
| 2 | **Rank root causes by probability** | Analytics Core → Root Cause Ranker (§4.3), now with a real calibrated probability model | Fully specified + validated (§11) |
| 3 | **Recommend corrective actions** | Copilot Layer → Recommendation Generator (§5.2) | Fully specified |
| 4 | **Flag upcoming batches** at risk | Analytics Core → Batch Risk Predictor (§4.4) | Fully specified |

---

## 2. Grounding in Real Fab Methodology

- **SPC (Statistical Process Control):** flag out-of-control parameters using Cpk < 1.33 or
  Western Electric rules (point beyond 3σ, 2-of-3 beyond 2σ), not arbitrary thresholds.
- **Spatial signature classification:** classify each wafer's defect map into
  edge-ring / center-cluster / scratch (linear) / random / donut — signature shape points to
  different root-cause families (e.g., edge-ring → chamber seal/edge exclusion issue).
- **Confounding awareness:** use conditional correlation narrowed by `detected_at_step`, and
  always report confidence + sample size alongside any score — never a bare number.
- **DOE (Design of Experiments) framing:** the tool always claims "leading candidate, recommend
  confirmation via targeted DOE" — never "confirmed root cause." Correlation alone never proves
  causation on fab data, and claiming otherwise is the fastest way to lose credibility with a
  judge who has real fab experience.
- **SEMI standards language:** ingestion is modeled on real fab data sources — **SECS/GEM
  (SEMI E30/E37)** for equipment communication, **SEMI E10** for equipment reliability metrics —
  even though the actual data is synthetic.

---

## 3. System Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                     FRONTEND — Dashboard + "Ask Bob" Copilot           │
│  Yield trend | Wafer defect heatmap | Root-cause ranking | Chat panel  │
└───────────────────────────────┬───────────────────────────────────────┘
                                 │ REST/JSON
┌───────────────────────────────▼───────────────────────────────────────┐
│                    BACKEND API (FastAPI)                              │
│  /lots  /defects  /patterns  /rootcause  /predict-risk  /chat  /validate │
└───────┬─────────────────────────────────────────────────┬─────────────┘
        │                                                  │
┌───────▼────────────────┐                     ┌──────────▼──────────────┐
│   DATA LAYER              │                     │  ANALYTICS CORE          │
│  Synthetic FDC/MES/       │──feature vectors───►│  SPC engine              │
│  inspection data gen,     │                     │  Spatial signature clf.  │
│  schema, storage, val.,   │                     │  Root cause ranker       │
│  ground-truth labels      │                     │   (calibrated probability)│
│  for validation           │                     │  Batch risk predictor    │
└────────────────────────────┘                     │  Validation harness      │
                                                    └──────────┬───────────────┘
                                                                │ findings JSON
                                                    ┌───────────▼───────────────┐
                                                    │  GENAI / COPILOT LAYER      │
                                                    │  Plain-English explanation  │
                                                    │  Corrective-action recs     │
                                                    │  Conversational "Bob"       │
                                                    └─────────────────────────────┘
```

---

## 4. Analytics Core — Detailed Spec (Person B)

### 4.1 Inputs
Reads from the DB populated by Person A, including the hidden ground-truth labels (§7.5) used
only for validation, never exposed to the ranker itself.

### 4.2 Pattern Engine
- Compute Cpk/Ppk per (tool, parameter) pair per time window; flag SPC violations via Western
  Electric rules.
- Classify each wafer's defect coordinates into a spatial signature class (rule-based thresholds
  on coordinate density/shape, or simple k-means/DBSCAN — no deep learning needed).
- Output: `(lot_id, step, tool_id, parameter, spc_violation_flag, spatial_signature)`.

### 4.3 Root Cause Ranker — now with a real calibrated probability
This is the corrected version of the requirement "rank root causes by probability." Two tiers,
build Tier 1 first, upgrade to Tier 2 if time allows:

- **Tier 1 (baseline, must-have):** composite deviation score, but **explicitly labeled and
  displayed as a "risk score" (0–1), never called a probability** in the UI or copilot text,
  unless Tier 2 is done. This is the honest fallback if you run out of time.
- **Tier 2 (target, do this if at all possible):** train a simple **logistic regression** (or
  gradient-boosted trees if time allows) where:
  - **Features:** deviation score, spatial signature match, frequency across affected lots,
    sample size, step/tool identity (one-hot).
  - **Label:** was this candidate cause the actual injected ground-truth cause for that lot?
    (from Person A's synthetic data — see §7.5).
  - **Output:** a genuinely calibrated `P(this is the root cause)` — check calibration with a
    simple reliability check (does "80% confidence" actually correspond to being right ~80% of
    the time across your synthetic lots?).
  - This is realistic to build in the timeframe because you control the ground truth — this
    is *exactly* the situation where a simple calibrated model is easy to validate correctly.
- Output: the `root_cause_findings` contract (§7.4) — `probability` field is only ever populated
  by a real model (Tier 2). If only Tier 1 is done, the field is named `risk_score` instead —
  **the field name itself communicates whether you actually met requirement #2 rigorously.**

### 4.4 Batch Risk Predictor
- Nearest-neighbor similarity between in-progress lots' parameter traces and historical
  low-yield fingerprints.
- Output: `at_risk_upcoming_batches` with a risk score (same Tier 1/Tier 2 honesty rule applies).

### 4.5 Validation Harness (new — mandatory, not optional)
- A script (`/analytics/validate.py`) that runs the ranker against every lot in Person A's
  synthetic dataset where a ground-truth cause was injected, and reports:
  - **Top-1 accuracy:** % of lots where the ranker's #1 candidate matches the injected cause.
  - **Top-3 accuracy:** % where it's in the top 3 (more forgiving, still useful signal).
  - **Calibration check (Tier 2 only):** bucket predictions by probability and compare to actual
    hit rate per bucket.
- **This harness must be run and pass its gate at Checkpoint 2 (§10) before moving to polish.**
  Target: Top-1 accuracy ≥ 70% on injected scenarios. If it's below that, the ranking logic gets
  fixed before anyone touches the frontend further — this is a hard gate, not a suggestion.

---

## 5. Copilot Layer — Detailed Spec (Person C)

### 5.1 Explanation Generator
- Input: `root_cause_findings` JSON.
- Output: plain-English explanation per candidate cause, always including the DOE-confirmation
  caveat, and phrasing that matches whichever field is populated (`probability` vs `risk_score`)
  — e.g. "we estimate a 78% probability" only when a real calibrated number exists; otherwise
  "this is the highest-risk candidate based on deviation and frequency."
- Build against hand-written fixture JSON from Hour 0.

### 5.2 Recommendation Generator
- Lookup table mapping root-cause categories (pressure drift, edge-exclusion issue, tool
  contamination, handling damage) to standard corrective actions (PM check, requal, quarantine),
  phrased naturally via LLM.

### 5.3 Conversational "Bob"
- Tool-calling/RAG over a lot's findings JSON for natural Q&A.
- System prompt enforces: cite evidence, state confidence honestly (never invent a probability
  number that wasn't actually produced by the Tier 2 model), always include the DOE caveat.

---

## 6. Frontend + Backend + Integration (Person D)

- **Backend:** thin FastAPI routes calling B's and C's functions; add a `/validate` endpoint
  that surfaces the validation harness results (§4.5) so it's visible in the demo, not just a
  private dev check.
- **Frontend:**
  - Yield trend chart, wafer defect heatmap, ranked root-cause list (clearly labeled probability
    vs. risk score depending on tier), at-risk batch list, chat panel.
  - A small **"Validation" panel/tab** showing Top-1/Top-3 accuracy against injected scenarios —
    this is a genuinely strong, differentiating thing to show a judge: "here's proof our ranking
    actually works, not just a demo that looks nice."
- **Integration lead:** owns `dev` branch health, the 3 checkpoints, contract mismatches, and the
  demo script (§12).

---

## 7. Data Model

### `wafer_lots`
| field | type |
|---|---|
| lot_id | string (PK) |
| product_id | string |
| start_time | datetime |
| fab_line | string |
| final_yield_pct | float (null if `in_progress`) |
| status | enum: `completed`, `in_progress`, `at_risk` |

### `process_steps`
| field | type |
|---|---|
| lot_id | string (FK) |
| step_name | enum: `litho`, `etch`, `cvd`, `cmp`, `implant` |
| tool_id | string |
| parameter_name | string |
| value | float |
| spec_min / spec_max | float |
| timestamp | datetime |

### `defects`
| field | type |
|---|---|
| lot_id | string (FK) |
| wafer_id | string |
| defect_type | enum: `particle`, `scratch`, `bridging`, `void` |
| x, y | float (normalized, -1 to 1) |
| severity | enum: `critical`, `major`, `minor` |
| detected_at_step | string |

### `root_cause_findings` (Analytics Core → Copilot contract)
```json
{
  "lot_id": "LOT-2231",
  "candidate_causes": [
    {
      "step": "etch",
      "tool_id": "ETCH-07",
      "parameter": "chamber_pressure",
      "spatial_signature": "edge-ring",
      "probability": 0.78,
      "risk_score": null,
      "confidence_basis": "logistic_regression_v1",
      "sample_size": 14,
      "evidence": "Pressure 3.2 sigma above spec on 14 of 16 affected lots; Cpk 0.91"
    }
  ],
  "at_risk_upcoming_batches": [
    {"lot_id": "LOT-2245", "probability": 0.71, "risk_score": null, "matched_signature": "edge-ring"}
  ]
}
```
**Rule:** exactly one of `probability` / `risk_score` is non-null per entry, and
`confidence_basis` states which method produced it (`logistic_regression_v1` vs
`composite_heuristic_v1`) — so the copilot layer and frontend always know how to phrase it
honestly.

### 7.5 Ground truth labels (Person A — for validation only, never fed to the ranker as input)
| field | type |
|---|---|
| lot_id | string |
| injected_cause_step | string |
| injected_cause_tool_id | string |
| injected_cause_parameter | string |
| injected_signature | string |

Person A injects 4–6 of these scenarios into the synthetic data with enough affected lots each
(aim for 12–20 lots per scenario) to give the Tier 2 model something real to learn from and the
validation harness something meaningful to measure against.

---

## 8. Work Division

| Person | Owns | Key deliverable |
|---|---|---|
| **A — Data Engineering** | `/data` | Synthetic FDC/MES/inspection dataset + 4–6 injected ground-truth scenarios (§7.5) with 12–20 affected lots each. DB populated by Hour 4. |
| **B — Analytics Core** | `/analytics` | SPC engine, spatial classifier, Tier 1 risk score → Tier 2 calibrated probability ranker, batch risk predictor, **validation harness (§4.5)**. |
| **C — GenAI Copilot** | `/copilot` | Explanation generator (probability-aware phrasing), recommendation generator, conversational Bob. |
| **D — Backend + Frontend + Integration** | `/backend`, `/frontend` | API routes incl. `/validate`, dashboard incl. validation panel, integration lead across all checkpoints + demo. |

---

## 9. Git Workflow

### Repo structure
```
/data          → Person A
/analytics     → Person B
/copilot       → Person C
/backend       → Person D
/frontend      → Person D
/contracts     → shared schemas + fixtures (Hour 0, rarely touched after)
/docs          → this plan, demo script
```

### Branches
```
main (protected) ← dev (integration) ← feature/data-pipeline (A)
                                     ← feature/analytics-core (B)
                                     ← feature/copilot (C)
                                     ← feature/backend-frontend (D)
```

### Rules
1. Hour 0: finalize `/contracts` (§7) together, commit to `dev`, split into feature branches.
2. Commit small and often (every 30–45 min), not one giant commit at the end.
3. **Commit convention:**
   ```
   feat(data): add synthetic data generator with 5 injected ground-truth scenarios
   feat(analytics): implement Tier 1 composite risk score
   feat(analytics): implement Tier 2 calibrated logistic regression ranker
   feat(analytics): add validation harness measuring top-1/top-3 accuracy
   feat(copilot): probability-aware explanation phrasing
   fix(backend): correct /rootcause response to match contract
   docs(contracts): finalize root_cause_findings schema with probability/risk_score split
   ```
4. Open PRs into `dev` as soon as a slice works.
5. **3 integration checkpoints** (30%, 60%, 90% of your clock) — merge to `dev`, smoke test.
   **Checkpoint 2 additionally requires the validation harness to pass its gate (§10, §11)
   before the team moves on to frontend polish.**
6. Nobody commits directly to `main`.

### Antigravity usage
One agent workspace per person, scoped to their folder:
- A: "Build the synthetic data generator with 5 injected ground-truth root-cause scenarios per
  `/contracts/schema.md`, including hidden ground-truth labels for validation."
- B: "Build the SPC engine, spatial classifier, and root cause ranker (Tier 1 composite score,
  then Tier 2 logistic regression using ground-truth labels), plus a validation harness measuring
  top-1/top-3 accuracy, outputting exactly `/contracts/findings_schema.json`."
- C, D scoped similarly. At each checkpoint, skim teammates' agent Artifacts (plans/screenshots)
  to catch contract drift before it becomes a conflict.

---

## 10. Timeline (~24-hour hackathon)

| Time | Milestone |
|---|---|
| Hour 0–1 | Finalize architecture + `/contracts`. Scaffold repo. |
| Hour 1–4 | Build against mocked contracts. Person A finishes real seed data + ground-truth labels. |
| **Checkpoint 1 (Hour 4)** | Person B switches to real data. Merge to `dev`, smoke test. |
| Hour 4–9 | Tier 1 risk score ranker working end-to-end. SPC + spatial signatures done. |
| Hour 9–10 | Tier 2 logistic regression ranker trained against ground-truth labels. |
| **Checkpoint 2 (Hour 10) — VALIDATION GATE** | Run `/analytics/validate.py`. **Top-1 accuracy must be ≥ 70% on injected scenarios before proceeding.** If it fails, fix the ranker — do not move to polish. |
| Hour 10–16 | Frontend (incl. validation panel), chat UI, recommendation phrasing, error handling. |
| **Checkpoint 3 (Hour 16)** | Feature freeze. Merge `dev` → `main`. |
| Hour 16–20 | Bug fixes only. Rehearse demo, including the validation panel. |
| Hour 20–24 | Final polish, pitch deck, 2x demo rehearsal, buffer. |

---

## 11. Validation Plan (mandatory — this is what proves requirement #2 is actually met)

1. Person A's synthetic dataset must include **4–6 injected ground-truth root-cause scenarios**,
   each affecting 12–20 lots, hidden from the ranker but stored in `ground_truth_labels` (§7.5).
2. Person B's `/analytics/validate.py` runs the ranker against every labeled lot and reports:
   - Top-1 accuracy (target ≥ 70%)
   - Top-3 accuracy (sanity check, should be notably higher than Top-1)
   - Calibration check for Tier 2: do lots ranked "~80% probability" actually turn out correct
     about 80% of the time across the synthetic set?
3. This is a **hard gate at Checkpoint 2** — if Top-1 accuracy is below target, the team fixes
   the ranking logic (better features, narrower confounding control, more training lots) before
   touching frontend polish.
4. The validation results are surfaced in the product itself (§6 — Validation panel) and used
   directly in the demo (§12) as proof the ranking is real, not just a plausible-looking UI.

---

## 12. Demo Script (5 minutes)

1. **Hook (20s):** "A 1% yield drop at 3nm costs tens of millions a month. Engineers spend weeks
   finding out why. Bob finds it in seconds — and we can actually prove how often it's right."
2. **Problem (30s):** Dashboard — a lot with a yield drop, defect heatmap showing edge-ring
   pattern.
3. **Core capability (90s):** Root cause ranking — Bob surfaces the etch tool pressure deviation
   as the top candidate with a real calibrated probability, evidence, Cpk, sample size, and the
   DOE-confirmation caveat.
4. **Proof, not just a claim (30s):** Show the Validation panel — "we tested this against known
   root causes we injected ourselves, and it correctly identifies the true cause X% of the time."
   This is the moment that separates you from a team that just built a nice-looking demo.
5. **Predictive angle (45s):** "Bob also flagged upcoming lots matching this signature before
   they finished running."
6. **Conversational copilot (45s):** Live-ask "Bob, why did Lot 2231 fail and what should we do?"
7. **Close (20s):** Tie back to real fab methodology (SPC, SEMI standards, DOE) and the
   validation proof — this isn't a generic ML demo, it's built and tested the way real yield
   engineers actually work.

---

## 13. Stretch Goals (only after §11's validation gate passes and core demo is solid)
- Replace rule-based spatial signature classification with a lightweight clustering/CNN model.
- SHAP-based feature importance for deeper root-cause explanations.
- Slack/Teams-style alert when a new lot is flagged at-risk.
