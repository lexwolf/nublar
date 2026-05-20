#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"
SEEDS=(111 222 333)
GENERATIONS=(400)
POPULATION_SIZE=64
EXCLUDE_TIMES="30,40,50,60"
STRATEGY_NAME="mmgm_early_bounded"

BASE_DATA_ROOT="data/output/tests/mmgm_early_global"
BASE_IMG_ROOT="img/tests/mmgm_early_global"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_early_global"
STATUS_FILE="${BASE_DATA_ROOT}/status.txt"
MMGM_PRIORS="data/input/optimal/optical_priors/mmgm_single_early_global.json"

DATA_ROOT="${BASE_DATA_ROOT}/${STRATEGY_NAME}_pop_${POPULATION_SIZE}"
IMG_ROOT="${BASE_IMG_ROOT}/${STRATEGY_NAME}_pop_${POPULATION_SIZE}"
GP_ROOT="${BASE_GP_ROOT}/${STRATEGY_NAME}_pop_${POPULATION_SIZE}"

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"
echo "=== MMGM early-regime global diagnostic started: $(timestamp) ===" >> "$STATUS_FILE"

python3 tools/optimal/build_mmgm_early_global_prior.py \
  --output "$MMGM_PRIORS"

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
    echo "==> MMGM early global diagnostic: generation=${generation}, seed=${seed}"
    set +e
    python3 tools/optimal/optimize_global_model_parameters.py \
      "$MODEL_FLAG" \
      --thesis-priors-json "$MMGM_PRIORS" \
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
python3 tests/analyze_regime_global_campaign.py \
  --root "$DATA_ROOT" \
  --label "MMGM EARLY GLOBAL DIAGNOSTIC"
analyzer_exit=$?
set -e
if [ "$analyzer_exit" -ne 0 ]; then
  echo "analyzer status:failed exit_code:${analyzer_exit} timestamp:$(timestamp)" >> "$STATUS_FILE"
  exit 0
fi
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
