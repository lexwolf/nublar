set terminal pngcairo size 2400,900 noenhanced
set output "/home/alessandro/GitHub/Academia/nublar/img/output/transmittance/transmittance_components.png"

common_lamin = 300
common_lamax = 798

set multiplot layout 1,3 rowsfirst title "Calculated transmittance components"
set grid
set xrange [common_lamin:common_lamax]
set xlabel "Wavelength (nm)"
set ylabel "Transmittance"
set key outside right

set title "T_total"
plot \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_10s.dat" using 1:3 with lines lw 2 title "10 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_20s.dat" using 1:3 with lines lw 2 title "20 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_30s.dat" using 1:3 with lines lw 2 title "30 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_40s.dat" using 1:3 with lines lw 2 title "40 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_50s.dat" using 1:3 with lines lw 2 title "50 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_60s.dat" using 1:3 with lines lw 2 title "60 s"

set title "T_front"
plot \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_10s.dat" using 1:4 with lines lw 2 title "10 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_20s.dat" using 1:4 with lines lw 2 title "20 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_30s.dat" using 1:4 with lines lw 2 title "30 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_40s.dat" using 1:4 with lines lw 2 title "40 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_50s.dat" using 1:4 with lines lw 2 title "50 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_60s.dat" using 1:4 with lines lw 2 title "60 s"

set title "T_back"
plot \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_10s.dat" using 1:5 with lines lw 2 title "10 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_20s.dat" using 1:5 with lines lw 2 title "20 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_30s.dat" using 1:5 with lines lw 2 title "30 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_40s.dat" using 1:5 with lines lw 2 title "40 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_50s.dat" using 1:5 with lines lw 2 title "50 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_60s.dat" using 1:5 with lines lw 2 title "60 s"

unset multiplot
