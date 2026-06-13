#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.dataset import (  # noqa: E402
    gather_json_files,
    load_filtered_payload_records,
    normalize_suffix,
    write_csv,
    write_dat_lines,
)
from build_experimental_input import (  # noqa: E402
    EFFE_PROXY_CHOICES,
    GEOMETRY_CHOICES,
    RADIUS_PROXY_CHOICES,
    THICKNESS_PROXY_CHOICES,
    ExperimentalInputError,
    build_rows,
    gather_transmittance_summaries,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build solver-facing transmittance JSON models directly from AFM-derived "
            "morphology summaries. The JSON files contain theory/model parameters only; "
            "experimental paths are written only to the sidecar manifest."
        )
    )
    parser.add_argument("afm_inputs", nargs="*", type=Path)
    parser.add_argument("--include-suffixes", default="001,003")
    parser.add_argument(
        "--transmittance-dir",
        type=Path,
        default=Path("data/experimental/final/transmittance"),
    )
    parser.add_argument(
        "--radius-proxy",
        choices=RADIUS_PROXY_CHOICES,
        default="volume_equivalent_radius_nm",
    )
    parser.add_argument(
        "--effe-proxy",
        choices=EFFE_PROXY_CHOICES,
        default="hybrid_alpha50",
    )
    parser.add_argument(
        "--thickness-proxy",
        choices=THICKNESS_PROXY_CHOICES,
        default="equivalent_thickness_nm",
    )
    parser.add_argument("--geometry", choices=GEOMETRY_CHOICES, default="spheres")
    parser.add_argument(
        "--effective-medium-model",
        choices=("mg", "bruggeman", "mmgm"),
        default="mmgm",
    )
    parser.add_argument("--ito-thickness-nm", type=float, default=10.0)
    parser.add_argument("--glass-thickness-nm", type=float, default=1_100_000.0)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/input/experimental/transmittance_models"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/input/experimental/transmittance_models.dat"),
    )
    parser.add_argument(
        "--calculated-dir",
        type=Path,
        default=Path("data/output/transmittance"),
    )
    return parser.parse_args()


def calculated_spectrum_path(
    calculated_dir: Path, time_s: int, effective_medium_model: str, geometry: str
) -> Path:
    basename = f"silver_nanoisland_{time_s}s"
    use_legacy_name = effective_medium_model == "mmgm" and geometry == "spheres"
    suffix = ".dat" if use_legacy_name else f"__em={effective_medium_model}__geom={geometry}.dat"
    return calculated_dir / f"{basename}{suffix}"


def model_json_from_row(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    effective_medium: dict[str, Any] = {
        "model": args.effective_medium_model,
        "geometry": args.geometry,
        "filling_fraction": float(row["effe_proxy"]),
        "metal_material": "silverUNICALeV.dat",
        "host_material": "air",
    }

    if args.effective_medium_model == "mmgm":
        effective_medium["distribution"] = {
            "type": "two_lognormal",
            "rave_nm": float(row["afm_Rave_nm"]),
            "w1": float(row["mixture_weight_1"]),
            "muL1": float(row["muL1"]),
            "sigL1": float(row["sigL1"]),
            "w2": float(row["mixture_weight_2"]),
            "muL2": float(row["muL2"]),
            "sigL2": float(row["sigL2"]),
        }

    return {
        "wavelength_grid_nm": {
            "min": float(row["lamin_nm"]),
            "max": float(row["lamax_nm"]),
            "step": float(row["dlam_nm"]),
        },
        "stack": {
            "incident_medium": {"material": "air"},
            "layers": [
                {
                    "name": "nano_island_slab",
                    "kind": "effective_medium",
                    "thickness_nm": float(row["equivalent_thickness_nm"]),
                    "coherence": "coherent",
                    "effective_medium": effective_medium,
                },
                {
                    "name": "ITO",
                    "kind": "dielectric",
                    "thickness_nm": args.ito_thickness_nm,
                    "material": "itoUNICALeV.dat",
                    "coherence": "coherent",
                },
                {
                    "name": "glass",
                    "kind": "dielectric",
                    "thickness_nm": args.glass_thickness_nm,
                    "material": "glassUNICALeV.dat",
                    "coherence": "incoherent",
                },
            ],
            "exit_medium": {"material": "air"},
        },
    }


def write_manifest(rows: list[dict[str, Any]], dat_path: Path, csv_path: Path) -> None:
    fieldnames = [
        "time_s",
        "sample_label",
        "model_json",
        "experimental_dat",
        "calculated_dat",
        "experimental_lamin_nm",
        "experimental_lamax_nm",
    ]
    write_csv(rows, csv_path, fieldnames)
    header = "# " + " ".join(fieldnames) + "\n"
    lines = [
        (
            f"{row['time_s']} "
            f"{str(row['sample_label']).replace(' ', '_')} "
            f"{row['model_json']} "
            f"{row['experimental_dat']} "
            f"{row['calculated_dat']} "
            f"{float(row['experimental_lamin_nm']):.10g} "
            f"{float(row['experimental_lamax_nm']):.10g}\n"
        )
        for row in rows
    ]
    write_dat_lines(dat_path, header, lines)


def main() -> int:
    try:
        args = parse_args()
        suffixes = {normalize_suffix(s) for s in args.include_suffixes.split(",")}
        afm_files = gather_json_files(args.afm_inputs)
        afm_grouped = load_filtered_payload_records(afm_files, suffixes)
        transmittance = gather_transmittance_summaries(args.transmittance_dir)
        rows = build_rows(
            afm_grouped,
            transmittance,
            args.geometry,
            args.radius_proxy,
            args.effe_proxy,
            args.thickness_proxy,
        )

        args.outdir.mkdir(parents=True, exist_ok=True)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.calculated_dir.mkdir(parents=True, exist_ok=True)

        manifest_rows: list[dict[str, Any]] = []
        for row in rows:
            time_s = int(row["time_s"])
            model_json_path = args.outdir / f"{time_s}s.json"
            calculated_dat = calculated_spectrum_path(
                args.calculated_dir, time_s, args.effective_medium_model, args.geometry
            )
            model_json_path.write_text(
                json.dumps(model_json_from_row(row, args), indent=2) + "\n",
                encoding="utf-8",
            )
            manifest_rows.append(
                {
                    "time_s": time_s,
                    "sample_label": row["transmittance_label"],
                    "model_json": model_json_path.as_posix(),
                    "experimental_dat": row["transmittance_dat"],
                    "calculated_dat": calculated_dat.as_posix(),
                    "experimental_lamin_nm": row["lamin_nm"],
                    "experimental_lamax_nm": row["lamax_nm"],
                }
            )

        csv_path = args.manifest.with_suffix(".csv")
        write_manifest(manifest_rows, args.manifest, csv_path)
        print(f"Wrote: {args.outdir}")
        print(f"Wrote: {args.manifest}")
        print(f"Wrote: {csv_path}")
        return 0
    except ExperimentalInputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
