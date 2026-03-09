#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"

# Function to show usage
show_usage() {
    echo "Usage: $0 [-c] Rave"
    exit 1
}

# Check for the correct number of arguments
if [ $# -lt 1 ]; then
    show_usage
fi

# Parse command line options
while getopts ":c" opt; do
    case ${opt} in
        c )
            compile=true
            ;;
        \? )
            show_usage
            ;;
    esac
done
shift $((OPTIND -1))

# Check if Rave is provided
if [ -z "$1" ]; then
    show_usage
fi

Rave=$1

# Compile the code if -c flag is given
if [ "$compile" = true ]; then
    g++ -std=c++17 -Wall -Iinclude -L/usr/local/lib src/mie.cxx -o bin/mie -lcomplex_bessel
fi

# Loop from 0.1 to 0.3 in increments of 0.1
for effe in $(seq 0.1 0.1 0.3); do
    ./bin/mie $Rave $effe
done

script="scripts/gnuplot/effe_Rave=$Rave.gp"

# Create the Gnuplot script
cat <<EOL > $script
reset

set term pdf color enhanced size 15cm,8cm;
sz=1.
set size sz

set output "img/10-30_Rave=${Rave}.pdf"

set label 1 at screen 0.45, screen 0.95 "R_{ave} = ${Rave} nm"
set multiplot layout 1, 2
set tmargin at screen 0.88
set ylabel "Distribution of Probability"
set xlabel "Nanoparticle radius (nm)"
plot[:100][0:1] "data/output/Maxwell-Boltzmann__Rave=${Rave}.00.dat" w l lw 2 lc rgb "dark-red" t ""
unset label 1
set ylabel "Effective Permittivity"
set xlabel "Wavelength (nm)"
plot[300:900] "data/output/Rave=${Rave}.00__f=0.100.dat" w l lw 2 t "f = 0.1",  "data/output/Rave=${Rave}.00__f=0.200.dat" w l lw 2 t "f = 0.2",  "data/output/Rave=${Rave}.00__f=0.300.dat" w l lw 2 t "f = 0.3";
unset multiplot
unset output
EOL
