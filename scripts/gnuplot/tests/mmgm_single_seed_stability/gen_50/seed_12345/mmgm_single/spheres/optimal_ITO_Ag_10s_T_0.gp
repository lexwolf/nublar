set terminal pngcairo noenhanced size 1400,900
set output '../../../../../../../../img/tests/mmgm_single_seed_stability/gen_50/seed_12345/mmgm_single/spheres/optimal_ITO_Ag_10s_T_0.png'
set title 'MMGM single-lognormal spheres fit ITO_Ag_10s_T_0: effe=0.42359, d=15.464 nm, rave=67.712 nm, sigL=0.23421, SSE=0.057058'
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
  '../../../../../../../../data/experimental/final/transmittance/ITO_Ag_10s_T_0.dat' using 1:3 with lines lw 2 title 'experimental', \
  '../../../../../../../../data/output/tests/mmgm_single_seed_stability/gen_50/seed_12345/mmgm_single/spheres/optimal_ITO_Ag_10s_T_0.dat' using 1:3 with lines lw 2 title 'mmgm_single spheres best fit'
