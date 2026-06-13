from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def plot_height_map(
    z: np.ndarray,
    *,
    x_size: float,
    y_size: float,
    x_unit: str,
    y_unit: str,
    z_unit: str,
    title: str,
) -> tuple[plt.Figure, plt.Axes]:
    """Render a standard AFM height map figure."""
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(
        z,
        cmap="viridis",
        origin="lower",
        extent=[0, x_size, 0, y_size],
        aspect="equal",
    )
    colorbar = plt.colorbar(image, ax=ax)
    colorbar.set_label(f"Height ({z_unit})")
    ax.set_xlabel(f"X ({x_unit})")
    ax.set_ylabel(f"Y ({y_unit})")
    ax.set_title(title)
    plt.tight_layout()
    return fig, ax


def save_overlay(out_png: Path, z_rel: np.ndarray, mask: np.ndarray, title: str) -> None:
    """Save a height-map overlay with mask contours."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(z_rel, origin="lower", cmap="viridis")
    ax.contour(mask, levels=[0.5], colors="r", linewidths=0.5, origin="lower")
    ax.set_title(title)
    ax.set_xlabel("pixel x")
    ax.set_ylabel("pixel y")
    colorbar = plt.colorbar(image, ax=ax)
    colorbar.set_label("Height above baseline (nm)")
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close(fig)
