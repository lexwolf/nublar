#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path(
    "data/input/optimal/optical_priors/mmgm_single_optical_trusted_branch.json"
)

MODEL_NAME = "mmgm_single"
DISTRIBUTION = "single_lognormal"
SIG_L_ABS_MIN = 0.08
SIG_L_ABS_MAX = 1.0

RAVE_SCALE = (0.80, 1.20)
SIG_L_SCALE = (0.80, 1.20)
THICKNESS_SCALE = (0.75, 1.25)


@dataclass(frozen=True)
class LocalFitReference:
    time_s: int
    effe: float
    thickness_nm: float
    rave_nm: float
    sig_l: float


TRUSTED_BRANCH_REFERENCES: tuple[LocalFitReference, ...] = (
    LocalFitReference(
        time_s=10,
        effe=0.181894,
        thickness_nm=5.69773,
        rave_nm=15.8052,
        sig_l=0.687242,
    ),
    LocalFitReference(
        time_s=20,
        effe=0.217587,
        thickness_nm=5.17879,
        rave_nm=16.0888,
        sig_l=0.617296,
    ),
    LocalFitReference(
        time_s=50,
        effe=0.386844,
        thickness_nm=10.44779,
        rave_nm=13.24950,
        sig_l=0.563185,
    ),
    LocalFitReference(
        time_s=60,
        effe=0.401533,
        thickness_nm=11.85155,
        rave_nm=11.99452,
        sig_l=0.551040,
    ),
)


class OpticalPriorError(RuntimeError):
    """Raised when optical-prior generation cannot proceed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build bounded MMGM morphology priors from trusted optical local fits."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def require_positive_finite(value: float, field: str, time_s: int) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise OpticalPriorError(f"{field} must be positive and finite for time_s={time_s}")


def scaled_bounds(
    reference: float,
    scale: tuple[float, float],
    *,
    absolute_bounds: tuple[float, float] | None = None,
) -> tuple[float, float]:
    low, high = scale
    minimum = low * reference
    maximum = high * reference
    if absolute_bounds is not None:
        abs_low, abs_high = absolute_bounds
        minimum = max(abs_low, minimum)
        maximum = min(abs_high, maximum)
    if minimum > reference or maximum < reference:
        raise OpticalPriorError(
            f"Reference {reference:g} lies outside generated bounds "
            f"[{minimum:g}, {maximum:g}]"
        )
    return minimum, maximum


def parameter_entry(
    reference: float,
    scale: tuple[float, float],
    *,
    absolute_bounds: tuple[float, float] | None = None,
) -> dict[str, float]:
    minimum, maximum = scaled_bounds(reference, scale, absolute_bounds=absolute_bounds)
    return {
        "min": minimum,
        "max": maximum,
        "reference": reference,
    }


def bounds_object(entry_by_parameter: dict[str, dict[str, float]]) -> dict[str, Any]:
    return {
        parameter: {
            "min": values["min"],
            "max": values["max"],
        }
        for parameter, values in entry_by_parameter.items()
    }


def build_document() -> dict[str, Any]:
    bounds_by_time_s: dict[str, Any] = {}
    seen_times: set[int] = set()
    for reference in TRUSTED_BRANCH_REFERENCES:
        if reference.time_s in seen_times:
            raise OpticalPriorError(f"Duplicate time_s: {reference.time_s}")
        seen_times.add(reference.time_s)
        require_positive_finite(reference.effe, "effe", reference.time_s)
        require_positive_finite(reference.thickness_nm, "thickness_nm", reference.time_s)
        require_positive_finite(reference.rave_nm, "Rave_nm", reference.time_s)
        require_positive_finite(reference.sig_l, "sigL", reference.time_s)
        if not SIG_L_ABS_MIN <= reference.sig_l <= SIG_L_ABS_MAX:
            raise OpticalPriorError(
                f"sigL must be between {SIG_L_ABS_MIN:g} and {SIG_L_ABS_MAX:g} "
                f"for time_s={reference.time_s}"
            )

        entry_by_parameter = {
            "rave_nm": parameter_entry(reference.rave_nm, RAVE_SCALE),
            "sig_l": parameter_entry(
                reference.sig_l,
                SIG_L_SCALE,
                absolute_bounds=(SIG_L_ABS_MIN, SIG_L_ABS_MAX),
            ),
            "thickness_nm": parameter_entry(reference.thickness_nm, THICKNESS_SCALE),
        }
        bounds_by_time_s[str(reference.time_s)] = {
            "time_s": reference.time_s,
            "reference_values": {
                "effe": reference.effe,
                "rave_nm": reference.rave_nm,
                "sig_l": reference.sig_l,
                "thickness_nm": reference.thickness_nm,
            },
            "bounds": bounds_object(entry_by_parameter),
            **entry_by_parameter,
        }

    return {
        "schema_version": 1,
        "source": {
            "input_file": "trusted local optical MMGM single-spectrum fits",
            "source_file": "trusted local optical MMGM single-spectrum fits",
            "model": MODEL_NAME,
            "distribution": DISTRIBUTION,
            "columns": ["time_s", "effe", "thickness_nm", "Rave_nm", "sigL"],
            "included_times_s": [reference.time_s for reference in TRUSTED_BRANCH_REFERENCES],
            "excluded_times_s": [30, 40],
        },
        "strategy": {
            "name": "optical_trusted_branch",
            "description": "bounded trusted local optical morphology branch; effe remains free",
            "sig_l_absolute_min": SIG_L_ABS_MIN,
            "sig_l_absolute_max": SIG_L_ABS_MAX,
            "parameter_scales": {
                "rave_nm": {
                    "scale_low": RAVE_SCALE[0],
                    "scale_high": RAVE_SCALE[1],
                },
                "sig_l": {
                    "scale_low": SIG_L_SCALE[0],
                    "scale_high": SIG_L_SCALE[1],
                },
                "thickness_nm": {
                    "scale_low": THICKNESS_SCALE[0],
                    "scale_high": THICKNESS_SCALE[1],
                },
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
    except OpticalPriorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
