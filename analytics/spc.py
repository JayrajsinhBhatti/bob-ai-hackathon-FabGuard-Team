"""Statistical Process Control (SPC) Engine for Semiconductor Manufacturing.

Implements:
- Cpk and Ppk process capability calculations
- Cpk < 1.33 out-of-capability flag
- Western Electric rules violation detection (Rules 1-4)
- Safe handling of zero variance, small sample sizes, and missing spec limits
- Grouped parameter-level SPC analysis
"""

from typing import List, Optional, Sequence, Tuple
import numpy as np

from analytics.models import SPCResult, WesternElectricViolations


def calculate_cpk(
    values: Sequence[float],
    spec_min: Optional[float],
    spec_max: Optional[float],
    subgroup_size: int = 1,
) -> Optional[float]:
    """Calculate Process Capability Index (Cpk).

    Formula:
        Cpu = (USL - mean) / (3 * sigma)
        Cpl = (mean - LSL) / (3 * sigma)
        Cpk = min(Cpu, Cpl)

    Handles single-sided specifications, zero standard deviation,
    missing specification limits, and sample sizes < 2 safely.
    """
    clean_vals = [v for v in values if v is not None and not np.isnan(v)]
    if len(clean_vals) < 2:
        return None

    if spec_min is None and spec_max is None:
        return None

    mean = float(np.mean(clean_vals))
    std = float(np.std(clean_vals, ddof=1))

    if std <= 1e-12:
        # Zero variance: if within specs, process is strictly capable, but standard Cpk is undefined
        # Return high value if centered inside specs, 0.0 if outside
        if spec_min is not None and mean < spec_min:
            return 0.0
        if spec_max is not None and mean > spec_max:
            return 0.0
        return 9.99  # Safe representative capability when variance is zero inside limits

    cp_u = (spec_max - mean) / (3.0 * std) if spec_max is not None else None
    cp_l = (mean - spec_min) / (3.0 * std) if spec_min is not None else None

    if cp_u is not None and cp_l is not None:
        return float(min(cp_u, cp_l))
    elif cp_u is not None:
        return float(cp_u)
    elif cp_l is not None:
        return float(cp_l)
    return None


def calculate_ppk(
    values: Sequence[float],
    spec_min: Optional[float],
    spec_max: Optional[float],
) -> Optional[float]:
    """Calculate Process Performance Index (Ppk) using overall sample standard deviation."""
    # In overall batch samples, Ppk calculation mirrors Cpk with sample standard deviation (ddof=1)
    return calculate_cpk(values, spec_min, spec_max)


def is_out_of_capability(cpk: Optional[float], threshold: float = 1.33) -> bool:
    """Check if process parameter Cpk indicates out-of-capability (standard: Cpk < 1.33)."""
    if cpk is None:
        return False
    return cpk < threshold


def detect_western_electric_violations(
    values: Sequence[float],
    mean: Optional[float] = None,
    std_dev: Optional[float] = None,
) -> WesternElectricViolations:
    """Detect Western Electric rules violations along a chronological sequence of observations.

    Rules implemented:
    - Rule 1: 1 point beyond ±3σ from center line
    - Rule 2: 2 of 3 consecutive points beyond ±2σ on the same side of center line
    - Rule 3: 4 of 5 consecutive points beyond ±1σ on the same side of center line
    - Rule 4: 8 consecutive points on the same side of center line

    Returns:
        WesternElectricViolations with indices of violating observation points.
    """
    clean_vals = [float(v) for v in values if v is not None and not np.isnan(v)]
    n = len(clean_vals)

    if n < 1:
        return WesternElectricViolations()

    calc_mean = float(np.mean(clean_vals)) if mean is None else float(mean)
    calc_std = (
        float(np.std(clean_vals, ddof=1))
        if std_dev is None
        else float(std_dev)
    )

    if calc_std <= 1e-12:
        calc_std = 1e-6  # avoid division by zero

    # Calculate z-scores for all points
    z_scores = [(x - calc_mean) / calc_std for x in clean_vals]

    r1: List[int] = []
    r2: List[int] = []
    r3: List[int] = []
    r4: List[int] = []

    for i in range(n):
        z = z_scores[i]

        # Rule 1: One point beyond 3 sigma
        if abs(z) > 3.0:
            r1.append(i)

        # Rule 2: 2 out of 3 consecutive points beyond 2 sigma on same side
        if i >= 2:
            window = z_scores[i - 2 : i + 1]
            # upper side
            if sum(1 for w in window if w > 2.0) >= 2:
                r2.append(i)
            # lower side
            elif sum(1 for w in window if w < -2.0) >= 2:
                r2.append(i)

        # Rule 3: 4 out of 5 consecutive points beyond 1 sigma on same side
        if i >= 4:
            window = z_scores[i - 4 : i + 1]
            if sum(1 for w in window if w > 1.0) >= 4:
                r3.append(i)
            elif sum(1 for w in window if w < -1.0) >= 4:
                r3.append(i)

        # Rule 4: 8 consecutive points on same side of center line (z > 0 or z < 0)
        if i >= 7:
            window = z_scores[i - 7 : i + 1]
            if all(w > 0.0 for w in window):
                r4.append(i)
            elif all(w < 0.0 for w in window):
                r4.append(i)

    return WesternElectricViolations(
        rule1_beyond_3sigma=sorted(list(set(r1))),
        rule2_two_of_three_beyond_2sigma=sorted(list(set(r2))),
        rule3_four_of_five_beyond_1sigma=sorted(list(set(r3))),
        rule4_eight_on_one_side=sorted(list(set(r4))),
    )


def analyze_parameter_series(
    step: str,
    tool_id: str,
    parameter: str,
    values: Sequence[float],
    spec_min: Optional[float] = None,
    spec_max: Optional[float] = None,
) -> SPCResult:
    """Perform full SPC analysis on a sequence of chronological parameter readings.

    Returns structured SPCResult.
    """
    clean_vals = [float(v) for v in values if v is not None and not np.isnan(v)]
    n = len(clean_vals)

    if n == 0:
        return SPCResult(
            step=step,
            tool_id=tool_id,
            parameter=parameter,
            mean=0.0,
            std_dev=0.0,
            sample_size=0,
            spec_min=spec_min,
            spec_max=spec_max,
            cpk=None,
            ppk=None,
            is_out_of_capability=False,
            violations=WesternElectricViolations(),
            latest_z_score=0.0,
            latest_value=0.0,
        )

    mean = float(np.mean(clean_vals))
    std = float(np.std(clean_vals, ddof=1)) if n > 1 else 0.0

    cpk = calculate_cpk(clean_vals, spec_min, spec_max)
    ppk = calculate_ppk(clean_vals, spec_min, spec_max)
    out_of_cap = is_out_of_capability(cpk, threshold=1.33)
    violations = detect_western_electric_violations(clean_vals, mean=mean, std_dev=std)

    latest_val = clean_vals[-1]
    latest_z = (latest_val - mean) / std if std > 1e-12 else 0.0

    return SPCResult(
        step=step,
        tool_id=tool_id,
        parameter=parameter,
        mean=mean,
        std_dev=std,
        sample_size=n,
        spec_min=spec_min,
        spec_max=spec_max,
        cpk=cpk,
        ppk=ppk,
        is_out_of_capability=out_of_cap,
        violations=violations,
        latest_z_score=latest_z,
        latest_value=latest_val,
    )
