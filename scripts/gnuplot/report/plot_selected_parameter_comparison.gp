set terminal pngcairo enhanced color size 1500,1050 font 'Arial,12'
set output '../../../img/report/selected_parameter_comparison.png'
set datafile commentschars '#'
set grid
set key top left
set xlabel 'Deposition time (s)'
set xrange [5:65]
set multiplot layout 2,2 title 'Selected MMGM parameters vs AFM/thesis priors'
set ylabel 'Radius (nm)'
set title 'AFM projected-area radius proxy vs MMGM optical Rave'
plot '../../../data/output/report/selected_vs_afm_parameters.dat' using 1:2 with linespoints lw 2 pt 7 title 'MMGM optical Rave', \
     '../../../data/output/report/selected_vs_afm_parameters.dat' using 1:3 with linespoints lw 2 pt 5 title 'AFM projected-area radius proxy'
set ylabel 'sigL'
set title 'Lognormal width'
plot '../../../data/output/report/selected_vs_afm_parameters.dat' using 1:4 with linespoints lw 2 pt 7 title 'MMGM sigL', \
     '../../../data/output/report/selected_vs_afm_parameters.dat' using 1:5 with linespoints lw 2 pt 5 title 'AFM/thesis sigL'
set ylabel 'Thickness (nm)'
set title 'Effective slab thickness'
plot '../../../data/output/report/selected_vs_afm_parameters.dat' using 1:6 with linespoints lw 2 pt 7 title 'MMGM thickness', \
     '../../../data/output/report/selected_vs_afm_parameters.dat' using 1:7 with linespoints lw 2 pt 5 title 'AFM/thesis thickness'
set ylabel 'Effective quantity'
set title 'Filling fraction and Ag volume-per-area'
plot '../../../data/output/report/selected_vs_afm_parameters.dat' using 1:8 with linespoints lw 2 pt 7 title 'effe', \
     '../../../data/output/report/selected_vs_afm_parameters.dat' using 1:9 with linespoints lw 2 pt 5 title 'hAg = effe * thickness (nm)'
unset multiplot
