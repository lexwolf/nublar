#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("data/output/tests/mmgm_single_global_seed_stability")
TIMES_S = (10, 20, 30, 40, 50, 60)
PARAMETERS = ("h_ag", "effe", "thickness", "rave", "sig_l")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze global MMGM single-lognormal seed-stability outputs."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    return parser.parse_args()


def rel_spread(values: list[float]) -> float:
    if not values:
        return math.nan
    minimum = min(values)
    maximum = max(values)
    mean_value = sum(values) / len(values)
    if mean_value == 0.0:
        return 0.0 if maximum == minimum else math.inf
    return (maximum - minimum) / abs(mean_value)


def format_percent(value: float) -> str:
    if math.isnan(value):
        return "n/a"
    if math.isinf(value):
        return "inf %"
    return f"{100.0 * value:.2f}%"


def required_float(mapping: dict[str, Any], key: str, source: Path) -> float:
    if key not in mapping:
        raise SystemExit(f"Missing {key} in {source}")
    value = float(mapping[key])
    if not math.isfinite(value):
        raise SystemExit(f"Non-finite {key} in {source}: {mapping[key]!r}")
    return value


def parse_generation_seed(path: Path) -> tuple[int, int]:
    try:
        generation = int(path.parents[3].name.removeprefix("gen_"))
        seed = int(path.parents[2].name.removeprefix("seed_"))
    except (IndexError, ValueError) as exc:
        raise SystemExit(f"Unexpected result path layout: {path}") from exc
    return generation, seed


def load_result(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    spectra = result.get("spectra", [])
    if len(spectra) != len(TIMES_S):
        raise SystemExit(
            f"Expected {len(TIMES_S)} spectra in {path}, found {len(spectra)}"
        )
    spectra_by_time = {int(item["time_s"]): item for item in spectra}
    missing = [time_s for time_s in TIMES_S if time_s not in spectra_by_time]
    if missing:
        raise SystemExit(f"Missing time(s) {missing} in {path}")
    return result


def row_from_result(path: Path) -> dict[str, float | int]:
    generation, seed = parse_generation_seed(path)
    result = load_result(path)
    objective = result.get("objective", {})
    total_sse = required_float(objective, "total_sse", path)
    finite_points = required_float(objective, "total_finite_points", path)
    if finite_points <= 0:
        raise SystemExit(f"Invalid total_finite_points in {path}: {finite_points}")

    row: dict[str, float | int] = {
        "generation": generation,
        "seed": seed,
        "total_sse": total_sse,
        "total_rmse": math.sqrt(total_sse / finite_points),
        "n_parameters": int(objective.get("n_parameters", 0)),
    }
    spectra_by_time = {int(item["time_s"]): item for item in result["spectra"]}
    for time_s in TIMES_S:
        suffix = f"{time_s}s"
        item = spectra_by_time[time_s]
        row[f"h_ag_{suffix}"] = required_float(item, "h_ag_nm", path)
        row[f"effe_{suffix}"] = required_float(item, "effe", path)
        row[f"thickness_{suffix}"] = required_float(item, "thickness_nm", path)
        row[f"rave_{suffix}"] = required_float(item, "rave_nm", path)
        row[f"sig_l_{suffix}"] = required_float(item, "sig_l", path)
    return row


def summary_columns() -> list[str]:
    columns = ["generation", "seed", "total_sse", "total_rmse", "n_parameters"]
    for prefix in PARAMETERS:
        columns.extend(f"{prefix}_{time_s}s" for time_s in TIMES_S)
    return columns


def write_summary(root: Path, rows: list[dict[str, float | int]]) -> Path:
    path = root / "global_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_columns())
        writer.writeheader()
        writer.writerows(rows)
    return path


def max_rel_spread(rows: list[dict[str, float | int]], prefix: str) -> float:
    spreads = [
        rel_spread([float(row[f"{prefix}_{time_s}s"]) for row in rows])
        for time_s in TIMES_S
    ]
    return max(spreads)


def stability_rows(
    rows: list[dict[str, float | int]]
) -> list[dict[str, float | int]]:
    grouped: dict[int, list[dict[str, float | int]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["generation"])].append(row)

    output_rows: list[dict[str, float | int]] = []
    for generation, group in sorted(grouped.items()):
        total_sse_values = [float(row["total_sse"]) for row in group]
        output_rows.append(
            {
                "generation": generation,
                "n_runs": len(group),
                "total_sse_min": min(total_sse_values),
                "total_sse_max": max(total_sse_values),
                "total_sse_rel_spread": rel_spread(total_sse_values),
                "h_ag_rel_spread_max": max_rel_spread(group, "h_ag"),
                "effe_rel_spread_max": max_rel_spread(group, "effe"),
                "thickness_rel_spread_max": max_rel_spread(group, "thickness"),
                "rave_rel_spread_max": max_rel_spread(group, "rave"),
                "sig_l_rel_spread_max": max_rel_spread(group, "sig_l"),
            }
        )
    return output_rows


def write_stability(
    root: Path, rows: list[dict[str, float | int]]
) -> Path:
    path = root / "global_stability_by_generation.csv"
    columns = [
        "generation",
        "n_runs",
        "total_sse_min",
        "total_sse_max",
        "total_sse_rel_spread",
        "h_ag_rel_spread_max",
        "effe_rel_spread_max",
        "thickness_rel_spread_max",
        "rave_rel_spread_max",
        "sig_l_rel_spread_max",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def h_ag_is_monotonic(row: dict[str, float | int]) -> bool:
    values = [float(row[f"h_ag_{time_s}s"]) for time_s in TIMES_S]
    return all(left <= right for left, right in zip(values, values[1:]))


def max_parameter_spread(row: dict[str, float | int]) -> float:
    return max(
        float(row[key])
        for key in (
            "h_ag_rel_spread_max",
            "effe_rel_spread_max",
            "thickness_rel_spread_max",
            "rave_rel_spread_max",
            "sig_l_rel_spread_max",
        )
    )


def classify(row: dict[str, float | int]) -> str:
    sse_spread = float(row["total_sse_rel_spread"])
    parameter_spread = max_parameter_spread(row)
    if sse_spread > 0.10:
        return "UNSTABLE"
    if sse_spread < 0.01 and parameter_spread < 0.10:
        return "STABLE"
    if sse_spread < 0.05 and parameter_spread > 0.50:
        return "DEGENERATE"
    if sse_spread < 0.05 and parameter_spread < 0.30:
        return "WEAKLY STABLE"
    return "UNSTABLE"


def build_report(
    summary: list[dict[str, float | int]],
    stability: list[dict[str, float | int]],
) -> str:
    lines: list[str] = ["=== GLOBAL MMGM SINGLE SEED STABILITY ===", ""]
    rows_by_generation = {int(row["generation"]): row for row in stability}
    summary_by_generation: dict[int, list[dict[str, float | int]]] = defaultdict(list)
    for row in summary:
        summary_by_generation[int(row["generation"])].append(row)

    for generation in sorted(rows_by_generation):
        row = rows_by_generation[generation]
        lines.append(f"Generation {generation}:")
        lines.append(
            f"  total SSE spread: {format_percent(float(row['total_sse_rel_spread']))}"
        )
        lines.append(
            f"  max hAg relative spread: {format_percent(float(row['h_ag_rel_spread_max']))}"
        )
        lines.append(
            f"  max rave relative spread: {format_percent(float(row['rave_rel_spread_max']))}"
        )
        lines.append(
            f"  max sigL relative spread: {format_percent(float(row['sig_l_rel_spread_max']))}"
        )
        lines.append("")

    lines.append("=== BEST RUN PER GENERATION ===")
    for generation in sorted(summary_by_generation):
        best = min(summary_by_generation[generation], key=lambda row: float(row["total_sse"]))
        lines.append(
            f"gen {generation}: seed {int(best['seed'])}, "
            f"total_SSE {float(best['total_sse']):.8g}"
        )
    lines.append("")

    lines.append("=== hAg MONOTONICITY CHECK ===")
    monotonic_failures = []
    for row in summary:
        ok = h_ag_is_monotonic(row)
        label = (
            f"gen {int(row['generation'])}, seed {int(row['seed'])}: "
            f"{'monotonic' if ok else 'NOT MONOTONIC'}"
        )
        lines.append(label)
        if not ok:
            monotonic_failures.append(label)
    lines.append("")

    lines.append("=== FINAL DIAGNOSIS ===")
    if monotonic_failures:
        lines.append("UNSTABLE")
        lines.append("Reason: at least one run violates hAg monotonicity.")
    elif stability:
        final_generation = max(int(row["generation"]) for row in stability)
        final_row = rows_by_generation[final_generation]
        diagnosis = classify(final_row)
        lines.append(diagnosis)
        lines.append(
            "Basis: latest generation "
            f"{final_generation}, total SSE spread "
            f"{format_percent(float(final_row['total_sse_rel_spread']))}, "
            "max parameter spread "
            f"{format_percent(max_parameter_spread(final_row))}."
        )
    else:
        lines.append("UNSTABLE")
        lines.append("Reason: no stability rows were available.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = args.root
    json_files = sorted(
        root.glob("gen_*/seed_*/mmgm_single/spheres/global_result.json")
    )
    if not json_files:
        raise SystemExit(f"No global_result.json files found under {root}")

    rows = [row_from_result(path) for path in json_files]
    rows.sort(key=lambda row: (int(row["generation"]), int(row["seed"])))
    stability = stability_rows(rows)

    summary_path = write_summary(root, rows)
    stability_path = write_stability(root, stability)
    report = build_report(rows, stability)
    report_path = root / "global_report.txt"
    report_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"Wrote {summary_path}")
    print(f"Wrote {stability_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
