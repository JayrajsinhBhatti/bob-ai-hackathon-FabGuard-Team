"""Deterministic and explainable spatial signature classifier for wafer defect patterns.

Classifies wafer defect maps into:
- edge-ring
- center-cluster
- scratch
- donut
- random

Operates on normalized (x, y) coordinates in [-1, 1].
Uses geometric metrics: radial distribution, PCA linearity, and angular dispersion.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Dict, Any
import numpy as np


@dataclass
class SpatialConfig:
    """Configurable thresholds for spatial defect pattern classification."""
    min_points_for_structure: int = 4
    # Radial thresholds
    center_radius_max: float = 0.35
    donut_radius_min: float = 0.30
    donut_radius_max: float = 0.80
    edge_radius_min: float = 0.72
    # Ratio thresholds
    center_cluster_ratio_threshold: float = 0.48
    donut_ring_ratio_threshold: float = 0.55
    donut_center_max_ratio: float = 0.18
    edge_ring_ratio_threshold: float = 0.58
    edge_ring_center_max_ratio: float = 0.15
    # Scratch (linearity) thresholds
    scratch_pca_ratio_threshold: float = 0.88
    scratch_min_span: float = 0.35
    # Angular spread requirements
    min_angular_quadrants: int = 3


@dataclass
class SpatialClassificationResult:
    """Detailed result of spatial pattern classification."""
    signature: str
    confidence: float
    point_count: int
    diagnostics: Dict[str, Any]


def classify_spatial_signature(
    points: Sequence[Tuple[float, float]],
    config: Optional[SpatialConfig] = None,
) -> str:
    """Classify defect points into a spatial signature name.

    Returns:
        One of 'edge-ring', 'center-cluster', 'scratch', 'donut', 'random'.
    """
    result = analyze_spatial_signature(points, config)
    return result.signature


def analyze_spatial_signature(
    points: Sequence[Tuple[float, float]],
    config: Optional[SpatialConfig] = None,
) -> SpatialClassificationResult:
    """Perform detailed spatial analysis and classification on normalized coordinates.

    Args:
        points: Sequence of (x, y) coordinates normalized to [-1, 1].
        config: Optional SpatialConfig override.

    Returns:
        SpatialClassificationResult with signature, confidence, and geometric diagnostics.
    """
    cfg = config or SpatialConfig()
    
    # Filter valid coordinates
    valid_pts = []
    for pt in points:
        if pt is None or len(pt) < 2:
            continue
        x, y = float(pt[0]), float(pt[1])
        if not (np.isnan(x) or np.isnan(y)):
            valid_pts.append((x, y))

    n = len(valid_pts)
    if n < cfg.min_points_for_structure:
        return SpatialClassificationResult(
            signature="random",
            confidence=0.50,
            point_count=n,
            diagnostics={"reason": "insufficient_points_for_structure", "count": n},
        )

    coords = np.array(valid_pts, dtype=float)
    x = coords[:, 0]
    y = coords[:, 1]

    # Radial distance from center (0, 0)
    r = np.sqrt(x**2 + y**2)
    mean_r = float(np.mean(r))

    # Proportions in spatial zones
    center_mask = r <= cfg.center_radius_max
    center_ratio = float(np.mean(center_mask))

    edge_mask = r >= cfg.edge_radius_min
    edge_ratio = float(np.mean(edge_mask))

    donut_mask = (r >= cfg.donut_radius_min) & (r <= cfg.donut_radius_max)
    donut_ratio = float(np.mean(donut_mask))

    # Angular distribution (polar angle theta)
    theta = np.arctan2(y, x)  # [-pi, pi]
    quadrants = set(((theta + np.pi) / (np.pi / 2)).astype(int) % 4)
    angular_spread_count = len(quadrants)

    # Linearity / PCA analysis
    pca_ratio = 0.0
    span_major = 0.0
    if n >= 4:
        coords_centered = coords - np.mean(coords, axis=0)
        cov = np.cov(coords_centered, rowvar=False)
        if cov.ndim == 2:
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            idx = np.argsort(eigenvalues)[::-1]
            eigenvalues = np.maximum(eigenvalues[idx], 0.0)
            total_var = np.sum(eigenvalues)
            if total_var > 1e-12:
                pca_ratio = float(eigenvalues[0] / total_var)
                # Projection along major eigenvector
                proj_major = np.dot(coords_centered, eigenvectors[:, idx[0]])
                span_major = float(np.ptp(proj_major))

    diagnostics: Dict[str, Any] = {
        "point_count": n,
        "mean_radial_distance": round(mean_r, 4),
        "center_ratio": round(center_ratio, 4),
        "edge_ratio": round(edge_ratio, 4),
        "donut_ratio": round(donut_ratio, 4),
        "pca_linearity_ratio": round(pca_ratio, 4),
        "major_span": round(span_major, 4),
        "quadrant_coverage": angular_spread_count,
    }

    # 1. Scratch check: high linearity and elongated span across wafer
    if (
        pca_ratio >= cfg.scratch_pca_ratio_threshold
        and span_major >= cfg.scratch_min_span
        and (edge_ratio < 0.85 or angular_spread_count <= 2)
    ):
        conf = min(0.95, 0.65 + 0.30 * pca_ratio)
        return SpatialClassificationResult("scratch", conf, n, diagnostics)

    # 2. Edge-ring check: defects heavily concentrated near circumference with broad angular spread
    if (
        edge_ratio >= cfg.edge_ring_ratio_threshold
        and center_ratio <= cfg.edge_ring_center_max_ratio
        and angular_spread_count >= cfg.min_angular_quadrants
    ):
        conf = min(0.95, 0.60 + 0.35 * edge_ratio)
        return SpatialClassificationResult("edge-ring", conf, n, diagnostics)

    # 3. Center-cluster check: defects heavily clustered in central region
    if center_ratio >= cfg.center_cluster_ratio_threshold and edge_ratio <= 0.25:
        conf = min(0.95, 0.60 + 0.35 * center_ratio)
        return SpatialClassificationResult("center-cluster", conf, n, diagnostics)

    # 4. Donut check: intermediate ring concentration, hollow center, multi-quadrant spread
    if (
        donut_ratio >= cfg.donut_ring_ratio_threshold
        and center_ratio <= cfg.donut_center_max_ratio
        and edge_ratio <= 0.40
        and angular_spread_count >= cfg.min_angular_quadrants
    ):
        conf = min(0.95, 0.60 + 0.35 * donut_ratio)
        return SpatialClassificationResult("donut", conf, n, diagnostics)

    # Fallback to random if no distinct geometrical structure
    return SpatialClassificationResult(
        "random",
        confidence=0.70,
        point_count=n,
        diagnostics=diagnostics,
    )
