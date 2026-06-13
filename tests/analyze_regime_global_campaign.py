#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


PARAMETERS = ("effe", "thickness_nm", "h_ag_nm", "rave_nm", "sig_l")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize diagnostic early/late global optimization campaigns."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--label", type=str, required=True)
    return parser.parse_args()


def finite_float(value: Any, source: Path, key: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Missing or non-numeric {key} in {source}: {value!r}") from exc
    if not math.isfinite(parsed):
        raise SystemExit(f"Non-finite {key} in {source}: {value!r}")
    return parsed


def optional_float(value: Any) -> float:
    if value is None:
        return math.nan
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return math.nan
    return parsed if math.isfinite(parsed) else math.nan


def parse_generation_seed(path: Path) -> tuple[int, int]:
    generation: int | None = None
    seed: int | None = None
    for part in path.parts:
        if part.startswith("gen_"):
            generation = int(part.removeprefix("gen_"))
        if part.startswith("seed_"):
            seed = int(part.removeprefix("seed_"))
    if generation is None or seed is None:
        raise SystemExit(f"Could not infer generation/seed from {path}")
    return generation, seed


def load_result(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    spectra = result.get("spectra")
    if not isinstance(spectra, list) or not spectra:
        raise SystemExit(f"Missing spectra in {path}")
    return result


def result_rows(path: Path) -> list[dict[str, Any]]:
    generation, seed = parse_generation_seed(path)
    result = load_result(path)
    objective = result.get("objective", {})
    total_sse = finite_float(objective.get("total_sse"), path, "objective.total_sse")
    total_points = finite_float(
        objective.get("total_finite_points"),
        path,
        "objective.total_finite_points",
    )
    rows: list[dict[str, Any]] = []
    for spectrum in result["spectra"]:
        if not isinstance(spectrum, dict):
            continue
        time_s = int(spectrum["time_s"])
        row: dict[str, Any] = {
            "generation": generation,
            "seed": seed,
            "time_s": time_s,
            "model": result.get("model", ""),
            "geometry": result.get("geometry", ""),
            "total_sse": total_sse,
            "total_rmse": math.sqrt(total_sse / total_points),
            "sse": finite_float(spectrum.get("sse"), path, f"spectra[{time_s}].sse"),
        }
        for parameter in PARAMETERS:
            row[parameter] = optional_float(spectrum.get(parameter))
        rows.append(row)
    return rows


def fmt(value: float) -> str:
    if math.isnan(value):
        return "NA"
    return f"{value:.12g}"


def rel_spread(values: list[float]) -> float:
    finite_values = [value for value in values if math.isfinite(value)]
    if not finite_values:
        return math.nan
    mean_value = sum(finite_values) / len(finite_values)
    if mean_value == 0.0:
        return 0.0 if max(finite_values) == min(finite_values) else math.inf
    return (max(finite_values) - min(finite_values)) / abs(mean_value)


def write_summary(root: Path, rows: list[dict[str, Any]]) -> Path:
    path = root / "summary_table.csv"
    columns = [
        "generation",
        "seed",
        "time_s",
        "model",
        "geometry",
        "total_sse",
        "total_rmse",
        "sse",
        "effe",
        "thickness_nm",
        "rave_nm",
        "sig_l",
        "h_ag_nm",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def build_report(label: str, rows: list[dict[str, Any]], summary_path: Path) -> str:
    lines = [f"=== {label} ===", ""]
    lines.append(f"Accepted spectrum rows: {len(rows)}")
    runs = sorted({(int(row["generation"]), int(row["seed"])) for row in rows})
    lines.append(f"Accepted runs: {len(runs)}")
    lines.append(f"Summary table: {summary_path.as_posix()}")
    lines.append("")

    by_run: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_run[(int(row["generation"]), int(row["seed"]))].append(row)

    lines.append("=== RUN SUMMARY ===")
    for (generation, seed), run_rows in sorted(by_run.items()):
        total_sse = float(run_rows[0]["total_sse"])
        total_rmse = float(run_rows[0]["total_rmse"])
        lines.append(
            f"generation {generation}, seed {seed}: total_SSE={total_sse:.8g}, "
            f"total_RMSE={total_rmse:.8g}"
        )
        for row in sorted(run_rows, key=lambda item: int(item["time_s"])):
            parts = [
                f"{int(row['time_s'])}s",
                f"SSE={float(row['sse']):.8g}",
                f"effe={fmt(float(row['effe']))}",
                f"thickness={fmt(float(row['thickness_nm']))}",
                f"hAg={fmt(float(row['h_ag_nm']))}",
            ]
            if math.isfinite(float(row["rave_nm"])):
                parts.append(f"Rave={fmt(float(row['rave_nm']))}")
            if math.isfinite(float(row["sig_l"])):
                parts.append(f"sigL={fmt(float(row['sig_l']))}")
            lines.append("  " + ", ".join(parts))
    lines.append("")

    lines.append("=== SEED SPREAD BY TIME ===")
    by_generation_time: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_generation_time[(int(row["generation"]), int(row["time_s"]))].append(row)
    for (generation, time_s), group in sorted(by_generation_time.items()):
        lines.append(f"generation {generation}, {time_s}s:")
        for parameter in PARAMETERS:
            values = [float(row[parameter]) for row in group]
            spread = rel_spread(values)
            if math.isfinite(spread):
                lines.append(f"  {parameter}: {100.0 * spread:.2f}%")
    lines.append("")
    lines.append("Interpretation: diagnostic only; compare curve overlays and SSE against prior campaign outputs before assigning regimes.")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    result_files = sorted(args.root.glob("gen_*/seed_*/*/*/global_result.json"))
    if not result_files:
        raise SystemExit(f"No global_result.json files found under {args.root}")
    rows: list[dict[str, Any]] = []
    for path in result_files:
        rows.extend(result_rows(path))
    rows.sort(key=lambda row: (int(row["generation"]), int(row["seed"]), int(row["time_s"])))
    summary_path = write_summary(args.root, rows)
    report = build_report(args.label, rows, summary_path)
    report_path = args.root / "global_report.txt"
    report_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
