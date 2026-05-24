set terminal pngcairo noenhanced size 1400,900
set output '../../../../../../../../../img/tests/mmgm_transition_hag_window/free_hag_1.0_3.0_pop_64/gen_400/seed_54321/mmgm_single/spheres/optimal_global_ITO_Ag_40s_T_0.png'
set title 'GLOBAL MMGM single-lognormal spheres fit ITO_Ag_40s_T_0: effe=0.18567, d=7.3992 nm, hAg=1.3738 nm, rave=17.126 nm, sigL=0.6797, SSE=0.04493'
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
  '../../../../../../../../../data/experimental/final/transmittance/ITO_Ag_40s_T_0.dat' using 1:3 with lines lw 2 title 'experimental', \
  '../../../../../../../../../data/output/tests/mmgm_transition_hag_window/free_hag_1.0_3.0_pop_64/gen_400/seed_54321/mmgm_single/spheres/optimal_global_ITO_Ag_40s_T_0.dat' using 1:3 with lines lw 2 title 'global mmgm_single spheres fit'
