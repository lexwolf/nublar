set terminal pngcairo size 1400,900 noenhanced font "Arial,12"
system "mkdir -p img/afm_diagnostics"
set output "img/afm_diagnostics/afm_hag_volume_equivalent.png"

datafile = "data/output/afm_diagnostics/afm_hag_volume_equivalent.dat"

set title "AFM-derived silver volume per unit area: volume-equivalent radius proxy"
set xlabel "Deposition time (s)"
set ylabel "h_Ag (nm)"
set grid
set key outside right top
set xrange [0:*]
set yrange [0:*]
set xtics 10

f(x) = a*x + b
fit f(x) datafile using 1:5 via a,b

plot \
    datafile using 1:5:8:9 with yerrorlines lw 2 pt 7 lc rgb "#1b9e77" title "AFM h_Ag proxy", \
    f(x) with lines lw 2 dt 2 lc rgb "#d95f02" title sprintf("linear fit: %.4g x %+.4g", a, b)

unset output
