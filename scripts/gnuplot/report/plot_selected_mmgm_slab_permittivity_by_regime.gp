set terminal pngcairo enhanced color size 1600,1000 font 'Arial,12'
set output '../../../img/report/selected_mmgm_slab_permittivity_by_regime.png'
set datafile commentschars '#'
set grid
set xlabel 'Wavelength (nm)'
set xrange [300:800]
set key outside right top
set multiplot layout 3,2 title 'Selected MMGM slab permittivity by regime'
set title 'early: Re epsilon_eff'
set ylabel 'Re epsilon_eff'
plot '../../../data/output/report/permittivity/eps_slab_10s.dat' using 1:2 with lines lw 2 lc rgb '#1b9e77' title '10s', \
     '../../../data/output/report/permittivity/eps_slab_20s.dat' using 1:2 with lines lw 2 lc rgb '#66a61e' title '20s'
set title 'early: Im epsilon_eff'
set ylabel 'Im epsilon_eff'
plot '../../../data/output/report/permittivity/eps_slab_10s.dat' using 1:3 with lines lw 2 lc rgb '#1b9e77' title '10s', \
     '../../../data/output/report/permittivity/eps_slab_20s.dat' using 1:3 with lines lw 2 lc rgb '#66a61e' title '20s'
set title 'transition: Re epsilon_eff'
set ylabel 'Re epsilon_eff'
plot '../../../data/output/report/permittivity/eps_slab_30s.dat' using 1:2 with lines lw 2 lc rgb '#d95f02' title '30s', \
     '../../../data/output/report/permittivity/eps_slab_40s.dat' using 1:2 with lines lw 2 lc rgb '#e6ab02' title '40s'
set title 'transition: Im epsilon_eff'
set ylabel 'Im epsilon_eff'
plot '../../../data/output/report/permittivity/eps_slab_30s.dat' using 1:3 with lines lw 2 lc rgb '#d95f02' title '30s', \
     '../../../data/output/report/permittivity/eps_slab_40s.dat' using 1:3 with lines lw 2 lc rgb '#e6ab02' title '40s'
set title 'late: Re epsilon_eff'
set ylabel 'Re epsilon_eff'
plot '../../../data/output/report/permittivity/eps_slab_50s.dat' using 1:2 with lines lw 2 lc rgb '#7570b3' title '50s', \
     '../../../data/output/report/permittivity/eps_slab_60s.dat' using 1:2 with lines lw 2 lc rgb '#e7298a' title '60s'
set title 'late: Im epsilon_eff'
set ylabel 'Im epsilon_eff'
plot '../../../data/output/report/permittivity/eps_slab_50s.dat' using 1:3 with lines lw 2 lc rgb '#7570b3' title '50s', \
     '../../../data/output/report/permittivity/eps_slab_60s.dat' using 1:3 with lines lw 2 lc rgb '#e7298a' title '60s'
unset multiplot
