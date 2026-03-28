#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.features import AFMFeatureError, MapSummary, process_stp
from afm_lib.plot_utils import save_overlay
from afm_lib.stp_io import json_safe



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
        json_path.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")

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
        json.dumps(json_safe(aggregate), indent=2),
        encoding="utf-8",
    )

    print(json.dumps(json_safe(aggregate["aggregate"]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
