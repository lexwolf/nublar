set terminal pngcairo size 1400,900 enhanced
set output 'img/output/Rave_proxy/Rave_proxy_comparison.png'

set title 'Candidate Rave proxies vs deposition time'
set xlabel 'Deposition time (s)'
set ylabel 'Radius proxy value (nm)'
set grid
set key outside right top
set xtics 10

plot \
    'data/output/Rave_proxy/Rave_proxy_comparison.dat' using 1:2 with linespoints lw 2 pt 7 title 'equivalent_radius_nm', \
    'data/output/Rave_proxy/Rave_proxy_comparison.dat' using 1:3 with linespoints lw 2 pt 7 title 'volume_equivalent_radius_nm', \
    'data/output/Rave_proxy/Rave_proxy_comparison.dat' using 1:4 with linespoints lw 2 pt 7 title 'height_equivalent_radius_mean_nm', \
    'data/output/Rave_proxy/Rave_proxy_comparison.dat' using 1:5 with linespoints lw 2 pt 7 title 'height_equivalent_radius_p95_nm'
