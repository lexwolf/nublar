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
DEFAULT_OUTPUT_DAT = Path("data/output/afm_diagnostics/afm_hag_volume_equivalent.dat")
DEFAULT_SUMMARY_JSON = Path(
    "data/output/afm_diagnostics/afm_hag_volume_equivalent_summary.json"
)

RADIUS_PROXY_NAME = "volume_equivalent_radius_nm"
RADIUS_PROXY_COLUMNS = (
    "volume_equivalent_radius_nm",
    "Rave_volume_equivalent_radius_nm",
)
FORMULA = "h_Ag_nm = coverage_fraction * (4/3) * Rave_nm * exp(2 sigL^2)"

RADIUS_LOW_FACTOR = 0.75
RADIUS_HIGH_FACTOR = 1.5
SIGL_LOW_FACTOR = 0.75
SIGL_HIGH_FACTOR = 1.25
SIGL_LOW_MIN = 0.05

REQUIRED_COLUMNS = (
    "time_s",
    "coverage_fraction",
    "single_lognormal_sigL",
)
DIAGNOSTIC_COLUMNS = (
    "equivalent_thickness_nm",
    "single_lognormal_Rave_nm",
    "single_lognormal_sigL",
)


class AfmHagProxyError(RuntimeError):
    """Raised when the AFM hAg proxy diagnostic cannot be extracted."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract an AFM-only h_Ag(t) diagnostic from the "
            "volume_equivalent_radius_nm radius proxy."
        )
    )
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dat", type=Path, default=DEFAULT_OUTPUT_DAT)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    return parser.parse_args()


def finite_float(value: str, field: str, time_s: float | None = None) -> float:
    context = f" for time_s={time_s:g}" if time_s is not None else ""
    if value == "":
        raise AfmHagProxyError(f"Field {field!r}{context} is empty")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise AfmHagProxyError(f"Field {field!r}{context} is not numeric: {value!r}") from exc
    if not math.isfinite(parsed):
        raise AfmHagProxyError(f"Field {field!r}{context} must be finite: {value!r}")
    return parsed


def optional_finite_float(row: dict[str, str], field: str, time_s: float) -> float:
    if field not in row or row[field] == "":
        return math.nan
    return finite_float(row[field], field, time_s)


def load_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise AfmHagProxyError(f"Input CSV does not exist: {path}")
    if not path.is_file():
        raise AfmHagProxyError(f"Input CSV is not a file: {path}")

    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AfmHagProxyError(f"Input CSV has no header: {path}")
        rows = list(reader)

    if not rows:
        raise AfmHagProxyError(f"Input CSV contains no rows: {path}")
    return list(reader.fieldnames), rows


def find_radius_proxy_column(fieldnames: list[str]) -> str:
    for candidate in RADIUS_PROXY_COLUMNS:
        if candidate in fieldnames:
            return candidate
    raise AfmHagProxyError(
        "Input CSV is missing the volume-equivalent radius proxy column. "
        "Expected one of: " + ", ".join(RADIUS_PROXY_COLUMNS)
    )


def check_required_columns(fieldnames: list[str]) -> None:
    missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
    if missing:
        raise AfmHagProxyError(
            "Input CSV is missing required columns: " + ", ".join(missing)
        )


def hag_nm(coverage_fraction: float, radius_nm: float, sig_l: float) -> float:
    return coverage_fraction * (4.0 / 3.0) * radius_nm * math.exp(2.0 * sig_l**2)


def extract_points(rows: list[dict[str, str]], radius_column: str) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    seen_times: set[float] = set()

    for row in rows:
        time_s = finite_float(row["time_s"], "time_s")
        if time_s in seen_times:
            raise AfmHagProxyError(f"Duplicate time_s in input CSV: {time_s:g}")
        seen_times.add(time_s)

        coverage_fraction = finite_float(row["coverage_fraction"], "coverage_fraction", time_s)
        rave_nm = finite_float(row[radius_column], radius_column, time_s)
        sig_l = finite_float(row["single_lognormal_sigL"], "single_lognormal_sigL", time_s)

        if coverage_fraction < 0.0:
            raise AfmHagProxyError(
                f"Field 'coverage_fraction' must be non-negative for time_s={time_s:g}"
            )
        if rave_nm <= 0.0:
            raise AfmHagProxyError(f"Field {radius_column!r} must be positive for time_s={time_s:g}")
        if sig_l < 0.0:
            raise AfmHagProxyError(
                f"Field 'single_lognormal_sigL' must be non-negative for time_s={time_s:g}"
            )

        r_low = RADIUS_LOW_FACTOR * rave_nm
        r_high = RADIUS_HIGH_FACTOR * rave_nm
        sig_l_low = max(SIGL_LOW_MIN, SIGL_LOW_FACTOR * sig_l)
        sig_l_high = SIGL_HIGH_FACTOR * sig_l

        h_ag = hag_nm(coverage_fraction, rave_nm, sig_l)
        h_low_radius = hag_nm(coverage_fraction, r_low, sig_l)
        h_high_radius = hag_nm(coverage_fraction, r_high, sig_l)
        h_low = hag_nm(coverage_fraction, r_low, sig_l_low)
        h_high = hag_nm(coverage_fraction, r_high, sig_l_high)

        points.append(
            {
                "time_s": time_s,
                "coverage_fraction": coverage_fraction,
                "Rave_nm": rave_nm,
                "sigL": sig_l,
                "h_Ag_nm": h_ag,
                "h_err_low": max(0.0, h_ag - h_low),
                "h_err_high": max(0.0, h_high - h_ag),
                "h_low": h_low,
                "h_high": h_high,
                "h_low_radius": h_low_radius,
                "h_high_radius": h_high_radius,
                "equivalent_thickness_nm": optional_finite_float(
                    row, "equivalent_thickness_nm", time_s
                ),
                "single_lognormal_Rave_nm": optional_finite_float(
                    row, "single_lognormal_Rave_nm", time_s
                ),
                "single_lognormal_sigL": sig_l,
            }
        )

    return sorted(points, key=lambda point: point["time_s"])


def linear_fit(points: list[dict[str, float]]) -> dict[str, float]:
    n = len(points)
    if n < 2:
        raise AfmHagProxyError("At least two points are required for a linear fit")

    xs = [point["time_s"] for point in points]
    ys = [point["h_Ag_nm"] for point in points]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    ss_xx = sum((x - x_mean) ** 2 for x in xs)
    if ss_xx == 0.0:
        raise AfmHagProxyError("Cannot fit a line because all time_s values are identical")

    ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean

    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot

    return {
        "slope_nm_per_s": slope,
        "intercept_nm": intercept,
        "r2": r2,
    }


def format_value(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.12g}"


def write_dat(path: Path, points: list[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "time_s",
        "coverage_fraction",
        "Rave_nm",
        "sigL",
        "h_Ag_nm",
        "h_err_low",
        "h_err_high",
        "h_low",
        "h_high",
        "equivalent_thickness_nm",
        "single_lognormal_Rave_nm",
        "single_lognormal_sigL",
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# AFM-derived h_Ag estimate using volume_equivalent_radius_nm\n")
        handle.write("# h_Ag_nm = coverage_fraction * (4/3) * Rave_nm * exp(2 sigL^2)\n")
        handle.write("# Columns:\n")
        handle.write("# " + " ".join(columns) + "\n")
        for point in points:
            handle.write(" ".join(format_value(point[column]) for column in columns) + "\n")


def write_summary(path: Path, fit: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document: dict[str, Any] = {
        "radius_proxy": RADIUS_PROXY_NAME,
        "formula": FORMULA,
        "linear_fit": fit,
    }
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    try:
        args = parse_args()
        fieldnames, rows = load_rows(args.input_csv)
        check_required_columns(fieldnames)
        radius_column = find_radius_proxy_column(fieldnames)
        points = extract_points(rows, radius_column)
        fit = linear_fit(points)

        write_dat(args.output_dat, points)
        write_summary(args.summary_json, fit)

        print(f"Input CSV: {args.input_csv}")
        print(f"Radius proxy column: {radius_column}")
        print(f"Wrote data: {args.output_dat}")
        print(f"Wrote summary: {args.summary_json}")
        print(
            "Linear fit: "
            f"slope={fit['slope_nm_per_s']:.12g} nm/s, "
            f"intercept={fit['intercept_nm']:.12g} nm, "
            f"r2={fit['r2']:.12g}"
        )
        return 0
    except AfmHagProxyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
