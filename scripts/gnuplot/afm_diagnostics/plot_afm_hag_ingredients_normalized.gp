set terminal pngcairo size 1800,1100 noenhanced font "Arial,12"
system "mkdir -p img/afm_diagnostics"
set output "img/afm_diagnostics/afm_hag_ingredients_normalized.png"

datafile = "data/output/afm_diagnostics/afm_hag_ingredients.dat"

stats datafile using ($1 == 10 ? $2 : 1/0) name "COV" nooutput
stats datafile using ($1 == 10 ? $3 : 1/0) name "RAD" nooutput
stats datafile using ($1 == 10 ? $4 : 1/0) name "SIG" nooutput
stats datafile using ($1 == 10 ? $5 : 1/0) name "EQ" nooutput
stats datafile using ($1 == 10 ? $6 : 1/0) name "RAVE" nooutput
stats datafile using ($1 == 10 ? $7 : 1/0) name "STD" nooutput

set grid
set key off
set xrange [0:*]
set xtics 10
set xlabel "Deposition time (s)"
set ylabel "quantity(t) / quantity(10s)"

set multiplot layout 2,3 title "AFM ingredients for hAg diagnostics: normalized to 10s"

set title "coverage_fraction"
plot datafile using 1:($2/COV_min) with linespoints lw 2 pt 7 lc rgb "#1b9e77"

set title "volume_equivalent_radius_nm"
plot datafile using 1:($3/RAD_min) with linespoints lw 2 pt 7 lc rgb "#7570b3"

set title "single_lognormal_sigL"
plot datafile using 1:($4/SIG_min) with linespoints lw 2 pt 7 lc rgb "#d95f02"

set title "equivalent_thickness_nm"
plot datafile using 1:($5/EQ_min) with linespoints lw 2 pt 7 lc rgb "#66a61e"

set title "single_lognormal_Rave_nm"
plot datafile using 1:($6/RAVE_min) with linespoints lw 2 pt 7 lc rgb "#e7298a"

set title "single_lognormal_std_nm"
plot datafile using 1:($7/STD_min) with linespoints lw 2 pt 7 lc rgb "#a6761d"

unset multiplot
unset output
