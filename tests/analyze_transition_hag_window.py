#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TARGET_TIMES = (30, 40)
HAG_MIN_NM = 1.0
HAG_MAX_NM = 3.0


@dataclass(frozen=True)
class SpectrumRow:
    time_s: int
    sse: float
    effe: float
    thickness_nm: float
    h_ag_nm: float
    rave_nm: float
    sig_l: float
    spectrum: str


@dataclass(frozen=True)
class Run:
    generation: int
    seed: int
    total_sse: float
    total_rmse: float
    result_path: Path
    spectra: tuple[SpectrumRow, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze MMGM 30s/40s transition-region hAg-window campaign outputs."
    )
    parser.add_argument("--root", type=Path, default=Path("data/output/tests/mmgm_transition_hag_window"))
    return parser.parse_args()


def finite_float(value: Any, label: str, path: Path) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Missing or non-numeric {label} in {path}: {value!r}") from exc
    if not math.isfinite(parsed):
        raise SystemExit(f"Non-finite {label} in {path}: {value!r}")
    return parsed


def parse_generation_seed(path: Path) -> tuple[int, int]:
    generation: int | None = None
    seed: int | None = None
    for part in path.parts:
        if part.startswith("gen_"):
            generation = int(part.removeprefix("gen_"))
        elif part.startswith("seed_"):
            seed = int(part.removeprefix("seed_"))
    if generation is None or seed is None:
        raise SystemExit(f"Could not infer generation/seed from {path}")
    return generation, seed


def load_run(path: Path) -> Run:
    raw = json.loads(path.read_text(encoding="utf-8"))
    generation, seed = parse_generation_seed(path)
    objective = raw.get("objective", {})
    total_sse = finite_float(objective.get("total_sse"), "objective.total_sse", path)
    total_points = finite_float(
        objective.get("total_finite_points"),
        "objective.total_finite_points",
        path,
    )
    spectra_raw = raw.get("spectra")
    if not isinstance(spectra_raw, list) or not spectra_raw:
        raise SystemExit(f"Missing spectra in {path}")
    rows: list[SpectrumRow] = []
    for item in spectra_raw:
        if not isinstance(item, dict):
            raise SystemExit(f"Malformed spectrum entry in {path}")
        time_s = int(item["time_s"])
        rows.append(
            SpectrumRow(
                time_s=time_s,
                sse=finite_float(item.get("sse"), f"spectra[{time_s}].sse", path),
                effe=finite_float(item.get("effe"), f"spectra[{time_s}].effe", path),
                thickness_nm=finite_float(
                    item.get("thickness_nm"),
                    f"spectra[{time_s}].thickness_nm",
                    path,
                ),
                h_ag_nm=finite_float(item.get("h_ag_nm"), f"spectra[{time_s}].h_ag_nm", path),
                rave_nm=finite_float(item.get("rave_nm"), f"spectra[{time_s}].rave_nm", path),
                sig_l=finite_float(item.get("sig_l"), f"spectra[{time_s}].sig_l", path),
                spectrum=str(item.get("spectrum", "")),
            )
        )
    times = tuple(sorted(row.time_s for row in rows))
    if times != TARGET_TIMES:
        raise SystemExit(f"Expected only {TARGET_TIMES} in {path}, found {times}")
    return Run(
        generation=generation,
        seed=seed,
        total_sse=total_sse,
        total_rmse=math.sqrt(total_sse / total_points),
        result_path=path,
        spectra=tuple(sorted(rows, key=lambda row: row.time_s)),
    )


def classify_parameter(row: SpectrumRow) -> str:
    labels: list[str] = []
    if row.rave_nm >= 100.0:
        labels.append("giant_Rave")
    elif row.rave_nm >= 50.0:
        labels.append("large_Rave")
    elif row.rave_nm <= 8.0:
        labels.append("small_Rave")
    else:
        labels.append("moderate_Rave")

    if row.sig_l >= 1.0:
        labels.append("large_sigL")
    elif row.sig_l <= 0.15:
        labels.append("narrow_sigL")
    else:
        labels.append("moderate_sigL")

    if row.thickness_nm <= 10.0 and row.effe >= 0.20:
        labels.append("thin_high_effe")
    elif row.thickness_nm >= 30.0 and row.effe <= 0.10:
        labels.append("thick_low_effe")
    elif row.thickness_nm <= 10.0:
        labels.append("thin")
    elif row.thickness_nm >= 30.0:
        labels.append("thick")
    else:
        labels.append("intermediate_thickness")
    return "+".join(labels)


def row_dict(run: Run, spectrum: SpectrumRow) -> dict[str, Any]:
    return {
        "rank": "",
        "generation": run.generation,
        "seed": run.seed,
        "time_s": spectrum.time_s,
        "total_sse": run.total_sse,
        "total_rmse": run.total_rmse,
        "sse": spectrum.sse,
        "effe": spectrum.effe,
        "thickness_nm": spectrum.thickness_nm,
        "h_ag_nm": spectrum.h_ag_nm,
        "rave_nm": spectrum.rave_nm,
        "sig_l": spectrum.sig_l,
        "cluster": classify_parameter(spectrum),
        "result_path": run.result_path.as_posix(),
    }


def write_ranked_runs(root: Path, runs: list[Run]) -> Path:
    path = root / "ranked_runs.csv"
    columns = [
        "rank",
        "generation",
        "seed",
        "total_sse",
        "total_rmse",
        "h_ag_30s",
        "h_ag_40s",
        "effe_30s",
        "effe_40s",
        "thickness_30s",
        "thickness_40s",
        "rave_30s",
        "rave_40s",
        "sig_l_30s",
        "sig_l_40s",
        "cluster_30s",
        "cluster_40s",
        "result_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for rank, run in enumerate(runs, start=1):
            by_time = {row.time_s: row for row in run.spectra}
            writer.writerow(
                {
                    "rank": rank,
                    "generation": run.generation,
                    "seed": run.seed,
                    "total_sse": f"{run.total_sse:.17g}",
                    "total_rmse": f"{run.total_rmse:.17g}",
                    "h_ag_30s": f"{by_time[30].h_ag_nm:.17g}",
                    "h_ag_40s": f"{by_time[40].h_ag_nm:.17g}",
                    "effe_30s": f"{by_time[30].effe:.17g}",
                    "effe_40s": f"{by_time[40].effe:.17g}",
                    "thickness_30s": f"{by_time[30].thickness_nm:.17g}",
                    "thickness_40s": f"{by_time[40].thickness_nm:.17g}",
                    "rave_30s": f"{by_time[30].rave_nm:.17g}",
                    "rave_40s": f"{by_time[40].rave_nm:.17g}",
                    "sig_l_30s": f"{by_time[30].sig_l:.17g}",
                    "sig_l_40s": f"{by_time[40].sig_l:.17g}",
                    "cluster_30s": classify_parameter(by_time[30]),
                    "cluster_40s": classify_parameter(by_time[40]),
                    "result_path": run.result_path.as_posix(),
                }
            )
    return path


def write_spectrum_table(root: Path, runs: list[Run]) -> Path:
    path = root / "spectrum_parameter_table.csv"
    columns = list(row_dict(runs[0], runs[0].spectra[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for rank, run in enumerate(runs, start=1):
            for spectrum in run.spectra:
                row = row_dict(run, spectrum)
                row["rank"] = rank
                writer.writerow(row)
    return path


def spread(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else 0.5 * (ordered[mid - 1] + ordered[mid])
    return {
        "min": ordered[0],
        "median": median,
        "max": ordered[-1],
        "mean": sum(ordered) / len(ordered),
    }


def write_spread_diagnostics(root: Path, runs: list[Run]) -> Path:
    path = root / "parameter_spread_diagnostics.csv"
    columns = ["time_s", "parameter", "min", "median", "max", "mean"]
    grouped: dict[int, list[SpectrumRow]] = defaultdict(list)
    for run in runs:
        for spectrum in run.spectra:
            grouped[spectrum.time_s].append(spectrum)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for time_s in TARGET_TIMES:
            for name in ("sse", "effe", "thickness_nm", "h_ag_nm", "rave_nm", "sig_l"):
                stats = spread([float(getattr(row, name)) for row in grouped[time_s]])
                writer.writerow({"time_s": time_s, "parameter": name, **stats})
    return path


def gnuplot_path(path: Path, target: Path) -> str:
    return os.path.relpath(target.resolve(), start=path.parent.resolve())


def read_spectrum_result(global_result: Path, spectrum_name: str) -> dict[str, Any]:
    spectrum_result = global_result.parent / f"optimal_global_{spectrum_name}.json"
    if not spectrum_result.exists():
        raise SystemExit(f"Missing spectrum result JSON: {spectrum_result}")
    return json.loads(spectrum_result.read_text(encoding="utf-8"))


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def write_overlay(root: Path, label: str, run: Run) -> tuple[Path, Path | None]:
    overlay_dir = root / "overlays"
    gp_path = overlay_dir / f"{label}_overlay.gp"
    png_path = overlay_dir / f"{label}_overlay.png"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "set terminal pngcairo noenhanced size 1500,900",
        f"set output '{gnuplot_path(gp_path, png_path)}'",
        f"set title 'MMGM transition hAg-window {label}: seed {run.seed}, SSE={run.total_sse:.6g}'",
        "set datafile commentschars '#'",
        "set grid",
        "set xlabel 'Wavelength (nm)'",
        "set ylabel 'Transmittance'",
        "set xrange [300:900]",
        "set key outside right",
        "plot \\",
    ]
    plot_lines: list[str] = []
    for spectrum in run.spectra:
        result = read_spectrum_result(run.result_path, spectrum.spectrum)
        experimental = project_path(str(result["experimental_file"]))
        theoretical = project_path(str(result["theoretical_file"]))
        plot_lines.append(
            f"  '{gnuplot_path(gp_path, experimental)}' using 1:3 with lines lw 2 "
            f"title '{spectrum.time_s}s experimental'"
        )
        plot_lines.append(
            f"  '{gnuplot_path(gp_path, theoretical)}' using 1:3 with lines lw 2 dt 2 "
            f"title '{spectrum.time_s}s MMGM fit'"
        )
    lines.extend(", \\\n".join(plot_lines).splitlines())
    gp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if shutil.which("gnuplot") is None:
        return gp_path, None
    subprocess.run(["gnuplot", gp_path.name], cwd=gp_path.parent, check=True)
    return gp_path, png_path


def build_report(
    runs: list[Run],
    ranked_path: Path,
    spectrum_path: Path,
    spread_path: Path,
    overlays: list[tuple[str, Path, Path | None]],
) -> str:
    lines = ["=== MMGM TRANSITION hAg-WINDOW DIAGNOSTIC ===", ""]
    lines.append(f"Runs ranked: {len(runs)}")
    lines.append(f"Ranked table: {ranked_path.as_posix()}")
    lines.append(f"Spectrum table: {spectrum_path.as_posix()}")
    lines.append(f"Spread diagnostics: {spread_path.as_posix()}")
    lines.append("")

    best = runs[0]
    median = runs[len(runs) // 2]
    worst = runs[-1]
    for label, run in (("best", best), ("median", median), ("worst", worst)):
        lines.append(
            f"{label}: generation={run.generation}, seed={run.seed}, "
            f"total_SSE={run.total_sse:.8g}, total_RMSE={run.total_rmse:.8g}"
        )
        for spectrum in run.spectra:
            lines.append(
                f"  {spectrum.time_s}s: SSE={spectrum.sse:.8g}, "
                f"hAg={spectrum.h_ag_nm:.6g}, effe={spectrum.effe:.6g}, "
                f"thickness={spectrum.thickness_nm:.6g}, Rave={spectrum.rave_nm:.6g}, "
                f"sigL={spectrum.sig_l:.6g}, cluster={classify_parameter(spectrum)}"
            )
    lines.append("")

    hags = [spectrum.h_ag_nm for run in runs for spectrum in run.spectra]
    violations = [
        spectrum.h_ag_nm
        for run in runs
        for spectrum in run.spectra
        if spectrum.h_ag_nm < HAG_MIN_NM or spectrum.h_ag_nm > HAG_MAX_NM
    ]
    lines.append("=== hAg DIAGNOSTICS ===")
    lines.append(
        f"hAg range: {min(hags):.8g} to {max(hags):.8g} nm; "
        f"window violations: {len(violations)}"
    )
    non_monotonic = sum(1 for run in runs if run.spectra[0].h_ag_nm > run.spectra[1].h_ag_nm)
    lines.append(f"30s->40s hAg non-monotonic runs: {non_monotonic}")
    lines.append("")

    lines.append("=== CLUSTERING SUMMARY ===")
    by_time: dict[int, Counter[str]] = defaultdict(Counter)
    pair_counter: Counter[str] = Counter()
    for run in runs:
        clusters = {row.time_s: classify_parameter(row) for row in run.spectra}
        for time_s, cluster in clusters.items():
            by_time[time_s][cluster] += 1
        pair_counter[f"30s:{clusters[30]} | 40s:{clusters[40]}"] += 1
    for time_s in TARGET_TIMES:
        lines.append(f"{time_s}s preferred branches:")
        for cluster, count in by_time[time_s].most_common():
            lines.append(f"  {count}: {cluster}")
    lines.append("Paired branches:")
    for cluster, count in pair_counter.most_common():
        lines.append(f"  {count}: {cluster}")
    lines.append("")

    lines.append("=== OVERLAYS ===")
    for label, gp_path, png_path in overlays:
        rendered = png_path.as_posix() if png_path is not None else "not rendered; gnuplot unavailable"
        lines.append(f"{label}: script={gp_path.as_posix()}, image={rendered}")
    lines.append("")
    lines.append("Interpretation: diagnostic only. Good low-SSE fits inside this window support MMGM-compatible transition behavior; low-SSE pathological clusters indicate the single-lognormal MMGM form is still under strain at 30s/40s.")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    result_files = sorted(args.root.glob("gen_*/seed_*/*/*/global_result.json"))
    if not result_files:
        raise SystemExit(f"No global_result.json files found under {args.root}")
    runs = sorted((load_run(path) for path in result_files), key=lambda run: run.total_sse)
    ranked_path = write_ranked_runs(args.root, runs)
    spectrum_path = write_spectrum_table(args.root, runs)
    spread_path = write_spread_diagnostics(args.root, runs)

    selected = [("best", runs[0]), ("median", runs[len(runs) // 2]), ("worst", runs[-1])]
    overlays = [(label, *write_overlay(args.root, label, run)) for label, run in selected]
    report = build_report(runs, ranked_path, spectrum_path, spread_path, overlays)
    report_path = args.root / "transition_hag_window_report.txt"
    report_path.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
