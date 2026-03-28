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
    group_summaries_by_time,
    mean_std,
    normalize_suffix,
    write_csv,
    write_dat_lines,
    write_gnuplot_script,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an aggregated AFM dataset from per-scan feature JSON files."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="Feature JSON files and/or directories containing them. If omitted, uses the default afm_batch tree.",
    )
    parser.add_argument(
        "--include-suffixes",
        default="001",
        help="Comma-separated scan suffixes to include (e.g. 001 or 001,003 or image). Default: 001",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/experimental/final"),
        help="Output directory for CSV, DAT, and gnuplot script.",
    )
    parser.add_argument(
        "--basename",
        default="afm_dataset",
        help="Base name for output files. Default: afm_dataset",
    )
    return parser.parse_args()


FIELDS = [
    "coverage_fraction",
    "equivalent_thickness_nm",
    "mean_equivalent_radius_nm",
    "std_equivalent_radius_nm",
    "number_density_per_um2",
    "island_count",
    "mean_island_height_nm",
]


def derived_reff_nm(coverage_fraction: float, number_density_per_um2: float) -> float:
    if number_density_per_um2 <= 0:
        return 0.0
    # sqrt(coverage / (pi * density)) gives a length in um
    return 1000.0 * ((coverage_fraction / (3.141592653589793 * number_density_per_um2)) ** 0.5)


def build_rows(grouped: dict[int, list[dict[str, float | str]]]) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, Any]] = []
    for time_s in sorted(grouped):
        entries = grouped[time_s]
        row: dict[str, Any] = {
            "time_s": time_s,
            "n_scans": len(entries),
            "sources": ";".join(sorted(e["_source"] for e in entries)),
        }
        for field in FIELDS:
            vals = [float(e[field]) for e in entries]
            mu, sigma = mean_std(vals)
            row[field] = mu
            row[f"{field}_std"] = sigma
        reff_vals = [
            derived_reff_nm(
                float(e["coverage_fraction"]),
                float(e["number_density_per_um2"]),
            )
            for e in entries
        ]
        reff_mu, reff_sigma = mean_std(reff_vals)
        row["derived_reff_nm"] = reff_mu
        row["derived_reff_nm_std"] = reff_sigma
        rows.append(row)
    return rows


CSV_FIELDNAMES = [
    "time_s",
    "n_scans",
    "sources",
    "coverage_fraction",
    "coverage_fraction_std",
    "equivalent_thickness_nm",
    "equivalent_thickness_nm_std",
    "mean_equivalent_radius_nm",
    "mean_equivalent_radius_nm_std",
    "std_equivalent_radius_nm",
    "std_equivalent_radius_nm_std",
    "number_density_per_um2",
    "number_density_per_um2_std",
    "derived_reff_nm",
    "derived_reff_nm_std",
    "island_count",
    "island_count_std",
    "mean_island_height_nm",
    "mean_island_height_nm_std",
]


def write_dat(rows: list[dict[str, Any]], path: Path) -> None:
    header = (
        "# time_s n_scans "
        "coverage coverage_std thickness_nm thickness_std "
        "mean_radius_nm mean_radius_std radius_sigma_nm radius_sigma_std "
        "density_um2 density_um2_std derived_reff_nm derived_reff_nm_std island_count island_count_std "
        "mean_height_nm mean_height_std\n"
    )
    lines = [
        (
            "{time_s} {n_scans} {coverage_fraction:.10g} {coverage_fraction_std:.10g} "
            "{equivalent_thickness_nm:.10g} {equivalent_thickness_nm_std:.10g} "
            "{mean_equivalent_radius_nm:.10g} {mean_equivalent_radius_nm_std:.10g} "
            "{std_equivalent_radius_nm:.10g} {std_equivalent_radius_nm_std:.10g} "
            "{number_density_per_um2:.10g} {number_density_per_um2_std:.10g} "
            "{derived_reff_nm:.10g} {derived_reff_nm_std:.10g} "
            "{island_count:.10g} {island_count_std:.10g} "
            "{mean_island_height_nm:.10g} {mean_island_height_nm_std:.10g}\n"
        ).format(**row)
        for row in rows
    ]
    write_dat_lines(path, header, lines)


GNUPLOT_TEMPLATE = r'''set terminal pngcairo size 1400,900
set output "{png_name}"

set multiplot layout 2,2 rowsfirst title "AFM morphology vs deposition time ({label})"

set style data yerrorlines
set grid
set key top left
set xlabel "Deposition time (s)"

# columns in .dat
# 1 time_s
# 3 coverage
# 4 coverage_std
# 5 thickness_nm
# 6 thickness_std
# 7 mean_radius_nm
# 8 mean_radius_std
# 11 density_um2
# 12 density_um2_std
# 13 derived_reff_nm
# 14 derived_reff_nm_std

set ylabel "Coverage fraction"
plot "{dat_name}" using 1:3:4 title "coverage"

set ylabel "Equivalent thickness (nm)"
plot "{dat_name}" using 1:5:6 title "thickness"

set ylabel "Mean equivalent radius (nm)"
plot "{dat_name}" using 1:7:8 title "mean radius"

set ylabel "Number density (1/um^2)"
plot "{dat_name}" using 1:11:12 title "density"

unset multiplot
'''


def main() -> int:
    args = parse_args()
    suffixes = {normalize_suffix(s) for s in args.include_suffixes.split(",")}

    files = gather_json_files(args.inputs)
    grouped = group_summaries_by_time(files, suffixes)
    label = "+".join(sorted(suffixes))
    rows = build_rows(grouped)

    args.outdir.mkdir(parents=True, exist_ok=True)
    csv_path = args.outdir / f"{args.basename}_{label}.csv"
    dat_path = args.outdir / f"{args.basename}_{label}.dat"
    gp_path = args.outdir / f"plot_{args.basename}_{label}.gp"
    png_name = f"{args.basename}_{label}.png"

    write_csv(rows, csv_path, CSV_FIELDNAMES)
    write_dat(rows, dat_path)
    write_gnuplot_script(gp_path, GNUPLOT_TEMPLATE, dat_path, png_name, label)

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {dat_path}")
    print(f"Wrote: {gp_path}")
    print("\nSuggested gnuplot run:")
    print(f"  cd {args.outdir} && gnuplot {gp_path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
