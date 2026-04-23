from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def level_rows(z: np.ndarray) -> np.ndarray:
    """Subtract row-wise medians to reduce scan-line offsets."""
    row_medians = np.median(z, axis=1, keepdims=True)
    return z - row_medians


def flatten_plane(z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit and subtract plane a*x + b*y + c."""
    rows, cols = z.shape
    yy, xx = np.indices((rows, cols))
    design = np.column_stack([xx.ravel(), yy.ravel(), np.ones(rows * cols)])
    coeffs, *_ = np.linalg.lstsq(design, z.ravel(), rcond=None)
    plane = coeffs[0] * xx + coeffs[1] * yy + coeffs[2]
    return z - plane, coeffs


def gaussian_smooth(z: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Apply the same Gaussian smoothing used by the current AFM pipeline."""
    return ndi.gaussian_filter(z, sigma=sigma)


def estimate_baseline(z: np.ndarray, q: float = 0.30) -> float:
    """Estimate a baseline from the lower-quantile median."""
    cutoff = np.quantile(z, q)
    return float(np.median(z[z <= cutoff]))

