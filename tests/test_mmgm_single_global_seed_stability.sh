#!/bin/bash
set -euo pipefail

# WARNING: this test runs the global MMGM optimizer across multiple seeds and
# generation counts, so it is intended for long unattended runs.

MODEL_FLAG="--mmgm-spheres-single"
SEEDS=(111 222 333)
GENERATIONS=(100 200 300)
POPULATION_SIZE=48

BASE_DATA_ROOT="data/output/tests/mmgm_single_global_seed_stability"
BASE_IMG_ROOT="img/tests/mmgm_single_global_seed_stability"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_global_seed_stability"

DATA_ROOT="${BASE_DATA_ROOT}/pop_${POPULATION_SIZE}"
IMG_ROOT="${BASE_IMG_ROOT}/pop_${POPULATION_SIZE}"
GP_ROOT="${BASE_GP_ROOT}/pop_${POPULATION_SIZE}"

mkdir -p "$DATA_ROOT" "$IMG_ROOT" "$GP_ROOT"

for generation in "${GENERATIONS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    OUT_DIR="${DATA_ROOT}/gen_${generation}/seed_${seed}"
    IMG_DIR="${IMG_ROOT}/gen_${generation}/seed_${seed}"
    GP_DIR="${GP_ROOT}/gen_${generation}/seed_${seed}"
    DONE_FILE="${OUT_DIR}/mmgm_single/spheres/global_result.json"
    if [[ -f "$DONE_FILE" ]]; then
      echo "==> Skipping completed global MMGM single run: generation=${generation}, seed=${seed}"
      continue
    fi

    echo "==> Global MMGM single seed stability: generation=${generation}, seed=${seed}"
    python3 tools/optimal/optimize_global_model_parameters.py "$MODEL_FLAG" \
      --seed "$seed" \
      --max-generations "$generation" \
      --population-size "$POPULATION_SIZE" \
      --output-dir "$OUT_DIR" \
      --image-dir "$IMG_DIR" \
      --gnuplot-dir "$GP_DIR"
  done
done

python3 tests/analyze_mmgm_single_global_stability.py --root "$DATA_ROOT"
