#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"
BASE_THESIS_PRIORS="data/input/optimal/thesis_priors/mmgm_single_thesis_hybrid_H3.json"

TIMES=(10 20 30)
STRATEGIES=(L1 L2 L3)
SEEDS=(111 222 333)
GENERATIONS=(150 300)
POPULATION_SIZE=48

BASE_DATA_ROOT="data/output/tests/mmgm_single_early_rescue"
BASE_IMG_ROOT="img/tests/mmgm_single_early_rescue"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_early_rescue"

STATUS_FILE="${BASE_DATA_ROOT}/status.txt"
SPECTRA_SOURCE_DIR="data/experimental/final/transmittance"

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"

LOCK_DIR="${BASE_DATA_ROOT}/.campaign.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Another early-rescue campaign appears to be running: $LOCK_DIR" >&2
  exit 1
fi
trap 'rmdir "$LOCK_DIR"' EXIT

echo "=== MMGM single early-time rescue campaign started: $(timestamp) ===" >> "$STATUS_FILE"

echo "priors status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
python3 - "$BASE_THESIS_PRIORS" "$BASE_DATA_ROOT" <<'PY'
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


base_path = Path(sys.argv[1])
base_data_root = Path(sys.argv[2])
raw = json.loads(base_path.read_text(encoding="utf-8"))

strategies = {
    "L1": {
        "description": "early local rescue: soft Rave, fixed sigL, soft thickness",
        "scales": {
            "rave_nm": (0.75, 1.25),
            "sig_l": (1.0, 1.0),
            "thickness_nm": (0.80, 1.20),
        },
    },
    "L2": {
        "description": "early local rescue: wide optical Rave, soft sigL, soft thickness",
        "scales": {
            "rave_nm": (0.25, 1.25),
            "sig_l": (0.75, 1.25),
            "thickness_nm": (0.50, 1.50),
        },
    },
    "L3": {
        "description": "early local rescue: wide geometry adjustment",
        "scales": {
            "rave_nm": (0.25, 1.50),
            "sig_l": (0.50, 1.50),
            "thickness_nm": (0.50, 2.00),
        },
    },
}

for strategy, config in strategies.items():
    out = deepcopy(raw)
    out["strategy"] = {
        "name": f"early_rescue_{strategy}",
        "description": config["description"],
        "base_prior": base_path.as_posix(),
        "parameter_scales": {
            key: {"scale_low": low, "scale_high": high}
            for key, (low, high) in config["scales"].items()
        },
    }
    bounds_by_time = {}
    for time_s in ("10", "20", "30"):
        entry = deepcopy(raw["bounds_by_time_s"][time_s])
        references = entry["reference_values"]
        for key, (low, high) in config["scales"].items():
            reference = float(references[key])
            minimum = reference * low
            maximum = reference * high
            entry[key] = {
                "min": minimum,
                "max": maximum,
                "reference": reference,
            }
            entry["bounds"][key] = {
                "min": minimum,
                "max": maximum,
            }
        bounds_by_time[time_s] = entry
    out["bounds_by_time_s"] = bounds_by_time
    strategy_root = base_data_root / strategy
    strategy_root.mkdir(parents=True, exist_ok=True)
    (strategy_root / "early_rescue_priors.json").write_text(
        json.dumps(out, indent=2) + "\n",
        encoding="utf-8",
    )
PY
echo "priors status:done timestamp:$(timestamp)" >> "$STATUS_FILE"

run_total=$(( ${#STRATEGIES[@]} * ${#TIMES[@]} * ${#SEEDS[@]} * ${#GENERATIONS[@]} ))
run_index=0

for strategy in "${STRATEGIES[@]}"; do
  THESIS_PRIORS="${BASE_DATA_ROOT}/${strategy}/early_rescue_priors.json"
  for time in "${TIMES[@]}"; do
    for generation in "${GENERATIONS[@]}"; do
      for seed in "${SEEDS[@]}"; do
        run_index=$(( run_index + 1 ))
        OUT_DIR="${BASE_DATA_ROOT}/${strategy}/time_${time}s/gen_${generation}/seed_${seed}"
        IMG_DIR="${BASE_IMG_ROOT}/${strategy}/time_${time}s/gen_${generation}/seed_${seed}"
        GP_DIR="${BASE_GP_ROOT}/${strategy}/time_${time}s/gen_${generation}/seed_${seed}"
        DONE_FILE="${OUT_DIR}/mmgm_single/spheres/result.json"
        RUN_SPECTRA_DIR="${OUT_DIR}/input_spectra"
        SPECTRUM_FILE="${SPECTRA_SOURCE_DIR}/ITO_Ag_${time}s_T_0.dat"
        status_prefix="strategy:${strategy} time:${time}s seed:${seed} generation:${generation} run:${run_index}/${run_total}"

        if [ -f "$DONE_FILE" ]; then
          echo "${status_prefix} status:skipped timestamp:$(timestamp)" >> "$STATUS_FILE"
          continue
        fi

        mkdir -p "$RUN_SPECTRA_DIR" "$IMG_DIR" "$GP_DIR"
        cp "$SPECTRUM_FILE" "$RUN_SPECTRA_DIR/"

        echo "${status_prefix} status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
        echo "==> Early rescue: strategy=${strategy}, time=${time}s, generation=${generation}, seed=${seed}"
        set +e
        python3 tools/optimal/optimize_model_parameters.py \
          "$MODEL_FLAG" \
          --thesis-priors-json "$THESIS_PRIORS" \
          --thesis-priors-mode bounded \
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
done

echo "analysis status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
set +e
python3 - "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT" <<'PY'
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


STRATEGIES = ("L1", "L2", "L3")
PARAMETERS = ("rave_nm", "sig_l", "thickness_nm", "effe", "sse")


@dataclass(frozen=True)
class Run:
    strategy: str
    time_s: int
    generation: int
    seed: int
    sse: float
    effe: float
    thickness_nm: float
    rave_nm: float
    sig_l: float
    ref_eff: float | None
    ref_thickness_nm: float
    ref_rave_nm: float
    ref_sig_l: float
    result_path: Path


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


def read_run(path: Path, base_data_root: Path) -> Run:
    raw = json.loads(path.read_text(encoding="utf-8"))
    params = raw["best_parameters"]
    thesis = raw["thesis_priors"]
    rel = path.relative_to(base_data_root)
    parts = rel.parts
    strategy = parts[0]
    reference = thesis["reference"]
    return Run(
        strategy=strategy,
        time_s=parse_part(parts, "time_", "s"),
        generation=parse_part(parts, "gen_"),
        seed=parse_part(parts, "seed_"),
        sse=finite_float(raw["objective"]["sse"], "SSE", path),
        effe=finite_float(params["effe"], "effe", path),
        thickness_nm=finite_float(params["thickness_nm"], "thickness", path),
        rave_nm=finite_float(params["rave_nm"], "Rave", path),
        sig_l=finite_float(params["sig_l"], "sigL", path),
        ref_eff=None,
        ref_thickness_nm=finite_float(reference["thickness_nm"], "reference thickness", path),
        ref_rave_nm=finite_float(reference["rave_nm"], "reference Rave", path),
        ref_sig_l=finite_float(reference["sig_l"], "reference sigL", path),
        result_path=path,
    )


def spread(values: list[float]) -> float:
    return max(values) - min(values)


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def value(run: Run, parameter: str) -> float:
    return getattr(run, parameter) if parameter != "sse" else run.sse


def reference(run: Run, parameter: str) -> float | None:
    if parameter == "rave_nm":
        return run.ref_rave_nm
    if parameter == "sig_l":
        return run.ref_sig_l
    if parameter == "thickness_nm":
        return run.ref_thickness_nm
    return None


def escape_label(run: Run, runs: list[Run]) -> str:
    shifts = {
        "Rave": (run.rave_nm - run.ref_rave_nm) / run.ref_rave_nm,
        "sigL": (run.sig_l - run.ref_sig_l) / run.ref_sig_l,
        "thickness": (run.thickness_nm - run.ref_thickness_nm) / run.ref_thickness_nm,
    }
    effe_values = [item.effe for item in runs]
    strongest = max(shifts.items(), key=lambda item: abs(item[1]))
    labels = []
    if shifts["Rave"] < -0.15:
        labels.append("Rave systematically decreases")
    if shifts["sigL"] > 0.15:
        labels.append("sigL systematically increases")
    if shifts["thickness"] < -0.20:
        labels.append("thickness collapses")
    if spread(effe_values) > 0.20 and abs(strongest[1]) < 0.10:
        labels.append("effe compensates more than geometry")
    if labels:
        return "; ".join(labels)
    return f"largest escape: {strongest[0]} ({strongest[1]:+.1%})"


base_data_root = Path(sys.argv[1])
base_img_root = Path(sys.argv[2])
base_gp_root = Path(sys.argv[3])

runs = [
    read_run(path, base_data_root)
    for path in sorted(base_data_root.glob("L*/time_*s/gen_*/seed_*/mmgm_single/spheres/result.json"))
]
if not runs:
    raise SystemExit(f"No result.json files found under {base_data_root}")

all_csv = base_data_root / "early_rescue_all_runs.csv"
best_csv = base_data_root / "early_rescue_best_by_strategy_time.csv"
stability_csv = base_data_root / "early_rescue_stability_by_generation.csv"
escape_report = base_data_root / "early_rescue_parameter_escape_report.txt"

with all_csv.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = [
        "strategy",
        "time_s",
        "generation",
        "seed",
        "sse",
        "effe",
        "thickness_nm",
        "rave_nm",
        "sig_l",
        "rave_rel_shift",
        "sig_l_rel_shift",
        "thickness_rel_shift",
        "result_path",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for run in runs:
        writer.writerow(
            {
                "strategy": run.strategy,
                "time_s": run.time_s,
                "generation": run.generation,
                "seed": run.seed,
                "sse": run.sse,
                "effe": run.effe,
                "thickness_nm": run.thickness_nm,
                "rave_nm": run.rave_nm,
                "sig_l": run.sig_l,
                "rave_rel_shift": (run.rave_nm - run.ref_rave_nm) / run.ref_rave_nm,
                "sig_l_rel_shift": (run.sig_l - run.ref_sig_l) / run.ref_sig_l,
                "thickness_rel_shift": (run.thickness_nm - run.ref_thickness_nm) / run.ref_thickness_nm,
                "result_path": run.result_path.as_posix(),
            }
        )

by_strategy_time: dict[tuple[str, int], list[Run]] = defaultdict(list)
by_strategy_time_gen: dict[tuple[str, int, int], list[Run]] = defaultdict(list)
for run in runs:
    by_strategy_time[(run.strategy, run.time_s)].append(run)
    by_strategy_time_gen[(run.strategy, run.time_s, run.generation)].append(run)

best_rows = []
for key in sorted(by_strategy_time):
    group = by_strategy_time[key]
    best = min(group, key=lambda run: run.sse)
    best_rows.append((best, escape_label(best, group)))

with best_csv.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = [
        "strategy",
        "time_s",
        "best_generation",
        "best_seed",
        "best_sse",
        "best_effe",
        "best_thickness_nm",
        "best_rave_nm",
        "best_sig_l",
        "rave_rel_shift",
        "sig_l_rel_shift",
        "thickness_rel_shift",
        "escape_diagnosis",
        "result_path",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for best, label in best_rows:
        writer.writerow(
            {
                "strategy": best.strategy,
                "time_s": best.time_s,
                "best_generation": best.generation,
                "best_seed": best.seed,
                "best_sse": best.sse,
                "best_effe": best.effe,
                "best_thickness_nm": best.thickness_nm,
                "best_rave_nm": best.rave_nm,
                "best_sig_l": best.sig_l,
                "rave_rel_shift": (best.rave_nm - best.ref_rave_nm) / best.ref_rave_nm,
                "sig_l_rel_shift": (best.sig_l - best.ref_sig_l) / best.ref_sig_l,
                "thickness_rel_shift": (best.thickness_nm - best.ref_thickness_nm) / best.ref_thickness_nm,
                "escape_diagnosis": label,
                "result_path": best.result_path.as_posix(),
            }
        )

with stability_csv.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = [
        "strategy",
        "time_s",
        "generation",
        "n_runs",
        "sse_min",
        "sse_max",
        "sse_spread",
        "effe_spread",
        "thickness_spread",
        "rave_spread",
        "sig_l_spread",
        "sse_mean",
        "effe_mean",
        "thickness_mean",
        "rave_mean",
        "sig_l_mean",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for key in sorted(by_strategy_time_gen):
        group = by_strategy_time_gen[key]
        writer.writerow(
            {
                "strategy": key[0],
                "time_s": key[1],
                "generation": key[2],
                "n_runs": len(group),
                "sse_min": min(run.sse for run in group),
                "sse_max": max(run.sse for run in group),
                "sse_spread": spread([run.sse for run in group]),
                "effe_spread": spread([run.effe for run in group]),
                "thickness_spread": spread([run.thickness_nm for run in group]),
                "rave_spread": spread([run.rave_nm for run in group]),
                "sig_l_spread": spread([run.sig_l for run in group]),
                "sse_mean": mean([run.sse for run in group]),
                "effe_mean": mean([run.effe for run in group]),
                "thickness_mean": mean([run.thickness_nm for run in group]),
                "rave_mean": mean([run.rave_nm for run in group]),
                "sig_l_mean": mean([run.sig_l for run in group]),
            }
        )

lines = [
    "Early-Time Local Rescue Parameter Escape Report",
    "",
    "Question: for 10s, 20s, and 30s, which parameter escapes its thesis prior?",
    "",
]
for strategy in STRATEGIES:
    lines.extend([f"Strategy {strategy}", ""])
    for time_s in (10, 20, 30):
        group = by_strategy_time[(strategy, time_s)]
        best = min(group, key=lambda run: run.sse)
        gen_groups = [
            by_strategy_time_gen[(strategy, time_s, generation)]
            for generation in sorted({run.generation for run in group})
        ]
        generation_note = "; ".join(
            f"gen {items[0].generation}: mean SSE={mean([run.sse for run in items]):.6g}, spread={spread([run.sse for run in items]):.6g}"
            for items in gen_groups
        )
        lines.extend(
            [
                f"{time_s}s best: seed={best.seed}, generation={best.generation}, SSE={best.sse:.8g}",
                f"  Rave: {best.rave_nm:.8g} vs thesis {best.ref_rave_nm:.8g} ({(best.rave_nm - best.ref_rave_nm) / best.ref_rave_nm:+.1%})",
                f"  sigL: {best.sig_l:.8g} vs thesis {best.ref_sig_l:.8g} ({(best.sig_l - best.ref_sig_l) / best.ref_sig_l:+.1%})",
                f"  thickness: {best.thickness_nm:.8g} vs thesis {best.ref_thickness_nm:.8g} ({(best.thickness_nm - best.ref_thickness_nm) / best.ref_thickness_nm:+.1%})",
                f"  effe: {best.effe:.8g}",
                f"  escape: {escape_label(best, group)}",
                f"  convergence: {generation_note}",
                "",
            ]
        )

escape_report.write_text("\n".join(lines), encoding="utf-8")

for strategy in STRATEGIES:
    strategy_img_root = base_img_root / strategy
    strategy_gp_root = base_gp_root / strategy
    strategy_data_root = base_data_root / strategy
    strategy_img_root.mkdir(parents=True, exist_ok=True)
    strategy_gp_root.mkdir(parents=True, exist_ok=True)
    strategy_data_root.mkdir(parents=True, exist_ok=True)

    best_dat = strategy_data_root / "best_by_time.dat"
    with best_dat.open("w", encoding="utf-8") as handle:
        handle.write("# time_s sse effe thickness_nm rave_nm sig_l ref_thickness_nm ref_rave_nm ref_sig_l\n")
        for time_s in (10, 20, 30):
            best = min(by_strategy_time[(strategy, time_s)], key=lambda run: run.sse)
            handle.write(
                f"{time_s} {best.sse:.17g} {best.effe:.17g} {best.thickness_nm:.17g} "
                f"{best.rave_nm:.17g} {best.sig_l:.17g} {best.ref_thickness_nm:.17g} "
                f"{best.ref_rave_nm:.17g} {best.ref_sig_l:.17g}\n"
            )

    stability_dat = strategy_data_root / "stability_by_generation.dat"
    with stability_dat.open("w", encoding="utf-8") as handle:
        handle.write("# time_s generation sse_min sse_max sse_mean effe_min effe_max thickness_min thickness_max rave_min rave_max sigl_min sigl_max\n")
        for time_s in (10, 20, 30):
            for generation in (150, 300):
                group = by_strategy_time_gen.get((strategy, time_s, generation), [])
                if not group:
                    continue
                handle.write(
                    f"{time_s} {generation} {min(run.sse for run in group):.17g} "
                    f"{max(run.sse for run in group):.17g} {mean([run.sse for run in group]):.17g} "
                    f"{min(run.effe for run in group):.17g} {max(run.effe for run in group):.17g} "
                    f"{min(run.thickness_nm for run in group):.17g} {max(run.thickness_nm for run in group):.17g} "
                    f"{min(run.rave_nm for run in group):.17g} {max(run.rave_nm for run in group):.17g} "
                    f"{min(run.sig_l for run in group):.17g} {max(run.sig_l for run in group):.17g}\n"
                )

    trajectory_specs = {
        "trajectory_rave": ("Rave (nm)", "5", "8"),
        "trajectory_sigl": ("sigL", "6", "9"),
        "trajectory_thickness": ("thickness (nm)", "4", "7"),
        "trajectory_effe": ("effe", "3", None),
        "trajectory_sse": ("SSE", "2", None),
    }
    for name, (ylabel, column, ref_column) in trajectory_specs.items():
        gp = strategy_gp_root / f"{name}.gp"
        png = strategy_img_root / f"{name}.png"
        plots = [
            f"  data using 1:{column} with linespoints lw 2 title 'best local'"
        ]
        if ref_column is not None:
            plots.append(
                f"  data using 1:{ref_column} with linespoints lw 2 dashtype 2 title 'thesis reference'"
            )
        gp.write_text(
            "\n".join(
                [
                    "set terminal pngcairo noenhanced size 1400,900",
                    f"set output '{png.resolve().as_posix()}'",
                    f"data = '{best_dat.resolve().as_posix()}'",
                    f"set title 'Early rescue {strategy}: {ylabel}'",
                    "set grid",
                    "set xlabel 'Deposition time (s)'",
                    f"set ylabel '{ylabel}'",
                    "set key outside right",
                    "plot \\",
                    ", \\\n".join(plots),
                    "",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(["gnuplot", gp.as_posix()], check=True)

    stability_gp = strategy_gp_root / "stability_sse_by_generation.gp"
    stability_png = strategy_img_root / "stability_sse_by_generation.png"
    stability_gp.write_text(
        "\n".join(
            [
                "set terminal pngcairo noenhanced size 1400,900",
                f"set output '{stability_png.resolve().as_posix()}'",
                f"data = '{stability_dat.resolve().as_posix()}'",
                f"set title 'Early rescue {strategy}: SSE seed spread by generation'",
                "set grid",
                "set xlabel 'Deposition time (s)'",
                "set ylabel 'SSE'",
                "set key outside right",
                "plot \\",
                "  data using ($2 == 150 ? $1 - 0.35 : 1/0):3:4 with yerrorbars lw 2 title 'gen 150 seed range', \\",
                "  data using ($2 == 150 ? $1 - 0.35 : 1/0):5 with linespoints lw 2 title 'gen 150 mean', \\",
                "  data using ($2 == 300 ? $1 + 0.35 : 1/0):3:4 with yerrorbars lw 2 title 'gen 300 seed range', \\",
                "  data using ($2 == 300 ? $1 + 0.35 : 1/0):5 with linespoints lw 2 title 'gen 300 mean'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(["gnuplot", stability_gp.as_posix()], check=True)

    for name, ylabel, min_col, max_col in (
        ("stability_rave", "Rave (nm)", 10, 11),
        ("stability_sigl", "sigL", 12, 13),
        ("stability_thickness", "thickness (nm)", 8, 9),
        ("stability_effe", "effe", 6, 7),
    ):
        gp = strategy_gp_root / f"{name}_by_generation.gp"
        png = strategy_img_root / f"{name}_by_generation.png"
        gp.write_text(
            "\n".join(
                [
                    "set terminal pngcairo noenhanced size 1400,900",
                    f"set output '{png.resolve().as_posix()}'",
                    f"data = '{stability_dat.resolve().as_posix()}'",
                    f"set title 'Early rescue {strategy}: {ylabel} seed spread by generation'",
                    "set grid",
                    "set xlabel 'Deposition time (s)'",
                    f"set ylabel '{ylabel}'",
                    "set key outside right",
                    "plot \\",
                    f"  data using ($2 == 150 ? $1 - 0.35 : 1/0):{min_col}:{max_col} with yerrorbars lw 2 title 'gen 150 seed range', \\",
                    f"  data using ($2 == 300 ? $1 + 0.35 : 1/0):{min_col}:{max_col} with yerrorbars lw 2 title 'gen 300 seed range'",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(["gnuplot", gp.as_posix()], check=True)
PY
analysis_exit=$?
set -e
if [ "$analysis_exit" -ne 0 ]; then
  echo "analysis status:failed exit_code:${analysis_exit} timestamp:$(timestamp)" >> "$STATUS_FILE"
  exit "$analysis_exit"
fi
echo "analysis status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
echo "=== MMGM single early-time rescue campaign finished: $(timestamp) ===" >> "$STATUS_FILE"
