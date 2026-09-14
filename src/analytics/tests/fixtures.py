"""Synthetic fab benchmark fixtures for analytics tests.

Provides realistic simulation datasets for:
- Case 1: Etch chamber pressure excursion with edge-ring defects (LOT-2231)
- Case 2: CMP handling scratch with linear defects (LOT-2232)
- Case 3: CVD temperature gradient with center cluster defects (LOT-2233)
- Case 4: Historical low-yield lots and an in-progress lot matching failure trace (LOT-2245)
"""

import numpy as np
from typing import Any, Dict, List, Tuple
from analytics.data_access import InMemoryRepository


def generate_edge_ring_points(n: int = 40, seed: int = 42) -> List[Tuple[float, float]]:
    """Generate defect coordinates distributed along the wafer perimeter."""
    rng = np.random.default_rng(seed)
    # Radial distances between 0.75 and 0.98
    r = rng.uniform(0.76, 0.96, size=n)
    theta = rng.uniform(-np.pi, np.pi, size=n)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return [(float(xi), float(yi)) for xi, yi in zip(x, y)]


def generate_scratch_points(n: int = 35, seed: int = 43) -> List[Tuple[float, float]]:
    """Generate defect coordinates forming a distinct linear scratch."""
    rng = np.random.default_rng(seed)
    # Line along y = 0.8 * x - 0.1 with tiny orthogonal noise
    t = rng.uniform(-0.8, 0.8, size=n)
    noise_x = rng.normal(0, 0.015, size=n)
    noise_y = rng.normal(0, 0.015, size=n)
    x = t + noise_x
    y = 0.75 * t - 0.1 + noise_y
    return [(float(xi), float(yi)) for xi, yi in zip(x, y)]


def generate_center_cluster_points(n: int = 45, seed: int = 44) -> List[Tuple[float, float]]:
    """Generate defect coordinates clustered tightly at wafer center."""
    rng = np.random.default_rng(seed)
    # 2D Gaussian around (0, 0)
    x = rng.normal(0.0, 0.12, size=n)
    y = rng.normal(0.0, 0.12, size=n)
    # Clip to wafer unit circle
    return [(float(np.clip(xi, -0.32, 0.32)), float(np.clip(yi, -0.32, 0.32))) for xi, yi in zip(x, y)]


def generate_donut_points(n: int = 45, seed: int = 45) -> List[Tuple[float, float]]:
    """Generate defect coordinates in an annular ring with hollow center."""
    rng = np.random.default_rng(seed)
    r = rng.uniform(0.42, 0.72, size=n)
    theta = rng.uniform(-np.pi, np.pi, size=n)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return [(float(xi), float(yi)) for xi, yi in zip(x, y)]


def generate_random_points(n: int = 30, seed: int = 46) -> List[Tuple[float, float]]:
    """Generate uniform random points across the wafer disc."""
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < n:
        x, y = rng.uniform(-0.95, 0.95, 2)
        if x**2 + y**2 <= 0.95**2:
            pts.append((float(x), float(y)))
    return pts


def get_benchmark_fixtures() -> InMemoryRepository:
    """Create a fully populated in-memory repository with benchmark test cases."""
    lots: List[Dict[str, Any]] = []
    process_steps: List[Dict[str, Any]] = []
    defects: List[Dict[str, Any]] = []
    ground_truth: List[Dict[str, Any]] = []

    # 1. Normal lots (LOT-0001 to LOT-0020)
    rng = np.random.default_rng(100)
    for i in range(1, 21):
        lid = f"LOT-{i:04d}"
        lots.append({
            "lot_id": lid,
            "product_id": "CHIP-3NM-A",
            "start_time": f"2026-09-01T{i:02d}:00:00",
            "fab_line": "FAB-EAST",
            "final_yield_pct": float(rng.uniform(94.0, 98.5)),
            "status": "completed",
        })
        # Litho step
        process_steps.append({
            "lot_id": lid,
            "step_name": "litho",
            "tool_id": "LITHO-02",
            "parameter_name": "focus_offset",
            "value": float(rng.normal(0.0, 0.05)),
            "spec_min": -0.20,
            "spec_max": 0.20,
            "timestamp": f"2026-09-01T{i:02d}:10:00",
        })
        # Etch step (nominal pressure around 50 mTorr)
        process_steps.append({
            "lot_id": lid,
            "step_name": "etch",
            "tool_id": "ETCH-07",
            "parameter_name": "chamber_pressure",
            "value": float(rng.normal(50.0, 1.2)),
            "spec_min": 45.0,
            "spec_max": 55.0,
            "timestamp": f"2026-09-01T{i:02d}:20:00",
        })
        # CVD step (nominal temp around 400 C)
        process_steps.append({
            "lot_id": lid,
            "step_name": "cvd",
            "tool_id": "CVD-03",
            "parameter_name": "deposition_temp",
            "value": float(rng.normal(400.0, 2.0)),
            "spec_min": 390.0,
            "spec_max": 410.0,
            "timestamp": f"2026-09-01T{i:02d}:30:00",
        })
        # CMP step
        process_steps.append({
            "lot_id": lid,
            "step_name": "cmp",
            "tool_id": "CMP-01",
            "parameter_name": "pad_downforce",
            "value": float(rng.normal(30.0, 0.8)),
            "spec_min": 25.0,
            "spec_max": 35.0,
            "timestamp": f"2026-09-01T{i:02d}:40:00",
        })

    # 2. Case 1: Etch Chamber Pressure Excursion (Edge-Ring)
    # LOT-2231 + cohort of 13 other lots (14 total affected lots)
    for i in range(1, 15):
        lid = f"LOT-{2230 + i}"
        is_target = (lid == "LOT-2231")
        lots.append({
            "lot_id": lid,
            "product_id": "CHIP-3NM-A",
            "start_time": f"2026-09-10T{i:02d}:00:00",
            "fab_line": "FAB-EAST",
            "final_yield_pct": float(rng.uniform(72.0, 83.0)),
            "status": "completed",
        })
        # Abnormal pressure on ETCH-07: ~56.5 to 58.2 (well above 55.0 spec max and > 3 sigma)
        val = 56.8 if is_target else float(rng.uniform(55.8, 58.0))
        process_steps.append({
            "lot_id": lid,
            "step_name": "etch",
            "tool_id": "ETCH-07",
            "parameter_name": "chamber_pressure",
            "value": val,
            "spec_min": 45.0,
            "spec_max": 55.0,
            "timestamp": f"2026-09-10T{i:02d}:20:00",
        })
        # Nominal other parameters
        process_steps.append({
            "lot_id": lid,
            "step_name": "litho",
            "tool_id": "LITHO-02",
            "parameter_name": "focus_offset",
            "value": float(rng.normal(0.01, 0.05)),
            "spec_min": -0.20,
            "spec_max": 0.20,
            "timestamp": f"2026-09-10T{i:02d}:10:00",
        })
        # Defects: edge-ring detected at etch
        edge_pts = generate_edge_ring_points(n=35, seed=200 + i)
        for idx, (x, y) in enumerate(edge_pts):
            defects.append({
                "lot_id": lid,
                "wafer_id": f"W-{lid}-01",
                "defect_type": "particle",
                "x": x,
                "y": y,
                "severity": "critical",
                "detected_at_step": "etch",
            })

        ground_truth.append({
            "lot_id": lid,
            "injected_cause_step": "etch",
            "injected_cause_tool_id": "ETCH-07",
            "injected_cause_parameter": "chamber_pressure",
            "injected_signature": "edge-ring",
        })

    # 3. Case 2: CMP Pad Downforce Scratch (LOT-2260)
    for i in range(1, 6):
        lid = f"LOT-{2260 + i}"
        lots.append({
            "lot_id": lid,
            "product_id": "CHIP-3NM-A",
            "start_time": f"2026-09-11T{i:02d}:00:00",
            "fab_line": "FAB-EAST",
            "final_yield_pct": float(rng.uniform(76.0, 84.0)),
            "status": "completed",
        })
        process_steps.append({
            "lot_id": lid,
            "step_name": "cmp",
            "tool_id": "CMP-01",
            "parameter_name": "pad_downforce",
            "value": 38.5,  # spec max is 35.0
            "spec_min": 25.0,
            "spec_max": 35.0,
            "timestamp": f"2026-09-11T{i:02d}:40:00",
        })
        # Scratches detected at CMP
        scratch_pts = generate_scratch_points(n=30, seed=300 + i)
        for idx, (x, y) in enumerate(scratch_pts):
            defects.append({
                "lot_id": lid,
                "wafer_id": f"W-{lid}-01",
                "defect_type": "scratch",
                "x": x,
                "y": y,
                "severity": "critical",
                "detected_at_step": "cmp",
            })
        ground_truth.append({
            "lot_id": lid,
            "injected_cause_step": "cmp",
            "injected_cause_tool_id": "CMP-01",
            "injected_cause_parameter": "pad_downforce",
            "injected_signature": "scratch",
        })

    # 4. Case 3: CVD Deposition Temperature Center-Cluster (LOT-2270)
    for i in range(1, 6):
        lid = f"LOT-{2270 + i}"
        lots.append({
            "lot_id": lid,
            "product_id": "CHIP-3NM-A",
            "start_time": f"2026-09-12T{i:02d}:00:00",
            "fab_line": "FAB-EAST",
            "final_yield_pct": float(rng.uniform(74.0, 82.0)),
            "status": "completed",
        })
        process_steps.append({
            "lot_id": lid,
            "step_name": "cvd",
            "tool_id": "CVD-03",
            "parameter_name": "deposition_temp",
            "value": 418.0,  # spec max is 410.0
            "spec_min": 390.0,
            "spec_max": 410.0,
            "timestamp": f"2026-09-12T{i:02d}:30:00",
        })
        center_pts = generate_center_cluster_points(n=40, seed=400 + i)
        for idx, (x, y) in enumerate(center_pts):
            defects.append({
                "lot_id": lid,
                "wafer_id": f"W-{lid}-01",
                "defect_type": "particle",
                "x": x,
                "y": y,
                "severity": "major",
                "detected_at_step": "cvd",
            })
        ground_truth.append({
            "lot_id": lid,
            "injected_cause_step": "cvd",
            "injected_cause_tool_id": "CVD-03",
            "injected_cause_parameter": "deposition_temp",
            "injected_signature": "center-cluster",
        })

    # 5. Case 4: In-progress lot exhibiting etch pressure drift (LOT-2245)
    lots.append({
        "lot_id": "LOT-2245",
        "product_id": "CHIP-3NM-A",
        "start_time": "2026-09-14T00:30:00",
        "fab_line": "FAB-EAST",
        "final_yield_pct": None,
        "status": "in_progress",
    })
    process_steps.append({
        "lot_id": "LOT-2245",
        "step_name": "etch",
        "tool_id": "ETCH-07",
        "parameter_name": "chamber_pressure",
        "value": 56.4,  # drifting matching LOT-2231 failure fingerprint
        "spec_min": 45.0,
        "spec_max": 55.0,
        "timestamp": "2026-09-14T00:45:00",
    })

    return InMemoryRepository(
        lots=lots,
        process_steps=process_steps,
        defects=defects,
        ground_truth_labels=ground_truth,
    )
