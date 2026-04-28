#!/bin/bash
set -euo pipefail

# WARNING: this test runs the global MMGM optimizer across multiple seeds and
# generation counts, so it is intended for long unattended runs.

MODEL_FLAG="--mmgm-spheres-single"
SEEDS=(12345 111 222 333 444)
GENERATIONS=(30 60 100)
POPULATION_SIZE=24

DATA_ROOT="data/output/tests/mmgm_single_global_seed_stability"
IMG_ROOT="img/tests/mmgm_single_global_seed_stability"
GP_ROOT="scripts/gnuplot/tests/mmgm_single_global_seed_stability"

mkdir -p "$DATA_ROOT" "$IMG_ROOT" "$GP_ROOT"

for generation in "${GENERATIONS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    RESULT_JSON="${DATA_ROOT}/gen_${generation}/seed_${seed}/mmgm_single/spheres/global_result.json"
    if [[ -f "$RESULT_JSON" ]]; then
      echo "==> Skipping completed global MMGM single run: generation=${generation}, seed=${seed}"
      continue
    fi

    echo "==> Global MMGM single seed stability: generation=${generation}, seed=${seed}"
    python3 tools/optimal/optimize_global_model_parameters.py "$MODEL_FLAG" \
      --seed "$seed" \
      --max-generations "$generation" \
      --population-size "$POPULATION_SIZE" \
      --output-dir "${DATA_ROOT}/gen_${generation}/seed_${seed}" \
      --image-dir "${IMG_ROOT}/gen_${generation}/seed_${seed}" \
      --gnuplot-dir "${GP_ROOT}/gen_${generation}/seed_${seed}"
  done
done

python3 tests/analyze_mmgm_single_global_stability.py
