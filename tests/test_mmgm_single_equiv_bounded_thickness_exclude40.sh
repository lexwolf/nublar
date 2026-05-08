#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"
AFM_PRIORS="data/input/optimal/afm_priors/mmgm_single_equivalent_radius_nm.json"
SEEDS=(111 222 333)
GENERATIONS=(80 150)
POPULATION_SIZE=36
EXCLUDE_TIMES="40"

DATA_ROOT="data/output/tests/mmgm_single_equiv_bounded_thickness_exclude40"
IMG_ROOT="img/tests/mmgm_single_equiv_bounded_thickness_exclude40"
GP_ROOT="scripts/gnuplot/tests/mmgm_single_equiv_bounded_thickness_exclude40"

mkdir -p "$DATA_ROOT" "$IMG_ROOT" "$GP_ROOT"

for generation in "${GENERATIONS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    OUT_DIR="${DATA_ROOT}/gen_${generation}/seed_${seed}"
    IMG_DIR="${IMG_ROOT}/gen_${generation}/seed_${seed}"
    GP_DIR="${GP_ROOT}/gen_${generation}/seed_${seed}"
    DONE_FILE="${OUT_DIR}/mmgm_single/spheres/global_result.json"
    if [ -f "$DONE_FILE" ]; then
      echo "Skipping $OUT_DIR (already complete)"
      continue
    fi

    echo "==> Bounded AFM thickness exclude-40 campaign: generation=${generation}, seed=${seed}"
    python3 tools/optimal/optimize_global_model_parameters.py "$MODEL_FLAG" \
      --afm-priors-json "$AFM_PRIORS" \
      --afm-priors-mode bounded \
      --afm-thickness-prior bounded \
      --exclude-times "$EXCLUDE_TIMES" \
      --seed "$seed" \
      --max-generations "$generation" \
      --population-size "$POPULATION_SIZE" \
      --output-dir "$OUT_DIR" \
      --image-dir "$IMG_DIR" \
      --gnuplot-dir "$GP_DIR"
  done
done

python3 tests/analyze_mmgm_single_global_stability.py --root "$DATA_ROOT"
