#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.dataset import (
    gather_json_files,
    gnuplot_dir_for_data_dir,
    image_dir_for_data_dir,
    load_filtered_payload_records,
    mean_std,
    normalize_suffix,
    write_csv,
    write_dat_lines,
    write_gnuplot_script,
)
from afm_lib.features import sigma_geo_from_radii_nm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build AFM -> EMT input table from per-scan AFM feature JSON files."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help=(
            "Feature JSON files and/or directories containing them. "
            "If omitted, uses data/experimental/intermediate/afm_batch."
        ),
    )
    parser.add_argument(
        "--include-suffixes",
        default="001,003",
        help=(
            "Comma-separated scan suffixes to include: 001,002,003,image "
            "(default: 001,003)"
        ),
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/experimental/final/afm"),
        help="Data output directory for CSV and DAT files (default: data/experimental/final/afm)",
    )
    parser.add_argument(
        "--basename",
        default="afm_to_emt_input",
        help="Base name for output files (default: afm_to_emt_input)",
    )
    return parser.parse_args()


def build_rows(grouped: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for time_s in sorted(grouped):
        entries = grouped[time_s]

        coverage_vals = [float(e["summary"]["coverage_fraction"]) for e in entries]
        rave_vals = [float(e["summary"]["mean_equivalent_radius_nm"]) for e in entries]
        sigma_geo_vals = [
            sigma_geo_from_radii_nm(
                [
                    float(record["equivalent_radius_nm"])
                    for record in e["islands"]
                    if float(record["equivalent_radius_nm"]) > 0.0
                ]
            )
            for e in entries
        ]
        thickness_vals = [float(e["summary"]["equivalent_thickness_nm"]) for e in entries]
        density_vals = [float(e["summary"]["number_density_per_um2"]) for e in entries]
        height_vals = [float(e["summary"]["mean_island_height_nm"]) for e in entries]

        coverage_mu, coverage_std = mean_std(coverage_vals)
        rave_mu, rave_std = mean_std(rave_vals)
        sg_mu, sg_std = mean_std(sigma_geo_vals)
        thick_mu, thick_std = mean_std(thickness_vals)
        dens_mu, dens_std = mean_std(density_vals)
        h_mu, h_std = mean_std(height_vals)

        row = {
            "time_s": time_s,
            "n_scans": len(entries),
            "sources": ";".join(sorted(e["_source"] for e in entries)),
            "coverage_fraction": coverage_mu,
            "coverage_fraction_std": coverage_std,
            "Rave_nm": rave_mu,
            "Rave_nm_std": rave_std,
            "sigma_geo_radius": sg_mu,
            "sigma_geo_radius_std": sg_std,
            "equivalent_thickness_nm": thick_mu,
            "equivalent_thickness_nm_std": thick_std,
            "number_density_per_um2": dens_mu,
            "number_density_per_um2_std": dens_std,
            "mean_island_height_nm": h_mu,
            "mean_island_height_nm_std": h_std,
        }
        rows.append(row)

    return rows


CSV_FIELDNAMES = [
    "time_s",
    "n_scans",
    "sources",
    "coverage_fraction",
    "coverage_fraction_std",
    "Rave_nm",
    "Rave_nm_std",
    "sigma_geo_radius",
    "sigma_geo_radius_std",
    "equivalent_thickness_nm",
    "equivalent_thickness_nm_std",
    "number_density_per_um2",
    "number_density_per_um2_std",
    "mean_island_height_nm",
    "mean_island_height_nm_std",
]


def write_dat(rows: list[dict[str, Any]], path: Path) -> None:
    header = (
        "# time_s n_scans "
        "coverage coverage_std "
        "Rave_nm Rave_nm_std "
        "sigma_geo sigma_geo_std "
        "eq_thickness_nm eq_thickness_nm_std "
        "density_um2 density_um2_std "
        "mean_height_nm mean_height_nm_std\n"
    )
    lines = [
        (
            "{time_s} {n_scans} "
            "{coverage_fraction:.10g} {coverage_fraction_std:.10g} "
            "{Rave_nm:.10g} {Rave_nm_std:.10g} "
            "{sigma_geo_radius:.10g} {sigma_geo_radius_std:.10g} "
            "{equivalent_thickness_nm:.10g} {equivalent_thickness_nm_std:.10g} "
            "{number_density_per_um2:.10g} {number_density_per_um2_std:.10g} "
            "{mean_island_height_nm:.10g} {mean_island_height_nm_std:.10g}\n"
        ).format(**row)
        for row in rows
    ]
    write_dat_lines(path, header, lines)


GNUPLOT_TEMPLATE = r'''set terminal pngcairo size 1400,900
set output "{png_name}"

set multiplot layout 2,2 rowsfirst title "AFM -> EMT inputs ({label})"

set style data yerrorlines
set grid
set key top left
set xlabel "Deposition time (s)"

# columns in .dat
# 1  time_s
# 2  n_scans
# 3  coverage
# 4  coverage_std
# 5  Rave_nm
# 6  Rave_nm_std
# 7  sigma_geo
# 8  sigma_geo_std
# 9  eq_thickness_nm
# 10 eq_thickness_nm_std
# 11 density_um2
# 12 density_um2_std
# 13 mean_height_nm
# 14 mean_height_nm_std

set ylabel "Coverage fraction"
plot "{dat_name}" using 1:3:4 title "coverage"

set ylabel "Rave (nm)"
plot "{dat_name}" using 1:5:6 title "Rave"

set ylabel "sigma_geo"
plot "{dat_name}" using 1:7:8 title "sigma_geo"

set ylabel "Equivalent thickness (nm)"
plot "{dat_name}" using 1:9:10 title "eq thickness"

unset multiplot
'''


def main() -> int:
    args = parse_args()
    suffixes = {normalize_suffix(s) for s in args.include_suffixes.split(",")}

    files = gather_json_files(args.inputs)
    grouped = load_filtered_payload_records(files, suffixes)
    rows = build_rows(grouped)

    label = "+".join(sorted(suffixes))

    args.outdir.mkdir(parents=True, exist_ok=True)
    img_dir = image_dir_for_data_dir(args.outdir)
    gp_dir = gnuplot_dir_for_data_dir(args.outdir)
    csv_path = args.outdir / f"{args.basename}_{label}.csv"
    dat_path = args.outdir / f"{args.basename}_{label}.dat"
    gp_path = gp_dir / f"plot_{args.basename}_{label}.gp"
    png_path = img_dir / f"{args.basename}_{label}.png"

    write_csv(rows, csv_path, CSV_FIELDNAMES)
    write_dat(rows, dat_path)
    write_gnuplot_script(gp_path, GNUPLOT_TEMPLATE, dat_path, png_path.as_posix(), label)

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {dat_path}")
    print(f"Wrote: {png_path} (via gnuplot)")
    print(f"Wrote: {gp_path}")
    print("\nSuggested gnuplot run:")
    print(f"  gnuplot {gp_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
