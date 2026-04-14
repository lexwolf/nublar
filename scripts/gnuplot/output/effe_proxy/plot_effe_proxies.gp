set terminal pngcairo size 1400,900 enhanced
set output 'img/output/effe_proxy/effe_proxy_comparison.png'

set title 'Candidate effe proxies vs deposition time'
set xlabel 'Deposition time (s)'
set ylabel 'Proxy value'
set grid
set key outside right top
set xtics 10

plot \
    'data/output/effe_proxy/effe_proxy_comparison.dat' using 1:2 with linespoints lw 2 pt 7 title 'coverage_fraction', \
    'data/output/effe_proxy/effe_proxy_comparison.dat' using 1:3 with linespoints lw 2 pt 7 title 'eq_thickness_over_mean_height', \
    'data/output/effe_proxy/effe_proxy_comparison.dat' using 1:7 with linespoints lw 2 pt 7 title 'coverage_times_eq_over_hmean', \
    'data/output/effe_proxy/effe_proxy_comparison.dat' using 1:8 with linespoints lw 2 pt 7 title 'sqrt_coverage_times_eq_over_hmean', \
    'data/output/effe_proxy/effe_proxy_comparison.dat' using 1:9 with linespoints lw 2 pt 7 title 'eq_thickness_over_Rave', \
    'data/output/effe_proxy/effe_proxy_comparison.dat' using 1:10 with linespoints lw 2 pt 7 title 'hybrid_alpha25', \
    'data/output/effe_proxy/effe_proxy_comparison.dat' using 1:11 with linespoints lw 2 pt 7 title 'hybrid_alpha50', \
    'data/output/effe_proxy/effe_proxy_comparison.dat' using 1:12 with linespoints lw 2 pt 7 title 'hybrid_alpha75'
