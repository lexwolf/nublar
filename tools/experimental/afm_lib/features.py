from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .preprocess import estimate_baseline, flatten_plane, gaussian_smooth, level_rows
from .segmentation import clean_mask, connected_components, threshold_mask
from .stp_io import load_stp


@dataclass
class IslandRecord:
    label: int
    area_px: int
    area_um2: float
    equivalent_radius_nm: float
    min_height_nm: float
    p50_height_nm: float
    p95_height_nm: float
    height_range_nm: float
    max_height_nm: float
    mean_height_nm: float
    height_equivalent_radius_mean_nm: float
    height_equivalent_radius_p95_nm: float
    volume_nm3: float
    volume_equivalent_radius_nm: float
    centroid_x_um: float
    centroid_y_um: float


@dataclass
class HoleRecord:
    label: int
    area_px: int
    area_um2: float
    equivalent_radius_nm: float
    centroid_x_um: float
    centroid_y_um: float


@dataclass
class MapSummary:
    path: str
    rows: int
    cols: int
    x_size_um: float
    y_size_um: float
    dx_nm: float
    dy_nm: float
    z_min_nm: float
    z_max_nm: float
    z_mean_nm: float
    z_std_nm: float
    percentile_p01_nm: float
    percentile_p50_nm: float
    percentile_p99_nm: float
    baseline_nm: float
    threshold_nm: float
    threshold_sigma: float
    coverage_fraction: float
    island_count: int
    hole_count: int
    number_density_per_um2: float
    hole_number_density_per_um2: float
    equivalent_thickness_nm: float
    mean_island_height_nm: float
    mean_equivalent_radius_nm: float
    std_equivalent_radius_nm: float
    mean_hole_equivalent_radius_nm: float
    std_hole_equivalent_radius_nm: float
    mean_p95_height_nm: float
    mean_height_equivalent_radius_nm: float
    mean_p95_height_equivalent_radius_nm: float
    mean_volume_equivalent_radius_nm: float
    std_volume_equivalent_radius_nm: float
    mean_volume_nm3: float


class AFMFeatureError(RuntimeError):
    """Raised when AFM feature extraction fails."""


def equivalent_radius_nm_from_area(area_nm2: float) -> float:
    """Compute equivalent circular radius from area in nm^2."""
    return float(np.sqrt(area_nm2 / np.pi))


def equivalent_thickness_nm_from_volume(total_volume_nm3: float, total_scan_area_nm2: float) -> float:
    """Compute equivalent thickness from volume and scan area."""
    if total_scan_area_nm2 <= 0:
        return 0.0
    return float(total_volume_nm3 / total_scan_area_nm2)


def volume_equivalent_radius_nm_from_volume(volume_nm3: float) -> float:
    """Compute equal-volume sphere radius from island volume in nm^3."""
    if volume_nm3 <= 0.0:
        return 0.0
    return float(((3.0 * volume_nm3) / (4.0 * np.pi)) ** (1.0 / 3.0))


def sigma_geo_from_radii_nm(radii_nm: list[float]) -> float:
    """Geometric standard deviation of positive island radii."""
    clean = [r for r in radii_nm if r > 0.0]
    if len(clean) < 2:
        return 1.0
    logs = [math.log(r) for r in clean]
    return math.exp(float(np.std(logs)))


def extract_islands(
    z_rel: np.ndarray,
    mask: np.ndarray,
    dx_nm: float,
    dy_nm: float,
) -> list[IslandRecord]:
    """Extract per-island morphology from a processed height map and mask."""
    labels, nlab = connected_components(mask)
    if nlab == 0:
        return []

    records: list[IslandRecord] = []
    pixel_area_nm2 = dx_nm * dy_nm
    yy, xx = np.indices(z_rel.shape)

    for lab in range(1, nlab + 1):
        sel = labels == lab
        area_px = int(np.count_nonzero(sel))
        if area_px == 0:
            continue

        heights = z_rel[sel]
        area_nm2 = area_px * pixel_area_nm2
        vol_nm3 = float(np.sum(heights) * pixel_area_nm2)
        cy_px = float(np.mean(yy[sel]))
        cx_px = float(np.mean(xx[sel]))
        min_height_nm = float(np.min(heights))
        p50_height_nm = float(np.quantile(heights, 0.50))
        p95_height_nm = float(np.quantile(heights, 0.95))
        max_height_nm = float(np.max(heights))
        mean_height_nm = float(np.mean(heights))

        records.append(
            IslandRecord(
                label=lab,
                area_px=area_px,
                area_um2=float(area_nm2 / 1e6),
                equivalent_radius_nm=equivalent_radius_nm_from_area(area_nm2),
                min_height_nm=min_height_nm,
                p50_height_nm=p50_height_nm,
                p95_height_nm=p95_height_nm,
                height_range_nm=max_height_nm - min_height_nm,
                max_height_nm=max_height_nm,
                mean_height_nm=mean_height_nm,
                height_equivalent_radius_mean_nm=0.5 * mean_height_nm,
                height_equivalent_radius_p95_nm=0.5 * p95_height_nm,
                volume_nm3=vol_nm3,
                volume_equivalent_radius_nm=volume_equivalent_radius_nm_from_volume(vol_nm3),
                centroid_x_um=float(cx_px * dx_nm / 1000.0),
                centroid_y_um=float(cy_px * dy_nm / 1000.0),
            )
        )

    return records


def extract_holes(
    mask: np.ndarray,
    dx_nm: float,
    dy_nm: float,
    min_pixels: int,
) -> list[HoleRecord]:
    """Extract per-hole lateral morphology from the complement of the metal mask.

    Hole geometry is defined as interior connected components of the air phase,
    i.e. complement components that do not touch the image boundary. Boundary-touching
    complement regions correspond to the exterior/background rather than enclosed holes.
    """
    complement = ~mask
    labels, nlab = connected_components(complement)
    if nlab == 0:
        return []

    boundary_labels = set(np.unique(np.concatenate([
        labels[0, :],
        labels[-1, :],
        labels[:, 0],
        labels[:, -1],
    ])))
    boundary_labels.discard(0)

    pixel_area_nm2 = dx_nm * dy_nm
    yy, xx = np.indices(mask.shape)
    records: list[HoleRecord] = []

    for lab in range(1, nlab + 1):
        if lab in boundary_labels:
            continue

        sel = labels == lab
        area_px = int(np.count_nonzero(sel))
        if area_px < min_pixels:
            continue

        area_nm2 = area_px * pixel_area_nm2
        cy_px = float(np.mean(yy[sel]))
        cx_px = float(np.mean(xx[sel]))

        records.append(
            HoleRecord(
                label=lab,
                area_px=area_px,
                area_um2=float(area_nm2 / 1e6),
                equivalent_radius_nm=equivalent_radius_nm_from_area(area_nm2),
                centroid_x_um=float(cx_px * dx_nm / 1000.0),
                centroid_y_um=float(cy_px * dy_nm / 1000.0),
            )
        )

    return records


def build_summary(
    path: Path,
    z: np.ndarray,
    x_size_um: float,
    y_size_um: float,
    dx_nm: float,
    dy_nm: float,
    baseline_nm: float,
    threshold_nm: float,
    threshold_sigma: float,
    islands: list[IslandRecord],
    holes: list[HoleRecord],
    mask: np.ndarray,
) -> MapSummary:
    """Build the map-level AFM morphology summary."""
    scan_area_um2 = x_size_um * y_size_um
    coverage_fraction = float(np.count_nonzero(mask) / mask.size)
    total_volume_nm3 = float(sum(record.volume_nm3 for record in islands))
    total_scan_area_nm2 = scan_area_um2 * 1e6
    eq_thickness_nm = equivalent_thickness_nm_from_volume(total_volume_nm3, total_scan_area_nm2)

    radii = np.array([record.equivalent_radius_nm for record in islands], dtype=float)
    hole_radii = np.array([record.equivalent_radius_nm for record in holes], dtype=float)
    heights = np.array([record.mean_height_nm for record in islands], dtype=float)
    p95_heights = np.array([record.p95_height_nm for record in islands], dtype=float)
    height_equiv_radii = np.array(
        [record.height_equivalent_radius_mean_nm for record in islands],
        dtype=float,
    )
    p95_height_equiv_radii = np.array(
        [record.height_equivalent_radius_p95_nm for record in islands],
        dtype=float,
    )
    volume_equiv_radii = np.array(
        [record.volume_equivalent_radius_nm for record in islands],
        dtype=float,
    )
    volumes = np.array([record.volume_nm3 for record in islands], dtype=float)

    return MapSummary(
        path=str(path),
        rows=int(z.shape[0]),
        cols=int(z.shape[1]),
        x_size_um=float(x_size_um),
        y_size_um=float(y_size_um),
        dx_nm=float(dx_nm),
        dy_nm=float(dy_nm),
        z_min_nm=float(np.min(z)),
        z_max_nm=float(np.max(z)),
        z_mean_nm=float(np.mean(z)),
        z_std_nm=float(np.std(z)),
        percentile_p01_nm=float(np.quantile(z, 0.01)),
        percentile_p50_nm=float(np.quantile(z, 0.50)),
        percentile_p99_nm=float(np.quantile(z, 0.99)),
        baseline_nm=float(baseline_nm),
        threshold_nm=float(threshold_nm),
        threshold_sigma=float(threshold_sigma),
        coverage_fraction=coverage_fraction,
        island_count=len(islands),
        hole_count=len(holes),
        number_density_per_um2=(len(islands) / scan_area_um2) if scan_area_um2 > 0 else 0.0,
        hole_number_density_per_um2=(len(holes) / scan_area_um2) if scan_area_um2 > 0 else 0.0,
        equivalent_thickness_nm=eq_thickness_nm,
        mean_island_height_nm=float(np.mean(heights)) if heights.size else 0.0,
        mean_equivalent_radius_nm=float(np.mean(radii)) if radii.size else 0.0,
        std_equivalent_radius_nm=float(np.std(radii)) if radii.size else 0.0,
        mean_hole_equivalent_radius_nm=float(np.mean(hole_radii)) if hole_radii.size else 0.0,
        std_hole_equivalent_radius_nm=float(np.std(hole_radii)) if hole_radii.size else 0.0,
        mean_p95_height_nm=float(np.mean(p95_heights)) if p95_heights.size else 0.0,
        mean_height_equivalent_radius_nm=float(np.mean(height_equiv_radii)) if height_equiv_radii.size else 0.0,
        mean_p95_height_equivalent_radius_nm=float(np.mean(p95_height_equiv_radii))
        if p95_height_equiv_radii.size else 0.0,
        mean_volume_equivalent_radius_nm=float(np.mean(volume_equiv_radii))
        if volume_equiv_radii.size else 0.0,
        std_volume_equivalent_radius_nm=float(np.std(volume_equiv_radii))
        if volume_equiv_radii.size else 0.0,
        mean_volume_nm3=float(np.mean(volumes)) if volumes.size else 0.0,
    )


def process_stp(
    path: Path,
    sigma_factor: float,
    min_pixels: int,
) -> tuple[MapSummary, list[IslandRecord], list[HoleRecord], dict[str, np.ndarray]]:
    """Run the current AFM feature pipeline on one STP file."""
    stp = load_stp(path)
    z_raw = np.array(stp["z"], dtype=float)

    z_rows = level_rows(z_raw)
    z_flat, _ = flatten_plane(z_rows)
    z_smooth = gaussian_smooth(z_flat, sigma=1.0)
    baseline = estimate_baseline(z_smooth)
    z_rel = z_smooth - baseline

    mask0, threshold_nm, threshold_sigma = threshold_mask(z_rel, sigma_factor=sigma_factor)
    mask = clean_mask(mask0, min_pixels=min_pixels)

    dx_nm = float(stp["scan"].get("dx_nm"))
    dy_nm = float(stp["scan"].get("dy_nm"))
    x_size_um = float(stp["scan"]["x_size"])
    y_size_um = float(stp["scan"]["y_size"])

    islands = extract_islands(z_rel, mask, dx_nm=dx_nm, dy_nm=dy_nm)
    holes = extract_holes(mask, dx_nm=dx_nm, dy_nm=dy_nm, min_pixels=min_pixels)
    summary = build_summary(
        path=path,
        z=z_raw,
        x_size_um=x_size_um,
        y_size_um=y_size_um,
        dx_nm=dx_nm,
        dy_nm=dy_nm,
        baseline_nm=baseline,
        threshold_nm=threshold_nm,
        threshold_sigma=threshold_sigma,
        islands=islands,
        holes=holes,
        mask=mask,
    )

    arrays = {
        "z_raw": z_raw,
        "z_rows": z_rows,
        "z_flat": z_flat,
        "z_rel": z_rel,
        "mask": mask.astype(np.uint8),
    }
    return summary, islands, holes, arrays
