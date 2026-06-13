#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.dataset import (
    gnuplot_dir_for_data_dir,
    image_dir_for_data_dir,
    write_csv,
    write_dat_lines,
    write_text,
)


TIME_RE = re.compile(r"_(\d+)s_", re.IGNORECASE)


class TransmittanceFormatError(RuntimeError):
    """Raised when a processed transmittance text file cannot be parsed safely."""


@dataclass
class SpectrumPoint:
    wavelength_nm: float
    auxiliary_value: float
    transmittance: float
    transmittance_error: float


@dataclass
class SpectrumRecord:
    input_path: Path
    sample_label: str
    time_s: int | None
    original_name: str
    wavelength_unit: str
    points: list[SpectrumPoint]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert processed transmittance TXT exports into DAT/CSV datasets."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help=(
            "Processed transmittance TXT files and/or directories. "
            "If omitted, uses data/experimental/processed/transmittance."
        ),
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/experimental/final/transmittance"),
        help=(
            "Data output directory for converted DAT/CSV files "
            "(default: data/experimental/final/transmittance)"
        ),
    )
    parser.add_argument(
        "--basename",
        default="transmittance_manifest",
        help="Base name for the aggregate manifest files (default: transmittance_manifest)",
    )
    return parser.parse_args()


def normalize_number(token: str) -> float:
    return float(token.strip().replace(",", "."))


def parse_time_s(path: Path) -> int | None:
    match = TIME_RE.search(path.name)
    if not match:
        return None
    return int(match.group(1))


def gather_input_files(inputs: list[Path]) -> list[Path]:
    if not inputs:
        base_dir = Path("data/experimental/processed/transmittance")
        if not base_dir.exists():
            raise TransmittanceFormatError(
                f"Default input directory does not exist: {base_dir}"
            )
        return sorted(base_dir.glob("*.txt"))

    files: list[Path] = []
    for path in inputs:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.txt")))
        elif path.is_file():
            files.append(path)
        else:
            raise TransmittanceFormatError(f"Input path does not exist: {path}")

    if not files:
        raise TransmittanceFormatError("No transmittance TXT files found in the provided inputs")
    return sorted(files)


def parse_transmittance_file(path: Path) -> SpectrumRecord:
    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(raw_lines) < 5:
        raise TransmittanceFormatError(f"Not enough lines in transmittance file: {path}")

    sample_label = raw_lines[0].strip()
    original_line = raw_lines[2].strip()
    wavelength_unit = raw_lines[3].strip()

    if original_line.startswith("Original[") and original_line.endswith("]"):
        original_name = original_line[len("Original["):-1]
    else:
        original_name = original_line

    points: list[SpectrumPoint] = []
    for line in raw_lines[4:]:
        stripped = line.strip()
        if not stripped:
            continue

        parts = re.split(r"\t+", stripped)
        if len(parts) != 5 or parts[0] != "pT":
            continue

        points.append(
            SpectrumPoint(
                wavelength_nm=normalize_number(parts[1]),
                auxiliary_value=normalize_number(parts[2]),
                transmittance=normalize_number(parts[3]),
                transmittance_error=normalize_number(parts[4]),
            )
        )

    if not points:
        raise TransmittanceFormatError(f"No spectral points found in: {path}")

    return SpectrumRecord(
        input_path=path,
        sample_label=sample_label,
        time_s=parse_time_s(path),
        original_name=original_name,
        wavelength_unit=wavelength_unit,
        points=points,
    )


def sanitize_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem)


def write_spectrum_csv(record: SpectrumRecord, path: Path) -> None:
    rows: list[dict[str, Any]] = [
        {
            "wavelength_nm": point.wavelength_nm,
            "auxiliary_value": point.auxiliary_value,
            "transmittance": point.transmittance,
            "transmittance_error": point.transmittance_error,
        }
        for point in record.points
    ]
    write_csv(
        rows,
        path,
        ["wavelength_nm", "auxiliary_value", "transmittance", "transmittance_error"],
    )


def write_spectrum_dat(record: SpectrumRecord, path: Path) -> None:
    header = (
        f"# sample_label {record.sample_label}\n"
        f"# original_name {record.original_name}\n"
        f"# wavelength_unit {record.wavelength_unit}\n"
        "# wavelength_nm auxiliary_value transmittance transmittance_error\n"
    )
    lines = [
        (
            f"{point.wavelength_nm:.10g} "
            f"{point.auxiliary_value:.10g} "
            f"{point.transmittance:.10g} "
            f"{point.transmittance_error:.10g}\n"
        )
        for point in record.points
    ]
    write_dat_lines(path, header, lines)


def build_manifest_rows(records: list[SpectrumRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        wavelengths = [point.wavelength_nm for point in record.points]
        transmittance = [point.transmittance for point in record.points]
        rows.append(
            {
                "sample_label": record.sample_label,
                "time_s": "" if record.time_s is None else record.time_s,
                "input_txt": record.input_path.as_posix(),
                "original_name": record.original_name,
                "wavelength_unit": record.wavelength_unit,
                "n_points": len(record.points),
                "wavelength_min_nm": min(wavelengths),
                "wavelength_max_nm": max(wavelengths),
                "transmittance_min": min(transmittance),
                "transmittance_max": max(transmittance),
            }
        )
    return rows


def write_manifest_dat(rows: list[dict[str, Any]], path: Path) -> None:
    header = (
        "# time_s n_points wavelength_min_nm wavelength_max_nm "
        "transmittance_min transmittance_max sample_label\n"
    )
    lines = [
        (
            f"{row['time_s'] if row['time_s'] != '' else -1} "
            f"{row['n_points']} "
            f"{row['wavelength_min_nm']:.10g} "
            f"{row['wavelength_max_nm']:.10g} "
            f"{row['transmittance_min']:.10g} "
            f"{row['transmittance_max']:.10g} "
            f"{str(row['sample_label']).replace(' ', '_')}\n"
        )
        for row in rows
    ]
    write_dat_lines(path, header, lines)


GNUPLOT_TEMPLATE = r'''set terminal pngcairo size 1400,900
set output "{png_name}"

set title "Processed transmittance spectra ({label})"
set grid
set key outside right
set xlabel "Wavelength (nm)"
set ylabel "Transmittance"

plot \
{plot_lines}
'''


def write_gnuplot_bundle(
    path: Path,
    dat_paths: list[Path],
    labels: list[str],
    png_name: str,
    label: str,
) -> None:
    plot_lines = ", \\\n".join(
        f'    "{dat_path.resolve().as_posix()}" using 1:3 with lines lw 2 title "{curve_label}"'
        for dat_path, curve_label in zip(dat_paths, labels, strict=True)
    )
    template = GNUPLOT_TEMPLATE.format(
        png_name=Path(png_name).resolve().as_posix(),
        label=label,
        plot_lines=plot_lines,
    )
    write_text(path, template)


def main() -> int:
    args = parse_args()
    input_files = gather_input_files(args.inputs)
    records = [parse_transmittance_file(path) for path in input_files]

    args.outdir.mkdir(parents=True, exist_ok=True)
    img_dir = image_dir_for_data_dir(args.outdir)
    gp_dir = gnuplot_dir_for_data_dir(args.outdir)
    img_dir.mkdir(parents=True, exist_ok=True)
    gp_dir.mkdir(parents=True, exist_ok=True)

    converted_dat_paths: list[Path] = []
    converted_labels: list[str] = []

    for record in records:
        stem = sanitize_stem(record.input_path)
        csv_path = args.outdir / f"{stem}.csv"
        dat_path = args.outdir / f"{stem}.dat"

        write_spectrum_csv(record, csv_path)
        write_spectrum_dat(record, dat_path)

        converted_dat_paths.append(dat_path)
        converted_labels.append(record.sample_label)

        print(f"Wrote: {csv_path}")
        print(f"Wrote: {dat_path}")

    manifest_rows = build_manifest_rows(records)
    manifest_csv_path = args.outdir / f"{args.basename}.csv"
    manifest_dat_path = args.outdir / f"{args.basename}.dat"
    plot_gp_path = gp_dir / f"plot_{args.basename}.gp"
    plot_png_path = img_dir / f"{args.basename}.png"

    write_csv(
        manifest_rows,
        manifest_csv_path,
        [
            "sample_label",
            "time_s",
            "input_txt",
            "original_name",
            "wavelength_unit",
            "n_points",
            "wavelength_min_nm",
            "wavelength_max_nm",
            "transmittance_min",
            "transmittance_max",
        ],
    )
    write_manifest_dat(manifest_rows, manifest_dat_path)
    write_gnuplot_bundle(
        plot_gp_path,
        converted_dat_paths,
        converted_labels,
        plot_png_path.as_posix(),
        args.basename,
    )

    print(f"Wrote: {manifest_csv_path}")
    print(f"Wrote: {manifest_dat_path}")
    print(f"Wrote: {plot_gp_path}")
    print(f"Wrote: {plot_png_path} (via gnuplot)")
    print("\nSuggested gnuplot run:")
    print(f"  gnuplot {plot_gp_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
