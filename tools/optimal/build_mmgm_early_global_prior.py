#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path("data/input/optimal/optical_priors/mmgm_single_early_global.json")

MODEL_NAME = "mmgm_single"
DISTRIBUTION = "single_lognormal"
SIG_L_ABS_MIN = 0.08
SIG_L_ABS_MAX = 1.0


@dataclass(frozen=True)
class EarlyReference:
    time_s: int
    effe_reference: float
    thickness_reference_nm: float
    thickness_bounds_nm: tuple[float, float]
    rave_reference_nm: float
    rave_bounds_nm: tuple[float, float]
    sig_l_reference: float
    sig_l_bounds: tuple[float, float]


EARLY_REFERENCES: tuple[EarlyReference, ...] = (
    EarlyReference(
        time_s=10,
        effe_reference=0.20,
        thickness_reference_nm=5.5,
        thickness_bounds_nm=(4.5, 7.0),
        rave_reference_nm=16.0,
        rave_bounds_nm=(12.8, 19.2),
        sig_l_reference=0.66,
        sig_l_bounds=(0.52, 0.78),
    ),
    EarlyReference(
        time_s=20,
        effe_reference=0.28,
        thickness_reference_nm=5.5,
        thickness_bounds_nm=(4.5, 7.0),
        rave_reference_nm=18.5,
        rave_bounds_nm=(14.8, 22.2),
        sig_l_reference=0.58,
        sig_l_bounds=(0.48, 0.68),
    ),
)


class EarlyPriorError(RuntimeError):
    """Raised when early-regime prior generation cannot proceed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build bounded MMGM early-regime morphology priors."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def require_positive_finite(value: float, field: str, time_s: int) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise EarlyPriorError(f"{field} must be positive and finite for time_s={time_s}")


def require_bounds(
    bounds: tuple[float, float],
    reference: float,
    field: str,
    time_s: int,
) -> None:
    low, high = bounds
    require_positive_finite(low, f"{field}.min", time_s)
    require_positive_finite(high, f"{field}.max", time_s)
    if low >= high:
        raise EarlyPriorError(f"{field} min must be less than max for time_s={time_s}")
    if not low <= reference <= high:
        raise EarlyPriorError(
            f"{field} reference {reference:g} lies outside [{low:g}, {high:g}] "
            f"for time_s={time_s}"
        )


def parameter_entry(reference: float, bounds: tuple[float, float]) -> dict[str, float]:
    return {
        "min": bounds[0],
        "max": bounds[1],
        "reference": reference,
    }


def bounds_object(entry_by_parameter: dict[str, dict[str, float]]) -> dict[str, Any]:
    return {
        parameter: {"min": values["min"], "max": values["max"]}
        for parameter, values in entry_by_parameter.items()
    }


def build_document() -> dict[str, Any]:
    bounds_by_time_s: dict[str, Any] = {}
    seen_times: set[int] = set()
    for reference in EARLY_REFERENCES:
        if reference.time_s in seen_times:
            raise EarlyPriorError(f"Duplicate time_s: {reference.time_s}")
        seen_times.add(reference.time_s)
        require_positive_finite(reference.effe_reference, "effe", reference.time_s)
        require_positive_finite(
            reference.thickness_reference_nm, "thickness_nm", reference.time_s
        )
        require_positive_finite(reference.rave_reference_nm, "Rave_nm", reference.time_s)
        require_positive_finite(reference.sig_l_reference, "sigL", reference.time_s)
        require_bounds(
            reference.thickness_bounds_nm,
            reference.thickness_reference_nm,
            "thickness_nm",
            reference.time_s,
        )
        require_bounds(
            reference.rave_bounds_nm,
            reference.rave_reference_nm,
            "rave_nm",
            reference.time_s,
        )
        require_bounds(
            reference.sig_l_bounds,
            reference.sig_l_reference,
            "sig_l",
            reference.time_s,
        )
        if reference.sig_l_bounds[0] < SIG_L_ABS_MIN or reference.sig_l_bounds[1] > SIG_L_ABS_MAX:
            raise EarlyPriorError(
                f"sig_l bounds must stay within [{SIG_L_ABS_MIN:g}, {SIG_L_ABS_MAX:g}]"
            )

        entry_by_parameter = {
            "rave_nm": parameter_entry(reference.rave_reference_nm, reference.rave_bounds_nm),
            "sig_l": parameter_entry(reference.sig_l_reference, reference.sig_l_bounds),
            "thickness_nm": parameter_entry(
                reference.thickness_reference_nm,
                reference.thickness_bounds_nm,
            ),
        }
        bounds_by_time_s[str(reference.time_s)] = {
            "time_s": reference.time_s,
            "reference_values": {
                "effe": reference.effe_reference,
                "rave_nm": reference.rave_reference_nm,
                "sig_l": reference.sig_l_reference,
                "thickness_nm": reference.thickness_reference_nm,
            },
            "bounds": bounds_object(entry_by_parameter),
            **entry_by_parameter,
        }

    return {
        "schema_version": 1,
        "source": {
            "input_file": "trusted early MMGM free-branch guidance",
            "source_file": "trusted early MMGM free-branch guidance",
            "model": MODEL_NAME,
            "distribution": DISTRIBUTION,
            "columns": ["time_s", "effe", "thickness_nm", "Rave_nm", "sigL"],
            "included_times_s": [reference.time_s for reference in EARLY_REFERENCES],
            "excluded_times_s": [30, 40, 50, 60],
        },
        "strategy": {
            "name": "mmgm_early_bounded",
            "description": "bounded early-regime MMGM morphology guidance; effe remains free",
            "sig_l_absolute_min": SIG_L_ABS_MIN,
            "sig_l_absolute_max": SIG_L_ABS_MAX,
            "parameter_bounds": {
                str(reference.time_s): {
                    "rave_nm": list(reference.rave_bounds_nm),
                    "sig_l": list(reference.sig_l_bounds),
                    "thickness_nm": list(reference.thickness_bounds_nm),
                }
                for reference in EARLY_REFERENCES
            },
        },
        "bounds_by_time_s": bounds_by_time_s,
    }


def main() -> int:
    try:
        args = parse_args()
        document = build_document()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
        return 0
    except EarlyPriorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
