set terminal pngcairo noenhanced size 1400,900
set output '../../../../../img/optimal/mmgm_holes_single/holes/optimal_ITO_Ag_60s_T_0.png'
set title 'MMGM single-lognormal holes fit ITO_Ag_60s_T_0: effe=0.43377, d=69.615 nm, rave=0.78924 nm, sigL=0.35076, SSE=0.062639'
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
  '../../../../../data/experimental/final/transmittance/ITO_Ag_60s_T_0.dat' using 1:3 with lines lw 2 title 'experimental', \
  '../../../../../data/output/optimal/mmgm_holes_single/holes/optimal_ITO_Ag_60s_T_0.dat' using 1:3 with lines lw 2 title 'mmgm_single holes best fit'
