set terminal pngcairo size 1400,900 noenhanced
set output "img/experimental/final/afm_dataset_001.png"

set multiplot layout 2,2 rowsfirst title "AFM morphology vs deposition time (001)"

set style data yerrorlines
set grid
set key top left
set xlabel "Deposition time (s)"

# columns in .dat
# 1 time_s
# 3 coverage
# 4 coverage_std
# 5 thickness_nm
# 6 thickness_std
# 7 mean_radius_nm
# 8 mean_radius_std
# 11 density_um2
# 12 density_um2_std

set ylabel "Coverage fraction"
plot "data/experimental/final/afm_dataset_001.dat" using 1:3:4 title "coverage"

set ylabel "Equivalent thickness (nm)"
plot "data/experimental/final/afm_dataset_001.dat" using 1:5:6 title "thickness"

set ylabel "Mean equivalent radius (nm)"
plot "data/experimental/final/afm_dataset_001.dat" using 1:7:8 title "mean radius"

set ylabel "Number density (1/um^2)"
plot "data/experimental/final/afm_dataset_001.dat" using 1:11:12 title "density"

unset multiplot
