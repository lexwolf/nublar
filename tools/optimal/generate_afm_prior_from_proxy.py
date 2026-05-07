#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_INPUT_CSV = Path("data/input/experimental/model_input.csv")
DEFAULT_OUTPUT_DIR = Path("data/input/optimal/afm_priors")

MODEL_NAME = "mmgm_single"
DISTRIBUTION = "single_lognormal"
STRATEGY_NAME = "proxy_generated"

RADIUS_MARGIN_LOW = 0.75
RADIUS_MARGIN_HIGH = 1.5
SIG_L_MIN = 0.1
SIG_L_MAX = 0.8

REQUIRED_COLUMNS = (
    "time_s",
    "single_lognormal_sigL",
    "single_lognormal_std_nm",
    "single_lognormal_fit_method",
    "effe_proxy",
    "equivalent_thickness_nm",
    "coverage_fraction",
)


class AfmProxyPriorError(RuntimeError):
    """Raised when AFM proxy-prior generation cannot proceed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate fixed-mode AFM priors for every radius proxy in model_input.csv."
    )
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def load_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise AfmProxyPriorError(f"Input CSV does not exist: {path}")
    if not path.is_file():
        raise AfmProxyPriorError(f"Input CSV is not a file: {path}")

    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AfmProxyPriorError(f"Input CSV has no header: {path}")
        missing = [name for name in REQUIRED_COLUMNS if name not in reader.fieldnames]
        if missing:
            raise AfmProxyPriorError(
                "Input CSV is missing required columns: " + ", ".join(missing)
            )
        rows = list(reader)
    if not rows:
        raise AfmProxyPriorError(f"Input CSV contains no rows: {path}")
    return list(reader.fieldnames), rows


def radius_proxy_columns(fieldnames: list[str]) -> list[tuple[str, str]]:
    columns = []
    for field in fieldnames:
        if not field.startswith("Rave_"):
            continue
        proxy_name = field.removeprefix("Rave_")
        if not proxy_name:
            continue
        columns.append((proxy_name, field))
    if not columns:
        raise AfmProxyPriorError("No radius proxy columns found with prefix 'Rave_'")
    return columns


def require_finite_number(value: str, field: str, time_s: int | None = None) -> float:
    context = f" for time_s={time_s}" if time_s is not None else ""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise AfmProxyPriorError(f"Field {field!r}{context} is not numeric: {value!r}") from exc
    if not math.isfinite(parsed):
        raise AfmProxyPriorError(f"Field {field!r}{context} must be finite: {value!r}")
    return parsed


def parse_time_s(value: str) -> int:
    parsed = require_finite_number(value, "time_s")
    if not parsed.is_integer():
        raise AfmProxyPriorError(f"Field 'time_s' must be an integer: {value!r}")
    return int(parsed)


def output_filename(proxy_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", proxy_name):
        raise AfmProxyPriorError(f"Unsafe radius proxy name for file path: {proxy_name!r}")
    return f"mmgm_single_{proxy_name}.json"


def build_document(
    *,
    input_csv: Path,
    proxy_name: str,
    proxy_field: str,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    seen_times: set[int] = set()
    bounds_by_time_s: dict[str, Any] = {}

    for row in rows:
        time_s = parse_time_s(row["time_s"])
        if time_s in seen_times:
            raise AfmProxyPriorError(f"Duplicate time_s in input CSV: {time_s}")
        seen_times.add(time_s)

        reference = require_finite_number(row.get(proxy_field, ""), proxy_field, time_s)
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

        if reference <= 0.0:
            raise AfmProxyPriorError(f"Field {proxy_field!r} must be positive for time_s={time_s}")
        if sig_l < 0.0:
            raise AfmProxyPriorError(
                f"Field 'single_lognormal_sigL' must be non-negative for time_s={time_s}"
            )
        if single_std_nm < 0.0:
            raise AfmProxyPriorError(
                f"Field 'single_lognormal_std_nm' must be non-negative for time_s={time_s}"
            )

        bounds_by_time_s[str(time_s)] = {
            "rave_nm": {
                "min": RADIUS_MARGIN_LOW * reference,
                "max": RADIUS_MARGIN_HIGH * reference,
                "reference": reference,
                "source_field": proxy_field,
            },
            "sig_l": {
                "min": SIG_L_MIN,
                "max": SIG_L_MAX,
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
            "input_csv": input_csv.as_posix(),
            "radius_proxy_name": proxy_name,
            "distribution": DISTRIBUTION,
            "model": MODEL_NAME,
        },
        "strategy": {
            "name": STRATEGY_NAME,
            "radius_margin_low": RADIUS_MARGIN_LOW,
            "radius_margin_high": RADIUS_MARGIN_HIGH,
            "sig_l_min": SIG_L_MIN,
            "sig_l_max": SIG_L_MAX,
        },
        "bounds_by_time_s": dict(
            sorted(bounds_by_time_s.items(), key=lambda item: int(item[0]))
        ),
    }


def main() -> int:
    try:
        args = parse_args()
        fieldnames, rows = load_rows(args.input_csv)
        proxy_columns = radius_proxy_columns(fieldnames)
        args.output_dir.mkdir(parents=True, exist_ok=True)

        print("radius_proxy_name, source_field, output_json")
        for proxy_name, proxy_field in proxy_columns:
            document = build_document(
                input_csv=args.input_csv,
                proxy_name=proxy_name,
                proxy_field=proxy_field,
                rows=rows,
            )
            output_path = args.output_dir / output_filename(proxy_name)
            if output_path.exists():
                desired_text = json.dumps(document, indent=2) + "\n"
                if output_path.read_text(encoding="utf-8") == desired_text:
                    print(f"{proxy_name}, {proxy_field}, {output_path} (exists unchanged)")
                    continue
                raise AfmProxyPriorError(
                    f"Refusing to overwrite existing AFM prior JSON with different content: {output_path}"
                )
            output_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
            print(f"{proxy_name}, {proxy_field}, {output_path}")
        return 0
    except AfmProxyPriorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
