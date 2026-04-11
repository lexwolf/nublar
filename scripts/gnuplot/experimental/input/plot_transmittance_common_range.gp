set terminal pngcairo size 1400,900
set output "/home/alessandro/GitHub/Academia/nublar/img/experimental/input/transmittance_common_range.png"

set title "Silver nanoisland transmittance spectra"
set xlabel "Wavelength (nm)"
set ylabel "Transmittance"
set xrange [300:798]
set grid
set key outside right

plot \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_10s_T_0.dat" using 1:3 with lines lw 2 title "10 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_20s_T_0.dat" using 1:3 with lines lw 2 title "20 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_30s_T_0.dat" using 1:3 with lines lw 2 title "30 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_40s_T_0.dat" using 1:3 with lines lw 2 title "40 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_50s_T_0.dat" using 1:3 with lines lw 2 title "50 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_60s_T_0.dat" using 1:3 with lines lw 2 title "60 s"
