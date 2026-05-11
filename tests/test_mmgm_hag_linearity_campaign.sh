#!/bin/bash
set -euo pipefail

MODEL_FLAG="--mmgm-spheres-single"
AFM_PRIORS="data/input/optimal/afm_priors/mmgm_single_equivalent_radius_nm.json"
EXCLUDE_TIMES="40"

SEEDS=(111 222 333)
GENERATIONS=(300)
POPULATION_SIZE=48

BASE_DATA_ROOT="data/output/tests/mmgm_hag_linearity_campaign"
BASE_IMG_ROOT="img/tests/mmgm_hag_linearity_campaign"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_hag_linearity_campaign"
STATUS_FILE="${BASE_DATA_ROOT}/status.txt"

STRATEGIES=(
  "no_hag_linearity"
  "soft_hag_linearity"
  "hard_hag_linearity"
)

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"
echo "=== MMGM hAg linearity campaign started: $(timestamp) ===" >> "$STATUS_FILE"

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
    no_hag_linearity)
      STRATEGY_ARGS=(--hag-linearity-mode none)
      ;;
    soft_hag_linearity)
      STRATEGY_ARGS=(--hag-linearity-mode soft --hag-linearity-weight 1.0)
      ;;
    hard_hag_linearity)
      STRATEGY_ARGS=(--hag-linearity-mode hard --hag-linearity-tolerance 0.15)
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
      status_prefix="strategy:${strategy_index}/${strategy_total} strategy_name:${strategy_name} seed:${seed} generation:${generation} run:${run_index}/${run_total}"

      if [ -f "$DONE_FILE" ]; then
        echo "Skipping $OUT_DIR (already complete)"
        echo "${status_prefix} status:skipped timestamp:$(timestamp)" >> "$STATUS_FILE"
        continue
      fi

      echo "${status_prefix} status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
      echo "==> MMGM hAg linearity campaign: strategy=${strategy_name}, generation=${generation}, seed=${seed}"
      set +e
      python3 tools/optimal/optimize_global_model_parameters.py \
        "$MODEL_FLAG" \
        --exclude-times "$EXCLUDE_TIMES" \
        --afm-priors-json "$AFM_PRIORS" \
        --afm-priors-mode bounded \
        --afm-sigl-mode bounded \
        --afm-thickness-prior bounded \
        --afm-thickness-scale-low 0.25 \
        --afm-thickness-scale-high 4.0 \
        "${STRATEGY_ARGS[@]}" \
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
import json
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


def best_hag_linearity(data_root: Path, generation: int) -> tuple[str, str]:
    best: tuple[float, str, str] | None = None
    for result_file in sorted(data_root.glob(f"gen_{generation}/seed_*/mmgm_single/spheres/global_result.json")):
        raw = json.loads(result_file.read_text(encoding="utf-8"))
        objective = raw.get("objective", {})
        total_sse = objective.get("total_sse") if isinstance(objective, dict) else None
        if not isinstance(total_sse, (int, float)) or not math.isfinite(float(total_sse)):
            continue
        hag_fit = raw.get("hag_linear_fit", {})
        if not isinstance(hag_fit, dict):
            hag_fit = {}
        r2 = hag_fit.get("r2")
        max_dev = hag_fit.get("max_relative_deviation")
        r2_text = f"{float(r2):.12g}" if isinstance(r2, (int, float)) and math.isfinite(float(r2)) else "NA"
        max_dev_text = (
            f"{float(max_dev):.12g}"
            if isinstance(max_dev, (int, float)) and math.isfinite(float(max_dev))
            else "NA"
        )
        if best is None or float(total_sse) < best[0]:
            best = (float(total_sse), r2_text, max_dev_text)
    if best is None:
        return "NA", "NA"
    return best[1], best[2]


base_data_root = Path(sys.argv[1])
population_size = sys.argv[2]
strategy_names = sys.argv[3:]
comparison_csv = base_data_root / "hag_linearity_comparison.csv"
comparison_report = base_data_root / "hag_linearity_comparison_report.txt"

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
            "hag_linear_r2": "NA",
            "hag_max_rel_dev": "NA",
            "diagnosis": "FAILED",
            "report_file": "NA",
        }
        rows.append(row)
        report_sections.extend([f"Strategy: {strategy_name}", "  diagnosis: FAILED", ""])
        continue

    stability = latest_stability_row(stability_file)
    latest_generation = int(stability["generation"])
    hag_r2, hag_max_dev = best_hag_linearity(data_root, latest_generation)
    row = {
        "strategy_name": strategy_name,
        "latest_generation": str(latest_generation),
        "best_total_sse": f"{parse_float(stability['total_sse_min']):.12g}",
        "total_sse_rel_spread": f"{parse_float(stability['total_sse_rel_spread']):.12g}",
        "max_hag_rel_spread": f"{parse_float(stability['h_ag_rel_spread_max']):.12g}",
        "max_thickness_rel_spread": f"{parse_float(stability['thickness_rel_spread_max']):.12g}",
        "max_rave_rel_spread": f"{parse_float(stability['rave_rel_spread_max']):.12g}",
        "max_sigl_rel_spread": f"{parse_float(stability['sig_l_rel_spread_max']):.12g}",
        "hag_linear_r2": hag_r2,
        "hag_max_rel_dev": hag_max_dev,
        "diagnosis": final_diagnosis(report_file),
        "report_file": report_file.as_posix(),
    }
    rows.append(row)
    report_sections.extend(
        [
            f"Strategy: {strategy_name}",
            f"  latest generation: {row['latest_generation']}",
            f"  best total SSE: {row['best_total_sse']}",
            f"  total SSE relative spread: {row['total_sse_rel_spread']}",
            f"  max hAg relative spread: {row['max_hag_rel_spread']}",
            f"  max thickness relative spread: {row['max_thickness_rel_spread']}",
            f"  max Rave relative spread: {row['max_rave_rel_spread']}",
            f"  max sigL relative spread: {row['max_sigl_rel_spread']}",
            f"  hAg linear R2: {row['hag_linear_r2']}",
            f"  hAg max relative deviation: {row['hag_max_rel_dev']}",
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
    "hag_linear_r2",
    "hag_max_rel_dev",
    "diagnosis",
    "report_file",
]
with comparison_csv.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

lines = ["=== MMGM hAg LINEARITY CAMPAIGN (exclude 40s) ===", "", *report_sections]
comparison_report.write_text("\n".join(lines), encoding="utf-8")

print(f"Wrote {comparison_csv}")
print(f"Wrote {comparison_report}")
PY

python3 tools/optimal/extract_global_parameter_trajectories.py \
  --root "$BASE_DATA_ROOT" \
  --output-dir "${BASE_DATA_ROOT}/trajectory_diagnostics"

python3 scripts/gnuplot/tests/generate_parameter_trajectory_plots.py \
  --root "$BASE_DATA_ROOT" \
  --output-dir "${BASE_DATA_ROOT}/trajectory_diagnostics"
