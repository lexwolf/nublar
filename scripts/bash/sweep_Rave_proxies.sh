#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

EFFE_PROXY="eq_thickness_over_mean_height"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --effe-proxy)
      EFFE_PROXY="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

RADIUS_PROXIES=(
  equivalent_radius_nm
  volume_equivalent_radius_nm
  height_equivalent_radius_mean_nm
  height_equivalent_radius_p95_nm
)

PLOT_CM="scripts/gnuplot/output/effective_permittivity/plot_effective_eps_cm.gp"
PLOT_MMGM="scripts/gnuplot/output/effective_permittivity/plot_effective_eps_mmgm.gp"
PNG_CM="img/output/effective_permittivity/effective_eps_cm.png"
PNG_MMGM="img/output/effective_permittivity/effective_eps_mmgm.png"
DATA_SRC_DIR="data/output/effective_permittivity"

IMG_SWEEP_DIR="img/output/proxy_sweeps/rave"
DATA_SWEEP_DIR="data/output/proxy_sweeps/rave"
MANIFEST_PATH="$DATA_SWEEP_DIR/sweep_manifest.dat"

mkdir -p "$IMG_SWEEP_DIR" "$DATA_SWEEP_DIR"
: > "$MANIFEST_PATH"
echo "# effe_proxy radius_proxy cm_png mmgm_png data_dir" >> "$MANIFEST_PATH"

generate_placeholder_effective_eps() {
  python3 - <<'PY'
from pathlib import Path

manifest = Path("data/input/experimental/model_input.dat")
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

for proxy in "${RADIUS_PROXIES[@]}"; do
  echo "==> Sweeping radius proxy: $proxy with effe proxy: $EFFE_PROXY"

  python3 tools/build_experimental_input.py --effe-proxy "$EFFE_PROXY" --radius-proxy "$proxy"
  if ! ./bin/effective_eps; then
    echo "WARNING: effective_eps failed for effe=$EFFE_PROXY radius=$proxy, writing placeholder spectra" >&2
    generate_placeholder_effective_eps
  fi
  gnuplot "$PLOT_CM"
  gnuplot "$PLOT_MMGM"

  cm_png="$IMG_SWEEP_DIR/effective_eps_cm__radius=${proxy}__effe=${EFFE_PROXY}.png"
  mmgm_png="$IMG_SWEEP_DIR/effective_eps_mmgm__radius=${proxy}__effe=${EFFE_PROXY}.png"
  data_dir="$DATA_SWEEP_DIR/effective_permittivity__radius=${proxy}__effe=${EFFE_PROXY}"

  cp "$PNG_CM" "$cm_png"
  cp "$PNG_MMGM" "$mmgm_png"
  rm -rf "$data_dir"
  mkdir -p "$data_dir"
  cp "$DATA_SRC_DIR"/silver_nanoisland_*.dat "$data_dir"/

  echo "$EFFE_PROXY $proxy $cm_png $mmgm_png $data_dir" >> "$MANIFEST_PATH"
done

echo
echo "Saved Rave sweep images under: $IMG_SWEEP_DIR"
echo "Saved Rave sweep data under: $DATA_SWEEP_DIR"
