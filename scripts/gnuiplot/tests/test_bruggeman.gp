set terminal pngcairo size 1600,1000 noenhanced
set output '/home/alessandro/GitHub/Academia/nublar/img/tests/test_bruggeman.png'
set datafile commentschars '#'
set grid
set key outside right
set xlabel 'Wavelength (nm)'
set multiplot layout 2,1 title 'Bruggeman effective permittivity vs air and silver'
set ylabel 'Re(epsilon)'
plot \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:2 with lines lw 3 lc rgb '#404040' title 'air', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:4 with lines lw 3 lc rgb '#c00000' title 'silver', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:6  with lines lw 1.5 dt 2 title 'Bruggeman f=0.0', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:8  with lines lw 1.5 dt 2 title 'Bruggeman f=0.2', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:10 with lines lw 1.5 dt 2 title 'Bruggeman f=0.4', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:12 with lines lw 1.5 dt 2 title 'Bruggeman f=0.6', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:14 with lines lw 1.5 dt 2 title 'Bruggeman f=0.8', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:16 with lines lw 1.5 dt 2 title 'Bruggeman f=1.0'
set ylabel 'Im(epsilon)'
set yrange [-0.1:*]
plot \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:3 with lines lw 3 lc rgb '#404040' title 'air', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:5 with lines lw 3 lc rgb '#c00000' title 'silver', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:7  with lines lw 1.5 dt 2 title 'Bruggeman f=0.0', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:9  with lines lw 1.5 dt 2 title 'Bruggeman f=0.2', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:11 with lines lw 1.5 dt 2 title 'Bruggeman f=0.4', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:13 with lines lw 1.5 dt 2 title 'Bruggeman f=0.6', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:15 with lines lw 1.5 dt 2 title 'Bruggeman f=0.8', \
  '/home/alessandro/GitHub/Academia/nublar/data/output/test_bruggeman.dat' using 1:17 with lines lw 1.5 dt 2 title 'Bruggeman f=1.0'
unset multiplot
