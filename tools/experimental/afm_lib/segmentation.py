from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def threshold_mask(z_rel: np.ndarray, sigma_factor: float = 2.0) -> tuple[np.ndarray, float, float]:
    """Threshold above baseline using the lower-half robust sigma estimate."""
    lower = z_rel[z_rel <= np.median(z_rel)]
    mad = np.median(np.abs(lower - np.median(lower)))
    robust_sigma = 1.4826 * mad if mad > 0 else float(np.std(z_rel))
    threshold = sigma_factor * robust_sigma
    mask = z_rel > threshold
    return mask, float(threshold), float(robust_sigma)


def clean_mask(mask: np.ndarray, min_pixels: int = 6) -> np.ndarray:
    """Apply the existing morphology cleanup and connected-component filtering."""
    mask = ndi.binary_opening(mask, structure=np.ones((2, 2)))
    mask = ndi.binary_closing(mask, structure=np.ones((2, 2)))
    labels, nlab = ndi.label(mask)
    if nlab == 0:
        return mask & False

    cleaned = np.zeros_like(mask, dtype=bool)
    counts = np.bincount(labels.ravel())
    for lab in range(1, len(counts)):
        if counts[lab] >= min_pixels:
            cleaned[labels == lab] = True
    return cleaned


def connected_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Return connected-component labels for a binary mask."""
    return ndi.label(mask)

