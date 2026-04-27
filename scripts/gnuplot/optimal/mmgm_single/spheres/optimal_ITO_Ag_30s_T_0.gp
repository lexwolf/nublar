set terminal pngcairo noenhanced size 1400,900
set output '../../../../../img/optimal/mmgm_single/spheres/optimal_ITO_Ag_30s_T_0.png'
set title 'MMGM single-lognormal spheres fit ITO_Ag_30s_T_0: effe=0.15003, d=3.2344 nm, rave=12.692 nm, sigL=0.66015, SSE=0.053514'
set datafile commentschars '#'
set grid
set xlabel 'Wavelength (nm)'
set ylabel 'Transmittance'
set xrange [300:798]
set key outside right
set arrow from 350, graph 0 to 350, graph 1 nohead dashtype 2
set arrow from 780, graph 0 to 780, graph 1 nohead dashtype 2
set label 'fit window' at 350, graph 0.95
plot \
  '../../../../../data/experimental/final/transmittance/ITO_Ag_30s_T_0.dat' using 1:3 with lines lw 2 title 'experimental', \
  '../../../../../data/output/optimal/mmgm_single/spheres/optimal_ITO_Ag_30s_T_0.dat' using 1:3 with lines lw 2 title 'mmgm_single spheres best fit'
