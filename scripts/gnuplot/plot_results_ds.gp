set terminal pngcairo size 1200,800 enhanced font "Helvetica,14"
set output "img/deposition.png"

set multiplot layout 2,2 title "Effective permittivity vs deposition step"
set title "(a)"
set xlabel "Wavelength (nm)"
set ylabel "Re(ε)"
set key right bottom
plot [300:900]"/home/alessandro/GitHub/Academia/nublar/data/output/Rave=1.34__f=0.133__lognormal__sg=1.60.dat" using 1:2 title "step 1" w l lw 2
set title "(c)"
set xlabel "Deposition step"
set ylabel "Wavelength (nm)"
set key top left
plot "data/output/summary_ds.dat" using 1:7 with linespoints lw 2 pt 5 title "ε'' max",      "data/output/summary_ds.dat" using 1:8 with linespoints lw 2 pt 7 title "LE-ENZ"
set title "(b)"
set xlabel "Wavelength (nm)"
set ylabel "Im(ε)"
set key right top
plot [300:900]"/home/alessandro/GitHub/Academia/nublar/data/output/Rave=1.34__f=0.133__lognormal__sg=1.60.dat" using 1:3 title "" w l lw 2
set title "(d)"
set xlabel "Deposition step"
set ylabel "ENZ wavelength (nm)"
plot "data/output/summary_ds.dat" using 1:9 with linespoints lw 2 pt 6 lc rgb "blue" title "HE-ENZ"

unset multiplot
