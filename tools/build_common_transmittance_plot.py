#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.dataset import write_text  # noqa: E402


class CommonTransmittancePlotError(RuntimeError):
    """Raised when the common-range transmittance plot cannot be prepared."""


@dataclass
class ModelInputRow:
    time_s: int
    lamin_nm: float
    lamax_nm: float
    transmittance_dat: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a gnuplot script that plots experimental transmittance spectra "
            "over the wavelength range common to all deposition times."
        )
    )
    parser.add_argument(
        "--model-input",
        type=Path,
        default=None,
        help="Legacy experimental model input manifest",
    )
    parser.add_argument(
        "--model-manifest",
        type=Path,
        default=Path("data/input/experimental/transmittance_models.dat"),
        help="JSON-model sidecar manifest from tools/build_transmittance_models.py",
    )
    parser.add_argument(
        "--gnuplot-out",
        type=Path,
        default=Path("scripts/gnuplot/experimental/plot_transmittance_common_range.gp"),
        help=(
            "Output path for the generated gnuplot script "
            "(default: scripts/gnuplot/experimental/plot_transmittance_common_range.gp)"
        ),
    )
    parser.add_argument(
        "--png-out",
        type=Path,
        default=Path("img/experimental/transmittance_common_range.png"),
        help=(
            "PNG path referenced by the generated gnuplot script "
            "(default: img/experimental/transmittance_common_range.png)"
        ),
    )
    return parser.parse_args()


def parse_model_manifest(path: Path) -> list[ModelInputRow]:
    if not path.exists():
        raise CommonTransmittancePlotError(f"Missing JSON model manifest: {path}")

    header_fields: list[str] | None = None
    rows: list[ModelInputRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if header_fields is None:
                header_fields = stripped[1:].strip().split()
            continue

        if header_fields is None:
            raise CommonTransmittancePlotError(f"Missing header row in model manifest: {path}")
        parts = stripped.split()
        if len(parts) < len(header_fields):
            raise CommonTransmittancePlotError(f"Malformed row in model manifest: {line}")
        record = dict(zip(header_fields, parts, strict=True))
        rows.append(
            ModelInputRow(
                time_s=int(record["time_s"]),
                lamin_nm=float(record["experimental_lamin_nm"]),
                lamax_nm=float(record["experimental_lamax_nm"]),
                transmittance_dat=Path(record["experimental_dat"]),
            )
        )

    if not rows:
        raise CommonTransmittancePlotError(f"No data rows found in manifest: {path}")
    return rows


def parse_model_input(path: Path) -> list[ModelInputRow]:
    if not path.exists():
        raise CommonTransmittancePlotError(
            "Missing experimental model input manifest: "
            f"{path}. Run `python3 tools/build_experimental_input.py` first."
        )

    header_fields: list[str] | None = None
    rows: list[ModelInputRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if header_fields is None:
                header_fields = stripped[1:].strip().split()
            continue

        parts = stripped.split()
        if header_fields is None:
            raise CommonTransmittancePlotError(
                f"Missing header row in model input manifest: {path}"
            )
        if len(parts) < len(header_fields):
            raise CommonTransmittancePlotError(
                f"Malformed row in model input manifest: {line}"
            )
        record = dict(zip(header_fields, parts, strict=True))

        rows.append(
            ModelInputRow(
                time_s=int(record["time_s"]),
                lamin_nm=float(record["lamin_nm"]),
                lamax_nm=float(record["lamax_nm"]),
                transmittance_dat=Path(record["transmittance_dat"]),
            )
        )

    if not rows:
        raise CommonTransmittancePlotError(f"No data rows found in manifest: {path}")
    return rows


GNUPLOT_TEMPLATE = """set terminal pngcairo size 1400,900
set output "{png_path}"

set title "Silver nanoisland transmittance spectra"
set xlabel "Wavelength (nm)"
set ylabel "Transmittance"
set xrange [{lamin}:{lamax}]
set grid
set key outside right

plot \\
{plot_lines}
"""


def build_plot_script(rows: list[ModelInputRow], png_out: Path) -> str:
    common_lamin = max(row.lamin_nm for row in rows)
    common_lamax = min(row.lamax_nm for row in rows)
    if common_lamin >= common_lamax:
        raise CommonTransmittancePlotError(
            "No positive common wavelength range exists across the transmittance spectra"
        )

    plot_lines = ", \\\n".join(
        f'    "{row.transmittance_dat.resolve().as_posix()}" using 1:3 with lines lw 2 title "{row.time_s} s"'
        for row in sorted(rows, key=lambda item: item.time_s)
    )

    return GNUPLOT_TEMPLATE.format(
        png_path=png_out.resolve().as_posix(),
        lamin=f"{common_lamin:.10g}",
        lamax=f"{common_lamax:.10g}",
        plot_lines=plot_lines,
    )


def main() -> int:
    args = parse_args()
    rows = parse_model_input(args.model_input) if args.model_input else parse_model_manifest(args.model_manifest)
    script = build_plot_script(rows, args.png_out)
    write_text(args.gnuplot_out, script)
    print(f"Wrote: {args.gnuplot_out}")
    print(f"Common wavelength range: {max(r.lamin_nm for r in rows):.10g} to {min(r.lamax_nm for r in rows):.10g} nm")
    print(f"PNG target: {args.png_out}")
    print("\nSuggested gnuplot run:")
    print(f"  gnuplot {args.gnuplot_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
