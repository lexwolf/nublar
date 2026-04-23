set terminal pngcairo noenhanced size 1400,900
set output '../../../../img/optimal/mg/optimal_ITO_Ag_30s_T_0.png'
set title 'MG fit ITO_Ag_30s_T_0: effe=0.59413, d=1 nm, SSE=1.3937'
set datafile commentschars '#'
set grid
set xlabel 'Wavelength (nm)'
set ylabel 'Transmittance'
set key outside right
plot \
  '../../../../data/experimental/final/transmittance/ITO_Ag_30s_T_0.dat' using 1:3 with lines lw 2 title 'experimental', \
  '../../../../data/output/optimal/mg/optimal_ITO_Ag_30s_T_0.dat' using 1:3 with lines lw 2 title 'mg best fit'
