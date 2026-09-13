# Bob Fab Copilot — Data Contracts & Schemas

This document defines the shared relational and JSON contracts across all team components.

---

## 1. Relational Schema (`bob_fab.db`)

The database is an SQLite 3 database structured according to [schema.sql](file:///c:/Users/yashg/Documents/BOBathon/contracts/schema.sql).

### 1.1 `wafer_lots`
Represents manufacturing lots (batches of ~25 wafers each).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `lot_id` | TEXT | PRIMARY KEY | Unique identifier, format `LOT-XXXX` (e.g. `LOT-2231`) |
| `product_id` | TEXT | NOT NULL | Product line (e.g., `PROD-3NM-SOC`, `PROD-5NM-GPU`) |
| `start_time` | TIMESTAMP | NOT NULL | ISO 8601 lot processing start timestamp |
| `fab_line` | TEXT | NOT NULL | Fab fabrication line ID (e.g., `LINE-01`) |
| `final_yield_pct`| REAL | NULLABLE | Overall percentage yield (0.0 – 100.0). `NULL` if lot is `in_progress`. |
| `status` | TEXT | NOT NULL | Enum: `'completed'`, `'in_progress'`, `'at_risk'` |

### 1.2 `process_steps`
FDC sensor readings recorded across 5 key fab processing steps.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT | Internal record ID |
| `lot_id` | TEXT | FK (`wafer_lots.lot_id`) | Reference to wafer lot |
| `step_name` | TEXT | NOT NULL | Enum: `'litho'`, `'etch'`, `'cvd'`, `'cmp'`, `'implant'` |
| `tool_id` | TEXT | NOT NULL | Specific equipment ID (e.g. `ETCH-07`, `LITHO-03`) |
| `parameter_name`| TEXT | NOT NULL | Monitored process parameter (e.g. `chamber_pressure`) |
| `value` | REAL | NOT NULL | Measured telemetry sensor value |
| `spec_min` | REAL | NOT NULL | Lower engineering specification limit (LSL) |
| `spec_max` | REAL | NOT NULL | Upper engineering specification limit (USL) |
| `timestamp` | TIMESTAMP | NOT NULL | Event timestamp |

### 1.3 `defects`
Defect coordinates detected by in-line optical and scanning inspection equipment.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT | Internal defect ID |
| `lot_id` | TEXT | FK (`wafer_lots.lot_id`) | Reference to wafer lot |
| `wafer_id` | TEXT | NOT NULL | Wafer ID within lot, e.g. `LOT-2231-W01` to `W25` |
| `defect_type` | TEXT | NOT NULL | Enum: `'particle'`, `'scratch'`, `'bridging'`, `'void'` |
| `x` | REAL | $-1.0 \le x \le 1.0$ | Normalized horizontal coordinate on wafer disk |
| `y` | REAL | $-1.0 \le y \le 1.0$ | Normalized vertical coordinate on wafer disk |
| `severity` | TEXT | NOT NULL | Enum: `'critical'`, `'major'`, `'minor'` |
| `detected_at_step` | TEXT | NOT NULL | Step where defect was observed (e.g., `'etch'`) |

> Note: All physical defect coordinates lie strictly on the circular wafer disk: $x^2 + y^2 \le 1.0$.

### 1.4 `ground_truth_labels` (Validation Only)
**CRITICAL:** Used only by Person B's `/analytics/validate.py` harness to compute Top-1 and Top-3 accuracy. **Never exposed to the ranker as input feature.**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `lot_id` | TEXT | PRIMARY KEY, FK | Reference to wafer lot |
| `injected_cause_step` | TEXT | NOT NULL | Injected true fault step (e.g. `'etch'`) |
| `injected_cause_tool_id` | TEXT | NOT NULL | Injected true tool (e.g. `'ETCH-07'`) |
| `injected_cause_parameter` | TEXT | NOT NULL | Injected true parameter (e.g. `'chamber_pressure'`) |
| `injected_signature` | TEXT | NOT NULL | Injected spatial pattern: `'edge-ring'`, `'center-cluster'`, `'scratch'`, `'donut'`, `'random'` |

---

## 2. Analytics to Copilot Contract: `root_cause_findings`

Defined in [findings_schema.json](file:///c:/Users/yashg/Documents/BOBathon/contracts/findings_schema.json).

### Honesty Rule (§4.3, §7.4):
- Exactly **one** of `probability` or `risk_score` MUST be non-null:
  - If Tier 2 calibrated logistic regression was executed: populate `probability` (e.g. `0.78`), set `risk_score: null`, set `confidence_basis: "logistic_regression_v1"`.
  - If Tier 1 heuristic composite score was executed: populate `risk_score` (e.g. `0.84`), set `probability: null`, set `confidence_basis: "composite_heuristic_v1"`.
- Person C's copilot and Person D's frontend MUST inspect which field is populated and adapt phrasing accordingly:
  - `"we estimate a 78% probability (calibrated ML model)..."` vs
  - `"this is the highest risk candidate based on heuristic deviation score 0.84..."`
