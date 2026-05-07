set terminal pngcairo size 1500,950 enhanced font "Arial,12"
system "mkdir -p img/afm_diagnostics"
set output "img/afm_diagnostics/afm_hag_estimators_normalized.png"

datafile = "data/output/afm_diagnostics/afm_hag_estimators.dat"

stats datafile using ($1 == 10 ? $6 : 1/0) name "EQ" nooutput
stats datafile using ($1 == 10 ? $7 : 1/0) name "RAD" nooutput
stats datafile using ($1 == 10 ? $8 : 1/0) name "COVRAD" nooutput

set title "AFM-derived hAg estimators compared: normalized trends"
set xlabel "Deposition time (s)"
set ylabel "hAg(t) / hAg(10s)"
set grid
set key outside right top
set xrange [0:*]
set yrange [0:*]
set xtics 10

plot \
    datafile using 1:($6/EQ_min) with linespoints lw 2 pt 7 lc rgb "#1b9e77" title "equivalent_thickness_nm", \
    datafile using 1:($7/RAD_min) with linespoints lw 2 pt 9 lc rgb "#7570b3" title "radius-lognormal estimator", \
    datafile using 1:($8/COVRAD_min) with linespoints lw 2 pt 5 lc rgb "#d95f02" title "coverage-radius estimator"

unset output
