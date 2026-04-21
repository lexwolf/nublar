#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

EFFECTIVE_MEDIUM_MODEL="mg"
GEOMETRY="spheres"
COMPILE=0
MODEL_INPUT="data/input/experimental/model_input.dat"
ITO_THICKNESS_NM="0.0"
GLASS_THICKNESS_NM="1100000.0"
INCLUDE_INCOHERENT_MULTIPLES="1"
ETA="1.0"
OVERRIDE_THICKNESS_NM=""
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

Sweep absolute effe values for transmittance runs.

This sweep is only valid for effective-medium models where effe is the only
non-permittivity control variable:
  - mg
  - bruggeman

Options:
  --effective-medium-model VALUE
      Required model selection for the sweep
      Options: mg, bruggeman
      Default: $EFFECTIVE_MEDIUM_MODEL
  --model-input PATH
      Solver manifest path passed to bin/transmittance
      Default: $MODEL_INPUT
  --geometry VALUE
      Morphology convention passed to bin/transmittance
      Options: spheres, holes
      Default: $GEOMETRY
  --ito-thickness-nm VALUE
      Optional transmittance binary override
      Default: $ITO_THICKNESS_NM
  --glass-thickness-nm VALUE
      Optional transmittance binary override
      Default: $GLASS_THICKNESS_NM
  --include-incoherent-multiples 0|1
      Optional transmittance binary override
      Default: $INCLUDE_INCOHERENT_MULTIPLES
  --eta VALUE
      Scale nanoisland thickness: d -> eta * d
      Default: $ETA
  --override-thickness-nm VALUE
      Fixed nanoisland thickness used for the whole sweep
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
    --model-input)
      MODEL_INPUT="$2"
      shift 2
      ;;
    --geometry)
      GEOMETRY="$2"
      shift 2
      ;;
    --ito-thickness-nm)
      ITO_THICKNESS_NM="$2"
      shift 2
      ;;
    --glass-thickness-nm)
      GLASS_THICKNESS_NM="$2"
      shift 2
      ;;
    --include-incoherent-multiples)
      INCLUDE_INCOHERENT_MULTIPLES="$2"
      shift 2
      ;;
    --eta)
      ETA="$2"
      shift 2
      ;;
    --override-thickness-nm)
      OVERRIDE_THICKNESS_NM="$2"
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

if [[ -z "$OVERRIDE_THICKNESS_NM" ]]; then
  echo "--override-thickness-nm is required for sweep_effe.sh" >&2
  exit 1
fi

if [[ $COMPILE -eq 1 || ! -x bin/transmittance ]]; then
  echo "==> Compiling bin/transmittance"
  make bin/transmittance
fi

SWEEP_DIR="$OUTROOT/model=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}"
MANIFEST_PATH="$SWEEP_DIR/sweep_manifest.dat"
GP_PATH="$GP_OUT_DIR/plot_transmittance_vs_effe__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}.gp"
PNG_PATH="$IMG_OUT_DIR/transmittance_vs_effe__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}.png"
TEMP_MANIFEST="$SWEEP_DIR/model_input_single_row.dat"
mkdir -p "$SWEEP_DIR"
mkdir -p "$GP_OUT_DIR" "$IMG_OUT_DIR"
: > "$MANIFEST_PATH"
echo "# effe spectrum_dat" >> "$MANIFEST_PATH"

python3 - "$MODEL_INPUT" "$TEMP_MANIFEST" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
lines = src.read_text(encoding="utf-8").splitlines()
header = None
row = None
for line in lines:
    stripped = line.strip()
    if not stripped:
        continue
    if stripped.startswith("#") and header is None:
        header = line
        continue
    if not stripped.startswith("#"):
        row = line
        break

if header is None or row is None:
    raise SystemExit("Could not extract first data row from model input manifest")

dst.write_text(f"{header}\n{row}\n", encoding="utf-8")
PY

for effe in "${EFFE_VALUES[@]}"; do
  echo "==> Sweeping effe=$effe with model=$EFFECTIVE_MEDIUM_MODEL"

  ./bin/transmittance \
    --effective-medium-model "$EFFECTIVE_MEDIUM_MODEL" \
    --geometry "$GEOMETRY" \
    --override-effe "$effe" \
    --override-thickness-nm "$OVERRIDE_THICKNESS_NM" \
    "$TEMP_MANIFEST" \
    "$ITO_THICKNESS_NM" \
    "$GLASS_THICKNESS_NM" \
    "$INCLUDE_INCOHERENT_MULTIPLES" \
    "$ETA"

  case "$EFFECTIVE_MEDIUM_MODEL" in
    mg)
      src_file="$(find data/output/transmittance -maxdepth 1 -type f -name "silver_nanoisland_*s__em=mg__geom=${GEOMETRY}.dat" | sort | head -n 1)"
      ;;
    bruggeman)
      src_file="$(find data/output/transmittance -maxdepth 1 -type f -name "silver_nanoisland_*s__em=bruggeman__geom=${GEOMETRY}.dat" | sort | head -n 1)"
      ;;
  esac

  if [[ -z "${src_file:-}" ]]; then
    echo "Could not locate transmittance output for effe=$effe" >&2
    exit 1
  fi

  dst_file="$SWEEP_DIR/transmittance__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}__effe=${effe}.dat"
  cp "$src_file" "$dst_file"

  echo "$effe $dst_file" >> "$MANIFEST_PATH"
done

{
  echo "set terminal pngcairo noenhanced size 1400,900"
  echo "set output '$PNG_PATH'"
  echo "set title 'Transmittance sweep vs effe (${EFFECTIVE_MEDIUM_MODEL}, ${GEOMETRY}, d=${OVERRIDE_THICKNESS_NM} nm)'"
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
    echo "  '$data_file' using 1:3 with lines lw 2 title 'effe=${effe}'${suffix}"
  done
} > "$GP_PATH"

gnuplot "$GP_PATH"

echo
echo "Effe sweep complete."
echo "  model:          $EFFECTIVE_MEDIUM_MODEL"
echo "  geometry:       $GEOMETRY"
echo "  model input:    $MODEL_INPUT"
echo "  single manifest:$TEMP_MANIFEST"
echo "  thickness (nm): $OVERRIDE_THICKNESS_NM"
echo "  out root:       $SWEEP_DIR"
echo "  manifest:       $MANIFEST_PATH"
echo "  gnuplot script: $GP_PATH"
echo "  plot target:    $PNG_PATH"
