#!/bin/bash
set xrange [0.56:]
set xtics nomirror
set x2tics
set xlabel "Volume fraction of Silver"
set x2label "Deposition times (s)"
set ylabel "Resonance center frequency (nm)"
set key left
plot "data/output/effe.dat" w lp lw 2 pt 7 t "Maxwell-Garnett", "data/output/expe.dat" axis x2y1  w lp lw 2 pt 7 t "Experimental Data"
