#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"

THESIS_PRIORS="data/input/optimal/thesis_priors/mmgm_single_thesis_hybrid_H3.json"

TIMES=(10 20 30 40 50 60)

SEEDS=(111 222 333)

GENERATIONS=(150 300)

POPULATION_SIZE=48

BASE_DATA_ROOT="data/output/tests/mmgm_single_spectrum_h3_campaign"
BASE_IMG_ROOT="img/tests/mmgm_single_spectrum_h3_campaign"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_spectrum_h3_campaign"

STATUS_FILE="${BASE_DATA_ROOT}/status.txt"

SPECTRA_SOURCE_DIR="data/experimental/final/transmittance"
GLOBAL_H3_ROOT="data/output/tests/mmgm_single_thesis_hybrid_campaign/H3_pop_${POPULATION_SIZE}"

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"

LOCK_DIR="${BASE_DATA_ROOT}/.campaign.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Another single-spectrum H3 campaign appears to be running: $LOCK_DIR" >&2
  exit 1
fi
trap 'rmdir "$LOCK_DIR"' EXIT

echo "=== single-spectrum H3 thesis-prior MMGM campaign started: $(timestamp) ===" >> "$STATUS_FILE"

run_total=$(( ${#TIMES[@]} * ${#SEEDS[@]} * ${#GENERATIONS[@]} ))
run_index=0

for time in "${TIMES[@]}"; do
  for generation in "${GENERATIONS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      run_index=$(( run_index + 1 ))
      OUT_DIR="${BASE_DATA_ROOT}/time_${time}s/gen_${generation}/seed_${seed}"
      IMG_DIR="${BASE_IMG_ROOT}/time_${time}s/gen_${generation}/seed_${seed}"
      GP_DIR="${BASE_GP_ROOT}/time_${time}s/gen_${generation}/seed_${seed}"
      DONE_FILE="${OUT_DIR}/mmgm_single/spheres/result.json"
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
      echo "==> Single-spectrum H3 campaign: time=${time}s, generation=${generation}, seed=${seed}"
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

echo "summary status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
set +e
python3 - "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT" "$GLOBAL_H3_ROOT" <<'PY'
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalRun:
    time_s: int
    generation: int
    seed: int
    sse: float
    effe: float
    thickness_nm: float
    rave_nm: float
    sig_l: float
    result_path: Path


@dataclass(frozen=True)
class GlobalSpectrum:
    time_s: int
    sse: float
    effe: float
    thickness_nm: float
    rave_nm: float
    sig_l: float
    result_path: Path
    total_sse: float


def finite_float(value: object, label: str, path: Path) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise SystemExit(f"Non-finite {label} in {path}: {value!r}")
    return parsed


def parse_int_from_part(part: str, prefix: str, suffix: str = "") -> int:
    if not part.startswith(prefix) or (suffix and not part.endswith(suffix)):
        raise ValueError(part)
    raw = part[len(prefix):]
    if suffix:
        raw = raw[:-len(suffix)]
    return int(raw)


def read_local_result(path: Path) -> LocalRun:
    raw = json.loads(path.read_text(encoding="utf-8"))
    params = raw["best_parameters"]
    objective = raw["objective"]
    parts = path.parts
    time_part = next(part for part in parts if part.startswith("time_"))
    gen_part = next(part for part in parts if part.startswith("gen_"))
    seed_part = next(part for part in parts if part.startswith("seed_"))
    return LocalRun(
        time_s=parse_int_from_part(time_part, "time_", "s"),
        generation=parse_int_from_part(gen_part, "gen_"),
        seed=parse_int_from_part(seed_part, "seed_"),
        sse=finite_float(objective["sse"], "local SSE", path),
        effe=finite_float(params["effe"], "local effe", path),
        thickness_nm=finite_float(params["thickness_nm"], "local thickness", path),
        rave_nm=finite_float(params["rave_nm"], "local Rave", path),
        sig_l=finite_float(params["sig_l"], "local sigL", path),
        result_path=path,
    )


def read_global_result(path: Path) -> list[GlobalSpectrum]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    total_sse = finite_float(raw["objective"]["total_sse"], "global total SSE", path)
    spectra = []
    for entry in raw["spectra"]:
        spectra.append(
            GlobalSpectrum(
                time_s=int(entry["time_s"]),
                sse=finite_float(entry["sse"], "global spectrum SSE", path),
                effe=finite_float(entry["effe"], "global effe", path),
                thickness_nm=finite_float(entry["thickness_nm"], "global thickness", path),
                rave_nm=finite_float(entry["rave_nm"], "global Rave", path),
                sig_l=finite_float(entry["sig_l"], "global sigL", path),
                result_path=path,
                total_sse=total_sse,
            )
        )
    return spectra


def spread(values: list[float]) -> float:
    return max(values) - min(values)


def diagnosis(local: LocalRun, global_row: GlobalSpectrum | None, runs: list[LocalRun]) -> str:
    rel_sse_spread = spread([run.sse for run in runs]) / max(local.sse, 1.0e-12)
    if global_row is None:
        return "local-only diagnostic; no H3 global result found"
    delta_sse = local.sse - global_row.sse
    param_shift = max(
        abs(local.rave_nm - global_row.rave_nm) / max(abs(global_row.rave_nm), 1.0e-12),
        abs(local.sig_l - global_row.sig_l) / max(abs(global_row.sig_l), 1.0e-12),
        abs(local.thickness_nm - global_row.thickness_nm) / max(abs(global_row.thickness_nm), 1.0e-12),
    )
    if delta_sse < -0.05 * max(global_row.sse, 1.0e-12) and param_shift > 0.05:
        return "supports B: local freedom improves fit versus global coupling"
    if abs(delta_sse) <= 0.05 * max(global_row.sse, 1.0e-12) and rel_sse_spread < 0.05:
        return "supports A: local H3 prior basin remains limiting"
    return "mixed: inspect local/global parameter shifts and seed spread"


base_data_root = Path(sys.argv[1])
base_img_root = Path(sys.argv[2])
base_gp_root = Path(sys.argv[3])
global_h3_root = Path(sys.argv[4])

local_runs = [read_local_result(path) for path in sorted(base_data_root.glob("time_*s/gen_*/seed_*/mmgm_single/spheres/result.json"))]
if not local_runs:
    raise SystemExit(f"No local result.json files found under {base_data_root}")

runs_by_time: dict[int, list[LocalRun]] = {}
for run in local_runs:
    runs_by_time.setdefault(run.time_s, []).append(run)

global_by_time: dict[int, GlobalSpectrum] = {}
global_results = sorted(global_h3_root.glob("gen_*/seed_*/mmgm_single/spheres/global_result.json"))
if global_results:
    best_global_path = min(
        global_results,
        key=lambda path: finite_float(
            json.loads(path.read_text(encoding="utf-8"))["objective"]["total_sse"],
            "global total SSE",
            path,
        ),
    )
    for spectrum in read_global_result(best_global_path):
        global_by_time[spectrum.time_s] = spectrum
else:
    best_global_path = None

summary_csv = base_data_root / "single_spectrum_summary.csv"
summary_report = base_data_root / "single_spectrum_summary_report.txt"
comparison_txt = base_data_root / "global_vs_local_comparison.txt"
trajectory_dat = base_data_root / "best_local_parameters.dat"
comparison_dat = base_data_root / "global_vs_local_parameters.dat"

summary_rows: list[dict[str, object]] = []
report_lines = [
    "Single-spectrum H3 thesis-prior MMGM campaign",
    "",
    "Best local fits by deposition time:",
]
for time_s in sorted(runs_by_time):
    runs = runs_by_time[time_s]
    best = min(runs, key=lambda run: run.sse)
    global_row = global_by_time.get(time_s)
    row = {
        "time_s": time_s,
        "best_seed": best.seed,
        "best_generation": best.generation,
        "best_sse": best.sse,
        "best_effe": best.effe,
        "best_thickness_nm": best.thickness_nm,
        "best_rave_nm": best.rave_nm,
        "best_sig_l": best.sig_l,
        "sse_spread": spread([run.sse for run in runs]),
        "rave_spread": spread([run.rave_nm for run in runs]),
        "sig_l_spread": spread([run.sig_l for run in runs]),
        "thickness_spread": spread([run.thickness_nm for run in runs]),
        "diagnosis": diagnosis(best, global_row, runs),
        "result_path": best.result_path.as_posix(),
    }
    summary_rows.append(row)
    report_lines.extend(
        [
            f"- {time_s}s: seed={best.seed}, generation={best.generation}, "
            f"SSE={best.sse:.10g}, effe={best.effe:.10g}, "
            f"thickness={best.thickness_nm:.10g}, Rave={best.rave_nm:.10g}, "
            f"sigL={best.sig_l:.10g}",
            f"  spreads: SSE={row['sse_spread']:.10g}, Rave={row['rave_spread']:.10g}, "
            f"sigL={row['sig_l_spread']:.10g}, thickness={row['thickness_spread']:.10g}",
            f"  diagnosis: {row['diagnosis']}",
        ]
    )

with summary_csv.open("w", newline="", encoding="utf-8") as handle:
    fieldnames = [
        "time_s",
        "best_seed",
        "best_generation",
        "best_sse",
        "best_effe",
        "best_thickness_nm",
        "best_rave_nm",
        "best_sig_l",
        "sse_spread",
        "rave_spread",
        "sig_l_spread",
        "thickness_spread",
        "diagnosis",
        "result_path",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(summary_rows)
summary_report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

comparison_lines = [
    "Global H3 vs best local single-spectrum H3",
    "",
    f"Global source: {best_global_path.as_posix() if best_global_path else 'missing'}",
    "",
]
with trajectory_dat.open("w", encoding="utf-8") as handle:
    handle.write("# time_s sse effe thickness_nm rave_nm sig_l seed generation\n")
    for row in summary_rows:
        handle.write(
            f"{row['time_s']} {row['best_sse']:.17g} {row['best_effe']:.17g} "
            f"{row['best_thickness_nm']:.17g} {row['best_rave_nm']:.17g} "
            f"{row['best_sig_l']:.17g} {row['best_seed']} {row['best_generation']}\n"
        )

with comparison_dat.open("w", encoding="utf-8") as handle:
    handle.write("# time_s local_sse global_sse local_eff global_eff local_thick global_thick local_rave global_rave local_sigl global_sigl\n")
    for row in summary_rows:
        time_s = int(row["time_s"])
        global_row = global_by_time.get(time_s)
        if global_row is None:
            comparison_lines.append(f"{time_s}s: no global H3 comparison available")
            continue
        delta_rave = float(row["best_rave_nm"]) - global_row.rave_nm
        delta_sig_l = float(row["best_sig_l"]) - global_row.sig_l
        delta_thickness = float(row["best_thickness_nm"]) - global_row.thickness_nm
        delta_effe = float(row["best_effe"]) - global_row.effe
        delta_sse = float(row["best_sse"]) - global_row.sse
        comparison_lines.extend(
            [
                f"{time_s}s:",
                f"  local:  SSE={float(row['best_sse']):.10g}, effe={float(row['best_effe']):.10g}, "
                f"thickness={float(row['best_thickness_nm']):.10g}, Rave={float(row['best_rave_nm']):.10g}, "
                f"sigL={float(row['best_sig_l']):.10g}",
                f"  global: SSE={global_row.sse:.10g}, effe={global_row.effe:.10g}, "
                f"thickness={global_row.thickness_nm:.10g}, Rave={global_row.rave_nm:.10g}, "
                f"sigL={global_row.sig_l:.10g}",
                f"  Delta:  dRave={delta_rave:.10g}, dSigL={delta_sig_l:.10g}, "
                f"dThickness={delta_thickness:.10g}, dEffe={delta_effe:.10g}, dSSE={delta_sse:.10g}",
            ]
        )
        handle.write(
            f"{time_s} {float(row['best_sse']):.17g} {global_row.sse:.17g} "
            f"{float(row['best_effe']):.17g} {global_row.effe:.17g} "
            f"{float(row['best_thickness_nm']):.17g} {global_row.thickness_nm:.17g} "
            f"{float(row['best_rave_nm']):.17g} {global_row.rave_nm:.17g} "
            f"{float(row['best_sig_l']):.17g} {global_row.sig_l:.17g}\n"
        )
comparison_txt.write_text("\n".join(comparison_lines) + "\n", encoding="utf-8")

base_img_root.mkdir(parents=True, exist_ok=True)
base_gp_root.mkdir(parents=True, exist_ok=True)

plot_specs = {
    "local_parameter_trajectory": [
        "set ylabel 'Parameter value'",
        "plot data using 1:4 with linespoints lw 2 title 'thickness nm', \\",
        "     data using 1:5 with linespoints lw 2 title 'Rave nm', \\",
        "     data using 1:6 with linespoints lw 2 title 'sigL'",
    ],
    "local_vs_global_rave": [
        "set ylabel 'Rave (nm)'",
        "plot comp using 1:8 with linespoints lw 2 title 'local', \\",
        "     comp using 1:9 with linespoints lw 2 title 'global'",
    ],
    "local_vs_global_sigl": [
        "set ylabel 'sigL'",
        "plot comp using 1:10 with linespoints lw 2 title 'local', \\",
        "     comp using 1:11 with linespoints lw 2 title 'global'",
    ],
    "local_vs_global_thickness": [
        "set ylabel 'thickness (nm)'",
        "plot comp using 1:6 with linespoints lw 2 title 'local', \\",
        "     comp using 1:7 with linespoints lw 2 title 'global'",
    ],
    "local_vs_global_sse": [
        "set ylabel 'SSE'",
        "plot comp using 1:2 with linespoints lw 2 title 'local', \\",
        "     comp using 1:3 with linespoints lw 2 title 'global'",
    ],
}

for name, body in plot_specs.items():
    gp = base_gp_root / f"{name}.gp"
    png = base_img_root / f"{name}.png"
    lines = [
        "set terminal pngcairo noenhanced size 1400,900",
        f"set output '{png.resolve().as_posix()}'",
        f"data = '{trajectory_dat.resolve().as_posix()}'",
        f"comp = '{comparison_dat.resolve().as_posix()}'",
        "set title 'Single-spectrum H3 diagnostic campaign'",
        "set grid",
        "set xlabel 'Deposition time (s)'",
        "set key outside right",
        *body,
        "",
    ]
    gp.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(["gnuplot", gp.as_posix()], check=True)
PY
summary_exit=$?
set -e
if [ "$summary_exit" -ne 0 ]; then
  echo "summary status:failed exit_code:${summary_exit} timestamp:$(timestamp)" >> "$STATUS_FILE"
  exit "$summary_exit"
fi
echo "summary status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
echo "=== single-spectrum H3 thesis-prior MMGM campaign finished: $(timestamp) ===" >> "$STATUS_FILE"
