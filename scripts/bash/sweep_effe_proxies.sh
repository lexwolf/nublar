#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RADIUS_PROXY="volume_equivalent_radius_nm"
GEOMETRY="spheres"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --radius-proxy)
      RADIUS_PROXY="$2"
      shift 2
      ;;
    --geometry)
      GEOMETRY="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

case "$GEOMETRY" in
  spheres)
    ;;
  holes)
    RADIUS_PROXY="equivalent_radius_nm"
    ;;
  *)
    echo "Invalid geometry: $GEOMETRY" >&2
    echo "Options are: spheres, holes" >&2
    exit 1
    ;;
esac

if [[ "$GEOMETRY" == "holes" ]]; then
  PROXIES=(
    coverage_fraction
    eq_thickness_over_mean_height
    coverage_times_eq_over_hmean
    sqrt_coverage_times_eq_over_hmean
    hybrid_alpha25
    hybrid_alpha50
    hybrid_alpha75
  )
else
  PROXIES=(
    coverage_fraction
    eq_thickness_over_mean_height
    coverage_times_eq_over_hmean
    sqrt_coverage_times_eq_over_hmean
    eq_thickness_over_Rave
    hybrid_alpha25
    hybrid_alpha50
    hybrid_alpha75
  )
fi

PLOT_CM="scripts/gnuplot/output/effective_permittivity/plot_effective_eps_cm.gp"
PLOT_MMGM="scripts/gnuplot/output/effective_permittivity/plot_effective_eps_mmgm.gp"
PNG_CM="img/output/effective_permittivity/effective_eps_cm.png"
PNG_MMGM="img/output/effective_permittivity/effective_eps_mmgm.png"
DATA_SRC_DIR="data/output/effective_permittivity"
MODEL_INPUT="data/input/experimental/model_input.dat"

IMG_SWEEP_DIR="img/output/proxy_sweeps/effe"
DATA_SWEEP_DIR="data/output/proxy_sweeps/effe"
MANIFEST_PATH="$DATA_SWEEP_DIR/sweep_manifest.dat"

if [[ "$GEOMETRY" != "spheres" ]]; then
  MODEL_INPUT="data/input/experimental/model_input__geom=${GEOMETRY}.dat"
fi

mkdir -p "$IMG_SWEEP_DIR" "$DATA_SWEEP_DIR"
: > "$MANIFEST_PATH"
echo "# geometry effe_proxy radius_proxy cm_png mmgm_png data_dir" >> "$MANIFEST_PATH"

generate_placeholder_effective_eps() {
  python3 - "$MODEL_INPUT" <<'PY'
from pathlib import Path
import math
import sys

manifest = Path(sys.argv[1])
outdir = Path("data/output/effective_permittivity")
outdir.mkdir(parents=True, exist_ok=True)
lines = manifest.read_text(encoding="utf-8").splitlines()
header = lines[0].split()[1:]
for line in lines[1:]:
    if not line.strip() or line.startswith("#"):
        continue
    parts = line.split()
    record = dict(zip(header, parts, strict=True))
    time_s = record["time_s"]
    n_lambda = int(record["n_lambda"])
    lamin = float(record["lamin_nm"])
    dlam = float(record["dlam_nm"])
    path = outdir / f"silver_nanoisland_{time_s}s.dat"
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"# time_s {time_s}\n")
        handle.write("# placeholder invalid_proxy_combination\n")
        handle.write("# columns: lambda_nm omega_eV eps_cm_re eps_cm_im eps_mmgm_re eps_mmgm_im eps_metal_re eps_metal_im\n")
        for i in range(n_lambda):
            lam = lamin + i * dlam
            handle.write(f"{lam:.10f} 0 0 0 0 0 0 0\n")
PY
}

for proxy in "${PROXIES[@]}"; do
  echo "==> Sweeping effe proxy: $proxy with radius proxy: $RADIUS_PROXY (geometry=$GEOMETRY)"

  python3 tools/build_experimental_input.py \
    --geometry "$GEOMETRY" \
    --effe-proxy "$proxy" \
    --radius-proxy "$RADIUS_PROXY"
  if ! ./bin/effective_eps "$MODEL_INPUT"; then
    echo "WARNING: effective_eps failed for effe=$proxy radius=$RADIUS_PROXY, writing placeholder spectra" >&2
    generate_placeholder_effective_eps
  fi
  gnuplot "$PLOT_CM"
  gnuplot "$PLOT_MMGM"

  cm_png="$IMG_SWEEP_DIR/effective_eps_cm__geom=${GEOMETRY}__effe=${proxy}__radius=${RADIUS_PROXY}.png"
  mmgm_png="$IMG_SWEEP_DIR/effective_eps_mmgm__geom=${GEOMETRY}__effe=${proxy}__radius=${RADIUS_PROXY}.png"
  data_dir="$DATA_SWEEP_DIR/effective_permittivity__geom=${GEOMETRY}__effe=${proxy}__radius=${RADIUS_PROXY}"

  cp "$PNG_CM" "$cm_png"
  cp "$PNG_MMGM" "$mmgm_png"
  rm -rf "$data_dir"
  mkdir -p "$data_dir"
  cp "$DATA_SRC_DIR"/silver_nanoisland_*.dat "$data_dir"/

  echo "$GEOMETRY $proxy $RADIUS_PROXY $cm_png $mmgm_png $data_dir" >> "$MANIFEST_PATH"
done

echo
echo "Saved effe sweep images under: $IMG_SWEEP_DIR"
echo "Saved effe sweep data under: $DATA_SWEEP_DIR"
