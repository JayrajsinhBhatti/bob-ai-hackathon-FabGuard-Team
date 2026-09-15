"""
Configuration and domain constants for Bob Fab synthetic semiconductor data generation.
Models a sub-5nm advanced CMOS fabrication line with SECS/GEM & SEMI E10 compliance.
"""

from typing import Dict, Any, List

# Product lines manufactured in the fab
PRODUCT_LINES: List[str] = [
    "PROD-3NM-SOC",
    "PROD-3NM-AI-ACCEL",
    "PROD-5NM-GPU",
    "PROD-5NM-MODEM",
]

FAB_LINES: List[str] = [
    "LINE-01-FAB12",
    "LINE-02-FAB12",
]

# 5 Core Process Steps and Equipment Tool Pools
TOOL_POOLS: Dict[str, List[str]] = {
    "litho": ["LITHO-01", "LITHO-02", "LITHO-03", "LITHO-04"],
    "etch": ["ETCH-01", "ETCH-02", "ETCH-03", "ETCH-04", "ETCH-05", "ETCH-06", "ETCH-07", "ETCH-08"],
    "cvd": ["CVD-01", "CVD-02", "CVD-03", "CVD-04", "CVD-05", "CVD-06"],
    "cmp": ["CMP-01", "CMP-02", "CMP-03", "CMP-04"],
    "implant": ["IMP-01", "IMP-02", "IMP-03"],
}

# FDC Telemetry Sensor Parameters per Step (Nominal mean, 1-sigma, LSL, USL, Unit)
# Engineering specs set to ~ 3.2 - 3.5 sigma under nominal conditions (nominal Cpk ~ 1.35 - 1.50)
PROCESS_SPECS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "litho": {
        "exposure_energy": {"mean": 24.5, "sigma": 0.22, "spec_min": 23.7, "spec_max": 25.3, "unit": "mJ/cm2"},
        "focus_offset": {"mean": 0.0, "sigma": 2.2, "spec_min": -7.5, "spec_max": 7.5, "unit": "nm"},
        "numerical_aperture": {"mean": 1.350, "sigma": 0.003, "spec_min": 1.339, "spec_max": 1.361, "unit": "NA"},
    },
    "etch": {
        "chamber_pressure": {"mean": 15.0, "sigma": 0.35, "spec_min": 13.8, "spec_max": 16.2, "unit": "mTorr"},
        "rf_power_forward": {"mean": 850.0, "sigma": 6.5, "spec_min": 828.0, "spec_max": 872.0, "unit": "W"},
        "gas_flow_cl2": {"mean": 120.0, "sigma": 1.2, "spec_min": 115.8, "spec_max": 124.2, "unit": "sccm"},
    },
    "cvd": {
        "deposition_temp": {"mean": 400.0, "sigma": 1.6, "spec_min": 394.5, "spec_max": 405.5, "unit": "degC"},
        "chamber_pressure": {"mean": 4.00, "sigma": 0.06, "spec_min": 3.79, "spec_max": 4.21, "unit": "Torr"},
        "rf_bias": {"mean": 250.0, "sigma": 2.8, "spec_min": 240.0, "spec_max": 260.0, "unit": "W"},
    },
    "cmp": {
        "head_downforce": {"mean": 3.50, "sigma": 0.05, "spec_min": 3.33, "spec_max": 3.67, "unit": "psi"},
        "platen_rpm": {"mean": 75.0, "sigma": 0.6, "spec_min": 72.9, "spec_max": 77.1, "unit": "rpm"},
        "slurry_flow_rate": {"mean": 180.0, "sigma": 2.0, "spec_min": 173.0, "spec_max": 187.0, "unit": "mL/min"},
    },
    "implant": {
        "beam_current": {"mean": 12.00, "sigma": 0.12, "spec_min": 11.58, "spec_max": 12.42, "unit": "mA"},
        "acceleration_energy": {"mean": 80.0, "sigma": 0.5, "spec_min": 78.2, "spec_max": 81.8, "unit": "keV"},
        "tilt_angle": {"mean": 7.00, "sigma": 0.06, "spec_min": 6.79, "spec_max": 7.21, "unit": "deg"},
    },
}

# Injected Fault Scenarios (Ground-Truth Definition for Validation Gate)
# Matches §7.5 and §11 of Implementation Plan v3
SCENARIOS_CONFIG = [
    {
        "scenario_id": 1,
        "name": "Etch Chamber Pressure Drift (Perimeter Edge Exclusion)",
        "step": "etch",
        "tool_id": "ETCH-07",
        "parameter": "chamber_pressure",
        "drift_sigma": 3.4,  # Shifts pressure to ~16.2 - 16.6 mTorr (> spec_max 16.5)
        "signature": "edge-ring",
        "defect_types": {"particle": 0.60, "void": 0.40},
        "lot_prefix": "LOT-22",
        "start_lot_num": 1,
        "num_lots": 16,  # LOT-2201 to LOT-2216
        "nominal_yield_range": (74.0, 78.5),
        "defects_per_wafer_range": (90, 160),
    },
    {
        "scenario_id": 2,
        "name": "Litho Optical Focus Aberration (Center Lens Drift)",
        "step": "litho",
        "tool_id": "LITHO-03",
        "parameter": "focus_offset",
        "drift_sigma": 3.5,  # Focus shifts to ~ +11.5 to +13.5 nm (> spec_max 10.0)
        "signature": "center-cluster",
        "defect_types": {"bridging": 0.75, "particle": 0.25},
        "lot_prefix": "LOT-22",
        "start_lot_num": 20,
        "num_lots": 15,  # LOT-2220 to LOT-2234
        "nominal_yield_range": (79.0, 83.5),
        "defects_per_wafer_range": (80, 140),
    },
    {
        "scenario_id": 3,
        "name": "CMP Head Downforce Mechanical Wear (Wafer Scratching)",
        "step": "cmp",
        "tool_id": "CMP-02",
        "parameter": "head_downforce",
        "drift_sigma": 3.6,  # Downforce shifts to ~ 3.72 - 3.82 psi (> spec_max 3.75)
        "signature": "scratch",
        "defect_types": {"scratch": 0.85, "particle": 0.15},
        "lot_prefix": "LOT-22",
        "start_lot_num": 40,
        "num_lots": 14,  # LOT-2240 to LOT-2253
        "nominal_yield_range": (70.0, 75.0),
        "defects_per_wafer_range": (110, 190),
    },
    {
        "scenario_id": 4,
        "name": "CVD Deposition Temperature Gradient (Mid-Radius Annular Donut)",
        "step": "cvd",
        "tool_id": "CVD-05",
        "parameter": "deposition_temp",
        "drift_sigma": -3.5,  # Deposition temp drops to ~ 390.5 - 392.2 degC (< spec_min 392.0)
        "signature": "donut",
        "defect_types": {"void": 0.70, "particle": 0.30},
        "lot_prefix": "LOT-22",
        "start_lot_num": 60,
        "num_lots": 15,  # LOT-2260 to LOT-2274
        "nominal_yield_range": (81.0, 85.5),
        "defects_per_wafer_range": (75, 130),
    },
    {
        "scenario_id": 5,
        "name": "Implant Beam Current Instability (Substrate Arcing Damage)",
        "step": "implant",
        "tool_id": "IMP-01",
        "parameter": "beam_current",
        "drift_sigma": 3.6,  # Beam current spikes to ~ 12.55 - 12.72 mA (> spec_max 12.6)
        "signature": "random",
        "defect_types": {"particle": 0.80, "void": 0.20},
        "lot_prefix": "LOT-22",
        "start_lot_num": 80,
        "num_lots": 14,  # LOT-2280 to LOT-2293
        "nominal_yield_range": (77.0, 81.5),
        "defects_per_wafer_range": (85, 150),
    },
]

# Baseline Clean Normal Lots Configuration
NORMAL_LOTS_CONFIG = {
    "lot_prefix": "LOT-20",
    "start_lot_num": 1,
    "num_lots": 35,  # LOT-2001 to LOT-2035
    "nominal_yield_range": (93.5, 98.2),
    "defects_per_wafer_range": (12, 28),
}

# In-Progress Lots Configuration (Upcoming Batches for Requirement 4)
IN_PROGRESS_LOTS_CONFIG = {
    "lot_prefix": "LOT-23",
    "start_lot_num": 1,
    "num_lots": 10,  # LOT-2301 to LOT-2310
    # 3 lots actively running on drifted tools (e.g. ETCH-07 pressure) to test predictive risk
    "at_risk_indices": [1, 5, 8],  # LOT-2301, LOT-2305, LOT-2308
    "at_risk_scenario_id": 1,  # Matches Scenario 1 (ETCH-07 chamber_pressure)
}
