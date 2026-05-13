#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("data/experimental/thesis/chap4-prior.dat")
DEFAULT_OUTPUT_DIR = Path("data/input/optimal/thesis_priors")

MODEL_NAME = "mmgm_single"
DISTRIBUTION = "single_lognormal"
SIG_L_ABS_MIN = 0.08
SIG_L_ABS_MAX = 1.0

STRATEGIES: dict[str, tuple[float, float] | None] = {
    "fixed": None,
    "hard": (0.90, 1.10),
    "soft": (0.75, 1.25),
    "softer": (0.50, 1.50),
}


class ThesisPriorError(RuntimeError):
    """Raised when thesis prior generation cannot proceed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate thesis-derived MMGM single-lognormal prior JSONs."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def require_finite_number(value: str, field: str, line_number: int) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ThesisPriorError(
            f"Field {field!r} on line {line_number} is not numeric: {value!r}"
        ) from exc
    if not math.isfinite(parsed):
        raise ThesisPriorError(
            f"Field {field!r} on line {line_number} must be finite: {value!r}"
        )
    return parsed


def load_rows(path: Path) -> list[dict[str, float | int]]:
    if not path.exists():
        raise ThesisPriorError(f"Input thesis prior file does not exist: {path}")
    if not path.is_file():
        raise ThesisPriorError(f"Input thesis prior path is not a file: {path}")

    rows: list[dict[str, float | int]] = []
    seen_times: set[int] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) != 4:
            raise ThesisPriorError(
                f"Expected 4 columns on line {line_number}, found {len(parts)}"
            )
        time_value = require_finite_number(parts[0], "time_s", line_number)
        if not time_value.is_integer():
            raise ThesisPriorError(f"time_s on line {line_number} must be an integer")
        time_s = int(time_value)
        if time_s in seen_times:
            raise ThesisPriorError(f"Duplicate time_s in thesis prior file: {time_s}")
        seen_times.add(time_s)

        rave_nm = require_finite_number(parts[1], "Rave_nm", line_number)
        sig_l = require_finite_number(parts[2], "sigL_radius", line_number)
        thickness_nm = require_finite_number(parts[3], "thickness_nm", line_number)
        if rave_nm <= 0.0:
            raise ThesisPriorError(f"Rave_nm must be positive for time_s={time_s}")
        if not SIG_L_ABS_MIN <= sig_l <= SIG_L_ABS_MAX:
            raise ThesisPriorError(
                f"sigL_radius for time_s={time_s} must be between "
                f"{SIG_L_ABS_MIN:g} and {SIG_L_ABS_MAX:g}"
            )
        if thickness_nm <= 0.0:
            raise ThesisPriorError(f"thickness_nm must be positive for time_s={time_s}")
        rows.append(
            {
                "time_s": time_s,
                "rave_nm": rave_nm,
                "sig_l": sig_l,
                "thickness_nm": thickness_nm,
            }
        )

    if not rows:
        raise ThesisPriorError(f"No data rows found in thesis prior file: {path}")
    return sorted(rows, key=lambda row: int(row["time_s"]))


def scaled_bounds(reference: float, scale: tuple[float, float]) -> tuple[float, float]:
    low, high = scale
    return low * reference, high * reference


def sig_l_bounds(reference: float, scale: tuple[float, float]) -> tuple[float, float]:
    low, high = scaled_bounds(reference, scale)
    return max(SIG_L_ABS_MIN, low), min(SIG_L_ABS_MAX, high)


def parameter_entry(
    reference: float,
    scale: tuple[float, float] | None,
    *,
    absolute_bounds: tuple[float, float] | None = None,
) -> dict[str, float]:
    if scale is None:
        minimum = maximum = reference
    elif absolute_bounds is None:
        minimum, maximum = scaled_bounds(reference, scale)
    else:
        low, high = scaled_bounds(reference, scale)
        abs_low, abs_high = absolute_bounds
        minimum, maximum = max(abs_low, low), min(abs_high, high)
    if minimum > reference or maximum < reference:
        raise ThesisPriorError(
            f"Reference {reference:g} lies outside generated bounds "
            f"[{minimum:g}, {maximum:g}]"
        )
    return {
        "min": minimum,
        "max": maximum,
        "reference": reference,
    }


def build_document(
    *,
    input_file: Path,
    strategy_name: str,
    scale: tuple[float, float] | None,
    rows: list[dict[str, float | int]],
) -> dict[str, Any]:
    bounds_by_time_s: dict[str, Any] = {}
    for row in rows:
        time_s = int(row["time_s"])
        bounds_by_time_s[str(time_s)] = {
            "time_s": time_s,
            "reference_values": {
                "rave_nm": row["rave_nm"],
                "sig_l": row["sig_l"],
                "thickness_nm": row["thickness_nm"],
            },
            "rave_nm": parameter_entry(float(row["rave_nm"]), scale),
            "sig_l": parameter_entry(
                float(row["sig_l"]),
                scale,
                absolute_bounds=(SIG_L_ABS_MIN, SIG_L_ABS_MAX),
            ),
            "thickness_nm": parameter_entry(float(row["thickness_nm"]), scale),
        }

    strategy: dict[str, Any] = {
        "name": strategy_name,
        "description": (
            "fixed thesis morphology values"
            if scale is None
            else "bounded thesis morphology values"
        ),
        "sig_l_absolute_min": SIG_L_ABS_MIN,
        "sig_l_absolute_max": SIG_L_ABS_MAX,
    }
    if scale is not None:
        strategy["scale_low"] = scale[0]
        strategy["scale_high"] = scale[1]

    return {
        "schema_version": 1,
        "source": {
            "input_file": input_file.as_posix(),
            "model": MODEL_NAME,
            "distribution": DISTRIBUTION,
            "columns": ["time_s", "Rave_nm", "sigL_radius", "thickness_nm"],
        },
        "strategy": strategy,
        "bounds_by_time_s": bounds_by_time_s,
    }


def main() -> int:
    try:
        args = parse_args()
        rows = load_rows(args.input)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for strategy_name, scale in STRATEGIES.items():
            document = build_document(
                input_file=args.input,
                strategy_name=strategy_name,
                scale=scale,
                rows=rows,
            )
            output_path = args.output_dir / f"mmgm_single_thesis_{strategy_name}.json"
            output_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
            print(f"Wrote {output_path}")
        return 0
    except ThesisPriorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
