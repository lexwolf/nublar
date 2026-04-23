#!/usr/bin/env bash

set -euo pipefail

RAW_DIR="data/experimental/raw/afm"
OUT_BASE="data/experimental/intermediate/afm_batch"

USE_IMAGE=false
SIGMA_FACTOR="2.5"
MIN_PIXELS="20"

usage() {
    cat <<EOF
Usage:
  ./tools/experimental/run_afm_batch.sh [--use-image] [--sigma-factor VAL] [--min-pixels N]

Options:
  --use-image         Use the processed '*Image 1*.stp' files instead of 001/002/003
  --sigma-factor VAL  Forwarded to extract_afm_features.py (default: 2.5)
  --min-pixels N      Forwarded to extract_afm_features.py (default: 20)
  -h, --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --use-image)
            USE_IMAGE=true
            shift
            ;;
        --sigma-factor)
            SIGMA_FACTOR="$2"
            shift 2
            ;;
        --min-pixels)
            MIN_PIXELS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if $USE_IMAGE; then
    MODE_TAG="image"
    CSV_OUT="$OUT_BASE/summary_image.csv"
else
    MODE_TAG="raw"
    CSV_OUT="$OUT_BASE/summary_raw.csv"
fi

mkdir -p "$OUT_BASE"
echo "time,file,coverage,thickness_nm,mean_radius_nm,density_um2,island_count,hole_count,mean_hole_radius_nm,hole_density_um2" > "$CSV_OUT"

for t in 10 20 30 40 50 60; do
    OUTDIR="$OUT_BASE/${t}s_2um_${MODE_TAG}"
    mkdir -p "$OUTDIR"

    if $USE_IMAGE; then
        FILE_CANDIDATES=(
            "$RAW_DIR/Nis_Ag_${t}s_2um Image 1.stp"
            "$RAW_DIR/Nis_Ag_${t}s_2um Image 1.txtNis_Ag_${t}s_2um Image 1.stp"
        )

        FILES=()
        for candidate in "${FILE_CANDIDATES[@]}"; do
            if [[ -f "$candidate" ]]; then
                FILES+=("$candidate")
            fi
        done

        if [[ ${#FILES[@]} -eq 0 ]]; then
            echo "Skipping ${t}s: no Image 1 file found"
            continue
        fi
    else
        FILES=(
            "$RAW_DIR/Nis_Ag_${t}s_2um_001.stp"
            "$RAW_DIR/Nis_Ag_${t}s_2um_002.stp"
            "$RAW_DIR/Nis_Ag_${t}s_2um_003.stp"
        )

        for f in "${FILES[@]}"; do
            if [[ ! -f "$f" ]]; then
                echo "Missing required file: $f" >&2
                exit 1
            fi
        done
    fi

    echo "Processing ${t}s (${MODE_TAG})..."

    python3 tools/experimental/extract_afm_features.py \
        "${FILES[@]}" \
        --sigma-factor "$SIGMA_FACTOR" \
        --min-pixels "$MIN_PIXELS" \
        --outdir "$OUTDIR" \
        --save-overlay

    for f in "$OUTDIR"/*_features.json; do
        python3 - <<EOF >> "$CSV_OUT"
import json
import pathlib

data = json.load(open("$f"))
s = data["summary"]
name = pathlib.Path("$f").name
time = name.split("_")[2]

print(
    f"{time},{name},{s['coverage_fraction']},{s['equivalent_thickness_nm']},"
    f"{s['mean_equivalent_radius_nm']},{s['number_density_per_um2']},"
    f"{s['island_count']},{s.get('hole_count', 0)},"
    f"{s.get('mean_hole_equivalent_radius_nm', 0.0)},"
    f"{s.get('hole_number_density_per_um2', 0.0)}"
)
EOF
    done
done

echo "Done. CSV written to $CSV_OUT"
