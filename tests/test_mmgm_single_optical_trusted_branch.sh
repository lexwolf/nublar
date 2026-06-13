#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"
SEEDS=(111 222 333)
GENERATIONS=(300)
POPULATION_SIZE=48
EXCLUDE_TIMES="30,40"
STRATEGY_NAME="optical_trusted_branch"

BASE_DATA_ROOT="data/output/tests/mmgm_single_optical_trusted_branch"
BASE_IMG_ROOT="img/tests/mmgm_single_optical_trusted_branch"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_optical_trusted_branch"
STATUS_FILE="${BASE_DATA_ROOT}/status.txt"
OPTICAL_PRIORS="data/input/optimal/optical_priors/mmgm_single_optical_trusted_branch.json"

DATA_ROOT="${BASE_DATA_ROOT}/${STRATEGY_NAME}_pop_${POPULATION_SIZE}"
IMG_ROOT="${BASE_IMG_ROOT}/${STRATEGY_NAME}_pop_${POPULATION_SIZE}"
GP_ROOT="${BASE_GP_ROOT}/${STRATEGY_NAME}_pop_${POPULATION_SIZE}"

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"
echo "=== trusted optical-branch MMGM global campaign started: $(timestamp) ===" >> "$STATUS_FILE"

python3 tools/optimal/build_optical_prior_from_local_fits.py \
  --output "$OPTICAL_PRIORS"

mkdir -p "$DATA_ROOT" "$IMG_ROOT" "$GP_ROOT"

run_total=$(( ${#SEEDS[@]} * ${#GENERATIONS[@]} ))
run_index=0

for generation in "${GENERATIONS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    run_index=$(( run_index + 1 ))
    OUT_DIR="${DATA_ROOT}/gen_${generation}/seed_${seed}"
    IMG_DIR="${IMG_ROOT}/gen_${generation}/seed_${seed}"
    GP_DIR="${GP_ROOT}/gen_${generation}/seed_${seed}"
    DONE_FILE="${OUT_DIR}/mmgm_single/spheres/global_result.json"
    status_prefix="seed:${seed} generation:${generation} run:${run_index}/${run_total}"

    if [ -f "$DONE_FILE" ]; then
      echo "${status_prefix} status:skipped timestamp:$(timestamp)" >> "$STATUS_FILE"
      continue
    fi

    echo "${status_prefix} status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
    echo "==> Trusted optical-branch global campaign: generation=${generation}, seed=${seed}"
    set +e
    python3 tools/optimal/optimize_global_model_parameters.py \
      "$MODEL_FLAG" \
      --thesis-priors-json "$OPTICAL_PRIORS" \
      --thesis-priors-mode bounded \
      --exclude-times "$EXCLUDE_TIMES" \
      --hag-linearity-mode none \
      --seed "$seed" \
      --max-generations "$generation" \
      --population-size "$POPULATION_SIZE" \
      --output-dir "$OUT_DIR" \
      --image-dir "$IMG_DIR" \
      --gnuplot-dir "$GP_DIR"
    exit_code=$?
    set -e
    if [ "$exit_code" -ne 0 ]; then
      echo "${status_prefix} status:failed exit_code:${exit_code} timestamp:$(timestamp)" >> "$STATUS_FILE"
      continue
    fi
    echo "${status_prefix} status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
  done
done

n_results=$(find "$DATA_ROOT" -name global_result.json | wc -l)
if [ "$n_results" -eq 0 ]; then
  echo "analyzer status:skipped reason:no_successful_runs timestamp:$(timestamp)" >> "$STATUS_FILE"
  exit 0
fi

echo "analyzer status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
set +e
python3 tests/analyze_mmgm_single_global_stability.py --root "$DATA_ROOT"
analyzer_exit=$?
set -e
if [ "$analyzer_exit" -ne 0 ]; then
  echo "analyzer status:failed exit_code:${analyzer_exit} timestamp:$(timestamp)" >> "$STATUS_FILE"
  exit 0
fi

python3 - "$DATA_ROOT" "$OPTICAL_PRIORS" <<'PY'
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path


def rel_delta(value: float, reference: float) -> float:
    return (value - reference) / reference


def fmt(value: float) -> str:
    return f"{value:.6g}"


data_root = Path(sys.argv[1])
prior_path = Path(sys.argv[2])
summary_path = data_root / "global_summary.csv"
report_path = data_root / "global_report.txt"
prior = json.loads(prior_path.read_text(encoding="utf-8"))
references = {
    int(time_s): entry["reference_values"]
    for time_s, entry in prior["bounds_by_time_s"].items()
}
with summary_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
if not rows:
    raise SystemExit(f"No rows in {summary_path}")
latest_generation = max(int(row["generation"]) for row in rows)
latest_rows = [row for row in rows if int(row["generation"]) == latest_generation]
best = min(latest_rows, key=lambda row: float(row["total_sse"]))
times_s = sorted(references)

max_abs_rel_by_parameter = {}
lines = [
    "",
    "=== TRUSTED OPTICAL BRANCH CHECK ===",
    f"Prior file: {prior_path.as_posix()}",
    f"Latest generation: {latest_generation}",
    f"Best latest-generation run: seed {best['seed']}, total_SSE {fmt(float(best['total_sse']))}, total_RMSE {fmt(float(best['total_rmse']))}",
    "",
    "Best-run relative deviations from trusted local-fit references:",
]
for parameter, column_prefix, ref_key in (
    ("effe", "effe", "effe"),
    ("thickness", "thickness", "thickness_nm"),
    ("Rave", "rave", "rave_nm"),
    ("sigL", "sig_l", "sig_l"),
):
    deviations = []
    for time_s in times_s:
        value = float(best[f"{column_prefix}_{time_s}s"])
        reference = float(references[time_s][ref_key])
        deviations.append(rel_delta(value, reference))
    max_abs_rel_by_parameter[parameter] = max(abs(value) for value in deviations)
    joined = ", ".join(
        f"{time_s}s {100.0 * deviation:+.2f}%"
        for time_s, deviation in zip(times_s, deviations, strict=True)
    )
    lines.append(f"  {parameter}: {joined}")

hag_values = [float(best[f"h_ag_{time_s}s"]) for time_s in times_s]
hag_monotonic = all(left <= right for left, right in zip(hag_values, hag_values[1:]))
lines.extend(
    [
        "",
        "Trusted-branch survival criteria:",
        f"  near trusted morphology: max |relative deviation| thickness={100.0 * max_abs_rel_by_parameter['thickness']:.2f}%, Rave={100.0 * max_abs_rel_by_parameter['Rave']:.2f}%, sigL={100.0 * max_abs_rel_by_parameter['sigL']:.2f}%",
        f"  hAg monotonic: {'yes' if hag_monotonic else 'no'}",
        "  curve quality proxy: inspect per-seed fit PNGs and total_RMSE above",
        "  seed stability: see spread metrics in the generation summary above",
        "",
    ]
)
with report_path.open("a", encoding="utf-8") as handle:
    handle.write("\n".join(lines))
PY

echo "analyzer status:done timestamp:$(timestamp)" >> "$STATUS_FILE"

echo "trajectory_diagnostics status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
python3 tools/optimal/extract_global_parameter_trajectories.py \
  --root "$BASE_DATA_ROOT" \
  --output-dir "${BASE_DATA_ROOT}/trajectory_diagnostics"

python3 scripts/gnuplot/tests/generate_parameter_trajectory_plots.py \
  --root "$BASE_DATA_ROOT" \
  --output-dir "${BASE_DATA_ROOT}/trajectory_diagnostics" \
  --gnuplot-dir "${BASE_GP_ROOT}/trajectory_diagnostics" \
  --image-dir "${BASE_IMG_ROOT}/trajectory_diagnostics"
echo "trajectory_diagnostics status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
