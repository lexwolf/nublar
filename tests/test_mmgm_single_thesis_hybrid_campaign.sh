#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"

SEEDS=(111 222 333)
GENERATIONS=(150 300)
POPULATION_SIZE=48

BASE_DATA_ROOT="data/output/tests/mmgm_single_thesis_hybrid_campaign"
BASE_IMG_ROOT="img/tests/mmgm_single_thesis_hybrid_campaign"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_thesis_hybrid_campaign"

STATUS_FILE="${BASE_DATA_ROOT}/status.txt"

STRATEGIES=(H1 H2 H3)
THESIS_PRIOR_DIR="data/input/optimal/thesis_priors"
THESIS_PRIOR_SOURCE="data/experimental/thesis/chap4-prior.dat"

timestamp() {
  date --iso-8601=seconds
}

strategy_name() {
  case "$1" in
    H1)
      echo "rave_soft_sigl_hard_thickness_hard"
      ;;
    H2)
      echo "rave_softer_sigl_hard_thickness_hard"
      ;;
    H3)
      echo "rave_soft_sigl_hard_thickness_soft"
      ;;
    *)
      echo "Unknown strategy: $1" >&2
      return 1
      ;;
  esac
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"
echo "=== thesis hybrid-prior MMGM campaign started: $(timestamp) ===" >> "$STATUS_FILE"

python3 tools/optimal/build_thesis_mmgm_prior.py \
  --input "$THESIS_PRIOR_SOURCE" \
  --output-dir "$THESIS_PRIOR_DIR"

strategy_total="${#STRATEGIES[@]}"
run_total=$(( strategy_total * ${#SEEDS[@]} * ${#GENERATIONS[@]} ))
run_index=0
strategy_index=0

for strategy in "${STRATEGIES[@]}"; do
  strategy_index=$(( strategy_index + 1 ))
  name="$(strategy_name "$strategy")"
  THESIS_PRIORS="${THESIS_PRIOR_DIR}/mmgm_single_thesis_hybrid_${strategy}.json"
  DATA_ROOT="${BASE_DATA_ROOT}/${strategy}_pop_${POPULATION_SIZE}"
  IMG_ROOT="${BASE_IMG_ROOT}/${strategy}_pop_${POPULATION_SIZE}"
  GP_ROOT="${BASE_GP_ROOT}/${strategy}_pop_${POPULATION_SIZE}"

  mkdir -p "$DATA_ROOT" "$IMG_ROOT" "$GP_ROOT"

  for generation in "${GENERATIONS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      run_index=$(( run_index + 1 ))
      OUT_DIR="${DATA_ROOT}/gen_${generation}/seed_${seed}"
      IMG_DIR="${IMG_ROOT}/gen_${generation}/seed_${seed}"
      GP_DIR="${GP_ROOT}/gen_${generation}/seed_${seed}"
      DONE_FILE="${OUT_DIR}/mmgm_single/spheres/global_result.json"
      status_prefix="strategy:${strategy_index}/${strategy_total} strategy_name:${name} seed:${seed} generation:${generation} run:${run_index}/${run_total}"

      if [ -f "$DONE_FILE" ]; then
        echo "${status_prefix} status:skipped timestamp:$(timestamp)" >> "$STATUS_FILE"
        continue
      fi

      echo "${status_prefix} status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
      echo "==> Thesis hybrid-prior campaign: strategy=${strategy} (${name}), generation=${generation}, seed=${seed}"
      set +e
      python3 tools/optimal/optimize_global_model_parameters.py \
        "$MODEL_FLAG" \
        --thesis-priors-json "$THESIS_PRIORS" \
        --thesis-priors-mode bounded \
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
    echo "strategy:${strategy_index}/${strategy_total} strategy_name:${name} status:analyzer_skipped reason:no_successful_runs timestamp:$(timestamp)" >> "$STATUS_FILE"
    continue
  fi

  analyzer_prefix="strategy:${strategy_index}/${strategy_total} strategy_name:${name}"
  echo "${analyzer_prefix} status:analyzer_started timestamp:$(timestamp)" >> "$STATUS_FILE"
  set +e
  python3 tests/analyze_mmgm_single_global_stability.py --root "$DATA_ROOT"
  analyzer_exit=$?
  set -e
  if [ "$analyzer_exit" -ne 0 ]; then
    echo "${analyzer_prefix} status:analyzer_failed exit_code:${analyzer_exit} timestamp:$(timestamp)" >> "$STATUS_FILE"
    continue
  fi
  echo "${analyzer_prefix} status:analyzer_done timestamp:$(timestamp)" >> "$STATUS_FILE"
done

python3 - "$BASE_DATA_ROOT" "$POPULATION_SIZE" "${STRATEGIES[@]}" <<'PY'
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


STRATEGY_NAMES = {
    "H1": "rave_soft_sigl_hard_thickness_hard",
    "H2": "rave_softer_sigl_hard_thickness_hard",
    "H3": "rave_soft_sigl_hard_thickness_soft",
}


def parse_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise SystemExit(f"Non-finite numeric value in stability CSV: {value!r}")
    return parsed


def final_diagnosis(report_file: Path) -> str:
    lines = report_file.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("=== FINAL DIAGNOSIS ===") + 1
    except ValueError as exc:
        raise SystemExit(f"Missing final diagnosis section in {report_file}") from exc
    for line in lines[start:]:
        stripped = line.strip()
        if stripped:
            return stripped
    raise SystemExit(f"Missing final diagnosis value in {report_file}")


def latest_stability_row(csv_file: Path) -> dict[str, str]:
    with csv_file.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"No stability rows in {csv_file}")
    return max(rows, key=lambda row: int(row["generation"]))


base_data_root = Path(sys.argv[1])
population_size = sys.argv[2]
strategy_ids = sys.argv[3:]
comparison_csv = base_data_root / "hybrid_comparison.csv"
comparison_report = base_data_root / "hybrid_comparison_report.txt"

rows: list[dict[str, str]] = []
report_sections: list[str] = []
for strategy_id in strategy_ids:
    name = STRATEGY_NAMES[strategy_id]
    data_root = base_data_root / f"{strategy_id}_pop_{population_size}"
    stability_file = data_root / "global_stability_by_generation.csv"
    report_file = data_root / "global_report.txt"
    if not report_file.exists() or not stability_file.exists():
        row = {
            "strategy_name": name,
            "latest_generation": "NA",
            "best_total_sse": "NA",
            "total_sse_rel_spread": "NA",
            "max_hag_rel_spread": "NA",
            "max_thickness_rel_spread": "NA",
            "max_rave_rel_spread": "NA",
            "max_sigl_rel_spread": "NA",
            "diagnosis": "FAILED",
            "report_file": "NA",
        }
    else:
        stability = latest_stability_row(stability_file)
        row = {
            "strategy_name": name,
            "latest_generation": str(int(stability["generation"])),
            "best_total_sse": f"{parse_float(stability['total_sse_min']):.12g}",
            "total_sse_rel_spread": f"{parse_float(stability['total_sse_rel_spread']):.12g}",
            "max_hag_rel_spread": f"{parse_float(stability['h_ag_rel_spread_max']):.12g}",
            "max_thickness_rel_spread": f"{parse_float(stability['thickness_rel_spread_max']):.12g}",
            "max_rave_rel_spread": f"{parse_float(stability['rave_rel_spread_max']):.12g}",
            "max_sigl_rel_spread": f"{parse_float(stability['sig_l_rel_spread_max']):.12g}",
            "diagnosis": final_diagnosis(report_file),
            "report_file": report_file.as_posix(),
        }
    rows.append(row)
    report_sections.extend(
        [
            f"Strategy: {row['strategy_name']}",
            f"  latest generation: {row['latest_generation']}",
            f"  best total SSE: {row['best_total_sse']}",
            f"  total SSE relative spread: {row['total_sse_rel_spread']}",
            f"  max hAg relative spread: {row['max_hag_rel_spread']}",
            f"  max thickness relative spread: {row['max_thickness_rel_spread']}",
            f"  max Rave relative spread: {row['max_rave_rel_spread']}",
            f"  max sigL relative spread: {row['max_sigl_rel_spread']}",
            f"  diagnosis: {row['diagnosis']}",
            f"  report: {row['report_file']}",
            "",
        ]
    )

columns = [
    "strategy_name",
    "latest_generation",
    "best_total_sse",
    "total_sse_rel_spread",
    "max_hag_rel_spread",
    "max_thickness_rel_spread",
    "max_rave_rel_spread",
    "max_sigl_rel_spread",
    "diagnosis",
    "report_file",
]
with comparison_csv.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

lines = ["MMGM THESIS HYBRID PRIOR CAMPAIGN", "", *report_sections]
comparison_report.write_text("\n".join(lines), encoding="utf-8")

print(f"Wrote {comparison_csv}")
print(f"Wrote {comparison_report}")
PY

echo "trajectory_diagnostics status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
python3 tools/optimal/extract_global_parameter_trajectories.py \
  --root "$BASE_DATA_ROOT" \
  --output-dir "${BASE_DATA_ROOT}/trajectory_diagnostics"

python3 scripts/gnuplot/tests/generate_parameter_trajectory_plots.py \
  --root "$BASE_DATA_ROOT" \
  --output-dir "${BASE_DATA_ROOT}/trajectory_diagnostics"
echo "trajectory_diagnostics status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
