"""
Visual diagnostic tool for wafer defect spatial patterns.
Generates a side-by-side PNG plot of the 5 spatial defect signatures on wafer disks.

Usage:
    python -m data.plot_samples --output docs/wafer_defect_patterns.png
"""

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

from data.spatial_patterns import (
    generate_edge_ring,
    generate_center_cluster,
    generate_scratch,
    generate_donut,
    generate_random_background,
)


def plot_patterns(output_path: Path):
    patterns = [
        ("Edge-Ring (Etch)", generate_edge_ring(140), "#e74c3c"),
        ("Center-Cluster (Litho)", generate_center_cluster(120), "#3498db"),
        ("Scratch (CMP)", generate_scratch(130), "#e67e22"),
        ("Donut (CVD)", generate_donut(120), "#9b59b6"),
        ("Random Noise (Nominal)", generate_random_background(25), "#2ecc71"),
    ]

    fig, axes = plt.subplots(1, 5, figsize=(18, 3.8), facecolor="#1e1e24")

    # Polar circle outline for wafer edge
    theta = np.linspace(0, 2 * np.pi, 200)
    circle_x = np.cos(theta)
    circle_y = np.sin(theta)

    for ax, (title, points, color) in zip(axes, patterns):
        ax.set_facecolor("#121216")
        ax.plot(circle_x, circle_y, color="#555566", linestyle="--", linewidth=1.2, label="Wafer Edge")
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.scatter(xs, ys, s=18, color=color, alpha=0.85, edgecolors="none")

        ax.set_title(title, color="#ffffff", fontsize=11, fontweight="bold", pad=10)
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])

        for spine in ax.spines.values():
            spine.set_color("#333344")

    fig.suptitle("Bob Fab Copilot — Synthetic Wafer Defect Spatial Signatures", color="#ffffff", fontsize=13, y=1.02)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"[+] Saved spatial pattern diagnostic plot to {output_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Plot wafer defect patterns")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent / "docs" / "wafer_defect_patterns.png")
    args = parser.parse_args()
    plot_patterns(args.output)


if __name__ == "__main__":
    main()
