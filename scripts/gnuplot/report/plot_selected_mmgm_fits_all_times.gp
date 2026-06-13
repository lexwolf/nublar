set terminal pngcairo enhanced color size 1600,1000 font 'Arial,12'
set output '../../../img/report/selected_mmgm_fits_all_times.png'
set datafile commentschars '#'
set grid
set xlabel 'Wavelength (nm)'
set ylabel 'Transmittance'
set xrange [300:800]
set yrange [0:1.08]
set key outside right top
set title 'all selected times'
plot '../../../data/output/report/selected_runs/experimental_ITO_Ag_10s_T_0.dat' using 1:3 with points pointtype 7 pointsize 0.45 lc rgb '#1b9e77' title '10s exp', \
     '../../../data/output/report/selected_runs/selected_ITO_Ag_10s_T_0.dat' using 1:3 with lines linewidth 2.2 lc rgb '#1b9e77' title '10s fit', \
     '../../../data/output/report/selected_runs/experimental_ITO_Ag_20s_T_0.dat' using 1:3 with points pointtype 7 pointsize 0.45 lc rgb '#66a61e' title '20s exp', \
     '../../../data/output/report/selected_runs/selected_ITO_Ag_20s_T_0.dat' using 1:3 with lines linewidth 2.2 lc rgb '#66a61e' title '20s fit', \
     '../../../data/output/report/selected_runs/experimental_ITO_Ag_30s_T_0.dat' using 1:3 with points pointtype 7 pointsize 0.45 lc rgb '#d95f02' title '30s exp', \
     '../../../data/output/report/selected_runs/selected_ITO_Ag_30s_T_0.dat' using 1:3 with lines linewidth 2.2 lc rgb '#d95f02' title '30s fit', \
     '../../../data/output/report/selected_runs/experimental_ITO_Ag_40s_T_0.dat' using 1:3 with points pointtype 7 pointsize 0.45 lc rgb '#e6ab02' title '40s exp', \
     '../../../data/output/report/selected_runs/selected_ITO_Ag_40s_T_0.dat' using 1:3 with lines linewidth 2.2 lc rgb '#e6ab02' title '40s fit', \
     '../../../data/output/report/selected_runs/experimental_ITO_Ag_50s_T_0.dat' using 1:3 with points pointtype 7 pointsize 0.45 lc rgb '#7570b3' title '50s exp', \
     '../../../data/output/report/selected_runs/selected_ITO_Ag_50s_T_0.dat' using 1:3 with lines linewidth 2.2 lc rgb '#7570b3' title '50s fit', \
     '../../../data/output/report/selected_runs/experimental_ITO_Ag_60s_T_0.dat' using 1:3 with points pointtype 7 pointsize 0.45 lc rgb '#e7298a' title '60s exp', \
     '../../../data/output/report/selected_runs/selected_ITO_Ag_60s_T_0.dat' using 1:3 with lines linewidth 2.2 lc rgb '#e7298a' title '60s fit'
