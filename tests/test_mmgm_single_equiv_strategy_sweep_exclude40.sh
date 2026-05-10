#!/bin/bash
set -euo pipefail

# Focused weekend sweep for the winning equivalent_radius_nm AFM proxy.

MODEL_FLAG="--mmgm-spheres-single"
AFM_PRIORS="data/input/optimal/afm_priors/mmgm_single_equivalent_radius_nm.json"
EXCLUDE_TIMES="40"

SEEDS=(111 222 333)
GENERATIONS=(80 150)
POPULATION_SIZE=36

BASE_DATA_ROOT="data/output/tests/mmgm_single_equiv_strategy_sweep_exclude40"
BASE_IMG_ROOT="img/tests/mmgm_single_equiv_strategy_sweep_exclude40"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_equiv_strategy_sweep_exclude40"
STATUS_FILE="${BASE_DATA_ROOT}/status.txt"

STRATEGIES=(
  "rave_bounded_sigl_fixed_no_thickness"
  "rave_bounded_sigl_fixed_thickness_05_2"
  "rave_bounded_sigl_bounded_thickness_025_4"
)

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"
echo "=== equivalent-radius strategy sweep exclude40 started: $(timestamp) ===" >> "$STATUS_FILE"

strategy_total="${#STRATEGIES[@]}"
run_total=$(( strategy_total * ${#SEEDS[@]} * ${#GENERATIONS[@]} ))
run_index=0
strategy_index=0

for strategy_name in "${STRATEGIES[@]}"; do
  strategy_index=$(( strategy_index + 1 ))
  DATA_ROOT="${BASE_DATA_ROOT}/${strategy_name}_pop_${POPULATION_SIZE}"
  IMG_ROOT="${BASE_IMG_ROOT}/${strategy_name}_pop_${POPULATION_SIZE}"
  GP_ROOT="${BASE_GP_ROOT}/${strategy_name}_pop_${POPULATION_SIZE}"

  mkdir -p "$DATA_ROOT" "$IMG_ROOT" "$GP_ROOT"

  case "$strategy_name" in
    rave_bounded_sigl_fixed_no_thickness)
      STRATEGY_ARGS=(
        --afm-priors-mode bounded
        --afm-sigl-mode fixed
        --afm-thickness-prior none
      )
      ;;
    rave_bounded_sigl_fixed_thickness_05_2)
      STRATEGY_ARGS=(
        --afm-priors-mode bounded
        --afm-sigl-mode fixed
        --afm-thickness-prior bounded
        --afm-thickness-scale-low 0.5
        --afm-thickness-scale-high 2.0
      )
      ;;
    rave_bounded_sigl_bounded_thickness_025_4)
      STRATEGY_ARGS=(
        --afm-priors-mode bounded
        --afm-sigl-mode bounded
        --afm-thickness-prior bounded
        --afm-thickness-scale-low 0.25
        --afm-thickness-scale-high 4.0
      )
      ;;
    *)
      echo "Unknown strategy: $strategy_name" >&2
      exit 1
      ;;
  esac

  for generation in "${GENERATIONS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      run_index=$(( run_index + 1 ))
      OUT_DIR="${DATA_ROOT}/gen_${generation}/seed_${seed}"
      IMG_DIR="${IMG_ROOT}/gen_${generation}/seed_${seed}"
      GP_DIR="${GP_ROOT}/gen_${generation}/seed_${seed}"
      DONE_FILE="${OUT_DIR}/mmgm_single/spheres/global_result.json"
      status_prefix="strategy:${strategy_index}/${strategy_total} strategy_name:${strategy_name} seed:${seed} generation:${generation} run:${run_index}/${run_total} excluded_times:${EXCLUDE_TIMES}"

      if [ -f "$DONE_FILE" ]; then
        echo "Skipping $OUT_DIR (already complete)"
        echo "${status_prefix} status:skipped timestamp:$(timestamp)" >> "$STATUS_FILE"
        continue
      fi

      echo "${status_prefix} status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
      echo "==> Equivalent-radius strategy sweep: strategy=${strategy_name}, generation=${generation}, seed=${seed}"
      set +e
      python3 tools/optimal/optimize_global_model_parameters.py \
        "$MODEL_FLAG" \
        --afm-priors-json "$AFM_PRIORS" \
        "${STRATEGY_ARGS[@]}" \
        --exclude-times "$EXCLUDE_TIMES" \
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
    echo "strategy:${strategy_index}/${strategy_total} strategy_name:${strategy_name} status:analyzer_skipped reason:no_successful_runs timestamp:$(timestamp)" >> "$STATUS_FILE"
    continue
  fi

  echo "strategy:${strategy_index}/${strategy_total} strategy_name:${strategy_name} status:analyzer_started timestamp:$(timestamp)" >> "$STATUS_FILE"
  python3 tests/analyze_mmgm_single_global_stability.py --root "$DATA_ROOT"
  echo "strategy:${strategy_index}/${strategy_total} strategy_name:${strategy_name} status:analyzer_done timestamp:$(timestamp)" >> "$STATUS_FILE"
done

python3 - "$BASE_DATA_ROOT" "$POPULATION_SIZE" "${STRATEGIES[@]}" <<'PY'
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


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
strategy_names = sys.argv[3:]
comparison_csv = base_data_root / "strategy_comparison.csv"
comparison_report = base_data_root / "strategy_comparison_report.txt"

rows: list[dict[str, str]] = []
report_sections: list[str] = []
for strategy_name in strategy_names:
    data_root = base_data_root / f"{strategy_name}_pop_{population_size}"
    stability_file = data_root / "global_stability_by_generation.csv"
    report_file = data_root / "global_report.txt"

    if not report_file.exists() or not stability_file.exists():
        row = {
            "strategy_name": strategy_name,
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
        rows.append(row)
        report_sections.extend(
            [
                f"Strategy: {strategy_name}",
                "  diagnosis: FAILED",
                "  reason: no successful optimizer runs",
                "",
            ]
        )
        continue

    stability = latest_stability_row(stability_file)
    row = {
        "strategy_name": strategy_name,
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

lines = ["=== EQUIVALENT RADIUS STRATEGY SWEEP EXCLUDING 40s ===", "", *report_sections]
comparison_report.write_text("\n".join(lines), encoding="utf-8")

print(f"Wrote {comparison_csv}")
print(f"Wrote {comparison_report}")
PY
