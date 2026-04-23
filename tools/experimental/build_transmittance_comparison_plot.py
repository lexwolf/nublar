#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(THIS_DIR))

from afm_lib.dataset import write_text  # noqa: E402


class TransmittanceComparisonPlotError(RuntimeError):
    """Raised when the comparison gnuplot script cannot be prepared."""


@dataclass
class ManifestRow:
    time_s: int
    sample_label: str
    experimental_dat: Path
    calculated_dat: Path
    common_lamin_nm: float
    common_lamax_nm: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a two-panel gnuplot script comparing experimental and calculated "
            "transmittance spectra over the common wavelength range."
        )
    )
    parser.add_argument(
        "--common-dataset",
        type=Path,
        default=Path("data/output/transmittance/common_transmittance_manifest.dat"),
        help=(
            "Common-range transmittance manifest "
            "(default: data/output/transmittance/common_transmittance_manifest.dat)"
        ),
    )
    parser.add_argument(
        "--gnuplot-out",
        type=Path,
        default=Path("scripts/gnuplot/comparisons/transmittance/plot_experimental_vs_calculated.gp"),
        help="Output path for the generated gnuplot script",
    )
    parser.add_argument(
        "--png-out",
        type=Path,
        default=Path("img/comparisons/transmittance/experimental_vs_calculated.png"),
        help="PNG path referenced by the generated gnuplot script",
    )
    return parser.parse_args()


def parse_manifest(path: Path) -> list[ManifestRow]:
    if not path.exists():
        raise TransmittanceComparisonPlotError(
            f"Missing common-range dataset: {path}. Run tools/experimental/build_common_transmittance_dataset.py first."
        )

    header_fields: list[str] | None = None
    rows: list[ManifestRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if header_fields is None:
                header_fields = stripped[1:].strip().split()
            continue

        if header_fields is None:
            raise TransmittanceComparisonPlotError(f"Missing header row in dataset: {path}")

        parts = stripped.split()
        if len(parts) < len(header_fields):
            raise TransmittanceComparisonPlotError(f"Malformed row in dataset: {line}")

        record = dict(zip(header_fields, parts, strict=True))
        row = ManifestRow(
            time_s=int(record["time_s"]),
            sample_label=record["sample_label"].replace("_", " "),
            experimental_dat=Path(record["experimental_dat"]),
            calculated_dat=Path(record["calculated_dat"]),
            common_lamin_nm=float(record["common_lamin_nm"]),
            common_lamax_nm=float(record["common_lamax_nm"]),
        )

        if not row.experimental_dat.exists():
            raise TransmittanceComparisonPlotError(
                f"Experimental spectrum does not exist: {row.experimental_dat}"
            )
        if not row.calculated_dat.exists():
            raise TransmittanceComparisonPlotError(
                f"Calculated spectrum does not exist: {row.calculated_dat}"
            )
        rows.append(row)

    if not rows:
        raise TransmittanceComparisonPlotError(f"No data rows found in: {path}")
    return rows


GNUPLOT_TEMPLATE = """set terminal pngcairo noenhanced size 1800,900
set output "{png_path}"

common_lamin = {common_lamin}
common_lamax = {common_lamax}

set multiplot layout 1,2 rowsfirst title "Experimental vs calculated transmittance spectra"
set grid
set xrange [common_lamin:common_lamax]
set xlabel "Wavelength (nm)"
set ylabel "Transmittance"
set key outside right

set title "Experimental spectra"
plot \\
{experimental_plot_lines}

set title "Calculated spectra"
plot \\
{calculated_plot_lines}

unset multiplot
"""


def build_plot_script(rows: list[ManifestRow], png_out: Path) -> str:
    common_lamin = max(row.common_lamin_nm for row in rows)
    common_lamax = min(row.common_lamax_nm for row in rows)
    if common_lamin >= common_lamax:
        raise TransmittanceComparisonPlotError(
            "The common wavelength range in the manifest is not valid"
        )

    experimental_plot_lines = ", \\\n".join(
        f'    "{row.experimental_dat.resolve().as_posix()}" using 1:3 with lines lw 2 title "{row.time_s} s"'
        for row in sorted(rows, key=lambda item: item.time_s)
    )
    calculated_plot_lines = ", \\\n".join(
        f'    "{row.calculated_dat.resolve().as_posix()}" using 1:3 with lines lw 2 title "{row.time_s} s"'
        for row in sorted(rows, key=lambda item: item.time_s)
    )

    return GNUPLOT_TEMPLATE.format(
        png_path=png_out.resolve().as_posix(),
        common_lamin=f"{common_lamin:.10g}",
        common_lamax=f"{common_lamax:.10g}",
        experimental_plot_lines=experimental_plot_lines,
        calculated_plot_lines=calculated_plot_lines,
    )


def main() -> int:
    args = parse_args()
    rows = parse_manifest(args.common_dataset)
    script = build_plot_script(rows, args.png_out)
    write_text(args.gnuplot_out, script)
    print(f"Wrote: {args.gnuplot_out}")
    print(f"PNG target: {args.png_out}")
    print(f"Suggested gnuplot run: gnuplot {args.gnuplot_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
