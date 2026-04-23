#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RAVE_PROXY="volume_equivalent_radius_nm"
EFFE_PROXY="hybrid_alpha50"
THICKNESS_PROXY="equivalent_thickness_nm"
COMPILE=0
MODEL_MANIFEST="data/input/experimental/transmittance_models.dat"
MODEL_JSON_DIR="data/input/experimental/transmittance_models"
CALCULATED_DIR="data/output/transmittance"
COMMON_DATASET="data/output/transmittance/common_transmittance_manifest.dat"
PLOT_SCRIPT="scripts/gnuplot/comparisons/transmittance/plot_experimental_vs_calculated.gp"
PLOT_PNG="img/comparisons/transmittance/experimental_vs_calculated.png"
ITO_THICKNESS_NM="10.0"
GLASS_THICKNESS_NM="1100000.0"
EFFECTIVE_MEDIUM_MODEL="mmgm"
GEOMETRY="spheres"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Run the AFM-derived JSON model -> transmittance -> common dataset -> plot-script pipeline.

Options:
  --Rave-proxy, --rave-proxy, --radius-proxy NAME
      Radius proxy passed to tools/build_transmittance_models.py
      Default: $RAVE_PROXY
  --effe-proxy NAME
      Effe proxy passed to tools/build_transmittance_models.py
      Default: $EFFE_PROXY
  --thickness-proxy NAME
      Thickness proxy passed to tools/build_transmittance_models.py
      Default: $THICKNESS_PROXY
  -c, --compile
      Force recompilation of bin/transmittance before execution
  --model-manifest PATH
      JSON-model sidecar manifest written by tools/build_transmittance_models.py
      Default: $MODEL_MANIFEST
  --model-json-dir PATH
      Directory for generated solver JSON files
      Default: $MODEL_JSON_DIR
  --common-dataset PATH
      Common-range manifest written by tools/build_common_transmittance_dataset.py
      Default: $COMMON_DATASET
  --calculated-dir PATH
      Directory for calculated spectra
      Default: $CALCULATED_DIR
  --plot-script PATH
      Output gnuplot script path
      Default: $PLOT_SCRIPT
  --plot-png PATH
      PNG target referenced by the generated gnuplot script
      Default: $PLOT_PNG
  --ito-thickness-nm VALUE
      ITO layer thickness written into generated JSON
      Default: $ITO_THICKNESS_NM
  --glass-thickness-nm VALUE
      Glass substrate thickness written into generated JSON
      Default: $GLASS_THICKNESS_NM
  --effective-medium-model VALUE
      Effective-medium model written into generated JSON
      Options: mg, bruggeman, mmgm
      Default: $EFFECTIVE_MEDIUM_MODEL
  --geometry VALUE
      Morphology convention written into generated JSON and recorded in manifests
      Options: spheres, holes
      Default: $GEOMETRY
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
    --model-manifest)
      MODEL_MANIFEST="$2"
      shift 2
      ;;
    --model-json-dir)
      MODEL_JSON_DIR="$2"
      shift 2
      ;;
    --common-dataset)
      COMMON_DATASET="$2"
      shift 2
      ;;
    --calculated-dir)
      CALCULATED_DIR="$2"
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
    --effective-medium-model)
      EFFECTIVE_MEDIUM_MODEL="$2"
      shift 2
      ;;
    --geometry)
      GEOMETRY="$2"
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

case "$EFFECTIVE_MEDIUM_MODEL" in
  mg|bruggeman|mmgm)
    ;;
  *)
    echo "Invalid effective-medium model: $EFFECTIVE_MEDIUM_MODEL" >&2
    echo "Options are: mg, bruggeman, mmgm" >&2
    exit 1
    ;;
esac

case "$GEOMETRY" in
  spheres|holes)
    ;;
  *)
    echo "Invalid geometry: $GEOMETRY" >&2
    echo "Options are: spheres, holes" >&2
    exit 1
    ;;
esac

if [[ "$EFFECTIVE_MEDIUM_MODEL" != "mmgm" || "$GEOMETRY" != "spheres" ]]; then
  if [[ "$COMMON_DATASET" == "data/output/transmittance/common_transmittance_manifest.dat" ]]; then
    COMMON_DATASET="data/output/transmittance/common_transmittance_manifest__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}.dat"
  fi
  if [[ "$PLOT_SCRIPT" == "scripts/gnuplot/comparisons/transmittance/plot_experimental_vs_calculated.gp" ]]; then
    PLOT_SCRIPT="scripts/gnuplot/comparisons/transmittance/plot_experimental_vs_calculated__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}.gp"
  fi
  if [[ "$PLOT_PNG" == "img/comparisons/transmittance/experimental_vs_calculated.png" ]]; then
    PLOT_PNG="img/comparisons/transmittance/experimental_vs_calculated__em=${EFFECTIVE_MEDIUM_MODEL}__geom=${GEOMETRY}.png"
  fi
fi

echo "==> Building transmittance JSON models"
python3 tools/build_transmittance_models.py \
  --radius-proxy "$RAVE_PROXY" \
  --effe-proxy "$EFFE_PROXY" \
  --thickness-proxy "$THICKNESS_PROXY" \
  --geometry "$GEOMETRY" \
  --effective-medium-model "$EFFECTIVE_MEDIUM_MODEL" \
  --ito-thickness-nm "$ITO_THICKNESS_NM" \
  --glass-thickness-nm "$GLASS_THICKNESS_NM" \
  --outdir "$MODEL_JSON_DIR" \
  --manifest "$MODEL_MANIFEST" \
  --calculated-dir "$CALCULATED_DIR"

if [[ $COMPILE -eq 1 || ! -x bin/transmittance ]]; then
  echo "==> Compiling bin/transmittance"
  make bin/transmittance
fi

echo "==> Running transmittance solver"
while read -r time_s sample_label model_json experimental_dat calculated_dat rest; do
  [[ -z "${time_s:-}" || "$time_s" == \#* ]] && continue
  ./bin/transmittance "$model_json" --output "$calculated_dat"
done < "$MODEL_MANIFEST"

echo "==> Building common-range transmittance dataset"
python3 tools/build_common_transmittance_dataset.py \
  --model-manifest "$MODEL_MANIFEST" \
  --effective-medium-model "$EFFECTIVE_MEDIUM_MODEL" \
  --geometry "$GEOMETRY" \
  --outdir "$(dirname "$COMMON_DATASET")" \
  --basename "$(basename "${COMMON_DATASET%.*}")"

echo "==> Building comparison gnuplot script"
python3 tools/build_transmittance_comparison_plot.py \
  --common-dataset "$COMMON_DATASET" \
  --gnuplot-out "$PLOT_SCRIPT" \
  --png-out "$PLOT_PNG"

echo
echo "Pipeline complete."
echo "  model manifest:  $MODEL_MANIFEST"
echo "  JSON models:     $MODEL_JSON_DIR"
echo "  common dataset:  $COMMON_DATASET"
echo "  spectra dir:     $CALCULATED_DIR"
echo "  thickness proxy: $THICKNESS_PROXY"
echo "  em model:        $EFFECTIVE_MEDIUM_MODEL"
echo "  geometry:        $GEOMETRY"
echo "  gnuplot script:  $PLOT_SCRIPT"
echo "  plot target:     $PLOT_PNG"
