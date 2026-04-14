#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

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

PLOT_CM="scripts/gnuplot/output/effective_permittivity/plot_effective_eps_cm.gp"
PLOT_MMGM="scripts/gnuplot/output/effective_permittivity/plot_effective_eps_mmgm.gp"
PNG_CM="img/output/effective_permittivity/effective_eps_cm.png"
PNG_MMGM="img/output/effective_permittivity/effective_eps_mmgm.png"
SWEEP_DIR="img/output/effective_permittivity/sweeps"

mkdir -p "$SWEEP_DIR"

for proxy in "${PROXIES[@]}"; do
  echo "==> Sweeping effe proxy: $proxy"

  python3 tools/build_experimental_input.py --effe-proxy "$proxy"
  ./bin/effective_eps
  gnuplot "$PLOT_CM"
  gnuplot "$PLOT_MMGM"

  cp "$PNG_CM" "$SWEEP_DIR/effective_eps_cm__${proxy}.png"
  cp "$PNG_MMGM" "$SWEEP_DIR/effective_eps_mmgm__${proxy}.png"
done

echo
echo "Saved sweep images under: $SWEEP_DIR"
