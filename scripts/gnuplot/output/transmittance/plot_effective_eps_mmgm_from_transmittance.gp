set terminal pngcairo size 1400,900 noenhanced
set output "img/output/transmittance/effective_eps_mmgm_from_transmittance.png"

set multiplot layout 2,1 title "Silver Nanoisland Effective Permittivity from Transmittance Solver"

set datafile commentschars "#"
set grid
set key outside right top
set xlabel "Wavelength (nm)"
set xrange [300:798]

set ylabel "Re(epsilon_eff)"
plot \
    "data/output/transmittance/silver_nanoisland_10s.dat" using 1:10 with lines lw 2 title "10 s", \
    "data/output/transmittance/silver_nanoisland_20s.dat" using 1:10 with lines lw 2 title "20 s", \
    "data/output/transmittance/silver_nanoisland_30s.dat" using 1:10 with lines lw 2 title "30 s", \
    "data/output/transmittance/silver_nanoisland_40s.dat" using 1:10 with lines lw 2 title "40 s", \
    "data/output/transmittance/silver_nanoisland_50s.dat" using 1:10 with lines lw 2 title "50 s", \
    "data/output/transmittance/silver_nanoisland_60s.dat" using 1:10 with lines lw 2 title "60 s"

set ylabel "Im(epsilon_eff)"
plot \
    "data/output/transmittance/silver_nanoisland_10s.dat" using 1:11 with lines lw 2 title "10 s", \
    "data/output/transmittance/silver_nanoisland_20s.dat" using 1:11 with lines lw 2 title "20 s", \
    "data/output/transmittance/silver_nanoisland_30s.dat" using 1:11 with lines lw 2 title "30 s", \
    "data/output/transmittance/silver_nanoisland_40s.dat" using 1:11 with lines lw 2 title "40 s", \
    "data/output/transmittance/silver_nanoisland_50s.dat" using 1:11 with lines lw 2 title "50 s", \
    "data/output/transmittance/silver_nanoisland_60s.dat" using 1:11 with lines lw 2 title "60 s"

unset multiplot
