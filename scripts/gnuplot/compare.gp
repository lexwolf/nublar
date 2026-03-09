#!/bin/bash
reset
set xrange[300:1000]
set xlabel "Wavelength (nm)"
plot "data/output/experimental.dat" u 1:3 w l lw 2 t "Experimental Data", \
     "data/output/clausius-mossotti.dat" u 1:5 w l lw 2 t "Maxwell-Garnett";
