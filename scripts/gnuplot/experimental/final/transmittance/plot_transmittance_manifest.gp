set terminal pngcairo size 1400,900 noenhanced
set output "/home/alessandro/GitHub/Academia/nublar/img/experimental/final/transmittance/transmittance_manifest.png"

set title "Processed transmittance spectra (transmittance_manifest)"
set grid
set key outside right
set xlabel "Wavelength (nm)"
set ylabel "Transmittance"

plot \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_10s_T_0.dat" using 1:3 with lines lw 2 title "ITO_Ag_10s_T", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_20s_T_0.dat" using 1:3 with lines lw 2 title "ITO_Ag_20s_T", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_30s_T_0.dat" using 1:3 with lines lw 2 title "ITO_Ag_30s_T", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_40s_T_0.dat" using 1:3 with lines lw 2 title "ITO_Ag_40s_T", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_50s_T_0.dat" using 1:3 with lines lw 2 title "ITO_Ag_50s_T", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_60s_T_0.dat" using 1:3 with lines lw 2 title "ITO_Ag_60s"
