#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"

# -----------------------
# Defaults
# -----------------------
compile=false
steps=5
thickness=10.0
d1=0    # first-step cumulative thickness (0 -> auto th/n)
alpha=1.0
sigma_geo=1.20
sigma_law="gauss"
sg_min=1.20
sg_peak=1.60
sg_mu=0
sg_w=0
packing_beta=0.0
f0=0.133
sigma_growth=true
zero_flag=false
f_zero=0.133

summary="data/output/summary_ds.dat"
mapping="data/output/mapping_ds.dat"

# --- Verbose subroutine logging ---
verbose_output=false
subroutine_logdir="data/output/subroutine_log"

# -----------------------
# Usage function
# -----------------------
show_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -c,  --compile              Compile mie, getmax, getenz (default: no)"
    echo "  -n,  --steps N              Number of deposition steps (default: 5)"
    echo "  -t,  --thickness VAL        Final thickness d_infty in nm (default: 10)"
    echo "       --d1 VAL               First-step cumulative thickness d(1) in nm (default: auto = th/n)"
    echo "       --alpha VAL            Alpha in d = Rave + alpha*sigma_nm (default: 1.0)"
    echo "  -sg, --sigma-geo VAL        Baseline geometric sigma (default: 1.20)"
    echo "       --sigma-law LAW        const | linear | gauss  (default: gauss)"
    echo "       --sg-min VAL           Min geometric sigma for law (default: 1.20)"
    echo "       --sg-peak VAL          Peak geometric sigma for law (default: 1.60)"
    echo "       --sg-mu VAL            Center (in steps) for gauss (0=mid) (default: 0)"
    echo "       --sg-w VAL             Width (in steps) for gauss (0=steps/4) (default: 0)"
    echo "       --packing-beta VAL     Packing penalty in f(sg) (default: 0.0 -> off)"
    echo "       --f0 VAL               Baseline f for MGM branch (default: 0.133)"
    echo "  -ns, --no-sigma-growth      Legacy switch (ignored if --sigma-law provided)"
    echo "  -z,  --zero                 MG baseline: ignore R, σ; use constant f"
    echo "  -zf VAL                     MG baseline filling fraction (default: 0.133)"
    echo "  -vb, --verbose-output       Enable subroutine debug output (writes plottable .dat files)"
    echo "  -so, --subroutine-output    Alias for --verbose-output"
    exit 1
}

# -----------------------
# Parse arguments
# -----------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--compile) compile=true ;;
        -n|--steps) steps=$2; shift ;;
        -t|--thickness) thickness=$2; shift ;;
        --d1) d1=$2; shift ;;
        --alpha) alpha=$2; shift ;;
        -sg|--sigma-geo) sigma_geo=$2; shift ;;
        --sigma-law) sigma_law=$2; shift ;;
        --sg-min) sg_min=$2; shift ;;
        --sg-peak) sg_peak=$2; shift ;;
        --sg-mu) sg_mu=$2; shift ;;
        --sg-w) sg_w=$2; shift ;;
        --packing-beta) packing_beta=$2; shift ;;
        --f0) f0=$2; shift ;;
        -ns|--no-sigma-growth) sigma_growth=false ;;  # kept for compatibility
        -z|--zero) zero_flag=true ;;
        -zf) f_zero=$2; shift ;;
        -vb|--verbose-output|-so|--subroutine-output) verbose_output=true ;;
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
    g++ -std=c++17 -Wall -Iinclude -L/usr/local/lib src/mie.cxx -o bin/mie -lcomplex_bessel
    g++ -std=c++17 -Iinclude src/getmax.cxx -o bin/getmax
    g++ -std=c++17 -Iinclude src/getenz.cxx -o bin/getenz
fi

# -----------------------
# Column selection
# -----------------------
if $zero_flag; then
    col_re=4   # Re(ε_MG)
    col_im=5   # Im(ε_MG)
    echo "> Using baseline Maxwell Garnett (Re=col $col_re, Im=col $col_im, f=$f_zero)"
else
    col_re=2   # Re(ε_eff)
    col_im=3   # Im(ε_eff)
    echo "> Using MGM model (Re=col $col_re, Im=col $col_im)"
fi

# -----------------------
# Sanity checks
# -----------------------
if (( $(echo "$sg_min <= 0" | bc -l) )); then
    echo "Error: --sg-min must be > 0 (got $sg_min)"
    exit 1
fi

if (( $(echo "$sg_peak <= 0" | bc -l) )); then
    echo "Error: --sg-peak must be > 0 (got $sg_peak)"
    exit 1
fi

if (( $(echo "$sg_min >= $sg_peak" | bc -l) )); then
    echo "Error: --sg-min ($sg_min) must be smaller than --sg-peak ($sg_peak)"
    exit 1
fi
# Steps sanity
if (( $steps < 1 )); then
    echo "Error: --steps must be >= 1 (got $steps)"; exit 1
fi
# d1 sanity (if set)
if (( $(echo "$d1 != 0" | bc -l) )); then
    if (( $(echo "$d1 <= 0" | bc -l) )); then
        echo "Error: --d1 must be > 0 (got $d1)"; exit 1
    fi
    if (( $(echo "$d1 >= $thickness" | bc -l) )) && (( $steps > 1 )); then
        echo "Error: --d1 ($d1) must be < thickness ($thickness) when steps > 1"; exit 1
    fi
fi

# -----------------------
# Prepare files
# -----------------------
if $verbose_output; then
    mkdir -p "$subroutine_logdir"
    rm -f "$subroutine_logdir"/*.dat
fi

mkdir -p data/output img
echo "# ds d[nm] Rave[nm] sigma_geo sigma_nm[nm] f lam_max[nm] ENZ1[nm] ENZ2[nm]" > "$summary"
echo "# file ds d[nm] Rave[nm] sigma_geo sigma_nm[nm] f" > "$mapping"

# -----------------------
# Helper: sigma_geo(ds)
# -----------------------
sigma_geo_of_ds() {
    local ds=$1
    local n=$2
    local law=$3
    local sg

    case "$law" in
        const)
            sg="$sg_min"
            ;;
        linear)
            sg=$(awk -v sgmin=$sg_min -v sgp=$sg_peak -v ds=$ds -v n=$n \
                'BEGIN{ if(n<=1){print sgmin}else{print sgmin + (sgp-sgmin)*(ds-1)/(n-1)} }')
            ;;
        gauss)
            local mu=$sg_mu
            local w=$sg_w
            if [[ "$mu" == "0" ]]; then
                mu=$(awk -v n=$n 'BEGIN{print (n+1)/2.0}')
            fi
            if [[ "$w" == "0" ]]; then
                w=$(awk -v n=$n 'BEGIN{print (n/4.0>1?n/4.0:1.0)}')
            fi
            sg=$(awk -v sgmin=$sg_min -v sgp=$sg_peak -v ds=$ds -v mu=$mu -v w=$w \
                'BEGIN{
                    amp = (sgp - sgmin);
                    val = sgmin + amp*exp(- (ds-mu)^2 / (2*w*w));
                    printf "%.3f", val
                }')
            ;;
        *)
            sg=$(awk -v sgmin=$sg_min -v sg=$sigma_geo -v ds=$ds -v n=$n \
                'BEGIN{ if(n<=1){print sgmin}else{print sgmin + (sg*1.0)*(ds-1)/(n-1)} }')
            ;;
    esac

    if $verbose_output; then
        echo "$ds $sg" >> "${subroutine_logdir}/sigma_geo_of_ds.dat"
    fi

    echo "$sg"
}

# -----------------------
# Sweep deposition steps
# -----------------------
k_ref=""
for ds in $(seq 1 $steps); do
    # Cumulative thickness d(ds)
    if (( $steps == 1 )); then
        d=$(awk -v th=$thickness 'BEGIN{printf "%.2f", th}')
    else
        if (( $(echo "$d1 == 0" | bc -l) )); then
            # default linear: th*ds/n
            d=$(awk -v th=$thickness -v ds=$ds -v n=$steps 'BEGIN{printf "%.2f", th*ds/n}')
        else
            # custom first-step thickness: linear from d1 at ds=1 to th at ds=n
            d=$(awk -v d1=$d1 -v th=$thickness -v ds=$ds -v n=$steps \
                'BEGIN{printf "%.2f", d1 + (th - d1)*(ds-1)/(n-1)}')
        fi
    fi

    if $zero_flag; then
        Rave=0.0; sg_now=$sigma_geo; sigma_nm=0.0; f=$f_zero
    else
        sg_now=$(sigma_geo_of_ds "$ds" "$steps" "$sigma_law")

        k=$(awk -v sg=$sg_now 'BEGIN{ l=log(sg); printf "%.8f", sqrt(exp(l*l)-1.0) }')

        Rave=$(awk -v d=$d -v a=$alpha -v k=$k 'BEGIN{printf "%.2f", d/(1.0 + a*k)}')
        sigma_nm=$(awk -v R=$Rave -v k=$k 'BEGIN{printf "%.2f", R*k}')

        if [ -z "$k_ref" ]; then k_ref="$k"; fi

        f=$(awk -v f0=$f0 -v a=$alpha -v k=$k -v kr=$k_ref -v beta=$packing_beta -v sg=$sg_now '
             BEGIN{
               fgeom = (1.0 + a*kr)/(1.0 + a*k);
               fpen  = 1.0/(1.0 + beta*(sg-1.0)^2);
               printf "%.3f", f0 * fgeom * fpen;
             }')
    fi

    echo "> ds=$ds d=$d Rave=$Rave sigma_geo=$sg_now sigma_nm=$sigma_nm f=$f"

    if $zero_flag; then
        outfile=$(./bin/mie 0 $f lognormal -pf)
    else
        outfile=$(./bin/mie $Rave $f lognormal -sg $sg_now -pf)
    fi

    echo "$outfile $ds $d $Rave $sg_now $sigma_nm $f" >> "$mapping"

    if [ -f "$outfile" ]; then
        maxfile="${outfile}.results"
        lam_max=$(./bin/getmax "$outfile" $col_im | awk '{print $1; exit}')
        enz_pos=$(./bin/getenz "$outfile" $col_re | xargs)

        {
            echo "# ds d[nm] Rave[nm] sigma_geo sigma_nm[nm] f lam_max[nm] ENZ1[nm] ENZ2[nm]"
            echo "$ds $d $Rave $sg_now $sigma_nm $f $lam_max $enz_pos"
        } > "$maxfile"

        echo "$ds $d $Rave $sg_now $sigma_nm $f $lam_max $enz_pos" >> "$summary"
        echo "  -> Results saved in $maxfile"
    else
        echo "  !! Output file $outfile not found"
    fi
done

# -----------------------
# Plot image (single png)
# -----------------------
imgdir="img"
mkdir -p "$imgdir"
pngfile="${imgdir}/deposition.png"
if $zero_flag; then
    pngfile="${imgdir}/deposition_MG.png"
fi

plotfile="scripts/gnuplot/plot_results_ds.gp"

{
cat <<EOF
set terminal pngcairo size 1200,800 enhanced font "Helvetica,14"
set output "$pngfile"

set multiplot layout 2,2 title "Effective permittivity vs deposition step"
EOF

# Panel (a): Re(eps)
echo 'set title "(a)"'
echo 'set xlabel "Wavelength (nm)"'
echo 'set ylabel "Re(ε)"'
echo 'set key right bottom'
echo -n "plot [300:900]"
awk -v col=$col_re 'NR>1 {if (c++) printf ",\\\n";
    printf "\"%s\" using 1:%d title \"step %s\" w l lw 2", $1,col,$2
}' "$mapping"
echo ""

# Panel (c): ε'' max and LE-ENZ
cat <<EOF
set title "(c)"
set xlabel "Deposition step"
set ylabel "Wavelength (nm)"
set key top left
plot "$summary" using 1:7 with linespoints lw 2 pt 5 title "ε'' max", \
     "$summary" using 1:8 with linespoints lw 2 pt 7 title "LE-ENZ"
EOF

# Panel (b): Im(eps)
echo 'set title "(b)"'
echo 'set xlabel "Wavelength (nm)"'
echo 'set ylabel "Im(ε)"'
echo 'set key right top'
echo -n "plot [300:900]"
awk -v col=$col_im 'NR>1 {if (c++) printf ",\\\n";
    printf "\"%s\" using 1:%d title \"\" w l lw 2",
           $1,col,$2,$3,$4,$5,$7
}' "$mapping"
echo ""

# Panel (d): HE-ENZ
cat <<EOF
set title "(d)"
set xlabel "Deposition step"
set ylabel "ENZ wavelength (nm)"
plot "$summary" using 1:9 with linespoints lw 2 pt 6 lc rgb "blue" title "HE-ENZ"

unset multiplot
EOF
} > "$plotfile"

if command -v gnuplot &> /dev/null; then
    echo "> Generating plot with gnuplot..."
    gnuplot "$plotfile"
    echo "  -> Plot saved as $pngfile"
else
    echo "!! gnuplot not found, skipping plotting step."
fi

caption_file="data/output/caption.tex"
{
    echo "\\caption{"
    echo "Simulation of effective permittivity during silver nano-island deposition."
    echo " Curves correspond to deposition steps (step 1 … step $steps)."
    echo " Parameters: final thickness $thickness nm,"
    if (( $(echo "$d1 > 0" | bc -l) )); then
        echo " first-step thickness $d1 nm,"
    fi
    echo " \\(\\alpha=$alpha\\), \\(f_0=$f0\\),"
    echo " sigma-law=$sigma_law, \\(\\sigma_{\\min}=$sg_min\\), \\(\\sigma_{\\mathrm{peak}}=$sg_peak\\)."
    echo " Detailed step-by-step values are reported in the summary.dat file."
    echo ""
    echo "Panels: (a) Real part of the effective permittivity (Re\\,(\\(\\varepsilon\\))) versus wavelength for each deposition step."
    echo " (b) Imaginary part of the effective permittivity (Im\\,(\\(\\varepsilon\\)))."
    echo " (c) Evolution of the wavelength corresponding to the maximum of Im\\,(\\(\\varepsilon\\)) (red points) and the low-energy ENZ crossing (blue points) as a function of deposition step."
    echo " (d) Evolution of the high-energy ENZ crossing as a function of deposition step."
    echo "}"
} > "$caption_file"

echo "> Caption written to $caption_file"
