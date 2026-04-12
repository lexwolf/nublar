set terminal pngcairo size 1400,900
set output "img/experimental/final/afm/afm_to_emt_input_001+003.png"

set multiplot layout 2,2 rowsfirst title "AFM -> EMT inputs (001+003)"

set style data yerrorlines
set grid
set key top left
set xlabel "Deposition time (s)"

# columns in .dat
# 1  time_s
# 2  n_scans
# 3  coverage
# 4  coverage_std
# 5  effe_proxy
# 6  effe_name
# 7  Rave_nm
# 8  Rave_nm_std
# 9  radius_proxy_name
# 10 sigma_geo
# 11 sigma_geo_std
# 12 eq_thickness_nm
# 13 eq_thickness_nm_std
# 14 density_um2
# 15 density_um2_std
# 16 mean_height_nm
# 17 mean_height_nm_std

set ylabel "Coverage fraction"
plot "data/experimental/final/afm/afm_to_emt_input_001+003.dat" using 1:3:4 title "coverage"

set ylabel "Rave (nm)"
plot "data/experimental/final/afm/afm_to_emt_input_001+003.dat" using 1:7:8 title "Rave"

set ylabel "sigma_geo"
plot "data/experimental/final/afm/afm_to_emt_input_001+003.dat" using 1:10:11 title "sigma_geo"

set ylabel "Equivalent thickness (nm)"
plot "data/experimental/final/afm/afm_to_emt_input_001+003.dat" using 1:12:13 title "eq thickness"

unset multiplot
