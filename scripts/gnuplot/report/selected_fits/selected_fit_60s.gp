set terminal pngcairo noenhanced size 1400,900
set output '../../../../../../../../../img/tests/mmgm_single_optical_trusted_branch/optical_trusted_branch_pop_48/gen_300/seed_111/mmgm_single/spheres/optimal_global_ITO_Ag_60s_T_0.png'
set title 'GLOBAL MMGM single-lognormal spheres fit ITO_Ag_60s_T_0: effe=0.48295, d=12.73 nm, hAg=6.1478 nm, rave=12.755 nm, sigL=0.49521, SSE=0.0098581'
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
  '../../../../../../../../../data/experimental/final/transmittance/ITO_Ag_60s_T_0.dat' using 1:3 with lines lw 2 title 'experimental', \
  '../../../../../../../../../data/output/tests/mmgm_single_optical_trusted_branch/optical_trusted_branch_pop_48/gen_300/seed_111/mmgm_single/spheres/optimal_global_ITO_Ag_60s_T_0.dat' using 1:3 with lines lw 2 title 'global mmgm_single spheres fit'
