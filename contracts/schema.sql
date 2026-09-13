-- Bob Fab Copilot: SQLite Relational Schema
-- S1: Wafer Yield Root Cause & Defect Pattern Analyser
-- Standardized contracts matching Section 7 of Implementation Plan

-- 1. Wafer Lots Table
CREATE TABLE IF NOT EXISTS wafer_lots (
    lot_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    fab_line TEXT NOT NULL,
    final_yield_pct REAL, -- NULL if status is 'in_progress'
    status TEXT NOT NULL CHECK (status IN ('completed', 'in_progress', 'at_risk'))
);

-- 2. Process Steps & FDC Sensor Telemetry Table
CREATE TABLE IF NOT EXISTS process_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id TEXT NOT NULL,
    step_name TEXT NOT NULL CHECK (step_name IN ('litho', 'etch', 'cvd', 'cmp', 'implant')),
    tool_id TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    value REAL NOT NULL,
    spec_min REAL NOT NULL,
    spec_max REAL NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (lot_id) REFERENCES wafer_lots(lot_id) ON DELETE CASCADE
);

-- 3. Defect Coordinates & Inspection Table
CREATE TABLE IF NOT EXISTS defects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id TEXT NOT NULL,
    wafer_id TEXT NOT NULL,
    defect_type TEXT NOT NULL CHECK (defect_type IN ('particle', 'scratch', 'bridging', 'void')),
    x REAL NOT NULL CHECK (x >= -1.0 AND x <= 1.0),
    y REAL NOT NULL CHECK (y >= -1.0 AND y <= 1.0),
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'major', 'minor')),
    detected_at_step TEXT NOT NULL,
    FOREIGN KEY (lot_id) REFERENCES wafer_lots(lot_id) ON DELETE CASCADE
);

-- 4. Ground Truth Labels (Validation only, hidden from ranker input)
CREATE TABLE IF NOT EXISTS ground_truth_labels (
    lot_id TEXT PRIMARY KEY,
    injected_cause_step TEXT NOT NULL,
    injected_cause_tool_id TEXT NOT NULL,
    injected_cause_parameter TEXT NOT NULL,
    injected_signature TEXT NOT NULL CHECK (injected_signature IN ('edge-ring', 'center-cluster', 'scratch', 'donut', 'random')),
    FOREIGN KEY (lot_id) REFERENCES wafer_lots(lot_id) ON DELETE CASCADE
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_process_steps_lot_id ON process_steps(lot_id);
CREATE INDEX IF NOT EXISTS idx_process_steps_tool_param ON process_steps(tool_id, parameter_name);
CREATE INDEX IF NOT EXISTS idx_defects_lot_id ON defects(lot_id);
CREATE INDEX IF NOT EXISTS idx_defects_wafer_id ON defects(wafer_id);
CREATE INDEX IF NOT EXISTS idx_defects_type ON defects(defect_type);
