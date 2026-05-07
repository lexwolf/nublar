#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INPUT_ROOT = Path("data/output/tests/mmgm_single_fixed_proxy_campaign")
OUTPUT_CSV = INPUT_ROOT / "effe_thickness_points.csv"
RESULT_PATTERN = "gen_*/seed_*/mmgm_single/spheres/global_result.json"
COLUMNS = [
    "proxy_name",
    "generation",
    "seed",
    "time_s",
    "spectrum",
    "total_sse",
    "sse",
    "effe",
    "thickness_nm",
    "h_ag_nm",
    "rave_nm",
    "sig_l",
]


@dataclass(frozen=True)
class CampaignRoot:
    path: Path
    proxy_name: str


class ExtractionError(RuntimeError):
    pass


def is_proxy_aware_name(name: str) -> bool:
    return "__fixed_pop_" in name and name.count("__") >= 2


def campaign_sort_key(path: Path) -> tuple[int, str]:
    return (0 if is_proxy_aware_name(path.name) else 1, path.name)


def campaign_roots(input_root: Path) -> list[CampaignRoot]:
    if not input_root.exists():
        raise ExtractionError(f"Input root does not exist: {input_root}")

    by_real_path: dict[Path, Path] = {}
    for child in sorted((path for path in input_root.iterdir() if path.is_dir()), key=campaign_sort_key):
        if not list(child.glob(RESULT_PATTERN)):
            continue
        real_path = child.resolve()
        by_real_path.setdefault(real_path, child)

    roots = [CampaignRoot(path=path, proxy_name=path.name) for path in by_real_path.values()]
    if not roots:
        raise ExtractionError(f"No campaign result roots found under {input_root}")
    return sorted(roots, key=lambda root: root.proxy_name)


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"Could not parse JSON {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ExtractionError(f"Expected JSON object in {path}")
    return raw


def result_context(path: Path) -> tuple[int, int]:
    generation_match = re.search(r"/gen_(\d+)/", path.as_posix())
    seed_match = re.search(r"/seed_(\d+)/", path.as_posix())
    if generation_match is None or seed_match is None:
        raise ExtractionError(f"Could not infer generation/seed from {path}")
    return int(generation_match.group(1)), int(seed_match.group(1))


def finite_number(value: Any, field: str, path: Path) -> float:
    if not isinstance(value, int | float):
        raise ExtractionError(f"Expected numeric field {field!r} in {path}")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ExtractionError(f"Expected finite field {field!r} in {path}")
    return parsed


def extract_rows(root: CampaignRoot) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result_path in sorted(root.path.glob(RESULT_PATTERN)):
        raw = load_json(result_path)
        generation, seed = result_context(result_path)
        objective = raw.get("objective")
        spectra = raw.get("spectra")
        if not isinstance(objective, dict):
            raise ExtractionError(f"Missing object field 'objective' in {result_path}")
        if not isinstance(spectra, list):
            raise ExtractionError(f"Missing list field 'spectra' in {result_path}")
        total_sse = finite_number(objective.get("total_sse"), "objective.total_sse", result_path)

        for spectrum in spectra:
            if not isinstance(spectrum, dict):
                raise ExtractionError(f"Expected spectrum object in {result_path}")
            rows.append(
                {
                    "proxy_name": root.proxy_name,
                    "generation": str(generation),
                    "seed": str(seed),
                    "time_s": str(int(finite_number(spectrum.get("time_s"), "time_s", result_path))),
                    "spectrum": str(spectrum.get("spectrum", "")),
                    "total_sse": f"{total_sse:.17g}",
                    "sse": f"{finite_number(spectrum.get('sse'), 'sse', result_path):.17g}",
                    "effe": f"{finite_number(spectrum.get('effe'), 'effe', result_path):.17g}",
                    "thickness_nm": f"{finite_number(spectrum.get('thickness_nm'), 'thickness_nm', result_path):.17g}",
                    "h_ag_nm": f"{finite_number(spectrum.get('h_ag_nm'), 'h_ag_nm', result_path):.17g}",
                    "rave_nm": f"{finite_number(spectrum.get('rave_nm'), 'rave_nm', result_path):.17g}",
                    "sig_l": f"{finite_number(spectrum.get('sig_l'), 'sig_l', result_path):.17g}",
                }
            )
    return rows


def main() -> int:
    try:
        roots = campaign_roots(INPUT_ROOT)
        rows: list[dict[str, str]] = []
        for root in roots:
            rows.extend(extract_rows(root))
        if not rows:
            raise ExtractionError(f"No rows extracted from {INPUT_ROOT}")

        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {OUTPUT_CSV} ({len(rows)} rows)")
        return 0
    except ExtractionError as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
