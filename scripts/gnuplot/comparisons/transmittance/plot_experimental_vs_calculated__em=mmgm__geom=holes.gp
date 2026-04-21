set terminal pngcairo noenhanced size 1800,900
set output "/home/alessandro/GitHub/Academia/nublar/img/comparisons/transmittance/experimental_vs_calculated__em=mmgm__geom=holes.png"

common_lamin = 300
common_lamax = 798

set multiplot layout 1,2 rowsfirst title "Experimental vs calculated transmittance spectra"
set grid
set xrange [common_lamin:common_lamax]
set xlabel "Wavelength (nm)"
set ylabel "Transmittance"
set key outside right

set title "Experimental spectra"
plot \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_10s_T_0.dat" using 1:3 with lines lw 2 title "10 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_20s_T_0.dat" using 1:3 with lines lw 2 title "20 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_30s_T_0.dat" using 1:3 with lines lw 2 title "30 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_40s_T_0.dat" using 1:3 with lines lw 2 title "40 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_50s_T_0.dat" using 1:3 with lines lw 2 title "50 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/experimental/final/transmittance/ITO_Ag_60s_T_0.dat" using 1:3 with lines lw 2 title "60 s"

set title "Calculated spectra"
plot \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_10s__em=mmgm__geom=holes.dat" using 1:3 with lines lw 2 title "10 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_20s__em=mmgm__geom=holes.dat" using 1:3 with lines lw 2 title "20 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_30s__em=mmgm__geom=holes.dat" using 1:3 with lines lw 2 title "30 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_40s__em=mmgm__geom=holes.dat" using 1:3 with lines lw 2 title "40 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_50s__em=mmgm__geom=holes.dat" using 1:3 with lines lw 2 title "50 s", \
    "/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/silver_nanoisland_60s__em=mmgm__geom=holes.dat" using 1:3 with lines lw 2 title "60 s"

unset multiplot
