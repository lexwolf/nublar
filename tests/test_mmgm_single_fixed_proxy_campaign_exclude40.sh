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
BASE_DATA_ROOT="data/output/tests/mmgm_single_fixed_proxy_campaign_exclude40"
BASE_IMG_ROOT="img/tests/mmgm_single_fixed_proxy_campaign_exclude40"
BASE_GP_ROOT="scripts/gnuplot/tests/mmgm_single_fixed_proxy_campaign_exclude40"

mkdir -p "$BASE_DATA_ROOT" "$BASE_IMG_ROOT" "$BASE_GP_ROOT"

shopt -s nullglob
AFM_PRIOR_FILES=("$AFM_PRIOR_DIR"/mmgm_single_*.json)
shopt -u nullglob

if [ "${#AFM_PRIOR_FILES[@]}" -eq 0 ]; then
  echo "No AFM prior files found matching $AFM_PRIOR_DIR/mmgm_single_*.json" >&2
  exit 1
fi

for AFM_PRIORS in "${AFM_PRIOR_FILES[@]}"; do
  prior_name="$(basename "$AFM_PRIORS" .json)"
  DATA_ROOT="${BASE_DATA_ROOT}/${prior_name}_exclude40_pop_${POPULATION_SIZE}"
  IMG_ROOT="${BASE_IMG_ROOT}/${prior_name}_exclude40_pop_${POPULATION_SIZE}"
  GP_ROOT="${BASE_GP_ROOT}/${prior_name}_exclude40_pop_${POPULATION_SIZE}"

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

      echo "==> Fixed-AFM exclude-40 proxy campaign: prior=${prior_name}, generation=${generation}, seed=${seed}"
      python3 tools/optimal/optimize_global_model_parameters.py "$MODEL_FLAG" \
        --afm-priors-json "$AFM_PRIORS" \
        --afm-priors-mode fixed \
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
done

python3 - "$BASE_DATA_ROOT" "$POPULATION_SIZE" <<'PY'
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


def result_metadata(data_root: Path) -> tuple[str, str, str]:
    result_files = sorted(data_root.glob("gen_*/seed_*/mmgm_single/spheres/global_result.json"))
    if not result_files:
        raise SystemExit(f"Missing optimizer results under {data_root}")
    raw = json.loads(result_files[0].read_text(encoding="utf-8"))
    excluded_times = raw.get("excluded_times_s")
    if excluded_times != [40]:
        raise SystemExit(f"Expected excluded_times_s=[40] in {result_files[0]}, found {excluded_times!r}")
    afm_priors = raw.get("afm_priors")
    if not isinstance(afm_priors, dict):
        raise SystemExit(f"Missing afm_priors metadata in {result_files[0]}")
    source = afm_priors.get("source")
    strategy = afm_priors.get("strategy")
    if not isinstance(source, dict) or not isinstance(strategy, dict):
        raise SystemExit(f"Missing AFM source/strategy metadata in {result_files[0]}")
    radius_proxy_name = source.get("radius_proxy_name")
    strategy_name = strategy.get("name")
    mode = afm_priors.get("mode")
    if not all(isinstance(value, str) and value for value in (radius_proxy_name, strategy_name, mode)):
        raise SystemExit(f"Invalid AFM metadata in {result_files[0]}")
    return radius_proxy_name, strategy_name, mode


base_data_root = Path(sys.argv[1])
population_size = sys.argv[2]
comparison_csv = base_data_root / "proxy_comparison.csv"
comparison_report = base_data_root / "proxy_comparison_report.txt"

candidate_roots: dict[str, Path] = {}
for data_root in sorted(path for path in base_data_root.iterdir() if path.is_dir()):
    stability_file = data_root / "global_stability_by_generation.csv"
    report_file = data_root / "global_report.txt"
    if not stability_file.exists() or not report_file.exists():
        continue
    radius_proxy_name, strategy_name, mode = result_metadata(data_root)
    proxy_aware_name = (
        f"{radius_proxy_name}__{strategy_name}__{mode}_exclude40_pop_{population_size}"
    )
    current = candidate_roots.get(proxy_aware_name)
    if current is None or data_root.name == proxy_aware_name:
        candidate_roots[proxy_aware_name] = data_root

rows: list[dict[str, str]] = []
for prior_name, data_root in sorted(candidate_roots.items()):
    if not data_root.is_dir():
        continue
    stability_file = data_root / "global_stability_by_generation.csv"
    report_file = data_root / "global_report.txt"
    if not stability_file.exists():
        raise SystemExit(f"Missing stability CSV: {stability_file}")
    if not report_file.exists():
        raise SystemExit(f"Missing stability report: {report_file}")

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

if not rows:
    raise SystemExit(f"No proxy result directories found under {base_data_root}")

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

lines = ["=== FIXED-AFM PRIOR PROXY COMPARISON EXCLUDING 40s ===", ""]
for row in rows:
    lines.extend(
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
comparison_report.write_text("\n".join(lines), encoding="utf-8")

print(f"Wrote {comparison_csv}")
print(f"Wrote {comparison_report}")
PY
