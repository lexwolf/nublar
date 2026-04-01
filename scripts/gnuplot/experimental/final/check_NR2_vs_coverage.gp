reset

set terminal pngcairo size 1200,800 enhanced font "Helvetica,14"
set output "img/experimental/final/check_NR2_vs_coverage.png"

set multiplot layout 2,1 title "Consistency check: coverage vs N R^2"

set grid
set key top left
set xlabel "Deposition time (s)"

# Columns in afm_to_emt_input_001+003.dat
# 1  time_s
# 2  n_scans
# 3  coverage
# 4  coverage_std
# 5  Rave_nm
# 6  Rave_nm_std
# 7  sigma_geo
# 8  sigma_geo_std
# 9  eq_thickness_nm
# 10 eq_thickness_nm_std
# 11 density_um2
# 12 density_um2_std
# 13 mean_height_nm
# 14 mean_height_nm_std

# --- Panel 1: raw comparison ---
set ylabel "Coverage / proxy"
plot \
    "data/experimental/final/afm_to_emt_input_001+003.dat" using 1:3:4 with yerrorlines lw 2 pt 7 title "coverage", \
    "data/experimental/final/afm_to_emt_input_001+003.dat" using 1:($11*($5/1000.0)**2*pi) with linespoints lw 2 pt 5 title "pi N R^2"

# --- Panel 2: ratio ---
set ylabel "(pi N R^2) / coverage"
plot \
    "data/experimental/final/afm_to_emt_input_001+003.dat" using 1:(($11*($5/1000.0)**2*pi)/$3) with linespoints lw 2 pt 7 title "(pi N R^2)/coverage"

unset multiplot
