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
TRANSMITTANCE_SRC_DIR="data/output/transmittance"
MODEL_INPUT="data/input/experimental/model_input.dat"
ITO_THICKNESS_NM="0.0"
GLASS_THICKNESS_NM="1100000.0"
INCLUDE_INCOHERENT_MULTIPLES="1"
ETA="1.0"
XI="1.0"

IMG_DIR="img/output/proxy_matrix"
DATA_DIR="data/output/proxy_matrix"
GP_DIR="scripts/gnuplot/output/proxy_matrix"
PERMITTIVITY_IMG_DIR="$IMG_DIR/permittivity"
PERMITTIVITY_DATA_DIR="$DATA_DIR/permittivity"
PERMITTIVITY_GP_DIR="$GP_DIR/permittivity"
TRANSMITTANCE_IMG_DIR="$IMG_DIR/transmittance"
TRANSMITTANCE_DATA_DIR="$DATA_DIR/transmittance"
TRANSMITTANCE_GP_DIR="$GP_DIR/transmittance"
PERMITTIVITY_MANIFEST_PATH="$PERMITTIVITY_DATA_DIR/sweep_manifest.dat"
TRANSMITTANCE_MANIFEST_PATH="$TRANSMITTANCE_DATA_DIR/sweep_manifest.dat"
CM_MATRIX_GP="$PERMITTIVITY_GP_DIR/plot_effective_eps_cm_matrix.gp"
MMGM_MATRIX_GP="$PERMITTIVITY_GP_DIR/plot_effective_eps_mmgm_matrix.gp"
CM_MATRIX_PNG="$PERMITTIVITY_IMG_DIR/effective_eps_cm_matrix.png"
MMGM_MATRIX_PNG="$PERMITTIVITY_IMG_DIR/effective_eps_mmgm_matrix.png"
TRANSMITTANCE_MATRIX_GP="$TRANSMITTANCE_GP_DIR/plot_transmittance_matrix.gp"
TRANSMITTANCE_MATRIX_PNG="$TRANSMITTANCE_IMG_DIR/transmittance_matrix.png"

mkdir -p \
  "$PERMITTIVITY_IMG_DIR" \
  "$PERMITTIVITY_DATA_DIR" \
  "$PERMITTIVITY_GP_DIR" \
  "$TRANSMITTANCE_IMG_DIR" \
  "$TRANSMITTANCE_DATA_DIR" \
  "$TRANSMITTANCE_GP_DIR"
: > "$PERMITTIVITY_MANIFEST_PATH"
echo "# effe_proxy radius_proxy cm_png mmgm_png data_dir" >> "$PERMITTIVITY_MANIFEST_PATH"
: > "$TRANSMITTANCE_MANIFEST_PATH"
echo "# effe_proxy radius_proxy plot_png plot_gp data_dir manifest_dat manifest_csv" >> "$TRANSMITTANCE_MANIFEST_PATH"

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

if [[ ! -x bin/transmittance ]]; then
  echo "==> Compiling transmittance solver"
  make bin/transmittance
fi

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

    cm_png="$PERMITTIVITY_IMG_DIR/effective_eps_cm__effe=${effe_proxy}__radius=${radius_proxy}.png"
    mmgm_png="$PERMITTIVITY_IMG_DIR/effective_eps_mmgm__effe=${effe_proxy}__radius=${radius_proxy}.png"
    data_dir="$PERMITTIVITY_DATA_DIR/effective_permittivity__effe=${effe_proxy}__radius=${radius_proxy}"

    cp "$PNG_CM_SINGLE" "$cm_png"
    cp "$PNG_MMGM_SINGLE" "$mmgm_png"
    rm -rf "$data_dir"
    mkdir -p "$data_dir"
    cp "$DATA_SRC_DIR"/silver_nanoisland_*.dat "$data_dir"/

    echo "$effe_proxy $radius_proxy $cm_png $mmgm_png $data_dir" >> "$PERMITTIVITY_MANIFEST_PATH"

    echo "==> Computing transmittance for effe=$effe_proxy radius=$radius_proxy"
    ./bin/transmittance \
      "$MODEL_INPUT" \
      "$ITO_THICKNESS_NM" \
      "$GLASS_THICKNESS_NM" \
      "$INCLUDE_INCOHERENT_MULTIPLES" \
      "$ETA" \
      "$XI"

    transmittance_data_dir="$TRANSMITTANCE_DATA_DIR/transmittance__effe=${effe_proxy}__radius=${radius_proxy}"
    transmittance_plot_gp="$TRANSMITTANCE_GP_DIR/plot_experimental_vs_calculated__effe=${effe_proxy}__radius=${radius_proxy}.gp"
    transmittance_plot_png="$TRANSMITTANCE_IMG_DIR/experimental_vs_calculated__effe=${effe_proxy}__radius=${radius_proxy}.png"
    transmittance_manifest_base="common_transmittance_manifest"
    transmittance_manifest_dat="$transmittance_data_dir/${transmittance_manifest_base}.dat"
    transmittance_manifest_csv="$transmittance_data_dir/${transmittance_manifest_base}.csv"

    rm -rf "$transmittance_data_dir"
    mkdir -p "$transmittance_data_dir"
    cp "$TRANSMITTANCE_SRC_DIR"/silver_nanoisland_*.dat "$transmittance_data_dir"/

    python3 tools/build_common_transmittance_dataset.py \
      --model-input "$MODEL_INPUT" \
      --calculated-dir "$transmittance_data_dir" \
      --outdir "$transmittance_data_dir" \
      --basename "$transmittance_manifest_base"

    python3 tools/build_transmittance_comparison_plot.py \
      --common-dataset "$transmittance_manifest_dat" \
      --gnuplot-out "$transmittance_plot_gp" \
      --png-out "$transmittance_plot_png"
    gnuplot "$transmittance_plot_gp"

    echo "$effe_proxy $radius_proxy $transmittance_plot_png $transmittance_plot_gp $transmittance_data_dir $transmittance_manifest_dat $transmittance_manifest_csv" \
      >> "$TRANSMITTANCE_MANIFEST_PATH"
  done
done

{
  echo 'set terminal pngcairo noenhanced size 2200,3600'
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
      data_dir="$PERMITTIVITY_DATA_DIR/effective_permittivity__effe=${effe_proxy}__radius=${radius_proxy}"
      echo "set title 'effe=${effe_proxy} | Rave=${radius_proxy}' font ',8'"
      if [[ -f "$data_dir/silver_nanoisland_10s.dat" ]]; then
        echo "plot \\"
        echo "  '$data_dir/silver_nanoisland_10s.dat' using 1:3 with lines lw 1 title '10 s', \\"
        echo "  '$data_dir/silver_nanoisland_20s.dat' using 1:3 with lines lw 1 title '20 s', \\"
        echo "  '$data_dir/silver_nanoisland_30s.dat' using 1:3 with lines lw 1 title '30 s', \\"
        echo "  '$data_dir/silver_nanoisland_40s.dat' using 1:3 with lines lw 1 title '40 s', \\"
        echo "  '$data_dir/silver_nanoisland_50s.dat' using 1:3 with lines lw 1 title '50 s', \\"
        echo "  '$data_dir/silver_nanoisland_60s.dat' using 1:3 with lines lw 1 title '60 s'"
      else
        echo "plot '-' using 1:2 with lines lc rgb '#cccccc' notitle"
        echo "300 0"
        echo "798 0"
        echo "e"
      fi
    done
  done
  echo 'unset multiplot'
} > "$CM_MATRIX_GP"

{
  echo 'set terminal pngcairo noenhanced size 2200,3600'
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
      data_dir="$PERMITTIVITY_DATA_DIR/effective_permittivity__effe=${effe_proxy}__radius=${radius_proxy}"
      echo "set title 'effe=${effe_proxy} | Rave=${radius_proxy}' font ',8'"
      if [[ -f "$data_dir/silver_nanoisland_10s.dat" ]]; then
        echo "plot \\"
        echo "  '$data_dir/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \\"
        echo "  '$data_dir/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \\"
        echo "  '$data_dir/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \\"
        echo "  '$data_dir/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \\"
        echo "  '$data_dir/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \\"
        echo "  '$data_dir/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'"
      else
        echo "plot '-' using 1:2 with lines lc rgb '#cccccc' notitle"
        echo "300 0"
        echo "798 0"
        echo "e"
      fi
    done
  done
  echo 'unset multiplot'
} > "$MMGM_MATRIX_GP"

gnuplot "$CM_MATRIX_GP"
gnuplot "$MMGM_MATRIX_GP"

{
  echo 'set terminal pngcairo noenhanced size 2200,3600'
  echo "set output '$TRANSMITTANCE_MATRIX_PNG'"
  echo "set multiplot layout ${#EFFE_PROXIES[@]},${#RADIUS_PROXIES[@]} rowsfirst title 'Transmittance Matrix (solid: calculated, dashed: experimental)'"
  echo 'set datafile commentschars "#"'
  echo 'set grid'
  echo 'set xrange [300:798]'
  echo 'set yrange [0:1]'
  echo 'set key off'
  echo 'set xlabel "Wavelength (nm)"'
  echo 'set ylabel "Transmittance"'
  for effe_proxy in "${EFFE_PROXIES[@]}"; do
    for radius_proxy in "${RADIUS_PROXIES[@]}"; do
      data_dir="$TRANSMITTANCE_DATA_DIR/transmittance__effe=${effe_proxy}__radius=${radius_proxy}"
      echo "set title 'effe=${effe_proxy} | Rave=${radius_proxy}' font ',8'"
      if [[ -f "$data_dir/silver_nanoisland_10s.dat" ]]; then
        echo "plot \\"
        echo "  'data/experimental/final/transmittance/ITO_Ag_10s_T_0.dat' using 1:3 with lines lw 1 dt 2 lc 1 title '10 s exp', \\"
        echo "  '$data_dir/silver_nanoisland_10s.dat' using 1:3 with lines lw 1 lc 1 title '10 s calc', \\"
        echo "  'data/experimental/final/transmittance/ITO_Ag_20s_T_0.dat' using 1:3 with lines lw 1 dt 2 lc 2 title '20 s exp', \\"
        echo "  '$data_dir/silver_nanoisland_20s.dat' using 1:3 with lines lw 1 lc 2 title '20 s calc', \\"
        echo "  'data/experimental/final/transmittance/ITO_Ag_30s_T_0.dat' using 1:3 with lines lw 1 dt 2 lc 3 title '30 s exp', \\"
        echo "  '$data_dir/silver_nanoisland_30s.dat' using 1:3 with lines lw 1 lc 3 title '30 s calc', \\"
        echo "  'data/experimental/final/transmittance/ITO_Ag_40s_T_0.dat' using 1:3 with lines lw 1 dt 2 lc 4 title '40 s exp', \\"
        echo "  '$data_dir/silver_nanoisland_40s.dat' using 1:3 with lines lw 1 lc 4 title '40 s calc', \\"
        echo "  'data/experimental/final/transmittance/ITO_Ag_50s_T_0.dat' using 1:3 with lines lw 1 dt 2 lc 5 title '50 s exp', \\"
        echo "  '$data_dir/silver_nanoisland_50s.dat' using 1:3 with lines lw 1 lc 5 title '50 s calc', \\"
        echo "  'data/experimental/final/transmittance/ITO_Ag_60s_T_0.dat' using 1:3 with lines lw 1 dt 2 lc 6 title '60 s exp', \\"
        echo "  '$data_dir/silver_nanoisland_60s.dat' using 1:3 with lines lw 1 lc 6 title '60 s calc'"
      else
        echo "plot '-' using 1:2 with lines lc rgb '#cccccc' notitle"
        echo "300 0"
        echo "798 0"
        echo "e"
      fi
    done
  done
  echo 'unset multiplot'
} > "$TRANSMITTANCE_MATRIX_GP"

gnuplot "$TRANSMITTANCE_MATRIX_GP"

echo
echo "Saved permittivity images under: $PERMITTIVITY_IMG_DIR"
echo "Saved permittivity data under: $PERMITTIVITY_DATA_DIR"
echo "Saved transmittance images under: $TRANSMITTANCE_IMG_DIR"
echo "Saved transmittance data under: $TRANSMITTANCE_DATA_DIR"
