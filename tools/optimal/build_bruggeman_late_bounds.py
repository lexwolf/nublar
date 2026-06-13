#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("data/input/optimal/bounds.json")
DEFAULT_OUTPUT = Path("data/input/optimal/bounds_bruggeman_late_global.json")


class BruggemanBoundsError(RuntimeError):
    """Raised when late-regime Bruggeman bounds cannot be generated."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build broad late-regime Bruggeman bounds for diagnostic global fits."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BruggemanBoundsError(f"{label} must be an object")
    return value


def build_bounds(input_path: Path) -> dict[str, Any]:
    if not input_path.is_file():
        raise BruggemanBoundsError(f"Input bounds JSON does not exist: {input_path}")
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    document = deepcopy(raw)
    models = require_mapping(document.get("models"), "models")
    bruggeman = require_mapping(models.get("bruggeman"), "models.bruggeman")
    native = require_mapping(
        bruggeman.get("native_fit_parameters"),
        "models.bruggeman.native_fit_parameters",
    )
    effe = require_mapping(native.get("effe"), "bruggeman.effe")
    thickness = require_mapping(native.get("thickness_nm"), "bruggeman.thickness_nm")
    optimizer = require_mapping(bruggeman.get("optimizer"), "bruggeman.optimizer")

    effe["min"] = 0.15
    effe["max"] = 0.95
    thickness["min"] = 3.0
    thickness["max"] = 120.0
    thickness["transform"] = "log"
    optimizer["global_method"] = "differential_evolution"
    optimizer.setdefault("differential_evolution", {})
    de = require_mapping(
        optimizer["differential_evolution"],
        "bruggeman.optimizer.differential_evolution",
    )
    de["population_size"] = 64
    de["max_generations"] = 400
    de.setdefault("mutation_min", 0.5)
    de.setdefault("mutation_max", 1.0)
    de.setdefault("recombination", 0.7)

    document["description"] = (
        "Bounds and fitting configuration for transmittance-model inverse scans in "
        "Nublar. This copy broadens late-regime Bruggeman thickness bounds while "
        "preserving the physical global structure."
    )
    document["placement_recommendation"] = DEFAULT_OUTPUT.as_posix()
    return document


def main() -> int:
    try:
        args = parse_args()
        document = build_bounds(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
        return 0
    except (BruggemanBoundsError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
