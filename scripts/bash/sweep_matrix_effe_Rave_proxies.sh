#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

EFFE_PROXIES=(
  coverage_fraction
  eq_thickness_over_mean_height
  coverage_times_eq_over_hmean
  sqrt_coverage_times_eq_over_hmean
  eq_thickness_over_Rave
  hybrid_alpha25
  hybrid_alpha50
  hybrid_alpha75
)

RADIUS_PROXIES=(
  equivalent_radius_nm
  volume_equivalent_radius_nm
  height_equivalent_radius_mean_nm
  height_equivalent_radius_p95_nm
)

PLOT_CM_SINGLE="scripts/gnuplot/output/effective_permittivity/plot_effective_eps_cm.gp"
PLOT_MMGM_SINGLE="scripts/gnuplot/output/effective_permittivity/plot_effective_eps_mmgm.gp"
PNG_CM_SINGLE="img/output/effective_permittivity/effective_eps_cm.png"
PNG_MMGM_SINGLE="img/output/effective_permittivity/effective_eps_mmgm.png"
DATA_SRC_DIR="data/output/effective_permittivity"

IMG_DIR="img/output/proxy_matrix"
DATA_DIR="data/output/proxy_matrix"
GP_DIR="scripts/gnuplot/output/proxy_matrix"
MANIFEST_PATH="$DATA_DIR/sweep_manifest.dat"
CM_MATRIX_GP="$GP_DIR/plot_effective_eps_cm_matrix.gp"
MMGM_MATRIX_GP="$GP_DIR/plot_effective_eps_mmgm_matrix.gp"
CM_MATRIX_PNG="$IMG_DIR/effective_eps_cm_matrix.png"
MMGM_MATRIX_PNG="$IMG_DIR/effective_eps_mmgm_matrix.png"

mkdir -p "$IMG_DIR" "$DATA_DIR" "$GP_DIR"
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

for effe_proxy in "${EFFE_PROXIES[@]}"; do
  for radius_proxy in "${RADIUS_PROXIES[@]}"; do
    echo "==> Matrix sweep effe=$effe_proxy radius=$radius_proxy"

    python3 tools/build_experimental_input.py --effe-proxy "$effe_proxy" --radius-proxy "$radius_proxy"
    if ! ./bin/effective_eps; then
      echo "WARNING: effective_eps failed for effe=$effe_proxy radius=$radius_proxy, writing placeholder spectra" >&2
      generate_placeholder_effective_eps
    fi
    gnuplot "$PLOT_CM_SINGLE"
    gnuplot "$PLOT_MMGM_SINGLE"

    cm_png="$IMG_DIR/effective_eps_cm__effe=${effe_proxy}__radius=${radius_proxy}.png"
    mmgm_png="$IMG_DIR/effective_eps_mmgm__effe=${effe_proxy}__radius=${radius_proxy}.png"
    data_dir="$DATA_DIR/effective_permittivity__effe=${effe_proxy}__radius=${radius_proxy}"

    cp "$PNG_CM_SINGLE" "$cm_png"
    cp "$PNG_MMGM_SINGLE" "$mmgm_png"
    rm -rf "$data_dir"
    mkdir -p "$data_dir"
    cp "$DATA_SRC_DIR"/silver_nanoisland_*.dat "$data_dir"/

    echo "$effe_proxy $radius_proxy $cm_png $mmgm_png $data_dir" >> "$MANIFEST_PATH"
  done
done

{
  echo 'set terminal pngcairo size 2200,3600'
  echo "set output '$CM_MATRIX_PNG'"
  echo "set multiplot layout ${#EFFE_PROXIES[@]},${#RADIUS_PROXIES[@]} rowsfirst title 'Effective Permittivity Matrix (Clausius-Mossotti)'"
  echo 'set datafile commentschars "#"'
  echo 'set grid'
  echo 'set xrange [300:798]'
  echo 'set key right top font ",6" spacing 0.8 samplen 1'
  echo 'set xlabel "Wavelength (nm)"'
  echo 'set ylabel "epsilon_eff"'
  for effe_proxy in "${EFFE_PROXIES[@]}"; do
    for radius_proxy in "${RADIUS_PROXIES[@]}"; do
      data_dir="$DATA_DIR/effective_permittivity__effe=${effe_proxy}__radius=${radius_proxy}"
      echo "set title 'effe=${effe_proxy} | Rave=${radius_proxy}' font ',8'"
      echo "plot \\"
      echo "  '$data_dir/silver_nanoisland_10s.dat' using 1:3 with lines lw 1 title '10 s', \\"
      echo "  '$data_dir/silver_nanoisland_20s.dat' using 1:3 with lines lw 1 title '20 s', \\"
      echo "  '$data_dir/silver_nanoisland_30s.dat' using 1:3 with lines lw 1 title '30 s', \\"
      echo "  '$data_dir/silver_nanoisland_40s.dat' using 1:3 with lines lw 1 title '40 s', \\"
      echo "  '$data_dir/silver_nanoisland_50s.dat' using 1:3 with lines lw 1 title '50 s', \\"
      echo "  '$data_dir/silver_nanoisland_60s.dat' using 1:3 with lines lw 1 title '60 s'"
    done
  done
  echo 'unset multiplot'
} > "$CM_MATRIX_GP"

{
  echo 'set terminal pngcairo size 2200,3600'
  echo "set output '$MMGM_MATRIX_PNG'"
  echo "set multiplot layout ${#EFFE_PROXIES[@]},${#RADIUS_PROXIES[@]} rowsfirst title 'Effective Permittivity Matrix (Extended Mie Maxwell-Garnett)'"
  echo 'set datafile commentschars "#"'
  echo 'set grid'
  echo 'set xrange [300:798]'
  echo 'set key right top font ",6" spacing 0.8 samplen 1'
  echo 'set xlabel "Wavelength (nm)"'
  echo 'set ylabel "epsilon_eff"'
  for effe_proxy in "${EFFE_PROXIES[@]}"; do
    for radius_proxy in "${RADIUS_PROXIES[@]}"; do
      data_dir="$DATA_DIR/effective_permittivity__effe=${effe_proxy}__radius=${radius_proxy}"
      echo "set title 'effe=${effe_proxy} | Rave=${radius_proxy}' font ',8'"
      echo "plot \\"
      echo "  '$data_dir/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \\"
      echo "  '$data_dir/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \\"
      echo "  '$data_dir/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \\"
      echo "  '$data_dir/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \\"
      echo "  '$data_dir/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \\"
      echo "  '$data_dir/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'"
    done
  done
  echo 'unset multiplot'
} > "$MMGM_MATRIX_GP"

gnuplot "$CM_MATRIX_GP"
gnuplot "$MMGM_MATRIX_GP"

echo
echo "Saved proxy matrix images under: $IMG_DIR"
echo "Saved proxy matrix data under: $DATA_DIR"
