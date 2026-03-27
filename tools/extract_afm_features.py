#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage as ndi

from read_stp import load_stp


@dataclass
class IslandRecord:
    label: int
    area_px: int
    area_um2: float
    equivalent_radius_nm: float
    max_height_nm: float
    mean_height_nm: float
    volume_nm3: float
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
    number_density_per_um2: float
    equivalent_thickness_nm: float
    mean_island_height_nm: float
    mean_equivalent_radius_nm: float
    std_equivalent_radius_nm: float
    mean_volume_nm3: float


class AFMFeatureError(RuntimeError):
    pass


# ---------- helpers ----------

def level_rows(z: np.ndarray) -> np.ndarray:
    """Subtract row-wise medians to reduce scan-line offsets."""
    row_medians = np.median(z, axis=1, keepdims=True)
    return z - row_medians



def flatten_plane(z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit and subtract plane a*x + b*y + c."""
    rows, cols = z.shape
    yy, xx = np.indices((rows, cols))
    a = np.column_stack([xx.ravel(), yy.ravel(), np.ones(rows * cols)])
    coeffs, *_ = np.linalg.lstsq(a, z.ravel(), rcond=None)
    plane = (coeffs[0] * xx + coeffs[1] * yy + coeffs[2])
    return z - plane, coeffs



def estimate_baseline(z: np.ndarray, q: float = 0.30) -> float:
    """Baseline from lower quantile median."""
    cutoff = np.quantile(z, q)
    return float(np.median(z[z <= cutoff]))



def threshold_mask(z_rel: np.ndarray, sigma_factor: float = 2.0) -> tuple[np.ndarray, float, float]:
    """Threshold above baseline using lower-half robust sigma estimate."""
    lower = z_rel[z_rel <= np.median(z_rel)]
    mad = np.median(np.abs(lower - np.median(lower)))
    robust_sigma = 1.4826 * mad if mad > 0 else float(np.std(z_rel))
    thr = sigma_factor * robust_sigma
    mask = z_rel > thr
    return mask, float(thr), float(robust_sigma)



def clean_mask(mask: np.ndarray, min_pixels: int = 6) -> np.ndarray:
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



def extract_islands(z_rel: np.ndarray, mask: np.ndarray, dx_nm: float, dy_nm: float) -> list[IslandRecord]:
    labels, nlab = ndi.label(mask)
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
        eq_radius_nm = float(np.sqrt(area_nm2 / np.pi))
        vol_nm3 = float(np.sum(heights) * pixel_area_nm2)
        cy_px = float(np.mean(yy[sel]))
        cx_px = float(np.mean(xx[sel]))

        records.append(
            IslandRecord(
                label=lab,
                area_px=area_px,
                area_um2=float(area_nm2 / 1e6),
                equivalent_radius_nm=eq_radius_nm,
                max_height_nm=float(np.max(heights)),
                mean_height_nm=float(np.mean(heights)),
                volume_nm3=vol_nm3,
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
    mask: np.ndarray,
) -> MapSummary:
    scan_area_um2 = x_size_um * y_size_um
    coverage_fraction = float(np.count_nonzero(mask) / mask.size)
    total_volume_nm3 = float(sum(r.volume_nm3 for r in islands))
    total_scan_area_nm2 = scan_area_um2 * 1e6
    eq_thickness_nm = total_volume_nm3 / total_scan_area_nm2 if total_scan_area_nm2 > 0 else 0.0

    radii = np.array([r.equivalent_radius_nm for r in islands], dtype=float)
    heights = np.array([r.mean_height_nm for r in islands], dtype=float)
    vols = np.array([r.volume_nm3 for r in islands], dtype=float)

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
        number_density_per_um2=(len(islands) / scan_area_um2) if scan_area_um2 > 0 else 0.0,
        equivalent_thickness_nm=float(eq_thickness_nm),
        mean_island_height_nm=float(np.mean(heights)) if heights.size else 0.0,
        mean_equivalent_radius_nm=float(np.mean(radii)) if radii.size else 0.0,
        std_equivalent_radius_nm=float(np.std(radii)) if radii.size else 0.0,
        mean_volume_nm3=float(np.mean(vols)) if vols.size else 0.0,
    )



def process_stp(path: Path, sigma_factor: float, min_pixels: int) -> tuple[MapSummary, list[IslandRecord], dict[str, np.ndarray]]:
    stp = load_stp(path)
    z_raw = np.array(stp["z"], dtype=float)

    z_rows = level_rows(z_raw)
    z_flat, _ = flatten_plane(z_rows)
    z_smooth = ndi.gaussian_filter(z_flat, sigma=1.0)
    baseline = estimate_baseline(z_smooth)
    z_rel = z_smooth - baseline

    mask0, thr, robust_sigma = threshold_mask(z_rel, sigma_factor=sigma_factor)
    mask = clean_mask(mask0, min_pixels=min_pixels)

    dx_nm = float(stp["scan"].get("dx_nm"))
    dy_nm = float(stp["scan"].get("dy_nm"))
    x_size_um = float(stp["scan"]["x_size"])
    y_size_um = float(stp["scan"]["y_size"])

    islands = extract_islands(z_rel, mask, dx_nm=dx_nm, dy_nm=dy_nm)
    summary = build_summary(
        path=path,
        z=z_raw,
        x_size_um=x_size_um,
        y_size_um=y_size_um,
        dx_nm=dx_nm,
        dy_nm=dy_nm,
        baseline_nm=baseline,
        threshold_nm=thr,
        threshold_sigma=robust_sigma,
        islands=islands,
        mask=mask,
    )

    arrays = {
        "z_raw": z_raw,
        "z_rows": z_rows,
        "z_flat": z_flat,
        "z_rel": z_rel,
        "mask": mask.astype(np.uint8),
    }
    return summary, islands, arrays



def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    return obj



def save_overlay(out_png: Path, z_rel: np.ndarray, mask: np.ndarray, title: str) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(z_rel, origin="lower", cmap="viridis")
    ax.contour(mask, levels=[0.5], colors="r", linewidths=0.5, origin="lower")
    ax.set_title(title)
    ax.set_xlabel("pixel x")
    ax.set_ylabel("pixel y")
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Height above baseline (nm)")
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close(fig)



def main() -> int:
    parser = argparse.ArgumentParser(description="Extract basic AFM morphology features from .stp files")
    parser.add_argument("stp_files", nargs="+", type=Path, help="One or more .stp AFM files")
    parser.add_argument("--sigma-factor", type=float, default=2.0, help="Threshold = sigma_factor * robust_sigma")
    parser.add_argument("--min-pixels", type=int, default=6, help="Minimum connected-component size")
    parser.add_argument("--outdir", type=Path, default=Path("data/experimental/intermediate/afm_features"), help="Output directory")
    parser.add_argument("--save-overlay", action="store_true", help="Save overlay images with island contours")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    all_summaries: list[MapSummary] = []
    aggregate: dict[str, Any] = {"files": []}

    for stp_file in args.stp_files:
        summary, islands, arrays = process_stp(
            stp_file,
            sigma_factor=args.sigma_factor,
            min_pixels=args.min_pixels,
        )
        all_summaries.append(summary)

        stem = stp_file.stem.replace(" ", "_")
        payload = {
            "summary": asdict(summary),
            "islands": [asdict(r) for r in islands],
        }
        json_path = args.outdir / f"{stem}_features.json"
        json_path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")

        if args.save_overlay:
            save_overlay(
                args.outdir / f"{stem}_overlay.png",
                arrays["z_rel"],
                arrays["mask"].astype(bool),
                title=stp_file.name,
            )

        aggregate["files"].append(payload["summary"])

    if not all_summaries:
        raise AFMFeatureError("No files processed")

    def arr(field: str) -> np.ndarray:
        return np.array([getattr(s, field) for s in all_summaries], dtype=float)

    aggregate["aggregate"] = {
        "n_files": len(all_summaries),
        "coverage_fraction_mean": float(np.mean(arr("coverage_fraction"))),
        "coverage_fraction_std": float(np.std(arr("coverage_fraction"))),
        "equivalent_thickness_nm_mean": float(np.mean(arr("equivalent_thickness_nm"))),
        "equivalent_thickness_nm_std": float(np.std(arr("equivalent_thickness_nm"))),
        "mean_equivalent_radius_nm_mean": float(np.mean(arr("mean_equivalent_radius_nm"))),
        "mean_equivalent_radius_nm_std": float(np.std(arr("mean_equivalent_radius_nm"))),
        "number_density_per_um2_mean": float(np.mean(arr("number_density_per_um2"))),
        "number_density_per_um2_std": float(np.std(arr("number_density_per_um2"))),
        "island_count_mean": float(np.mean(arr("island_count"))),
        "island_count_std": float(np.std(arr("island_count"))),
    }

    (args.outdir / "aggregate_summary.json").write_text(
        json.dumps(_json_safe(aggregate), indent=2),
        encoding="utf-8",
    )

    print(json.dumps(_json_safe(aggregate["aggregate"]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
