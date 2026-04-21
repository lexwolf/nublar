#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RAVE_PROXY="volume_equivalent_radius_nm"
EFFE_PROXY="hybrid_alpha50"
THICKNESS_PROXY="equivalent_thickness_nm"
COMPILE=0
MODEL_INPUT="data/input/experimental/model_input.dat"
COMMON_DATASET="data/output/transmittance/common_transmittance_manifest.dat"
PLOT_SCRIPT="scripts/gnuplot/comparisons/transmittance/plot_experimental_vs_calculated.gp"
PLOT_PNG="img/comparisons/transmittance/experimental_vs_calculated.png"
ITO_THICKNESS_NM="0.0"
GLASS_THICKNESS_NM="1100000.0"
INCLUDE_INCOHERENT_MULTIPLES="1"
ETA="1.0"
XI="1.0"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Run the experimental-input -> common-transmittance dataset -> transmittance -> plot-script pipeline.

Options:
  --Rave-proxy, --rave-proxy, --radius-proxy NAME
      Radius proxy passed to tools/build_experimental_input.py
      Default: $RAVE_PROXY
  --effe-proxy NAME
      Effe proxy passed to tools/build_experimental_input.py
      Default: $EFFE_PROXY
  --thickness-proxy NAME
      Thickness proxy passed to tools/build_experimental_input.py
      Default: $THICKNESS_PROXY
  -c, --compile
      Force recompilation of bin/transmittance before execution
  --model-input PATH
      Solver manifest path passed to bin/transmittance
      Default: $MODEL_INPUT
  --common-dataset PATH
      Common-range manifest written by tools/build_common_transmittance_dataset.py
      Default: $COMMON_DATASET
  --plot-script PATH
      Output gnuplot script path
      Default: $PLOT_SCRIPT
  --plot-png PATH
      PNG target referenced by the generated gnuplot script
      Default: $PLOT_PNG
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
  --xi VALUE
      Scale effective filling fraction: effe -> xi * effe
      Default: $XI
  -h, --help
      Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --Rave-proxy|--rave-proxy|--radius-proxy)
      RAVE_PROXY="$2"
      shift 2
      ;;
    --effe-proxy)
      EFFE_PROXY="$2"
      shift 2
      ;;
    --thickness-proxy)
      THICKNESS_PROXY="$2"
      shift 2
      ;;
    -c|--compile)
      COMPILE=1
      shift
      ;;
    --model-input)
      MODEL_INPUT="$2"
      shift 2
      ;;
    --common-dataset)
      COMMON_DATASET="$2"
      shift 2
      ;;
    --plot-script)
      PLOT_SCRIPT="$2"
      shift 2
      ;;
    --plot-png)
      PLOT_PNG="$2"
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
    --xi)
      XI="$2"
      shift 2
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

echo "==> Building experimental input"
python3 tools/build_experimental_input.py \
  --radius-proxy "$RAVE_PROXY" \
  --effe-proxy "$EFFE_PROXY" \
  --thickness-proxy "$THICKNESS_PROXY" \
  --outdir "$(dirname "$MODEL_INPUT")" \
  --basename "$(basename "${MODEL_INPUT%.*}")"

echo "==> Building common-range transmittance dataset"
python3 tools/build_common_transmittance_dataset.py \
  --model-input "$MODEL_INPUT" \
  --outdir "$(dirname "$COMMON_DATASET")" \
  --basename "$(basename "${COMMON_DATASET%.*}")"

if [[ $COMPILE -eq 1 || ! -x bin/transmittance ]]; then
  echo "==> Compiling bin/transmittance"
  make bin/transmittance
fi

echo "==> Running transmittance solver"
./bin/transmittance \
  "$MODEL_INPUT" \
  "$ITO_THICKNESS_NM" \
  "$GLASS_THICKNESS_NM" \
  "$INCLUDE_INCOHERENT_MULTIPLES" \
  "$ETA" \
  "$XI"

echo "==> Building comparison gnuplot script"
python3 tools/build_transmittance_comparison_plot.py \
  --common-dataset "$COMMON_DATASET" \
  --gnuplot-out "$PLOT_SCRIPT" \
  --png-out "$PLOT_PNG"

echo
echo "Pipeline complete."
echo "  model input:     $MODEL_INPUT"
echo "  common dataset:  $COMMON_DATASET"
echo "  spectra dir:     data/output/transmittance"
echo "  thickness proxy: $THICKNESS_PROXY"
echo "  eta:             $ETA"
echo "  xi:              $XI"
echo "  gnuplot script:  $PLOT_SCRIPT"
echo "  plot target:     $PLOT_PNG"
