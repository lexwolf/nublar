#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


DEFAULT_INPUT_CSV = Path("data/input/experimental/model_input.csv")
DEFAULT_OUTPUT_JSON = Path("data/input/optimal/afm_priors/mmgm_single_loose.json")

SUPPORTED_MODEL = "mmgm_single"
SUPPORTED_DISTRIBUTION = "single_lognormal"
SUPPORTED_STRATEGY = "loose"

REQUIRED_COLUMNS = (
    "time_s",
    "radius_proxy_name",
    "single_lognormal_Rave_nm",
    "single_lognormal_sigL",
    "single_lognormal_std_nm",
    "single_lognormal_fit_method",
    "effe_proxy",
    "equivalent_thickness_nm",
    "coverage_fraction",
)


class AfmPriorBoundsError(RuntimeError):
    """Raised when AFM prior-bound generation fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build AFM-derived prior bounds from the enriched experimental manifest "
            "for later optimizer use."
        )
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=DEFAULT_INPUT_CSV,
        help=f"Input enriched experimental manifest (default: {DEFAULT_INPUT_CSV})",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help=f"Output prior-bounds JSON path (default: {DEFAULT_OUTPUT_JSON})",
    )
    parser.add_argument(
        "--strategy",
        default=SUPPORTED_STRATEGY,
        help=f"Prior strategy to build; currently only {SUPPORTED_STRATEGY!r} is supported",
    )
    parser.add_argument(
        "--model",
        default=SUPPORTED_MODEL,
        help=f"Target model; currently only {SUPPORTED_MODEL!r} is supported",
    )
    parser.add_argument(
        "--distribution",
        default=SUPPORTED_DISTRIBUTION,
        help=(
            "Radius distribution descriptor to use; currently only "
            f"{SUPPORTED_DISTRIBUTION!r} is supported"
        ),
    )
    parser.add_argument(
        "--radius-margin-low",
        type=float,
        default=0.5,
        help="Lower multiplicative margin applied to single_lognormal_Rave_nm",
    )
    parser.add_argument(
        "--radius-margin-high",
        type=float,
        default=2.0,
        help="Upper multiplicative margin applied to single_lognormal_Rave_nm",
    )
    parser.add_argument(
        "--sigl-min",
        type=float,
        default=0.1,
        help="Lower sigma-lognormal prior bound",
    )
    parser.add_argument(
        "--sigl-max",
        type=float,
        default=0.8,
        help="Upper sigma-lognormal prior bound",
    )
    return parser.parse_args()


def require_supported_args(args: argparse.Namespace) -> None:
    if args.model != SUPPORTED_MODEL:
        raise AfmPriorBoundsError(
            f"Unsupported model {args.model!r}; currently supported: {SUPPORTED_MODEL!r}"
        )
    if args.distribution != SUPPORTED_DISTRIBUTION:
        raise AfmPriorBoundsError(
            "Unsupported distribution "
            f"{args.distribution!r}; currently supported: {SUPPORTED_DISTRIBUTION!r}"
        )
    if args.strategy != SUPPORTED_STRATEGY:
        raise AfmPriorBoundsError(
            f"Unsupported strategy {args.strategy!r}; currently supported: {SUPPORTED_STRATEGY!r}"
        )


def require_finite_number(value: str, field: str, time_s: int | None = None) -> float:
    context = f" for time_s={time_s}" if time_s is not None else ""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise AfmPriorBoundsError(f"Field {field!r}{context} is not numeric: {value!r}") from exc
    if not math.isfinite(parsed):
        raise AfmPriorBoundsError(f"Field {field!r}{context} must be finite: {value!r}")
    return parsed


def parse_time_s(value: str) -> int:
    try:
        parsed_float = float(value)
    except ValueError as exc:
        raise AfmPriorBoundsError(f"Field 'time_s' is not numeric: {value!r}") from exc
    if not math.isfinite(parsed_float) or not parsed_float.is_integer():
        raise AfmPriorBoundsError(f"Field 'time_s' must be a finite integer: {value!r}")
    return int(parsed_float)


def validate_strategy_numbers(args: argparse.Namespace) -> None:
    radius_margin_low = float(args.radius_margin_low)
    radius_margin_high = float(args.radius_margin_high)
    sigl_min = float(args.sigl_min)
    sigl_max = float(args.sigl_max)

    for name, value in (
        ("radius_margin_low", radius_margin_low),
        ("radius_margin_high", radius_margin_high),
        ("sigl_min", sigl_min),
        ("sigl_max", sigl_max),
    ):
        if not math.isfinite(value):
            raise AfmPriorBoundsError(f"{name} must be finite: {value!r}")

    if radius_margin_low <= 0.0 or radius_margin_high <= 0.0:
        raise AfmPriorBoundsError("Radius margins must be positive")
    if radius_margin_low >= radius_margin_high:
        raise AfmPriorBoundsError("radius_margin_low must be less than radius_margin_high")
    if sigl_min < 0.0:
        raise AfmPriorBoundsError("sigl_min must be >= 0")
    if sigl_min >= sigl_max:
        raise AfmPriorBoundsError("sigl_min must be less than sigl_max")


def load_manifest_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise AfmPriorBoundsError(f"Input CSV does not exist: {path}")
    if not path.is_file():
        raise AfmPriorBoundsError(f"Input CSV is not a file: {path}")

    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AfmPriorBoundsError(f"Input CSV has no header: {path}")
        missing = [field for field in REQUIRED_COLUMNS if field not in reader.fieldnames]
        if missing:
            raise AfmPriorBoundsError(
                f"Input CSV is missing required columns: {', '.join(missing)}"
            )
        rows = list(reader)

    if not rows:
        raise AfmPriorBoundsError(f"Input CSV contains no data rows: {path}")
    return rows


def build_bounds_document(args: argparse.Namespace) -> dict[str, Any]:
    require_supported_args(args)
    validate_strategy_numbers(args)
    rows = load_manifest_rows(args.input_csv)

    seen_times: set[int] = set()
    parsed_rows: list[tuple[int, dict[str, str]]] = []
    radius_proxy_names: set[str] = set()

    for row in rows:
        time_s = parse_time_s(row["time_s"])
        if time_s in seen_times:
            raise AfmPriorBoundsError(f"Duplicate time_s in input CSV: {time_s}")
        seen_times.add(time_s)
        parsed_rows.append((time_s, row))

        radius_proxy_name = row["radius_proxy_name"].strip()
        if not radius_proxy_name:
            raise AfmPriorBoundsError(f"radius_proxy_name is empty for time_s={time_s}")
        radius_proxy_names.add(radius_proxy_name)

    if len(radius_proxy_names) != 1:
        names = ", ".join(sorted(radius_proxy_names))
        raise AfmPriorBoundsError(
            "Expected one radius_proxy_name across the manifest; found: " + names
        )

    bounds_by_time_s: dict[str, Any] = {}
    for time_s, row in sorted(parsed_rows, key=lambda item: item[0]):
        rave_nm = require_finite_number(row["single_lognormal_Rave_nm"], "single_lognormal_Rave_nm", time_s)
        sig_l = require_finite_number(row["single_lognormal_sigL"], "single_lognormal_sigL", time_s)
        single_std_nm = require_finite_number(
            row["single_lognormal_std_nm"],
            "single_lognormal_std_nm",
            time_s,
        )
        effe_proxy = require_finite_number(row["effe_proxy"], "effe_proxy", time_s)
        equivalent_thickness_nm = require_finite_number(
            row["equivalent_thickness_nm"],
            "equivalent_thickness_nm",
            time_s,
        )
        coverage_fraction = require_finite_number(
            row["coverage_fraction"],
            "coverage_fraction",
            time_s,
        )

        if rave_nm <= 0.0:
            raise AfmPriorBoundsError(
                f"single_lognormal_Rave_nm must be positive for time_s={time_s}"
            )
        if sig_l < 0.0:
            raise AfmPriorBoundsError(
                f"single_lognormal_sigL must be non-negative for time_s={time_s}"
            )
        if single_std_nm < 0.0:
            raise AfmPriorBoundsError(
                f"single_lognormal_std_nm must be non-negative for time_s={time_s}"
            )

        rave_min = args.radius_margin_low * rave_nm
        rave_max = args.radius_margin_high * rave_nm
        if not math.isfinite(rave_min) or not math.isfinite(rave_max):
            raise AfmPriorBoundsError(f"Radius bounds must be finite for time_s={time_s}")
        if rave_min <= 0.0 or rave_max <= 0.0:
            raise AfmPriorBoundsError(f"Radius bounds must be positive for time_s={time_s}")

        bounds_by_time_s[str(time_s)] = {
            "rave_nm": {
                "min": rave_min,
                "max": rave_max,
                "reference": rave_nm,
                "source_field": "single_lognormal_Rave_nm",
            },
            "sig_l": {
                "min": args.sigl_min,
                "max": args.sigl_max,
                "reference": sig_l,
                "source_field": "single_lognormal_sigL",
            },
            "afm_reference": {
                "single_lognormal_std_nm": single_std_nm,
                "single_lognormal_fit_method": row["single_lognormal_fit_method"],
                "effe_proxy": effe_proxy,
                "equivalent_thickness_nm": equivalent_thickness_nm,
                "coverage_fraction": coverage_fraction,
            },
        }

    return {
        "schema_version": 1,
        "source": {
            "input_csv": args.input_csv.as_posix(),
            "radius_proxy_name": sorted(radius_proxy_names)[0],
            "distribution": args.distribution,
            "model": args.model,
        },
        "strategy": {
            "name": args.strategy,
            "radius_margin_low": args.radius_margin_low,
            "radius_margin_high": args.radius_margin_high,
            "sig_l_min": args.sigl_min,
            "sig_l_max": args.sigl_max,
        },
        "bounds_by_time_s": bounds_by_time_s,
    }


def main() -> int:
    try:
        args = parse_args()
        document = build_bounds_document(args)
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote: {args.output_json}")
        return 0
    except AfmPriorBoundsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
