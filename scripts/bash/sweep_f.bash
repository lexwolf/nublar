#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"
NGM_ROOT="$(realpath "${ROOT_DIR}/extern/nano_geo_matrix")"
NGM_INC="${NGM_ROOT}/include"
NGM_CUP="${NGM_ROOT}/modules/cup"

# -----------------------
# Defaults
# -----------------------
compile=false
range_min=0.1
range_max=1.0
density=5
square=2
thickness=12.0
saturation=true
zero_flag=false
sigma_geo=1.20   # default (Battie)

summary="data/output/summary.dat"
mapping="data/output/mapping.dat"

# -----------------------
# Usage function
# -----------------------
show_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -c, --compile           Compile mie, getmax, getenz (default: no)"
    echo "  -r, --range min max     Filling fraction range (default: 0.1 1.0)"
    echo "  -d, --density N         Number of steps (default: 5)"
    echo "  -s, --square N          Exponent for R(f) ~ f^(1/N) (default: 2)"
    echo "  -t, --thickness VAL     R_infty in nm (default: 12)"
    echo "  -ns, --no-saturation    Use pure power-law (disable saturation)"
    echo "  -z, --zero              Run naked Maxwell Garnett baseline (default: no)"
    echo "  -sg, --sigma-geo VAL    Geometric sigma for lognormal (default: 1.20)"
    exit 1
}

# -----------------------
# Parse arguments
# -----------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--compile) compile=true ;;
        -r|--range) range_min=$2; range_max=$3; shift 2 ;;
        -d|--density) density=$2; shift ;;
        -s|--square) square=$2; shift ;;
        -t|--thickness) thickness=$2; shift ;;
        -ns|--no-saturation) saturation=false ;;
        -z|--zero) zero_flag=true ;;
        -sg|--sigma-geo) sigma_geo=$2; shift ;;
        -h|--help) show_usage ;;
        *) echo "Unknown option $1"; show_usage ;;
    esac
    shift
done

# -----------------------
# Compile if requested
# -----------------------
if $compile; then
    echo "> Compiling codes..."
    g++ -std=c++17 -Wall -Iinclude -I"${NGM_INC}" -I"${NGM_CUP}" -I/usr/include/eigen3 -L/usr/local/lib src/mie.cxx -o bin/mie -lcomplex_bessel
    g++ -std=c++17 -Iinclude -I"${NGM_INC}" -I"${NGM_CUP}" -I/usr/include/eigen3 src/getmax.cxx -o bin/getmax
    g++ -std=c++17 -Iinclude -I"${NGM_INC}" -I"${NGM_CUP}" -I/usr/include/eigen3 src/getenz.cxx -o bin/getenz
fi

# -----------------------
# Column selection
# -----------------------
if $zero_flag; then
    col_re=4   # Re(ε_MG)
    col_im=5   # Im(ε_MG)
    echo "> Using baseline Maxwell Garnett (Re=col $col_re, Im=col $col_im)"
else
    col_re=2   # Re(ε_eff)
    col_im=3   # Im(ε_eff)
    echo "> Using MGM model (Re=col $col_re, Im=col $col_im)"
fi

echo "> Using sigma_geo = $sigma_geo"

# -----------------------
# Compute alpha for saturation
# -----------------------
alpha=4.0
step=$(awk -v rmin=$range_min -v rmax=$range_max -v dens=$density \
           'BEGIN{print (rmax-rmin)/(dens-1)}')

# -----------------------
# Prepare files
# -----------------------
mkdir -p data/output
echo "# step f Rave[nm] lam_max[nm] ENZ1[nm] ENZ2[nm]" > $summary
echo "# file Rave f" > $mapping

# -----------------------
# Sweep filling fraction
# -----------------------
stepid=1
for i in $(seq 0 $(($density-1))); do
    f=$(awk -v rmin=$range_min -v step=$step -v i=$i \
           'BEGIN{printf "%.3f", rmin + i*step}')

    if $saturation; then
        Rave=$(awk -v f=$f -v th=$thickness -v sq=$square -v al=$alpha \
            'BEGIN{printf "%.2f", th*(1 - exp(-al* (f^(1/sq))))}')
    else
        Rave=$(awk -v f=$f -v th=$thickness -v sq=$square \
            'BEGIN{printf "%.2f", th*(f^(1/sq))}')
    fi

    echo "> Running mie with f=$f Rave=$Rave"
    outfile=$(./bin/mie $Rave $f lognormal -sg $sigma_geo -pf)
    echo "$outfile $Rave $f" >> $mapping

    if [ -f "$outfile" ]; then
        maxfile="${outfile}.results"
        lam_max=$(./bin/getmax "$outfile" $col_im)
        enz_pos=$(./bin/getenz "$outfile" $col_re)

        {
            echo "# f Rave[nm] lam_max[nm] ENZs[nm]"
            echo "$f $Rave $lam_max $enz_pos"
        } > "$maxfile"

        echo "$stepid $f $Rave $lam_max $enz_pos" >> $summary
        echo "  -> Results saved in $maxfile"
    else
        echo "  !! Output file $outfile not found"
    fi

    stepid=$((stepid+1))
done

# -----------------------
# Prepare image output path
# -----------------------
imgdir="img/sigma_geo=${sigma_geo}"
mkdir -p "$imgdir"

if $zero_flag; then
    pngfile="img/0.png"
elif ! $saturation; then
    pngfile="${imgdir}/ns_N=${square}.png"
else
    pngfile="${imgdir}/N=${square}.png"
fi


plotfile="scripts/gnuplot/plot_results.gp"

# -----------------------
# Generate gnuplot script
# -----------------------
{
cat <<EOF
set terminal pngcairo size 1200,800 enhanced font "Helvetica,14"
set output "$pngfile"

set multiplot layout 2,2 title "Effective permittivity vs deposition (σ_{geo}=$sigma_geo)"
EOF

# Panel (a): Re(eps)
echo 'set title "(a)"'
echo 'set xlabel "Wavelength (nm)"'
echo 'set ylabel "Re(ε)"'
echo 'set key right bottom'
echo -n "plot [300:900]"
if $zero_flag; then
    awk -v col=$col_re 'NR>1 {if (c++) printf ",\\\n"; printf "\"%s\" using 1:%d title \"f=%s\" w l lw 2", $1,col,$3}' $mapping
else
    awk -v col=$col_re 'NR>1 {if (c++) printf ",\\\n"; printf "\"%s\" using 1:%d title \"<R> = %s nm  f=%s\" w l lw 2", $1,col,$2,$3}' $mapping
fi
echo ""

# Panel (c): ε'' max and LE-ENZ
cat <<EOF
set title "(c)"
set xlabel "Deposition step"
set ylabel "Wavelength (nm)"
set key top left
plot "$summary" using 1:4 with linespoints lw 2 pt 5 title "ε'' max", \
     "$summary" using 1:5 with linespoints lw 2 pt 7 title "LE-ENZ"
EOF

# Panel (b): Im(eps)
echo 'set title "(b)"'
echo 'set xlabel "Wavelength (nm)"'
echo 'set ylabel "Im(ε)"'
echo 'set key right top'
echo -n "plot [300:900]"
if $zero_flag; then
    awk -v col=$col_im 'NR>1 {if (c++) printf ",\\\n"; printf "\"%s\" using 1:%d title \"f=%s\" w l lw 2", $1,col,$3}' $mapping
else
    awk -v col=$col_im 'NR>1 {if (c++) printf ",\\\n"; printf "\"%s\" using 1:%d title \"<R> = %s nm  f=%s\" w l lw 2", $1,col,$2,$3}' $mapping
fi
echo ""

# Panel (d): HE-ENZ
cat <<EOF
set title "(d)"
set xlabel "Deposition step"
set ylabel "ENZ wavelength (nm)"
plot "$summary" using 1:6 with linespoints lw 2 pt 6 lc rgb "blue" title "HE-ENZ"

unset multiplot
EOF
} > $plotfile

# -----------------------
# Run gnuplot
# -----------------------
if command -v gnuplot &> /dev/null; then
    echo "> Generating plot with gnuplot..."
    gnuplot $plotfile
    echo "  -> Plot saved as $pngfile"
else
    echo "!! gnuplot not found, skipping plotting step."
fi


# -----------------------
# Compile if requested
# -----------------------
if $compile; then
    echo "> Compiling codes..."
    g++ -std=c++17 -Wall -Iinclude -I"${NGM_INC}" -I"${NGM_CUP}" -I/usr/include/eigen3 -L/usr/local/lib src/mie.cxx -o bin/mie -lcomplex_bessel
    g++ -std=c++17 -Iinclude -I"${NGM_INC}" -I"${NGM_CUP}" -I/usr/include/eigen3 src/getmax.cxx -o bin/getmax
    g++ -std=c++17 -Iinclude -I"${NGM_INC}" -I"${NGM_CUP}" -I/usr/include/eigen3 src/getenz.cxx -o bin/getenz
fi

# -----------------------
# Column selection
# -----------------------
if $zero_flag; then
    col_re=4   # Re(ε_MG)
    col_im=5   # Im(ε_MG)
    echo "> Using baseline Maxwell Garnett (Re=col $col_re, Im=col $col_im)"
else
    col_re=2   # Re(ε_eff)
    col_im=3   # Im(ε_eff)
    echo "> Using MGM model (Re=col $col_re, Im=col $col_im)"
fi

# -----------------------
# Compute alpha for saturation
# -----------------------
alpha=4.0
step=$(awk -v rmin=$range_min -v rmax=$range_max -v dens=$density \
           'BEGIN{print (rmax-rmin)/(dens-1)}')

# -----------------------
# Prepare files
# -----------------------
mkdir -p data/output
echo "# step f Rave[nm] lam_max[nm] ENZ1[nm] ENZ2[nm]" > $summary
echo "# file Rave f" > $mapping

# -----------------------
# Sweep filling fraction
# -----------------------
stepid=1
for i in $(seq 0 $(($density-1))); do
    f=$(awk -v rmin=$range_min -v step=$step -v i=$i \
           'BEGIN{printf "%.3f", rmin + i*step}')

    if $saturation; then
        Rave=$(awk -v f=$f -v th=$thickness -v sq=$square -v al=$alpha \
            'BEGIN{printf "%.2f", th*(1 - exp(-al* (f^(1/sq))))}')
    else
        Rave=$(awk -v f=$f -v th=$thickness -v sq=$square \
            'BEGIN{printf "%.2f", th*(f^(1/sq))}')
    fi

    echo "> Running mie with f=$f Rave=$Rave"
    outfile=$(./bin/mie $Rave $f lognormal -pf)
    echo "$outfile $Rave $f" >> $mapping

    if [ -f "$outfile" ]; then
        maxfile="${outfile}.results"
        lam_max=$(./bin/getmax "$outfile" $col_im)
        enz_pos=$(./bin/getenz "$outfile" $col_re)

        {
            echo "# f Rave[nm] lam_max[nm] ENZs[nm]"
            echo "$f $Rave $lam_max $enz_pos"
        } > "$maxfile"

        echo "$stepid $f $Rave $lam_max $enz_pos" >> $summary
        echo "  -> Results saved in $maxfile"
    else
        echo "  !! Output file $outfile not found"
    fi

    stepid=$((stepid+1))
done

# -----------------------
# Generate gnuplot script
# -----------------------
plotfile="scripts/gnuplot/plot_results.gp"
pngfile="img/comparison.png"

{
cat <<EOF
set terminal pngcairo size 1200,800 enhanced font "Helvetica,14"
set output "$pngfile"

set multiplot layout 2,2 title "Effective permittivity vs deposition"
EOF

# Panel (a): Re(eps)
echo 'set title "(a)"'
echo 'set xlabel "Wavelength (nm)"'
echo 'set ylabel "Re(ε)"'
echo 'set key right bottom'
echo -n "plot [300:900]"
if $zero_flag; then
    awk -v col=$col_re 'NR>1 {
        if (c++) printf ",\\\n";
        printf "\"%s\" using 1:%d title \"f=%s\" w l lw 2", $1,col,$3
    }' $mapping
else
    awk -v col=$col_re 'NR>1 {
        if (c++) printf ",\\\n";
        printf "\"%s\" using 1:%d title \"<R> = %s nm  f=%s\" w l lw 2", $1,col,$2,$3
    }' $mapping
fi
echo ""

# Panel (c): ε'' max and LE-ENZ
cat <<EOF
set title "(c)"
set xlabel "Deposition step"
set ylabel "Wavelength (nm)"
set key top left
plot "$summary" using 1:4 with linespoints lw 2 pt 5 title "ε'' max", \
     "$summary" using 1:5 with linespoints lw 2 pt 7 title "LE-ENZ"
EOF

# Panel (b): Im(eps)
echo 'set title "(b)"'
echo 'set xlabel "Wavelength (nm)"'
echo 'set ylabel "Im(ε)"'
echo 'set key right top'
echo -n "plot [300:900]"
if $zero_flag; then
    awk -v col=$col_im 'NR>1 {
        if (c++) printf ",\\\n";
        printf "\"%s\" using 1:%d title \"f=%s\" w l lw 2", $1,col,$3
    }' $mapping
else
    awk -v col=$col_im 'NR>1 {
        if (c++) printf ",\\\n";
        printf "\"%s\" using 1:%d title \"<R> = %s nm  f=%s\" w l lw 2", $1,col,$2,$3
    }' $mapping
fi
echo ""

# Panel (d): HE-ENZ
cat <<EOF
set title "(d)"
set xlabel "Deposition step"
set ylabel "ENZ wavelength (nm)"
plot "$summary" using 1:6 with linespoints lw 2 pt 6 lc rgb "blue" title "HE-ENZ"

unset multiplot
EOF
} > $plotfile

# -----------------------
# Run gnuplot
# -----------------------
if command -v gnuplot &> /dev/null; then
    echo "> Generating plot with gnuplot..."
    gnuplot $plotfile
    echo "  -> Plot saved as $pngfile"
else
    echo "!! gnuplot not found, skipping plotting step."
fi
