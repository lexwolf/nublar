set terminal pngcairo size 2200,3600 noenhanced
set output 'img/output/proxy_matrix/effective_eps_mmgm_matrix.png'
set multiplot layout 8,4 rowsfirst title 'Effective Permittivity Matrix (Extended Mie Maxwell-Garnett)'
set datafile commentschars "#"
set grid
set xrange [300:798]
set key right top font ",6" spacing 0.8 samplen 1
set xlabel "Wavelength (nm)"
set ylabel "epsilon_eff"
set title 'effe=coverage_fraction | Rave=equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=coverage_fraction | Rave=volume_equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=volume_equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=volume_equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=volume_equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=volume_equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=volume_equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=volume_equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=coverage_fraction | Rave=height_equivalent_radius_mean_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_mean_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_mean_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_mean_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_mean_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_mean_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_mean_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=coverage_fraction | Rave=height_equivalent_radius_p95_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_p95_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_p95_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_p95_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_p95_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_p95_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_fraction__radius=height_equivalent_radius_p95_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=eq_thickness_over_mean_height | Rave=equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=eq_thickness_over_mean_height | Rave=volume_equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=volume_equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=volume_equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=volume_equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=volume_equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=volume_equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=volume_equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=eq_thickness_over_mean_height | Rave=height_equivalent_radius_mean_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_mean_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_mean_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_mean_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_mean_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_mean_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_mean_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=eq_thickness_over_mean_height | Rave=height_equivalent_radius_p95_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_p95_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_p95_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_p95_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_p95_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_p95_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_mean_height__radius=height_equivalent_radius_p95_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=coverage_times_eq_over_hmean | Rave=equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=coverage_times_eq_over_hmean | Rave=volume_equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=coverage_times_eq_over_hmean | Rave=height_equivalent_radius_mean_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=coverage_times_eq_over_hmean | Rave=height_equivalent_radius_p95_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=sqrt_coverage_times_eq_over_hmean | Rave=equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=sqrt_coverage_times_eq_over_hmean | Rave=volume_equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=volume_equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=sqrt_coverage_times_eq_over_hmean | Rave=height_equivalent_radius_mean_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_mean_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=sqrt_coverage_times_eq_over_hmean | Rave=height_equivalent_radius_p95_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=sqrt_coverage_times_eq_over_hmean__radius=height_equivalent_radius_p95_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=eq_thickness_over_Rave | Rave=equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=eq_thickness_over_Rave | Rave=volume_equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=volume_equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=volume_equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=volume_equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=volume_equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=volume_equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=volume_equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=eq_thickness_over_Rave | Rave=height_equivalent_radius_mean_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_mean_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_mean_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_mean_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_mean_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_mean_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_mean_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=eq_thickness_over_Rave | Rave=height_equivalent_radius_p95_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_p95_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_p95_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_p95_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_p95_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_p95_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=eq_thickness_over_Rave__radius=height_equivalent_radius_p95_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha25 | Rave=equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha25 | Rave=volume_equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=volume_equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=volume_equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=volume_equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=volume_equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=volume_equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=volume_equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha25 | Rave=height_equivalent_radius_mean_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_mean_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_mean_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_mean_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_mean_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_mean_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_mean_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha25 | Rave=height_equivalent_radius_p95_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_p95_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_p95_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_p95_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_p95_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_p95_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha25__radius=height_equivalent_radius_p95_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha50 | Rave=equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha50 | Rave=volume_equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=volume_equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=volume_equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=volume_equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=volume_equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=volume_equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=volume_equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha50 | Rave=height_equivalent_radius_mean_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_mean_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_mean_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_mean_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_mean_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_mean_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_mean_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha50 | Rave=height_equivalent_radius_p95_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_p95_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_p95_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_p95_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_p95_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_p95_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha50__radius=height_equivalent_radius_p95_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha75 | Rave=equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha75 | Rave=volume_equivalent_radius_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=volume_equivalent_radius_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=volume_equivalent_radius_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=volume_equivalent_radius_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=volume_equivalent_radius_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=volume_equivalent_radius_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=volume_equivalent_radius_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha75 | Rave=height_equivalent_radius_mean_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_mean_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_mean_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_mean_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_mean_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_mean_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_mean_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
set title 'effe=hybrid_alpha75 | Rave=height_equivalent_radius_p95_nm' font ',8'
plot \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_p95_nm/silver_nanoisland_10s.dat' using 1:5 with lines lw 1 title '10 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_p95_nm/silver_nanoisland_20s.dat' using 1:5 with lines lw 1 title '20 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_p95_nm/silver_nanoisland_30s.dat' using 1:5 with lines lw 1 title '30 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_p95_nm/silver_nanoisland_40s.dat' using 1:5 with lines lw 1 title '40 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_p95_nm/silver_nanoisland_50s.dat' using 1:5 with lines lw 1 title '50 s', \
  'data/output/proxy_matrix/effective_permittivity__effe=hybrid_alpha75__radius=height_equivalent_radius_p95_nm/silver_nanoisland_60s.dat' using 1:5 with lines lw 1 title '60 s'
unset multiplot
