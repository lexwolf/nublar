#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"
EXCLUDE_TIMES="10,20,50,60"

if [ -n "${CAMPAIGN_SEEDS:-}" ]; then
  read -r -a SEEDS <<< "$CAMPAIGN_SEEDS"
else
  SEEDS=(111 222 333 444 555 777 999 12345 54321 99999 424242 8675309)
fi

if [ -n "${CAMPAIGN_GENERATIONS:-}" ]; then
  read -r -a GENERATIONS <<< "$CAMPAIGN_GENERATIONS"
else
  GENERATIONS=(400)
fi

POPULATION_SIZE="${CAMPAIGN_POPULATION_SIZE:-64}"
HAG_MIN_NM="${CAMPAIGN_HAG_MIN_NM:-1.0}"
HAG_MAX_NM="${CAMPAIGN_HAG_MAX_NM:-3.0}"

BASE_DATA_ROOT="data/output/tests/mmgm_transition_hag_window"
BASE_IMG_ROOT="img/tests/mmgm_transition_hag_window"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_transition_hag_window"
STATUS_FILE="${BASE_DATA_ROOT}/status.txt"
FREE_BOUNDS_JSON="${BASE_DATA_ROOT}/transition_hag_window_bounds.json"
BASE_BOUNDS_JSON="data/input/optimal/bounds.json"

DATA_ROOT="${BASE_DATA_ROOT}/free_hag_${HAG_MIN_NM}_${HAG_MAX_NM}_pop_${POPULATION_SIZE}"
IMG_ROOT="${BASE_IMG_ROOT}/free_hag_${HAG_MIN_NM}_${HAG_MAX_NM}_pop_${POPULATION_SIZE}"
GP_ROOT="${BASE_GP_ROOT}/free_hag_${HAG_MIN_NM}_${HAG_MAX_NM}_pop_${POPULATION_SIZE}"

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"
echo "=== MMGM transition hAg-window campaign started: $(timestamp) ===" >> "$STATUS_FILE"

python3 - "$BASE_BOUNDS_JSON" "$FREE_BOUNDS_JSON" "$POPULATION_SIZE" <<'PY'
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
population_size = int(sys.argv[3])

raw = json.loads(source.read_text(encoding="utf-8"))
out = deepcopy(raw)
params = out["models"]["mmgm_spheres_single"]["native_fit_parameters"]
params["effe"].update({"min": 0.001, "max": 0.95, "transform": "none"})
params["thickness_nm"].update({"min": 1.0, "max": 100.0, "transform": "log"})
params["rave_nm"].update({"min": 0.5, "max": 200.0, "transform": "log"})
params["sig_l"].update({"min": 0.02, "max": 2.0, "transform": "log"})
optimizer = out["models"]["mmgm_spheres_single"].setdefault("optimizer", {})
de = optimizer.setdefault("differential_evolution", {})
de["population_size"] = population_size
de["max_generations"] = 400
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
PY

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
    echo "==> MMGM transition hAg-window: generation=${generation}, seed=${seed}"
    set +e
    python3 tools/optimal/optimize_global_model_parameters.py \
      "$MODEL_FLAG" \
      --bounds-json "$FREE_BOUNDS_JSON" \
      --exclude-times "$EXCLUDE_TIMES" \
      --hag-linearity-mode none \
      --hag-window-mode bounded \
      --hag-window-min-nm "$HAG_MIN_NM" \
      --hag-window-max-nm "$HAG_MAX_NM" \
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
python3 tests/analyze_transition_hag_window.py --root "$DATA_ROOT"
analyzer_exit=$?
set -e
if [ "$analyzer_exit" -ne 0 ]; then
  echo "analyzer status:failed exit_code:${analyzer_exit} timestamp:$(timestamp)" >> "$STATUS_FILE"
  exit 0
fi
echo "analyzer status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
