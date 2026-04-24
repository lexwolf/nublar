set terminal pngcairo noenhanced size 1400,900
set output '../../../../../img/optimal/bruggeman/holes/optimal_ITO_Ag_60s_T_0.png'
set title 'Bruggeman holes fit ITO_Ag_60s_T_0: effe=0.92209, d=13.111 nm, SSE=0.20227'
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
  '../../../../../data/output/optimal/bruggeman/holes/optimal_ITO_Ag_60s_T_0.dat' using 1:3 with lines lw 2 title 'bruggeman holes best fit'
