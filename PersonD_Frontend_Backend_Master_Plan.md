# Person D — Frontend + Backend Master Implementation Plan
## Bob Fab Copilot — BOBathon-collab
### Repo: github.com/Yashgohel018/BOBathon-collab

> Current repo state: `docs/`, `README.md`, `S1_FINAL_Implementation_Plan_v3.md`. No `/backend`
> or `/frontend` yet — this plan is what you (Person D) build into those two folders, following
> the contracts already frozen in the master plan (§7 of `S1_FINAL_Implementation_Plan_v3.md`).
> Everything below is scoped so it plugs directly into Person B's `root_cause_findings` JSON and
> Person C's copilot endpoints without needing to touch their code.

---

## 1. What "done" looks like for Person D

Two things, and both matter equally for judging:
1. **A landing page that makes the differentiation obvious in 10 seconds** — before anyone even
   clicks into the dashboard, they should understand what Bob does differently from a generic
   yield-analytics tool.
2. **A working product** — dashboard, wafer visualization, root-cause ranking, validation proof,
   and the conversational copilot, all wired to real backend data (not just mocks) by the final
   checkpoint.

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend framework | React + Vite | Fast dev loop, easy to wire to FastAPI JSON |
| Styling | Tailwind CSS | Pairs cleanly with Stitch-generated designs (§5) |
| Charts | Recharts (yield trend, validation accuracy bars) | Simple, reliable, fast to implement |
| 3D wafer visualization | **react-three-fiber + drei** (Three.js wrapper for React) | For the interactive 3D wafer defect map — see §6.3 |
| Backend framework | FastAPI (Python) | Matches Person B/C's Python stack, auto-generates OpenAPI docs you can use as a live contract check |
| DB access | SQLAlchemy or direct SQLite/DuckDB queries (matches Person A's DB) | |
| Dev/design tool | **Stitch MCP (via Antigravity)** | Generate UI layout/visual designs, then hand-translate into Tailwind/React — see §5 |

---

## 3. Landing Page — Differentiation Strategy

This is the page that has to answer, immediately: **"why is this not just another dashboard?"**
Structure it as a narrative, not a feature list:

### Section 1 — Hero
- Headline built around the cost hook, not the tech: *"A 1% yield drop costs tens of millions a
  month. Bob finds the root cause in seconds — and proves how often it's right."*
- Subheadline names the 3 things that make this different from a generic analytics dashboard:
  **calibrated probability (not a guess-score), a validation gate against known ground truth,
  and a conversational copilot that never overclaims.**
- One clear CTA: "Open the Dashboard" / "Ask Bob a question."

### Section 2 — The Problem (short, visual)
- 3 stat callouts (large numbers, small labels): "$90B/yr" (maintenance-adjacent framing),
  "weeks" (current manual root-cause time), "1%" (yield drop cost). Keep this scannable, not
  paragraph-heavy — this is the section most people skim.

### Section 3 — What Makes Bob Different (the actual differentiation, spelled out)
Three columns, each with a short claim + one line of proof:
1. **"Not a black box"** — every candidate cause ships with Cpk, sample size, and confidence, not
   just a bare score.
2. **"Not overclaiming"** — every finding carries a DOE-confirmation caveat, the same discipline
   real process engineers use, instead of declaring "root cause found."
3. **"Provably accurate"** — the validation panel shows real Top-1/Top-3 accuracy against
   injected ground-truth scenarios, live in the product, not just in a slide.

### Section 4 — Live Preview / Interactive Teaser
- An embedded, simplified preview of the 3D wafer defect map (§6.3) right on the landing page —
  this is your best "wow" moment and costs nothing extra since the component is reused from the
  dashboard.

### Section 5 — How It Works (short pipeline visual)
- A simple horizontal flow diagram: Sensor/Defect Data → Pattern Engine → Calibrated Ranking →
  Copilot Explanation → Action. Keep it to 4–5 steps, icon + one line each.

### Section 6 — Footer CTA
- Repeat the CTA to the dashboard/chat. Don't add anything new here.

---

## 4. App Structure (routes/pages)

| Route | Purpose |
|---|---|
| `/` | Landing page (§3) |
| `/dashboard` | Main product — yield trend, lot selector, defect heatmap, root-cause ranking |
| `/dashboard/lot/:lotId` | Deep-dive view for a single lot — full findings, evidence, recommendations |
| `/dashboard/validation` | The Validation panel (§6.5) — Top-1/Top-3 accuracy, calibration chart |
| `/dashboard/at-risk` | Upcoming batch risk list |
| `/chat` (or a persistent side panel available from any page) | "Ask Bob" conversational copilot |

A persistent chat panel (rather than a separate page) is usually the stronger UX — keep Bob
reachable from every screen, not tucked away.

---

## 5. Using Stitch (MCP in Antigravity) — Workflow

Stitch is a **design generator**, not a code generator you ship directly — treat its output as a
high-fidelity mockup/reference, then implement it properly in Tailwind/React so it matches your
actual data and stays maintainable. Suggested workflow:

1. **Prompt Stitch for the landing page hero and section layout** — describe the narrative from
   §3 (industrial/technical aesthetic, not generic SaaS — think precision, data, dark-mode
   fab-monitoring feel rather than a consumer app). Ask for a few variations.
2. **Prompt Stitch for the dashboard layout** — panel arrangement (heatmap + ranking + trend +
   chat), so you get a defensible visual hierarchy instead of guessing.
3. **Translate, don't copy-paste blindly:** take Stitch's color palette, spacing, typography, and
   layout structure, then hand-build the actual components in React/Tailwind bound to real data.
   Stitch won't know your JSON contracts — you do.
4. **Use it again for the 3D wafer map's 2D reference** — even though the final component is
   Three.js, ask Stitch for what the *2D heatmap legend/color scheme* should look like (severity
   colors, signature-type iconography), then apply those exact colors inside the 3D scene so the
   whole product feels visually consistent.
5. Keep Stitch outputs in `/docs/design-reference/` in the repo (screenshots or exported assets)
   so the whole team — and judges, if you show it — can see the design process was intentional.

---

## 6. Required Components — Full Breakdown

### 6.1 Yield Trend Chart
- Recharts line chart, yield % over time, filterable by product line/fab line.
- Data source: `GET /lots` aggregated by date.

### 6.2 Root Cause Ranking Panel
- Ranked list of candidate causes for a selected lot, pulled directly from
  `root_cause_findings.candidate_causes`.
- **Must render `probability` vs `risk_score` differently** per the contract rule in the master
  plan (§7.4) — show a clear badge: "Calibrated probability" vs "Heuristic risk score" — this is
  the honesty mechanism from the master plan and should be visually obvious, not buried in a
  tooltip.
- Show evidence text, Cpk, sample size, spatial signature tag, and the DOE-confirmation caveat
  inline — don't hide it in a modal, it's part of the credibility story.

### 6.3 3D Wafer Defect Map (the visual centerpiece)
- Build with **react-three-fiber**: render a wafer as a flat cylinder/disc, plot defects as
  points/instanced meshes at their normalized (x, y) coordinates, colored by `severity`.
- Support **rotation/orbit controls** (via `drei`'s `OrbitControls`) so it's genuinely
  interactive, not just a static image — this is your strongest "proper UI" moment in a demo.
- Overlay the classified **spatial signature** (edge-ring, center-cluster, scratch, donut,
  random) as a label/highlight region on the wafer, since that's a core requirement output, not
  just decoration.
- Data source: `GET /defects?lot_id=...`.
- Keep a 2D fallback (simple scatter plot) behind a toggle in case 3D rendering has issues during
  the live demo — never let your core feature be a single point of failure on stage.

### 6.4 At-Risk Upcoming Batches Panel
- List of `at_risk_upcoming_batches` with probability/risk_score, matched signature, and a link
  into that lot's deep-dive view.
- Data source: `GET /predict-risk`.

### 6.5 Validation Panel (differentiator — do not skip this)
- Pulls from the `/validate` endpoint (Person B's harness output).
- Show Top-1 and Top-3 accuracy as large, clear stat cards.
- Show a calibration chart (bar chart: predicted probability bucket vs. actual hit rate) — this
  is the strongest "we're not just demoing a nice UI" proof point in the whole product.

### 6.6 "Ask Bob" Copilot Panel
- Persistent chat component, calls `POST /chat` with `{lot_id, question}`.
- Render responses with clear source grounding — if Bob references a finding, link it back to
  the relevant candidate cause card so answers feel traceable, not generic chatbot output.
- Add 3–4 suggested starter questions ("Why did this lot fail?", "What should I check first?")
  so judges don't have to think of a question live.

### 6.7 Lot Selector / Search
- Simple dropdown or search-by-lot-ID, shared across dashboard pages via URL param
  (`/dashboard/lot/:lotId`) so any panel can deep-link to a specific lot.

---

## 7. Backend — API Spec (thin layer over B's and C's functions)

| Endpoint | Method | Input | Output | Calls |
|---|---|---|---|---|
| `/lots` | GET | query params (fab_line, date range) | list of lots + yield trend data | Data layer (direct DB query) |
| `/defects` | GET | `lot_id` | defect list with x, y, severity, type | Data layer |
| `/patterns` | GET | `lot_id` | SPC violations + spatial signature per step | Person B's Pattern Engine |
| `/rootcause` | GET | `lot_id` | `root_cause_findings` JSON (§7.4 of master plan) | Person B's Ranker |
| `/predict-risk` | GET | — | `at_risk_upcoming_batches` list | Person B's Batch Risk Predictor |
| `/validate` | GET | — | Top-1/Top-3 accuracy + calibration data | Person B's validation harness |
| `/chat` | POST | `{lot_id, question}` | copilot response text + cited findings | Person C's conversational layer |
| `/recommend` | GET | `lot_id` | corrective action recommendations | Person C's Recommendation Generator |

**Build order matters:** stub every endpoint with hardcoded fixture JSON matching these exact
shapes on Day 1 — this unblocks your own frontend work immediately and gives B and C something
concrete to plug into rather than a spec on paper.

---

## 8. Folder Structure to Commit

```
/backend
  /app
    main.py                 # FastAPI app entrypoint
    routes/
      lots.py
      defects.py
      rootcause.py
      predict_risk.py
      validate.py
      chat.py
      recommend.py
    services/                # thin wrappers calling analytics/copilot modules
    db.py                    # connection to Person A's DB
  requirements.txt

/frontend
  /src
    /pages
      Landing.jsx
      Dashboard.jsx
      LotDetail.jsx
      Validation.jsx
      AtRisk.jsx
    /components
      YieldTrendChart.jsx
      RootCauseRankingPanel.jsx
      WaferMap3D.jsx
      WaferMap2DFallback.jsx
      AtRiskList.jsx
      ValidationPanel.jsx
      ChatPanel.jsx
      LotSelector.jsx
    /lib
      api.js                 # fetch wrappers for every backend endpoint in §7
    App.jsx
    main.jsx
  package.json
  tailwind.config.js

/docs
  design-reference/           # Stitch exports/screenshots
```

---

## 9. Build Timeline (aligned to the master plan's checkpoints)

| Time | Milestone |
|---|---|
| Hour 0–1 | Scaffold `/backend` and `/frontend`. Stub every endpoint in §7 with fixture JSON. Prompt Stitch for landing page + dashboard layout references, save to `/docs/design-reference`. |
| Hour 1–4 | Build landing page (§3) fully against static content — doesn't depend on anyone else. Build dashboard shell + routing (§4). |
| **Checkpoint 1 (Hour 4)** | Wire `/lots` and `/defects` to Person A's real DB. Build Yield Trend Chart and start WaferMap3D against real defect coordinates. |
| Hour 4–10 | Build RootCauseRankingPanel, AtRiskList, ChatPanel against stubbed B/C responses. Finish WaferMap3D with OrbitControls + 2D fallback toggle. |
| **Checkpoint 2 (Hour 10) — depends on B's validation gate passing** | Swap stubbed `/rootcause`, `/predict-risk`, `/chat` for real calls to B's and C's modules. Build ValidationPanel against B's real harness output. |
| Hour 10–16 | Polish: probability vs risk_score badges, evidence display, chat source-linking, responsive layout pass. |
| **Checkpoint 3 (Hour 16)** | Feature freeze, full end-to-end smoke test across every route. |
| Hour 16–20 | Bug fixes only. Rehearse the demo flow through the actual UI, not slides. |
| Hour 20–24 | Final polish, deploy (or confirm local demo reliability), buffer. |

---

## 10. Demo Flow Through the UI (ties back to master plan §12)

1. Open on the **landing page** — let the differentiation section (§3.3) speak for itself for a
   few seconds before clicking in.
2. Land on **Dashboard** — point out the yield trend and click into a lot with a visible drop.
3. Rotate the **3D wafer map** live — this is your visual "wow" moment, use it.
4. Show the **Root Cause Ranking Panel** — call out the "Calibrated probability" badge and the
   DOE caveat explicitly.
5. Switch to **Validation Panel** — "here's proof, not just a claim."
6. Open **At-Risk panel** — show a flagged upcoming batch.
7. Use the **Chat panel** live — ask a real question, show the answer citing the actual finding.

---

## 11. Risk Notes (things that commonly break live demos)

- **3D rendering can be fragile on unfamiliar demo hardware/projectors** — always have the 2D
  fallback toggle tested and ready; don't discover a WebGL issue on stage.
- **Don't let `/chat` depend on a live external LLM call with no timeout/fallback** — add a
  loading state and a graceful error message so a slow API response doesn't stall the whole demo.
- **Keep a local, offline-capable fallback dataset** loaded in case live DB/API access is flaky
  during the actual presentation.
