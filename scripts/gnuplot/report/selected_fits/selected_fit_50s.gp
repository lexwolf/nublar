set terminal pngcairo noenhanced size 1400,900
set output '../../../../../../../../../img/tests/mmgm_single_optical_trusted_branch/optical_trusted_branch_pop_48/gen_300/seed_111/mmgm_single/spheres/optimal_global_ITO_Ag_50s_T_0.png'
set title 'GLOBAL MMGM single-lognormal spheres fit ITO_Ag_50s_T_0: effe=0.31455, d=8.189 nm, hAg=2.5759 nm, rave=14.75 nm, sigL=0.61643, SSE=0.005929'
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
  '../../../../../../../../../data/experimental/final/transmittance/ITO_Ag_50s_T_0.dat' using 1:3 with lines lw 2 title 'experimental', \
  '../../../../../../../../../data/output/tests/mmgm_single_optical_trusted_branch/optical_trusted_branch_pop_48/gen_300/seed_111/mmgm_single/spheres/optimal_global_ITO_Ag_50s_T_0.dat' using 1:3 with lines lw 2 title 'global mmgm_single spheres fit'
