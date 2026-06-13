#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"

TIMES=(10 20 30)
SEEDS=(111 222 333 444 555 12345 54321 99999)
GENERATIONS=(100 300)
POPULATION_SIZE=48

BASE_DATA_ROOT="data/output/tests/mmgm_single_free_branch_stability"
BASE_IMG_ROOT="img/tests/mmgm_single_free_branch_stability"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_free_branch_stability"
REPORT_ROOT="${BASE_DATA_ROOT}/report"
STATUS_FILE="${BASE_DATA_ROOT}/status.txt"

SPECTRA_SOURCE_DIR="data/experimental/final/transmittance"
BASE_BOUNDS_JSON="data/input/optimal/bounds.json"
FREE_BOUNDS_JSON="${BASE_DATA_ROOT}/free_branch_bounds.json"

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT" "$REPORT_ROOT"

LOCK_DIR="${BASE_DATA_ROOT}/.campaign.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Another free-branch stability campaign appears to be running: $LOCK_DIR" >&2
  exit 1
fi
trap 'rmdir "$LOCK_DIR"' EXIT

echo "=== MMGM single free-branch stability campaign started: $(timestamp) ===" >> "$STATUS_FILE"

echo "bounds status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
python3 - "$BASE_BOUNDS_JSON" "$FREE_BOUNDS_JSON" <<'PY'
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
raw = json.loads(source.read_text(encoding="utf-8"))
out = deepcopy(raw)
params = out["models"]["mmgm_spheres_single"]["native_fit_parameters"]
params["effe"].update({"min": 0.001, "max": 0.95, "transform": "none"})
params["thickness_nm"].update({"min": 1.0, "max": 100.0, "transform": "log"})
params["rave_nm"].update({"min": 0.5, "max": 200.0, "transform": "log"})
params["sig_l"].update({"min": 0.02, "max": 2.0, "transform": "log"})
optimizer = out["models"]["mmgm_spheres_single"].setdefault("optimizer", {})
de = optimizer.setdefault("differential_evolution", {})
de["population_size"] = 48
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
PY
echo "bounds status:done timestamp:$(timestamp)" >> "$STATUS_FILE"

run_total=$(( ${#TIMES[@]} * ${#SEEDS[@]} * ${#GENERATIONS[@]} ))
run_index=0

for time in "${TIMES[@]}"; do
  for generation in "${GENERATIONS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      run_index=$(( run_index + 1 ))
      OUT_DIR="${BASE_DATA_ROOT}/time_${time}s/gen_${generation}/seed_${seed}"
      IMG_DIR="${BASE_IMG_ROOT}/time_${time}s/gen_${generation}/seed_${seed}"
      GP_DIR="${BASE_GP_ROOT}/time_${time}s/gen_${generation}/seed_${seed}"
      DONE_FILE="${OUT_DIR}/mmgm_single/spheres/global_result.json"
      RUN_SPECTRA_DIR="${OUT_DIR}/input_spectra"
      SPECTRUM_FILE="${SPECTRA_SOURCE_DIR}/ITO_Ag_${time}s_T_0.dat"
      status_prefix="time:${time}s seed:${seed} generation:${generation} run:${run_index}/${run_total}"

      if [ -f "$DONE_FILE" ]; then
        echo "${status_prefix} status:skipped timestamp:$(timestamp)" >> "$STATUS_FILE"
        continue
      fi

      mkdir -p "$RUN_SPECTRA_DIR" "$IMG_DIR" "$GP_DIR"
      cp "$SPECTRUM_FILE" "$RUN_SPECTRA_DIR/"

      echo "${status_prefix} status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
      echo "==> Free-branch stability: time=${time}s, generation=${generation}, seed=${seed}"
      set +e
      python3 tools/optimal/optimize_model_parameters.py \
        "$MODEL_FLAG" \
        --bounds-json "$FREE_BOUNDS_JSON" \
        --spectrum-time-s "$time" \
        --seed "$seed" \
        --max-generations "$generation" \
        --population-size "$POPULATION_SIZE" \
        --spectra-dir "$RUN_SPECTRA_DIR" \
        --output-dir "$OUT_DIR" \
        --image-dir "$IMG_DIR" \
        --gnuplot-dir "$GP_DIR"
      exit_code=$?
      set -e

      if [ "$exit_code" -ne 0 ]; then
        echo "${status_prefix} status:failed exit_code:${exit_code} timestamp:$(timestamp)" >> "$STATUS_FILE"
        continue
      fi

      result_source="${OUT_DIR}/mmgm_single/spheres/optimal_ITO_Ag_${time}s_T_0.json"
      if [ ! -f "$result_source" ]; then
        echo "${status_prefix} status:failed exit_code:missing_result timestamp:$(timestamp)" >> "$STATUS_FILE"
        continue
      fi
      cp "$result_source" "$DONE_FILE"
      echo "${status_prefix} status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
    done
  done
done

echo "analyzer status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
set +e
python3 - "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT" "$REPORT_ROOT" <<'PY'
from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


TIMES = (10, 20, 30)
GENERATIONS = (100, 300)


@dataclass(frozen=True)
class Run:
    time_s: int
    generation: int
    seed: int
    sse: float
    effe: float
    thickness_nm: float
    rave_nm: float
    sig_l: float
    result_path: Path
    experimental_file: Path
    theoretical_file: Path


def finite_float(value: object, label: str, path: Path) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise SystemExit(f"Non-finite {label} in {path}: {value!r}")
    return parsed


def parse_part(parts: tuple[str, ...], prefix: str, suffix: str = "") -> int:
    part = next(item for item in parts if item.startswith(prefix))
    raw = part[len(prefix):]
    if suffix:
        raw = raw[:-len(suffix)]
    return int(raw)


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def read_run(path: Path, base_data_root: Path) -> Run:
    raw = json.loads(path.read_text(encoding="utf-8"))
    params = raw["best_parameters"]
    objective = raw["objective"]
    rel = path.relative_to(base_data_root)
    parts = rel.parts
    return Run(
        time_s=parse_part(parts, "time_", "s"),
        generation=parse_part(parts, "gen_"),
        seed=parse_part(parts, "seed_"),
        sse=finite_float(objective["sse"], "SSE", path),
        effe=finite_float(params["effe"], "effe", path),
        thickness_nm=finite_float(params["thickness_nm"], "thickness_nm", path),
        rave_nm=finite_float(params["rave_nm"], "rave_nm", path),
        sig_l=finite_float(params["sig_l"], "sig_l", path),
        result_path=path,
        experimental_file=project_path(raw["experimental_file"]),
        theoretical_file=project_path(raw["theoretical_file"]),
    )


def values(runs: list[Run], attr: str) -> list[float]:
    return [float(getattr(run, attr)) for run in runs]


def spread(runs: list[Run], attr: str) -> float:
    vals = values(runs, attr)
    return max(vals) - min(vals)


def branch(run: Run) -> str:
    if 8.0 <= run.rave_nm <= 20.0 and run.sig_l >= 0.4:
        return "AFM-like broad branch"
    if 50.0 <= run.rave_nm <= 100.0 and run.sig_l <= 0.3:
        return "large-radius narrow branch"
    if run.rave_nm > 40.0 and run.sig_l <= 0.4:
        return "large-radius transition branch"
    return "other branch"


def median_sse_run(runs: list[Run]) -> Run:
    ordered = sorted(runs, key=lambda run: run.sse)
    return ordered[len(ordered) // 2]


def gnuplot_string(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "\\'")


base_data_root = Path(sys.argv[1])
base_img_root = Path(sys.argv[2])
base_gp_root = Path(sys.argv[3])
report_root = Path(sys.argv[4])
report_root.mkdir(parents=True, exist_ok=True)
plot_root = report_root / "plots"
plot_root.mkdir(parents=True, exist_ok=True)
gp_report_root = base_gp_root / "report"
gp_report_root.mkdir(parents=True, exist_ok=True)

runs = [
    read_run(path, base_data_root)
    for path in sorted(base_data_root.glob("time_*s/gen_*/seed_*/mmgm_single/spheres/global_result.json"))
]
if not runs:
    raise SystemExit(f"No global_result.json files found under {base_data_root}")

all_csv = report_root / "free_branch_all_runs.csv"
stats_csv = report_root / "free_branch_stability_stats.csv"
representatives_csv = report_root / "free_branch_representative_runs.csv"
scatter_dat = report_root / "scatter_points.dat"

with all_csv.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = [
        "time_s",
        "generation",
        "seed",
        "sse",
        "effe",
        "thickness_nm",
        "rave_nm",
        "sig_l",
        "branch",
        "result_path",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for run in sorted(runs, key=lambda item: (item.time_s, item.generation, item.seed)):
        writer.writerow(
            {
                "time_s": run.time_s,
                "generation": run.generation,
                "seed": run.seed,
                "sse": run.sse,
                "effe": run.effe,
                "thickness_nm": run.thickness_nm,
                "rave_nm": run.rave_nm,
                "sig_l": run.sig_l,
                "branch": branch(run),
                "result_path": run.result_path.as_posix(),
            }
        )

by_time: dict[int, list[Run]] = defaultdict(list)
by_time_generation: dict[tuple[int, int], list[Run]] = defaultdict(list)
for run in runs:
    by_time[run.time_s].append(run)
    by_time_generation[(run.time_s, run.generation)].append(run)

stats_rows: list[dict[str, object]] = []
for time_s in TIMES:
    for generation in GENERATIONS:
        group = by_time_generation.get((time_s, generation), [])
        if not group:
            continue
        branches = Counter(branch(run) for run in group)
        stats_rows.append(
            {
                "time_s": time_s,
                "generation": generation,
                "n_runs": len(group),
                "sse_min": min(values(group, "sse")),
                "sse_median": statistics.median(values(group, "sse")),
                "sse_max": max(values(group, "sse")),
                "sse_spread": spread(group, "sse"),
                "effe_min": min(values(group, "effe")),
                "effe_max": max(values(group, "effe")),
                "effe_spread": spread(group, "effe"),
                "thickness_min": min(values(group, "thickness_nm")),
                "thickness_max": max(values(group, "thickness_nm")),
                "thickness_spread": spread(group, "thickness_nm"),
                "rave_min": min(values(group, "rave_nm")),
                "rave_max": max(values(group, "rave_nm")),
                "rave_spread": spread(group, "rave_nm"),
                "sig_l_min": min(values(group, "sig_l")),
                "sig_l_max": max(values(group, "sig_l")),
                "sig_l_spread": spread(group, "sig_l"),
                "branch_counts": "; ".join(f"{name}={count}" for name, count in sorted(branches.items())),
            }
        )

with stats_csv.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = list(stats_rows[0].keys()) if stats_rows else []
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(stats_rows)

representatives: list[tuple[str, Run]] = []
for time_s in TIMES:
    group = sorted(by_time[time_s], key=lambda run: run.sse)
    representatives.extend(
        [
            ("best", group[0]),
            ("median", median_sse_run(group)),
            ("worst", group[-1]),
        ]
    )

with representatives_csv.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = [
        "role",
        "time_s",
        "generation",
        "seed",
        "sse",
        "effe",
        "thickness_nm",
        "rave_nm",
        "sig_l",
        "branch",
        "result_path",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for role, run in representatives:
        writer.writerow(
            {
                "role": role,
                "time_s": run.time_s,
                "generation": run.generation,
                "seed": run.seed,
                "sse": run.sse,
                "effe": run.effe,
                "thickness_nm": run.thickness_nm,
                "rave_nm": run.rave_nm,
                "sig_l": run.sig_l,
                "branch": branch(run),
                "result_path": run.result_path.as_posix(),
            }
        )

with scatter_dat.open("w", encoding="utf-8") as handle:
    handle.write("# time_s generation seed sse rave_nm sig_l thickness_nm effe\n")
    for run in sorted(runs, key=lambda item: (item.time_s, item.generation, item.seed)):
        handle.write(
            f"{run.time_s} {run.generation} {run.seed} {run.sse:.17g} "
            f"{run.rave_nm:.17g} {run.sig_l:.17g} {run.thickness_nm:.17g} {run.effe:.17g}\n"
        )

for time_s in TIMES:
    time_dat = report_root / f"time_{time_s}s_seed_metrics.dat"
    with time_dat.open("w", encoding="utf-8") as handle:
        handle.write("# seed generation sse rave_nm sig_l thickness_nm effe\n")
        for run in sorted(by_time[time_s], key=lambda item: (item.generation, item.seed)):
            handle.write(
                f"{run.seed} {run.generation} {run.sse:.17g} {run.rave_nm:.17g} "
                f"{run.sig_l:.17g} {run.thickness_nm:.17g} {run.effe:.17g}\n"
            )

    for plot_name, ylabel, column in (
        ("sse_vs_seed", "SSE", 3),
        ("rave_nm_vs_seed", "Rave (nm)", 4),
        ("sig_l_vs_seed", "sigL", 5),
        ("thickness_nm_vs_seed", "thickness (nm)", 6),
        ("effe_vs_seed", "effe", 7),
    ):
        gp = gp_report_root / f"time_{time_s}s_{plot_name}.gp"
        png = plot_root / f"time_{time_s}s_{plot_name}.png"
        gp.write_text(
            "\n".join(
                [
                    "set terminal pngcairo noenhanced size 1400,900",
                    f"set output '{gnuplot_string(png)}'",
                    f"data = '{gnuplot_string(time_dat)}'",
                    f"set title 'Free-branch stability {time_s}s: {ylabel} vs seed'",
                    "set grid",
                    "set xlabel 'Seed'",
                    f"set ylabel '{ylabel}'",
                    "set key outside right",
                    "plot \\",
                    f"  data using ($2 == 100 ? $1 : 1/0):{column} with points pt 7 ps 1.4 title 'gen 100', \\",
                    f"  data using ($2 == 300 ? $1 : 1/0):{column} with points pt 5 ps 1.4 title 'gen 300'",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(["gnuplot", gp.as_posix()], check=True)

    for plot_name, xlabel, xcol, ylabel, ycol in (
        ("scatter_rave_nm_vs_sig_l", "Rave (nm)", 5, "sigL", 6),
        ("scatter_rave_nm_vs_thickness_nm", "Rave (nm)", 5, "thickness (nm)", 7),
        ("scatter_rave_nm_vs_effe", "Rave (nm)", 5, "effe", 8),
    ):
        gp = gp_report_root / f"time_{time_s}s_{plot_name}.gp"
        png = plot_root / f"time_{time_s}s_{plot_name}.png"
        gp.write_text(
            "\n".join(
                [
                    "set terminal pngcairo noenhanced size 1400,900",
                    f"set output '{gnuplot_string(png)}'",
                    f"data = '{gnuplot_string(scatter_dat)}'",
                    f"set title 'Free-branch stability {time_s}s: {xlabel} vs {ylabel}'",
                    "set grid",
                    f"set xlabel '{xlabel}'",
                    f"set ylabel '{ylabel}'",
                    "set cblabel 'SSE'",
                    "set palette rgb 33,13,10",
                    "set key off",
                    "plot \\",
                    f"  data using ($1 == {time_s} ? ${xcol} : 1/0):{ycol}:4 with points pt 7 ps 1.6 palette",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(["gnuplot", gp.as_posix()], check=True)

    reps = {role: run for role, run in representatives if run.time_s == time_s}
    gp = gp_report_root / f"time_{time_s}s_best_median_worst_comparison.gp"
    png = plot_root / f"time_{time_s}s_best_median_worst_comparison.png"
    lines = [
        "set terminal pngcairo noenhanced size 1800,650",
        f"set output '{gnuplot_string(png)}'",
        "set datafile commentschars '#'",
        "set multiplot layout 1,3 title 'Free-branch representative fits {0}s'".format(time_s),
        "set grid",
        "set xlabel 'Wavelength (nm)'",
        "set ylabel 'Transmittance'",
        "set key bottom right",
    ]
    for role in ("best", "median", "worst"):
        run = reps[role]
        lines.extend(
            [
                f"set title '{role}: seed {run.seed}, gen {run.generation}, SSE {run.sse:.5g}'",
                "plot \\",
                f"  '{gnuplot_string(run.experimental_file)}' using 1:3 with lines lw 2 title 'experimental', \\",
                f"  '{gnuplot_string(run.theoretical_file)}' using 1:3 with lines lw 2 title 'fit'",
            ]
        )
    lines.extend(["unset multiplot", ""])
    gp.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(["gnuplot", gp.as_posix()], check=True)

summary = report_root / "report_summary.md"
summary_lines = [
    "# MMGM Single Free-Branch Stability",
    "",
    "This diagnostic uses the single-spectrum optimizer with no AFM priors, no thesis priors, and no global coupling.",
    "",
    "Bounds: `effe=0.001..0.95`, `thickness_nm=1..100`, `rave_nm=0.5..200`, `sig_l=0.02..2.0`.",
    "",
    "## Representative Runs",
    "",
    "| time | role | gen | seed | SSE | Rave | sigL | thickness | effe | branch |",
    "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
]
for role, run in representatives:
    summary_lines.append(
        f"| {run.time_s}s | {role} | {run.generation} | {run.seed} | {run.sse:.6g} | "
        f"{run.rave_nm:.6g} | {run.sig_l:.6g} | {run.thickness_nm:.6g} | {run.effe:.6g} | {branch(run)} |"
    )

summary_lines.extend(["", "## Stability Statistics", ""])
for row in stats_rows:
    summary_lines.extend(
        [
            f"### {row['time_s']}s, generation {row['generation']}",
            "",
            f"- SSE min/median/max: {row['sse_min']:.6g} / {row['sse_median']:.6g} / {row['sse_max']:.6g}",
            f"- Rave range: {row['rave_min']:.6g} to {row['rave_max']:.6g} (spread {row['rave_spread']:.6g})",
            f"- sigL range: {row['sig_l_min']:.6g} to {row['sig_l_max']:.6g} (spread {row['sig_l_spread']:.6g})",
            f"- thickness range: {row['thickness_min']:.6g} to {row['thickness_max']:.6g} (spread {row['thickness_spread']:.6g})",
            f"- effe range: {row['effe_min']:.6g} to {row['effe_max']:.6g} (spread {row['effe_spread']:.6g})",
            f"- branch counts: {row['branch_counts']}",
            "",
        ]
    )

summary_lines.extend(["## Branch Interpretation", ""])
for time_s in TIMES:
    group = by_time[time_s]
    counts = Counter(branch(run) for run in group)
    large_count = counts["large-radius narrow branch"] + counts["large-radius transition branch"]
    afm_count = counts["AFM-like broad branch"]
    best = min(group, key=lambda run: run.sse)
    if large_count >= max(2, len(group) // 3):
        large_note = "large-radius branch appears repeatedly"
    else:
        large_note = "large-radius branch is not repeatedly recovered"
    if afm_count >= 2:
        branch_note = "multiple branches appear" if large_count else "AFM-like branch dominates the classified solutions"
    else:
        branch_note = "classified AFM-like branch is weak or absent"
    summary_lines.extend(
        [
            f"- {time_s}s: {large_note}; {branch_note}. Best SSE run is `{branch(best)}` "
            f"with Rave={best.rave_nm:.6g}, sigL={best.sig_l:.6g}, thickness={best.thickness_nm:.6g}, effe={best.effe:.6g}.",
        ]
    )

summary_lines.extend(
    [
        "",
        "## Files",
        "",
        f"- All runs CSV: `{all_csv.as_posix()}`",
        f"- Stability CSV: `{stats_csv.as_posix()}`",
        f"- Representative runs CSV: `{representatives_csv.as_posix()}`",
        f"- Plots: `{plot_root.as_posix()}`",
    ]
)
summary.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
PY
analyzer_exit=$?
set -e
if [ "$analyzer_exit" -ne 0 ]; then
  echo "analyzer status:failed exit_code:${analyzer_exit} timestamp:$(timestamp)" >> "$STATUS_FILE"
  exit "$analyzer_exit"
fi
echo "analyzer status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
echo "=== MMGM single free-branch stability campaign finished: $(timestamp) ===" >> "$STATUS_FILE"
