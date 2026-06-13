#!/bin/bash
set -euo pipefail

# WARNING: this test runs the MMGM optimizer across multiple seeds and generation
# counts, so it can take a long time.

DATA_ROOT="data/output/tests/mmgm_single_seed_stability"
IMG_ROOT="img/tests/mmgm_single_seed_stability"
GP_ROOT="scripts/gnuplot/tests/mmgm_single_seed_stability"

SEEDS=(12345 111 222 333 444)
GENERATIONS=(50 100 200)
MODEL_FLAG="--mmgm-spheres-single"

mkdir -p "$DATA_ROOT" "$IMG_ROOT" "$GP_ROOT"

for generation in "${GENERATIONS[@]}"; do
  for seed in "${SEEDS[@]}"; do
    OUT_DIR="${DATA_ROOT}/gen_${generation}/seed_${seed}"
    IMG_DIR="${IMG_ROOT}/gen_${generation}/seed_${seed}"
    GP_DIR="${GP_ROOT}/gen_${generation}/seed_${seed}"

    echo "==> MMGM single seed stability: generation=${generation}, seed=${seed}"
    python3 tools/optimal/optimize_model_parameters.py "$MODEL_FLAG" \
      --seed "$seed" \
      --max-generations "$generation" \
      --output-dir "$OUT_DIR" \
      --image-dir "$IMG_DIR" \
      --gnuplot-dir "$GP_DIR"
  done
done

python3 - "$DATA_ROOT" <<'PY'
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


data_root = Path(sys.argv[1])
summary_path = data_root / "summary.csv"
stability_path = data_root / "stability_by_generation.csv"

summary_columns = [
    "generation",
    "seed",
    "spectrum",
    "sse",
    "rmse",
    "effe",
    "thickness_nm",
    "rave_nm",
    "sig_l",
    "mean_radius_nm",
    "median_radius_nm",
    "mode_radius_nm",
    "r_p95_nm",
    "r_p99_nm",
    "thickness_over_2rp95",
    "thickness_over_2rp99",
    "json_file",
    "image_file",
]
stability_columns = [
    "generation",
    "spectrum",
    "n_runs",
    "sse_min",
    "sse_max",
    "sse_rel_spread",
    "effe_min",
    "effe_max",
    "thickness_nm_min",
    "thickness_nm_max",
    "rave_nm_min",
    "rave_nm_max",
    "sig_l_min",
    "sig_l_max",
]


def required_number(mapping: dict, key: str, source: Path) -> float:
    value = mapping.get(key)
    if value is None:
        raise SystemExit(f"Missing {key} in {source}")
    return float(value)


rows = []
json_files = sorted(data_root.glob("gen_*/seed_*/mmgm_single/spheres/*.json"))
if not json_files:
    raise SystemExit(f"No result JSON files found under {data_root}")

for json_file in json_files:
    try:
        generation = int(json_file.parts[-5].removeprefix("gen_"))
        seed = int(json_file.parts[-4].removeprefix("seed_"))
    except (IndexError, ValueError) as exc:
        raise SystemExit(f"Unexpected result path layout: {json_file}") from exc

    result = json.loads(json_file.read_text(encoding="utf-8"))
    params = result.get("best_parameters", {})
    objective = result.get("objective", {})
    descriptors = result.get("distribution_descriptors", {})
    rows.append(
        {
            "generation": generation,
            "seed": seed,
            "spectrum": json_file.stem,
            "sse": required_number(objective, "sse", json_file),
            "rmse": required_number(objective, "rmse", json_file),
            "effe": required_number(params, "effe", json_file),
            "thickness_nm": required_number(params, "thickness_nm", json_file),
            "rave_nm": required_number(params, "rave_nm", json_file),
            "sig_l": required_number(params, "sig_l", json_file),
            "mean_radius_nm": required_number(descriptors, "mean_radius_nm", json_file),
            "median_radius_nm": required_number(descriptors, "median_radius_nm", json_file),
            "mode_radius_nm": required_number(descriptors, "mode_radius_nm", json_file),
            "r_p95_nm": required_number(descriptors, "r_p95_nm", json_file),
            "r_p99_nm": required_number(descriptors, "r_p99_nm", json_file),
            "thickness_over_2rp95": required_number(
                descriptors, "thickness_over_2rp95", json_file
            ),
            "thickness_over_2rp99": required_number(
                descriptors, "thickness_over_2rp99", json_file
            ),
            "json_file": json_file.as_posix(),
            "image_file": result.get("image_file", ""),
        }
    )

rows.sort(key=lambda row: (row["generation"], row["seed"], row["spectrum"]))
with summary_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=summary_columns)
    writer.writeheader()
    writer.writerows(rows)

groups = defaultdict(list)
for row in rows:
    groups[(row["generation"], row["spectrum"])].append(row)

stability_rows = []
for (generation, spectrum), group_rows in sorted(groups.items()):
    sse_values = [row["sse"] for row in group_rows]
    sse_min = min(sse_values)
    sse_max = max(sse_values)
    stability_rows.append(
        {
            "generation": generation,
            "spectrum": spectrum,
            "n_runs": len(group_rows),
            "sse_min": sse_min,
            "sse_max": sse_max,
            "sse_rel_spread": ((sse_max - sse_min) / sse_min) if sse_min != 0 else "",
            "effe_min": min(row["effe"] for row in group_rows),
            "effe_max": max(row["effe"] for row in group_rows),
            "thickness_nm_min": min(row["thickness_nm"] for row in group_rows),
            "thickness_nm_max": max(row["thickness_nm"] for row in group_rows),
            "rave_nm_min": min(row["rave_nm"] for row in group_rows),
            "rave_nm_max": max(row["rave_nm"] for row in group_rows),
            "sig_l_min": min(row["sig_l"] for row in group_rows),
            "sig_l_max": max(row["sig_l"] for row in group_rows),
        }
    )

with stability_path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=stability_columns)
    writer.writeheader()
    writer.writerows(stability_rows)

print(f"Wrote {summary_path}")
print(f"Wrote {stability_path}")
PY
