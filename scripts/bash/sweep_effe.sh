#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

EFFECTIVE_MEDIUM_MODEL="mg"
GEOMETRY="spheres"
COMPILE=0
BASE_JSON="data/input/sample.json"
THICKNESS_NM=""
OUTROOT="data/output/sweeps/transmittance_effe"
GP_OUT_DIR="scripts/gnuplot/output/sweep_effe"
IMG_OUT_DIR="img/output/sweep_effe"

EFFE_VALUES=(
  0.0
  0.2
  0.4
  0.6
  0.8
  1.0
)

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Sweep absolute filling_fraction values by editing a solver JSON template.

Options:
  --effective-medium-model VALUE
      Effective-medium model written into each sweep JSON
      Options: mg, bruggeman
      Default: $EFFECTIVE_MEDIUM_MODEL
  --base-json PATH
      Template solver JSON to edit
      Default: $BASE_JSON
  --geometry VALUE
      Geometry written into each sweep JSON
      Options: spheres, holes
      Default: $GEOMETRY
  --thickness-nm VALUE
      Fixed nanoisland slab thickness for the whole sweep
      Required
  --outroot PATH
      Root directory for sweep outputs
      Default: $OUTROOT
  -c, --compile
      Force recompilation of bin/transmittance before execution
  -h, --help
      Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --effective-medium-model)
      EFFECTIVE_MEDIUM_MODEL="$2"
      shift 2
      ;;
    --base-json)
      BASE_JSON="$2"
      shift 2
      ;;
    --geometry)
      GEOMETRY="$2"
      shift 2
      ;;
    --thickness-nm|--override-thickness-nm)
      THICKNESS_NM="$2"
      shift 2
      ;;
    --outroot)
      OUTROOT="$2"
      shift 2
      ;;
    -c|--compile)
      COMPILE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$EFFECTIVE_MEDIUM_MODEL" in
  mg|bruggeman)
    ;;
  *)
    echo "Invalid effective-medium model for effe sweep: $EFFECTIVE_MEDIUM_MODEL" >&2
    echo "Options are: mg, bruggeman" >&2
    exit 1
    ;;
esac

case "$GEOMETRY" in
  spheres|holes)
    ;;
  *)
    echo "Invalid geometry for effe sweep: $GEOMETRY" >&2
    echo "Options are: spheres, holes" >&2
    exit 1
    ;;
esac

if [[ -z "$THICKNESS_NM" ]]; then
  echo "--thickness-nm is required for sweep_effe.sh" >&2
  exit 1
fi

if [[ $COMPILE -eq 1 || ! -x bin/transmittance ]]; then
  echo "==> Compiling bin/transmittance"
  make bin/transmittance
fi

SWEEP_DIR="$OUTROOT/model=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}"
JSON_DIR="$SWEEP_DIR/json"
MANIFEST_PATH="$SWEEP_DIR/sweep_manifest.dat"
GP_PATH="$GP_OUT_DIR/plot_transmittance_vs_effe__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}.gp"
PNG_PATH="$IMG_OUT_DIR/transmittance_vs_effe__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}.png"
mkdir -p "$SWEEP_DIR" "$JSON_DIR" "$GP_OUT_DIR" "$IMG_OUT_DIR"
: > "$MANIFEST_PATH"
echo "# effe model_json spectrum_dat" >> "$MANIFEST_PATH"

for effe in "${EFFE_VALUES[@]}"; do
  echo "==> Sweeping filling_fraction=$effe with model=$EFFECTIVE_MEDIUM_MODEL"

  json_file="$JSON_DIR/model__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}__effe=${effe}.json"
  dst_file="$SWEEP_DIR/transmittance__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}__effe=${effe}.dat"

  python3 - "$BASE_JSON" "$json_file" "$EFFECTIVE_MEDIUM_MODEL" "$GEOMETRY" "$effe" "$THICKNESS_NM" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
model_name = sys.argv[3]
geometry = sys.argv[4]
filling_fraction = float(sys.argv[5])
thickness_nm = float(sys.argv[6])

model = json.loads(src.read_text(encoding="utf-8"))
for layer in model["stack"]["layers"]:
    if layer.get("kind") != "effective_medium":
        continue
    layer["thickness_nm"] = thickness_nm
    em = layer["effective_medium"]
    em["model"] = model_name
    em["geometry"] = geometry
    em["filling_fraction"] = filling_fraction
    if model_name in {"mg", "bruggeman"}:
        em.pop("distribution", None)
    break
else:
    raise SystemExit("Template JSON has no effective_medium layer")

dst.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
PY

  ./bin/transmittance "$json_file" --output "$dst_file"
  echo "$effe $json_file $dst_file" >> "$MANIFEST_PATH"
done

{
  echo "set terminal pngcairo noenhanced size 1400,900"
  echo "set output '$PNG_PATH'"
  echo "set title 'Transmittance sweep vs filling_fraction (${EFFECTIVE_MEDIUM_MODEL}, ${GEOMETRY}, d=${THICKNESS_NM} nm)'"
  echo "set datafile commentschars '#'"
  echo "set grid"
  echo "set xrange [300:798]"
  echo "set yrange [0:1]"
  echo "set xlabel 'Wavelength (nm)'"
  echo "set ylabel 'T_total'"
  echo "set key outside right"
  echo "plot \\"
  for idx in "${!EFFE_VALUES[@]}"; do
    effe="${EFFE_VALUES[$idx]}"
    data_file="$SWEEP_DIR/transmittance__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}__effe=${effe}.dat"
    suffix=", \\"
    if [[ $idx -eq $((${#EFFE_VALUES[@]} - 1)) ]]; then
      suffix=""
    fi
    echo "  '$data_file' using 1:3 with lines lw 2 title 'f=${effe}'${suffix}"
  done
} > "$GP_PATH"

gnuplot "$GP_PATH"

echo
echo "Effe sweep complete."
echo "  model:          $EFFECTIVE_MEDIUM_MODEL"
echo "  geometry:       $GEOMETRY"
echo "  base JSON:      $BASE_JSON"
echo "  thickness (nm): $THICKNESS_NM"
echo "  out root:       $SWEEP_DIR"
echo "  manifest:       $MANIFEST_PATH"
echo "  gnuplot script: $GP_PATH"
echo "  plot target:    $PNG_PATH"
