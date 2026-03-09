reset

set term pdf color enhanced size 15cm,8cm;
sz=1.
set size sz

set output "img/10-30_Rave=1i.pdf"

set label 1 at screen 0.45, screen 0.95 "R_{ave} = 1 nm"
set multiplot layout 1, 2
set tmargin at screen 0.88
set ylabel "Distribution of Probability"
set xlabel "Nanoparticle radius (nm)"
plot[:100][0:1] "data/output/Maxwell-Boltzmann__Rave=1.00.dat" w l lw 2 lc rgb "dark-red" t ""
unset label 1
set ylabel "Effective Permittivity"
set xlabel "Wavelength (nm)"
plot[300:900] "data/output/Rave=1.00__f=0.100.dat" u 1:3 w l lw 2 t "f = 0.1",  "data/output/Rave=1.00__f=0.200.dat" u 1:3 w l lw 2 t "f = 0.2",  "data/output/Rave=1.00__f=0.300.dat" u 1:3 w l lw 2 t "f = 0.3";
unset multiplot
unset output
