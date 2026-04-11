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
from afm_lib.distribution_fit import fit_two_lognormal_mixture
from afm_lib.features import sigma_geo_from_radii_nm

RADIUS_PROXY_CHOICES = (
    "equivalent_radius_nm",
    "volume_equivalent_radius_nm",
    "height_equivalent_radius_mean_nm",
    "height_equivalent_radius_p95_nm",
)
SUMMARY_FIELD_FOR_RADIUS_PROXY = {
    "equivalent_radius_nm": "mean_equivalent_radius_nm",
    "volume_equivalent_radius_nm": "mean_volume_equivalent_radius_nm",
    "height_equivalent_radius_mean_nm": "mean_height_equivalent_radius_nm",
    "height_equivalent_radius_p95_nm": "mean_p95_height_equivalent_radius_nm",
}


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
        "--radius-proxy",
        choices=RADIUS_PROXY_CHOICES,
        default="volume_equivalent_radius_nm",
        help=(
            "Per-island radius proxy used for the two-lognormal fit and exported Rave "
            "(default: volume_equivalent_radius_nm)"
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


def build_rows(
    grouped: dict[int, list[dict[str, Any]]],
    radius_proxy: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for time_s in sorted(grouped):
        entries = grouped[time_s]

        coverage_vals = [float(e["summary"]["coverage_fraction"]) for e in entries]
        rave_vals = [float(e["summary"][SUMMARY_FIELD_FOR_RADIUS_PROXY[radius_proxy]]) for e in entries]
        pooled_radii = [
            float(record[radius_proxy])
            for e in entries
            for record in e["islands"]
            if float(record[radius_proxy]) > 0.0
        ]
        sigma_geo_vals = [
            sigma_geo_from_radii_nm(
                [
                    float(record[radius_proxy])
                    for record in e["islands"]
                    if float(record[radius_proxy]) > 0.0
                ]
            )
            for e in entries
        ]
        thickness_vals = [float(e["summary"]["equivalent_thickness_nm"]) for e in entries]
        density_vals = [float(e["summary"]["number_density_per_um2"]) for e in entries]
        height_vals = [float(e["summary"]["mean_island_height_nm"]) for e in entries]
        fit = fit_two_lognormal_mixture(pooled_radii)

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
            "radius_proxy_name": radius_proxy,
            "sigma_geo_radius": sg_mu,
            "sigma_geo_radius_std": sg_std,
            "distribution_type": "two_lognormal",
            "distribution_axis_name": radius_proxy,
            "distribution_log_likelihood": fit.log_likelihood,
            "distribution_bic": fit.bic,
            "distribution_fit_converged": int(fit.converged),
            "distribution_fit_iterations": fit.n_iter,
            "distribution_sample_count": fit.n_samples,
            "mixture_weight_1": fit.component_1.weight,
            "muL1": fit.component_1.mu_ln,
            "sigL1": fit.component_1.sigma_ln,
            "component_1_mean_nm": fit.component_1.mean_nm,
            "component_1_std_nm": fit.component_1.std_nm,
            "mixture_weight_2": fit.component_2.weight,
            "muL2": fit.component_2.mu_ln,
            "sigL2": fit.component_2.sigma_ln,
            "component_2_mean_nm": fit.component_2.mean_nm,
            "component_2_std_nm": fit.component_2.std_nm,
            "distribution_mean_nm": fit.mixture_mean_nm,
            "distribution_std_nm": fit.mixture_std_nm,
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
    "radius_proxy_name",
    "sigma_geo_radius",
    "sigma_geo_radius_std",
    "distribution_type",
    "distribution_axis_name",
    "distribution_log_likelihood",
    "distribution_bic",
    "distribution_fit_converged",
    "distribution_fit_iterations",
    "distribution_sample_count",
    "mixture_weight_1",
    "muL1",
    "sigL1",
    "component_1_mean_nm",
    "component_1_std_nm",
    "mixture_weight_2",
    "muL2",
    "sigL2",
    "component_2_mean_nm",
    "component_2_std_nm",
    "distribution_mean_nm",
    "distribution_std_nm",
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
        "radius_proxy_name "
        "sigma_geo sigma_geo_std "
        "w1 muL1 sigL1 mean1_nm std1_nm "
        "w2 muL2 sigL2 mean2_nm std2_nm "
        "dist_mean_nm dist_std_nm "
        "eq_thickness_nm eq_thickness_nm_std "
        "density_um2 density_um2_std "
        "mean_height_nm mean_height_nm_std\n"
    )
    lines = [
        (
            "{time_s} {n_scans} "
            "{coverage_fraction:.10g} {coverage_fraction_std:.10g} "
            "{Rave_nm:.10g} {Rave_nm_std:.10g} "
            "{radius_proxy_name} "
            "{sigma_geo_radius:.10g} {sigma_geo_radius_std:.10g} "
            "{mixture_weight_1:.10g} {muL1:.10g} {sigL1:.10g} {component_1_mean_nm:.10g} {component_1_std_nm:.10g} "
            "{mixture_weight_2:.10g} {muL2:.10g} {sigL2:.10g} {component_2_mean_nm:.10g} {component_2_std_nm:.10g} "
            "{distribution_mean_nm:.10g} {distribution_std_nm:.10g} "
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
# 7  radius_proxy_name
# 8  sigma_geo
# 9  sigma_geo_std
# 10 eq_thickness_nm
# 11 eq_thickness_nm_std
# 12 density_um2
# 13 density_um2_std
# 14 mean_height_nm
# 15 mean_height_nm_std

set ylabel "Coverage fraction"
plot "{dat_name}" using 1:3:4 title "coverage"

set ylabel "Rave (nm)"
plot "{dat_name}" using 1:5:6 title "Rave"

set ylabel "sigma_geo"
plot "{dat_name}" using 1:8:9 title "sigma_geo"

set ylabel "Equivalent thickness (nm)"
plot "{dat_name}" using 1:10:11 title "eq thickness"

unset multiplot
'''


def main() -> int:
    args = parse_args()
    suffixes = {normalize_suffix(s) for s in args.include_suffixes.split(",")}

    files = gather_json_files(args.inputs)
    grouped = load_filtered_payload_records(files, suffixes)
    rows = build_rows(grouped, args.radius_proxy)

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
