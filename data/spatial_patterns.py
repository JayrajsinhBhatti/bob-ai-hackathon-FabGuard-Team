"""
Spatial Defect Coordinate Generators for Semiconductor Wafer Inspection.
Generates realistic normalized (x, y) coordinates on the wafer unit disk (x^2 + y^2 <= 1.0).

Signatures supported:
- 'edge-ring': Concentrated ring near the wafer bevel / exclusion zone (r in [0.80, 0.98])
- 'center-cluster': Dense cluster centered around wafer origin (r <= 0.40)
- 'scratch': Linear abrasive track across the wafer with lateral jitter
- 'donut': Mid-radius annular defect band (r in [0.45, 0.70])
- 'random': Uniformly distributed Poisson noise across wafer surface
"""

import math
import random
from typing import List, Tuple, Dict, Any

MAX_WAFER_RADIUS = 0.98  # Safe physical wafer margin (excludes bevel edge)


def _polar_to_cartesian(r: float, theta: float) -> Tuple[float, float]:
    """Convert polar coordinates (r, theta) to Cartesian (x, y)."""
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return round(x, 4), round(y, 4)


def generate_random_background(n_points: int) -> List[Tuple[float, float]]:
    """Generate uniform Poisson-like random defects over the circular wafer disk."""
    points = []
    for _ in range(n_points):
        # Uniform sampling on a disk: r = R * sqrt(u), theta in [0, 2pi)
        u = random.random()
        r = MAX_WAFER_RADIUS * math.sqrt(u)
        theta = random.uniform(0, 2 * math.pi)
        points.append(_polar_to_cartesian(r, theta))
    return points


def generate_edge_ring(n_points: int, background_ratio: float = 0.10) -> List[Tuple[float, float]]:
    """
    Generate edge-ring pattern: defects concentrated along the wafer perimeter.
    Common in plasma etch non-uniformity, edge-exclusion clamps, or chamber seal leaks.
    """
    n_bg = int(n_points * background_ratio)
    n_pattern = n_points - n_bg
    points = generate_random_background(n_bg)

    for _ in range(n_pattern):
        # Sample radius using a skewed distribution concentrated between 0.80 and 0.98
        # Beta distribution with alpha=7, beta=1.5
        r_norm = random.betavariate(7.0, 1.5)
        r = 0.78 + (MAX_WAFER_RADIUS - 0.78) * r_norm
        theta = random.uniform(0, 2 * math.pi)
        points.append(_polar_to_cartesian(r, theta))
    return points


def generate_center_cluster(n_points: int, background_ratio: float = 0.10) -> List[Tuple[float, float]]:
    """
    Generate center-cluster pattern: dense concentration at the center of the wafer.
    Common in lithography lens heating/focus aberration, spin-coat puddle defects.
    """
    n_bg = int(n_points * background_ratio)
    n_pattern = n_points - n_bg
    points = generate_random_background(n_bg)

    for _ in range(n_pattern):
        # Half-normal distribution centered at 0 with small variance
        r = min(abs(random.gauss(0, 0.14)), 0.45)
        theta = random.uniform(0, 2 * math.pi)
        points.append(_polar_to_cartesian(r, theta))
    return points


def generate_scratch(n_points: int, background_ratio: float = 0.08) -> List[Tuple[float, float]]:
    """
    Generate linear scratch pattern: abrasive line across the wafer with micro-jitter.
    Common in CMP pad diamond dresser dislodgement or robotic wafer handling damage.
    """
    n_bg = int(n_points * background_ratio)
    n_pattern = n_points - n_bg
    points = generate_random_background(n_bg)

    # Random line segment across disk: angle alpha and offset distance d
    alpha = random.uniform(0, math.pi)
    d = random.uniform(-0.4, 0.4)
    # Unit normal vector (cos alpha, sin alpha), direction vector (-sin alpha, cos alpha)
    nx, ny = math.cos(alpha), math.sin(alpha)
    dx, dy = -math.sin(alpha), math.cos(alpha)

    # Base point along normal
    bx, by = d * nx, d * ny

    # Length along line segment within unit circle:
    # (bx + t*dx)^2 + (by + t*dy)^2 <= R^2 => d^2 + t^2 <= R^2 => |t| <= sqrt(R^2 - d^2)
    max_t = math.sqrt(max(0.01, MAX_WAFER_RADIUS**2 - d**2))

    for _ in range(n_pattern):
        t = random.uniform(-max_t * 0.95, max_t * 0.95)
        jitter = random.gauss(0, 0.018)  # slight width of scratch
        x = bx + t * dx + jitter * nx
        y = by + t * dy + jitter * ny

        # Ensure inside wafer disk
        r = math.sqrt(x * x + y * y)
        if r > MAX_WAFER_RADIUS:
            x *= (MAX_WAFER_RADIUS - 0.01) / r
            y *= (MAX_WAFER_RADIUS - 0.01) / r
        points.append((round(x, 4), round(y, 4)))

    return points


def generate_donut(n_points: int, background_ratio: float = 0.10) -> List[Tuple[float, float]]:
    """
    Generate donut (annular) pattern: circular defect ring midway between center and edge.
    Common in CVD heating coil multi-zone temperature gradients or gas showerhead non-uniformity.
    """
    n_bg = int(n_points * background_ratio)
    n_pattern = n_points - n_bg
    points = generate_random_background(n_bg)

    for _ in range(n_pattern):
        # Gaussian distribution centered at radius ~0.58 with small std dev
        r = random.gauss(0.58, 0.045)
        r = max(0.42, min(0.72, r))
        theta = random.uniform(0, 2 * math.pi)
        points.append(_polar_to_cartesian(r, theta))
    return points


def generate_spatial_defects(
    signature: str,
    total_defects: int,
    defect_type_weights: Dict[str, float],
    step_detected: str,
    lot_id: str,
    wafer_id: str,
) -> List[Dict[str, Any]]:
    """
    Master dispatcher for generating a list of defect records for a specific wafer.
    Returns defect records ready for insertion into the 'defects' table.
    """
    if signature == "edge-ring":
        coords = generate_edge_ring(total_defects)
    elif signature == "center-cluster":
        coords = generate_center_cluster(total_defects)
    elif signature == "scratch":
        coords = generate_scratch(total_defects)
    elif signature == "donut":
        coords = generate_donut(total_defects)
    else:
        coords = generate_random_background(total_defects)

    types = list(defect_type_weights.keys())
    weights = list(defect_type_weights.values())

    defect_records = []
    for x, y in coords:
        d_type = random.choices(types, weights=weights, k=1)[0]

        # Severity assignment: scratches and large clusters are higher severity
        r_sq = x * x + y * y
        if d_type == "scratch":
            severity = random.choices(["critical", "major", "minor"], weights=[0.55, 0.35, 0.10], k=1)[0]
        elif signature in ("edge-ring", "center-cluster", "donut") and (r_sq > 0.65 or r_sq < 0.09):
            severity = random.choices(["critical", "major", "minor"], weights=[0.30, 0.50, 0.20], k=1)[0]
        else:
            severity = random.choices(["critical", "major", "minor"], weights=[0.10, 0.40, 0.50], k=1)[0]

        defect_records.append({
            "lot_id": lot_id,
            "wafer_id": wafer_id,
            "defect_type": d_type,
            "x": x,
            "y": y,
            "severity": severity,
            "detected_at_step": step_detected,
        })

    return defect_records
