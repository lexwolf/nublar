#!/bin/bash
set -euo pipefail

# WARNING: this campaign runs the global MMGM optimizer for every AFM prior
# proxy across multiple seeds and generation counts. It may take hours.

MODEL_FLAG="--mmgm-spheres-single"
SEEDS=(111 222 333)
GENERATIONS=(80 150)
POPULATION_SIZE=36
EXCLUDE_TIMES="40"

AFM_PRIOR_DIR="data/input/optimal/afm_priors"

BASE_DATA_ROOT="data/output/tests/mmgm_single_bounded_proxy_campaign_exclude40"
BASE_IMG_ROOT="img/tests/mmgm_single_bounded_proxy_campaign_exclude40"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_bounded_proxy_campaign_exclude40"

STATUS_FILE="${BASE_DATA_ROOT}/status.txt"
CURRENT_STATUS_PREFIX=""

timestamp() {
  date --iso-8601=seconds
}

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"
echo "=== bounded proxy exclude40 campaign started: $(timestamp) ===" >> "$STATUS_FILE"

shopt -s nullglob
AFM_PRIOR_FILES=("$AFM_PRIOR_DIR"/mmgm_single_*.json)
shopt -u nullglob

if [ "${#AFM_PRIOR_FILES[@]}" -eq 0 ]; then
  echo "No AFM prior files found matching $AFM_PRIOR_DIR/mmgm_single_*.json" >&2
  exit 1
fi

proxy_total="${#AFM_PRIOR_FILES[@]}"
run_total=$(( proxy_total * ${#SEEDS[@]} * ${#GENERATIONS[@]} ))
run_index=0
proxy_index=0

for AFM_PRIORS in "${AFM_PRIOR_FILES[@]}"; do
  proxy_index=$(( proxy_index + 1 ))
  prior_name="$(basename "$AFM_PRIORS" .json)"
  DATA_ROOT="${BASE_DATA_ROOT}/${prior_name}_bounded_exclude40_pop_${POPULATION_SIZE}"
  IMG_ROOT="${BASE_IMG_ROOT}/${prior_name}_bounded_exclude40_pop_${POPULATION_SIZE}"
  GP_ROOT="${BASE_GP_ROOT}/${prior_name}_bounded_exclude40_pop_${POPULATION_SIZE}"

  mkdir -p "$DATA_ROOT" "$IMG_ROOT" "$GP_ROOT"

  for generation in "${GENERATIONS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      run_index=$(( run_index + 1 ))
      OUT_DIR="${DATA_ROOT}/gen_${generation}/seed_${seed}"
      IMG_DIR="${IMG_ROOT}/gen_${generation}/seed_${seed}"
      GP_DIR="${GP_ROOT}/gen_${generation}/seed_${seed}"
      DONE_FILE="${OUT_DIR}/mmgm_single/spheres/global_result.json"
      if [ -f "$DONE_FILE" ]; then
        echo "Skipping $OUT_DIR (already complete)"
        echo "proxy:${proxy_index}/${proxy_total} proxy_name:${prior_name} seed:${seed} generation:${generation} run:${run_index}/${run_total} excluded_times:${EXCLUDE_TIMES} status:skipped timestamp:$(timestamp)" >> "$STATUS_FILE"
        continue
      fi

      CURRENT_STATUS_PREFIX="proxy:${proxy_index}/${proxy_total} proxy_name:${prior_name} seed:${seed} generation:${generation} run:${run_index}/${run_total} excluded_times:${EXCLUDE_TIMES}"
      echo "${CURRENT_STATUS_PREFIX} status:started timestamp:$(timestamp)" >> "$STATUS_FILE"
      echo "==> Bounded-AFM exclude-40 proxy campaign: prior=${prior_name}, generation=${generation}, seed=${seed}"
      set +e
      python3 tools/optimal/optimize_global_model_parameters.py \
        "$MODEL_FLAG" \
        --afm-priors-json "$AFM_PRIORS" \
        --afm-priors-mode bounded \
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
        echo "${CURRENT_STATUS_PREFIX} status:failed exit_code:${exit_code} timestamp:$(timestamp)" >> "$STATUS_FILE"
        CURRENT_STATUS_PREFIX=""
        continue
      fi
      echo "${CURRENT_STATUS_PREFIX} status:done timestamp:$(timestamp)" >> "$STATUS_FILE"
      CURRENT_STATUS_PREFIX=""
    done
  done

  n_results=$(find "$DATA_ROOT" -name global_result.json | wc -l)
  if [ "$n_results" -eq 0 ]; then
    echo "proxy:${proxy_index}/${proxy_total} proxy_name:${prior_name} status:analyzer_skipped reason:no_successful_runs timestamp:$(timestamp)" >> "$STATUS_FILE"
    continue
  fi

  CURRENT_STATUS_PREFIX="proxy:${proxy_index}/${proxy_total} proxy_name:${prior_name}"
  echo "${CURRENT_STATUS_PREFIX} status:analyzer_started timestamp:$(timestamp)" >> "$STATUS_FILE"
  python3 tests/analyze_mmgm_single_global_stability.py --root "$DATA_ROOT"
  echo "${CURRENT_STATUS_PREFIX} status:analyzer_done timestamp:$(timestamp)" >> "$STATUS_FILE"
  CURRENT_STATUS_PREFIX=""
done

python3 - "$BASE_DATA_ROOT" "$POPULATION_SIZE" "$AFM_PRIOR_DIR" <<'PY'
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
afm_prior_dir = Path(sys.argv[3])
comparison_csv = base_data_root / "proxy_comparison.csv"
comparison_report = base_data_root / "proxy_comparison_report.txt"

prior_files = sorted(afm_prior_dir.glob("mmgm_single_*.json"))
if not prior_files:
    raise SystemExit(f"No AFM prior files found matching {afm_prior_dir / 'mmgm_single_*.json'}")

rows: list[dict[str, str]] = []
report_sections: list[str] = []
for prior_file in prior_files:
    prior_name = prior_file.stem
    data_root = base_data_root / f"{prior_name}_bounded_exclude40_pop_{population_size}"
    stability_file = data_root / "global_stability_by_generation.csv"
    report_file = data_root / "global_report.txt"
    if not report_file.exists() or not stability_file.exists():
        row = {
            "prior_name": prior_name,
            "latest_generation": "NA",
            "best_total_sse": "NA",
            "total_sse_rel_spread": "NA",
            "max_hag_rel_spread": "NA",
            "max_thickness_rel_spread": "NA",
            "diagnosis": "FAILED",
            "report_file": "NA",
        }
        rows.append(row)
        report_sections.extend(
            [
                f"Prior: {prior_name}",
                "  diagnosis: FAILED",
                "  reason: no successful optimizer runs",
                "",
            ]
        )
        continue

    stability = latest_stability_row(stability_file)
    row = {
        "prior_name": prior_name,
        "latest_generation": str(int(stability["generation"])),
        "best_total_sse": f"{parse_float(stability['total_sse_min']):.12g}",
        "total_sse_rel_spread": f"{parse_float(stability['total_sse_rel_spread']):.12g}",
        "max_hag_rel_spread": f"{parse_float(stability['h_ag_rel_spread_max']):.12g}",
        "max_thickness_rel_spread": f"{parse_float(stability['thickness_rel_spread_max']):.12g}",
        "diagnosis": final_diagnosis(report_file),
        "report_file": report_file.as_posix(),
    }
    rows.append(row)
    report_sections.extend(
        [
            f"Prior: {row['prior_name']}",
            f"  latest generation: {row['latest_generation']}",
            f"  best total SSE: {row['best_total_sse']}",
            f"  total SSE relative spread: {row['total_sse_rel_spread']}",
            f"  max hAg relative spread: {row['max_hag_rel_spread']}",
            f"  max thickness relative spread: {row['max_thickness_rel_spread']}",
            f"  diagnosis: {row['diagnosis']}",
            f"  report: {row['report_file']}",
            "",
        ]
    )

columns = [
    "prior_name",
    "latest_generation",
    "best_total_sse",
    "total_sse_rel_spread",
    "max_hag_rel_spread",
    "max_thickness_rel_spread",
    "diagnosis",
    "report_file",
]
with comparison_csv.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

lines = ["=== BOUNDED-AFM PRIOR PROXY COMPARISON EXCLUDING 40s ===", "", *report_sections]
comparison_report.write_text("\n".join(lines), encoding="utf-8")

print(f"Wrote {comparison_csv}")
print(f"Wrote {comparison_report}")
PY
