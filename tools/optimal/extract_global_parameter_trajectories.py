#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PARAMETERS = ("rave_nm", "sig_l", "thickness_nm", "effe", "h_ag_nm")
ANOMALY_LOW = 0.7
ANOMALY_HIGH = 1.3


@dataclass(frozen=True)
class RunPath:
    strategy: str
    generation: int
    seed: int
    path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract temporal MMGM global-fit parameter trajectories."
    )
    parser.add_argument("--root", type=Path, required=True, help="Campaign or strategy root.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for extracted data.")
    return parser.parse_args()


def sanitize_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def canonical_strategy_name(name: str) -> str:
    return re.sub(r"_pop_\d+$", "", name)


def parse_generation_seed(path: Path) -> tuple[int, int] | None:
    generation: int | None = None
    seed: int | None = None
    for part in path.parts:
        if part.startswith("gen_"):
            try:
                generation = int(part.removeprefix("gen_"))
            except ValueError:
                return None
        if part.startswith("seed_"):
            try:
                seed = int(part.removeprefix("seed_"))
            except ValueError:
                return None
    if generation is None or seed is None:
        return None
    return generation, seed


def infer_strategy(root: Path, result_path: Path) -> str:
    relative_parts = result_path.relative_to(root).parts
    for index, part in enumerate(relative_parts):
        if part.startswith("gen_"):
            if index == 0:
                return canonical_strategy_name(root.name)
            return canonical_strategy_name(relative_parts[index - 1])
    return canonical_strategy_name(result_path.parent.name)


def discover_runs(root: Path) -> list[RunPath]:
    runs: list[RunPath] = []
    for path in sorted(root.glob("**/global_result.json")):
        parsed = parse_generation_seed(path)
        if parsed is None:
            continue
        generation, seed = parsed
        runs.append(
            RunPath(
                strategy=infer_strategy(root, path),
                generation=generation,
                seed=seed,
                path=path,
            )
        )
    return runs


def finite_or_nan(value: Any) -> float:
    if value is None:
        return math.nan
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return math.nan
    return parsed if math.isfinite(parsed) else math.nan


def format_value(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    return f"{value:.12g}"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def spectrum_rows(run: RunPath, result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    spectra = result.get("spectra")
    if not isinstance(spectra, list):
        return rows
    for spectrum in spectra:
        if not isinstance(spectrum, dict):
            continue
        time_s = spectrum.get("time_s")
        if not isinstance(time_s, int):
            continue
        rows.append(
            {
                "generation": run.generation,
                "seed": run.seed,
                "time": time_s,
                "effe": finite_or_nan(spectrum.get("effe")),
                "thickness_nm": finite_or_nan(spectrum.get("thickness_nm")),
                "h_ag_nm": finite_or_nan(spectrum.get("h_ag_nm")),
                "rave_nm": finite_or_nan(spectrum.get("rave_nm")),
                "sig_l": finite_or_nan(spectrum.get("sig_l")),
            }
        )
    return sorted(rows, key=lambda row: int(row["time"]))


def reference_rows(result: dict[str, Any]) -> dict[int, dict[str, float]]:
    references: dict[int, dict[str, float]] = {}
    spectra = result.get("spectra")
    if not isinstance(spectra, list):
        return references
    for spectrum in spectra:
        if not isinstance(spectrum, dict) or not isinstance(spectrum.get("time_s"), int):
            continue
        time_s = int(spectrum["time_s"])
        prior = spectrum.get("afm_prior_reference")
        reference_source = "afm"
        if not isinstance(prior, dict):
            prior = spectrum.get("thesis_prior_reference")
            reference_source = "thesis"
        if not isinstance(prior, dict):
            continue
        thickness = spectrum.get("afm_thickness_reference")
        thickness_ref = math.nan
        if isinstance(thickness, dict):
            thickness_ref = finite_or_nan(thickness.get("thickness_nm"))
        elif reference_source == "thesis":
            thickness_ref = finite_or_nan(prior.get("thickness_nm"))
        references[time_s] = {
            "rave_ref": finite_or_nan(prior.get("rave_nm")),
            "sigl_ref": finite_or_nan(prior.get("sig_l")),
            "thickness_ref": thickness_ref,
        }
    return references


def write_trajectory(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# generation seed time effe thickness_nm hAg_nm rave_nm sig_l\n")
        for row in sorted(rows, key=lambda item: (item["generation"], item["seed"], item["time"])):
            handle.write(
                "{generation:d} {seed:d} {time:d} {effe} {thickness_nm} {h_ag_nm} {rave_nm} {sig_l}\n".format(
                    generation=int(row["generation"]),
                    seed=int(row["seed"]),
                    time=int(row["time"]),
                    effe=format_value(float(row["effe"])),
                    thickness_nm=format_value(float(row["thickness_nm"])),
                    h_ag_nm=format_value(float(row["h_ag_nm"])),
                    rave_nm=format_value(float(row["rave_nm"])),
                    sig_l=format_value(float(row["sig_l"])),
                )
            )


def write_references(path: Path, rows: dict[int, dict[str, float]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# time rave_ref sigl_ref thickness_ref\n")
        for time_s, values in sorted(rows.items()):
            handle.write(
                f"{time_s:d} {format_value(values['rave_ref'])} "
                f"{format_value(values['sigl_ref'])} {format_value(values['thickness_ref'])}\n"
            )


def parameter_ranges(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    ranges: dict[str, dict[str, float]] = {}
    for parameter in PARAMETERS:
        values = [
            float(row[parameter])
            for row in rows
            if not math.isnan(float(row[parameter]))
        ]
        if values:
            ranges[parameter] = {"min": min(values), "max": max(values)}
        else:
            ranges[parameter] = {"min": math.nan, "max": math.nan}
    return ranges


def run_values_by_time(rows: list[dict[str, Any]]) -> dict[tuple[int, int], dict[int, dict[str, float]]]:
    grouped: dict[tuple[int, int], dict[int, dict[str, float]]] = {}
    for row in rows:
        key = (int(row["generation"]), int(row["seed"]))
        grouped.setdefault(key, {})[int(row["time"])] = {
            parameter: float(row[parameter]) for parameter in PARAMETERS
        }
    return grouped


def anomaly_ratios(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ratios: dict[str, list[dict[str, Any]]] = {parameter: [] for parameter in PARAMETERS}
    for (generation, seed), by_time in run_values_by_time(rows).items():
        if not {20, 30, 50}.issubset(by_time):
            continue
        for parameter in PARAMETERS:
            value_30 = by_time[30][parameter]
            left = by_time[20][parameter]
            right = by_time[50][parameter]
            if any(math.isnan(value) for value in (value_30, left, right)):
                continue
            denominator = 0.5 * (left + right)
            if denominator == 0.0:
                continue
            ratio = value_30 / denominator
            ratios[parameter].append(
                {
                    "generation": generation,
                    "seed": seed,
                    "ratio": ratio,
                    "anomalous": ratio < ANOMALY_LOW or ratio > ANOMALY_HIGH,
                }
            )
    summary: dict[str, Any] = {}
    for parameter, values in ratios.items():
        summary[parameter] = {
            "n_runs": len(values),
            "n_anomalous": sum(1 for value in values if value["anomalous"]),
            "ratios": values,
        }
    return summary


def best_run_metadata(entries: list[dict[str, Any]]) -> dict[str, Any]:
    best = min(entries, key=lambda entry: entry["total_sse"])
    return {
        "generation": best["generation"],
        "seed": best["seed"],
        "total_sse": best["total_sse"],
        "path": best["path"],
    }


def report_lines(manifest: dict[str, Any]) -> list[str]:
    lines = ["=== TEMPORAL PARAMETER TRAJECTORY DIAGNOSTICS ===", ""]
    for strategy in manifest["strategies"]:
        lines.extend(
            [
                f"Strategy: {strategy['name']}",
                f"  runs: {strategy['n_runs']}",
            ]
        )
        if strategy["n_runs"] == 0:
            lines.extend(["  diagnosis: FAILED", ""])
            continue
        best = strategy["best_run"]
        lines.extend(
            [
                f"  best total SSE: {best['total_sse']:.12g}",
                f"  best run: generation {best['generation']}, seed {best['seed']}",
                "  parameter ranges:",
            ]
        )
        for parameter in PARAMETERS:
            values = strategy["parameter_ranges"][parameter]
            lines.append(
                f"    {parameter}: {format_value(values['min'])} to {format_value(values['max'])}"
            )
        lines.append("  30s neighbor-ratio anomaly checks: x(30s)/mean(x20s,x50s)")
        for parameter in PARAMETERS:
            anomaly = strategy["anomaly_ratios"][parameter]
            n_runs = anomaly["n_runs"]
            n_anomalous = anomaly["n_anomalous"]
            if n_runs == 0:
                lines.append(f"    {parameter}: unavailable")
                continue
            marker = "ANOMALOUS" if n_anomalous else "within threshold"
            lines.append(f"    {parameter}: {n_anomalous}/{n_runs} anomalous ({marker})")
        lines.append("")
    return lines


def main() -> int:
    args = parse_args()
    root = args.root
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    runs = discover_runs(root)
    grouped: dict[str, list[RunPath]] = {}
    for run in runs:
        grouped.setdefault(run.strategy, []).append(run)

    manifest: dict[str, Any] = {
        "root": root.as_posix(),
        "output_dir": output_dir.as_posix(),
        "strategies": [],
    }
    for strategy, strategy_runs in sorted(grouped.items()):
        safe_strategy = sanitize_name(strategy)
        all_rows: list[dict[str, Any]] = []
        all_references: dict[int, dict[str, float]] = {}
        run_entries: list[dict[str, Any]] = []

        for run in sorted(strategy_runs, key=lambda item: (item.generation, item.seed, item.path.as_posix())):
            result = read_json(run.path)
            all_rows.extend(spectrum_rows(run, result))
            all_references.update(reference_rows(result))
            objective = result.get("objective")
            total_sse = math.nan
            if isinstance(objective, dict):
                total_sse = finite_or_nan(objective.get("total_sse"))
            run_entries.append(
                {
                    "generation": run.generation,
                    "seed": run.seed,
                    "total_sse": total_sse,
                    "path": run.path.as_posix(),
                    "excluded_times_s": result.get("excluded_times_s", []),
                    "afm_priors_mode": (
                        result.get("afm_priors", {}).get("mode")
                        if isinstance(result.get("afm_priors"), dict)
                        else None
                    ),
                    "afm_sigl_mode": result.get("afm_sigl_mode")
                    or (
                        result.get("afm_priors", {}).get("afm_sigl_mode")
                        if isinstance(result.get("afm_priors"), dict)
                        else None
                    ),
                    "thesis_priors_mode": (
                        result.get("thesis_priors", {}).get("mode")
                        if isinstance(result.get("thesis_priors"), dict)
                        else None
                    ),
                    "thesis_strategy": (
                        result.get("thesis_priors", {}).get("strategy")
                        if isinstance(result.get("thesis_priors"), dict)
                        else None
                    ),
                    "n_parameters": (
                        objective.get("n_parameters")
                        if isinstance(objective, dict)
                        else None
                    ),
                    "optimizer": result.get("optimizer", {}),
                }
            )

        trajectory_file = output_dir / f"trajectory_{safe_strategy}.dat"
        reference_file = output_dir / f"morphology_reference_{safe_strategy}.dat"
        write_trajectory(trajectory_file, all_rows)
        write_references(reference_file, all_references)

        finite_runs = [entry for entry in run_entries if not math.isnan(float(entry["total_sse"]))]
        strategy_entry = {
            "name": strategy,
            "safe_name": safe_strategy,
            "trajectory_file": trajectory_file.as_posix(),
            "reference_file": reference_file.as_posix(),
            "n_runs": len(finite_runs),
            "runs": run_entries,
            "parameter_ranges": parameter_ranges(all_rows),
            "anomaly_ratios": anomaly_ratios(all_rows),
        }
        if finite_runs:
            strategy_entry["best_run"] = best_run_metadata(finite_runs)
        else:
            strategy_entry["best_run"] = None
        manifest["strategies"].append(strategy_entry)

    manifest_path = output_dir / "trajectory_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=True) + "\n", encoding="utf-8")
    report_path = output_dir / "trajectory_summary_report.txt"
    report_path.write_text("\n".join(report_lines(manifest)), encoding="utf-8")

    print(f"Wrote {manifest_path}")
    print(f"Wrote {report_path}")
    for strategy in manifest["strategies"]:
        print(f"Wrote {strategy['trajectory_file']}")
        print(f"Wrote {strategy['reference_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
