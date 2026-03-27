#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


TIME_RE = re.compile(r"Nis_Ag_(\d+)s_.*_features\.json$")
SUFFIX_RE = re.compile(r"_(001|002|003|Image_1|Image_1\.txtNis_Ag_\d+s_2um_Image_1)$")


class DatasetBuildError(RuntimeError):
    pass


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


def normalize_suffix(token: str) -> str:
    t = token.strip().lower()
    if t in {"image", "img", "image1", "image_1"}:
        return "image"
    if t in {"001", "002", "003"}:
        return t
    raise DatasetBuildError(f"Unsupported suffix token: {token}")


def extract_time_s(path: Path) -> int:
    m = TIME_RE.search(path.name)
    if not m:
        raise DatasetBuildError(f"Could not parse deposition time from filename: {path}")
    return int(m.group(1))


def extract_source_label(path: Path) -> str:
    name = path.name
    if "Image_1" in name:
        return "image"
    for s in ("001", "002", "003"):
        if f"_{s}_" in name or name.endswith(f"_{s}_features.json"):
            return s
    raise DatasetBuildError(f"Could not parse source label from filename: {path}")


DEFAULT_BATCH_ROOT = Path("data/experimental/intermediate/afm_batch")


def gather_json_files(inputs: list[Path]) -> list[Path]:
    if not inputs:
        if not DEFAULT_BATCH_ROOT.exists():
            raise DatasetBuildError(
                "No inputs provided and default batch directory does not exist: "
                f"{DEFAULT_BATCH_ROOT}"
            )
        return sorted(DEFAULT_BATCH_ROOT.rglob("*_features.json"))

    files: list[Path] = []
    for p in inputs:
        if p.is_dir():
            files.extend(sorted(p.rglob("*_features.json")))
        elif p.is_file():
            files.append(p)
        else:
            raise DatasetBuildError(f"Input path does not exist: {p}")

    if not files:
        raise DatasetBuildError("No feature JSON files found in the provided inputs")
    return sorted(files)


def load_summary(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if "summary" not in payload:
        raise DatasetBuildError(f"Missing 'summary' section in: {path}")
    return payload["summary"]


FIELDS = [
    "coverage_fraction",
    "equivalent_thickness_nm",
    "mean_equivalent_radius_nm",
    "std_equivalent_radius_nm",
    "number_density_per_um2",
    "island_count",
    "mean_island_height_nm",
]


def group_by_time(files: list[Path], allowed_sources: set[str]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for path in files:
        source = extract_source_label(path)
        if source not in allowed_sources:
            continue
        time_s = extract_time_s(path)
        summary = load_summary(path)
        summary = dict(summary)
        summary["_source"] = source
        summary["_path"] = str(path)
        grouped.setdefault(time_s, []).append(summary)

    if not grouped:
        raise DatasetBuildError("No JSON summaries matched the requested suffix selection")
    return grouped


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    return float(mean(values)), float(pstdev(values))

def derived_reff_nm(coverage_fraction: float, number_density_per_um2: float) -> float:
    if number_density_per_um2 <= 0:
        return 0.0
    # sqrt(coverage / (pi * density)) gives a length in um
    return 1000.0 * ((coverage_fraction / (3.141592653589793 * number_density_per_um2)) ** 0.5)

def build_rows(grouped: dict[int, list[dict[str, Any]]], source_label: str) -> list[dict[str, Any]]:
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


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
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
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_dat(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# time_s n_scans "
        "coverage coverage_std thickness_nm thickness_std "
        "mean_radius_nm mean_radius_std radius_sigma_nm radius_sigma_std "
        "density_um2 density_um2_std derived_reff_nm derived_reff_nm_std island_count island_count_std "
        "mean_height_nm mean_height_std\n"
    )
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        for r in rows:
            f.write(
                "{time_s} {n_scans} {coverage_fraction:.10g} {coverage_fraction_std:.10g} "
                "{equivalent_thickness_nm:.10g} {equivalent_thickness_nm_std:.10g} "
                "{mean_equivalent_radius_nm:.10g} {mean_equivalent_radius_nm_std:.10g} "
                "{std_equivalent_radius_nm:.10g} {std_equivalent_radius_nm_std:.10g} "
                "{number_density_per_um2:.10g} {number_density_per_um2_std:.10g} "
                "{derived_reff_nm:.10g} {derived_reff_nm_std:.10g} "
                "{island_count:.10g} {island_count_std:.10g} "
                "{mean_island_height_nm:.10g} {mean_island_height_nm_std:.10g}\n".format(**r)
            )


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


def write_gnuplot_script(path: Path, dat_path: Path, png_name: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    script = GNUPLOT_TEMPLATE.format(
        dat_name=dat_path.name,
        png_name=png_name,
        label=label,
    )
    path.write_text(script, encoding="utf-8")


def main() -> int:
    args = parse_args()
    suffixes = {normalize_suffix(s) for s in args.include_suffixes.split(",")}

    files = gather_json_files(args.inputs)
    grouped = group_by_time(files, suffixes)
    label = "+".join(sorted(suffixes))
    rows = build_rows(grouped, label)

    args.outdir.mkdir(parents=True, exist_ok=True)
    csv_path = args.outdir / f"{args.basename}_{label}.csv"
    dat_path = args.outdir / f"{args.basename}_{label}.dat"
    gp_path = args.outdir / f"plot_{args.basename}_{label}.gp"
    png_name = f"{args.basename}_{label}.png"

    write_csv(rows, csv_path)
    write_dat(rows, dat_path)
    write_gnuplot_script(gp_path, dat_path, png_name, label)

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {dat_path}")
    print(f"Wrote: {gp_path}")
    print("\nSuggested gnuplot run:")
    print(f"  cd {args.outdir} && gnuplot {gp_path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
