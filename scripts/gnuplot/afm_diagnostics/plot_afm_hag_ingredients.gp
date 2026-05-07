set terminal pngcairo size 1800,1100 enhanced font "Arial,12"
system "mkdir -p img/afm_diagnostics"
set output "img/afm_diagnostics/afm_hag_ingredients.png"

datafile = "data/output/afm_diagnostics/afm_hag_ingredients.dat"

set grid
set key off
set xrange [0:*]
set xtics 10
set xlabel "Deposition time (s)"

set multiplot layout 2,3 title "AFM ingredients for hAg diagnostics"

set title "coverage_fraction"
set ylabel "coverage_fraction"
plot datafile using 1:2 with linespoints lw 2 pt 7 lc rgb "#1b9e77"

set title "volume_equivalent_radius_nm"
set ylabel "radius (nm)"
plot datafile using 1:3 with linespoints lw 2 pt 7 lc rgb "#7570b3"

set title "single_lognormal_sigL"
set ylabel "sigL"
plot datafile using 1:4 with linespoints lw 2 pt 7 lc rgb "#d95f02"

set title "equivalent_thickness_nm"
set ylabel "thickness (nm)"
plot datafile using 1:5 with linespoints lw 2 pt 7 lc rgb "#66a61e"

set title "single_lognormal_Rave_nm"
set ylabel "Rave (nm)"
plot datafile using 1:6 with linespoints lw 2 pt 7 lc rgb "#e7298a"

set title "single_lognormal_std_nm"
set ylabel "std (nm)"
plot datafile using 1:7 with linespoints lw 2 pt 7 lc rgb "#a6761d"

unset multiplot
unset output
