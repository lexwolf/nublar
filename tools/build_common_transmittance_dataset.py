#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(THIS_DIR))

from afm_lib.dataset import write_csv, write_dat_lines  # noqa: E402


class CommonTransmittanceDatasetError(RuntimeError):
    """Raised when the common-range transmittance dataset cannot be prepared."""


@dataclass
class ModelInputRow:
    time_s: int
    sample_label: str
    lamin_nm: float
    lamax_nm: float
    transmittance_dat: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a common-range manifest tying experimental transmittance spectra "
            "to their expected calculated spectra."
        )
    )
    parser.add_argument(
        "--model-input",
        type=Path,
        default=Path("data/input/experimental/model_input.dat"),
        help="Experimental model input manifest (default: data/input/experimental/model_input.dat)",
    )
    parser.add_argument(
        "--calculated-dir",
        type=Path,
        default=Path("data/output/transmittance"),
        help="Directory for calculated spectra (default: data/output/transmittance)",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/output/transmittance"),
        help="Output directory for the common-range manifest (default: data/output/transmittance)",
    )
    parser.add_argument(
        "--basename",
        default="common_transmittance_manifest",
        help="Base name for output files (default: common_transmittance_manifest)",
    )
    return parser.parse_args()


def parse_model_input(path: Path) -> list[ModelInputRow]:
    if not path.exists():
        raise CommonTransmittanceDatasetError(
            f"Missing model input manifest: {path}. Run tools/build_experimental_input.py first."
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

        if header_fields is None:
            raise CommonTransmittanceDatasetError(f"Missing header row in model input: {path}")

        parts = stripped.split()
        if len(parts) < len(header_fields):
            raise CommonTransmittanceDatasetError(f"Malformed row in model input: {line}")

        record = dict(zip(header_fields, parts, strict=True))
        rows.append(
            ModelInputRow(
                time_s=int(record["time_s"]),
                sample_label=record["transmittance_label"],
                lamin_nm=float(record["lamin_nm"]),
                lamax_nm=float(record["lamax_nm"]),
                transmittance_dat=Path(record["transmittance_dat"]),
            )
        )

    if not rows:
        raise CommonTransmittanceDatasetError(f"No data rows found in: {path}")
    return rows


def build_manifest_rows(rows: list[ModelInputRow], calculated_dir: Path) -> list[dict[str, object]]:
    common_lamin = max(row.lamin_nm for row in rows)
    common_lamax = min(row.lamax_nm for row in rows)
    if common_lamin >= common_lamax:
        raise CommonTransmittanceDatasetError(
            "No positive common wavelength range exists across the experimental spectra"
        )

    manifest_rows: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: item.time_s):
        calculated_dat = calculated_dir / f"silver_nanoisland_{row.time_s}s.dat"
        manifest_rows.append(
            {
                "time_s": row.time_s,
                "sample_label": row.sample_label,
                "experimental_dat": row.transmittance_dat.as_posix(),
                "calculated_dat": calculated_dat.as_posix(),
                "experimental_lamin_nm": row.lamin_nm,
                "experimental_lamax_nm": row.lamax_nm,
                "common_lamin_nm": common_lamin,
                "common_lamax_nm": common_lamax,
            }
        )
    return manifest_rows


def write_manifest_dat(rows: list[dict[str, object]], path: Path) -> None:
    header = (
        "# time_s sample_label experimental_dat calculated_dat "
        "experimental_lamin_nm experimental_lamax_nm common_lamin_nm common_lamax_nm\n"
    )
    lines = [
        (
            f"{row['time_s']} "
            f"{str(row['sample_label']).replace(' ', '_')} "
            f"{row['experimental_dat']} "
            f"{row['calculated_dat']} "
            f"{float(row['experimental_lamin_nm']):.10g} "
            f"{float(row['experimental_lamax_nm']):.10g} "
            f"{float(row['common_lamin_nm']):.10g} "
            f"{float(row['common_lamax_nm']):.10g}\n"
        )
        for row in rows
    ]
    write_dat_lines(path, header, lines)


def main() -> int:
    args = parse_args()
    rows = parse_model_input(args.model_input)
    manifest_rows = build_manifest_rows(rows, args.calculated_dir)

    args.outdir.mkdir(parents=True, exist_ok=True)
    csv_path = args.outdir / f"{args.basename}.csv"
    dat_path = args.outdir / f"{args.basename}.dat"

    write_csv(
        manifest_rows,
        csv_path,
        [
            "time_s",
            "sample_label",
            "experimental_dat",
            "calculated_dat",
            "experimental_lamin_nm",
            "experimental_lamax_nm",
            "common_lamin_nm",
            "common_lamax_nm",
        ],
    )
    write_manifest_dat(manifest_rows, dat_path)

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {dat_path}")
    print(
        "Common wavelength range: "
        f"{float(manifest_rows[0]['common_lamin_nm']):.10g} to "
        f"{float(manifest_rows[0]['common_lamax_nm']):.10g} nm"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
