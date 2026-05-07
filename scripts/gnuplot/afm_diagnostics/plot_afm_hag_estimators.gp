set terminal pngcairo size 1500,950 noenhanced font "Arial,12"
system "mkdir -p img/afm_diagnostics"
set output "img/afm_diagnostics/afm_hag_estimators.png"

datafile = "data/output/afm_diagnostics/afm_hag_estimators.dat"

set title "AFM-derived hAg estimators compared"
set xlabel "Deposition time (s)"
set ylabel "hAg estimate (nm)"
set grid
set key outside right top
set xrange [0:*]
set yrange [0:*]
set xtics 10

f_equiv(x) = a_equiv*x + b_equiv
f_radius(x) = a_radius*x + b_radius
f_covrad(x) = a_covrad*x + b_covrad

fit f_equiv(x) datafile using 1:6 via a_equiv,b_equiv
fit f_radius(x) datafile using 1:7 via a_radius,b_radius
fit f_covrad(x) datafile using 1:8 via a_covrad,b_covrad

plot \
    datafile using 1:6 with linespoints lw 2 pt 7 lc rgb "#1b9e77" title "equivalent_thickness_nm", \
    datafile using 1:7:($7-$9):($7+$10) with yerrorlines lw 2 pt 9 lc rgb "#7570b3" title "radius-lognormal estimator", \
    datafile using 1:8 with linespoints lw 2 pt 5 lc rgb "#d95f02" title "coverage-radius estimator", \
    f_equiv(x) with lines lw 2 dt 2 lc rgb "#1b9e77" title sprintf("equiv fit: %.4g x %+.4g", a_equiv, b_equiv), \
    f_radius(x) with lines lw 2 dt 2 lc rgb "#7570b3" title sprintf("radius fit: %.4g x %+.4g", a_radius, b_radius), \
    f_covrad(x) with lines lw 2 dt 2 lc rgb "#d95f02" title sprintf("coverage-radius fit: %.4g x %+.4g", a_covrad, b_covrad)

unset output
