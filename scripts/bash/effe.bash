#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BIN_CM="${ROOT_DIR}/bin/cm"
INPUT_FILE="${ROOT_DIR}/data/input/islas.dat"
OUTPUT_DIR="${ROOT_DIR}/data/output/effe"
TEMP_OUTPUT="${ROOT_DIR}/data/output/nublar.dat"

g++ -std=c++17 -I"${ROOT_DIR}/include" -I"${ROOT_DIR}/extern/nano_geo_matrix/include" -I"${ROOT_DIR}/extern/nano_geo_matrix/modules/cup" -I/usr/include/eigen3 "${ROOT_DIR}/src/clausius-mossotti.cxx" -lgsl -o "${BIN_CM}"
rm -f "${OUTPUT_DIR}"/*
mkdir -p "${OUTPUT_DIR}"
# effemin=0.577;
effemin=0.0;
effemax=0.3;

deffe=`echo "($effemax-$effemin)/9"|bc -l`;
for i in {0..9}; do 
    effe=`echo "$effemin+$i*$deffe"| bc -l`
    echo "300" "1000" $effe > "${INPUT_FILE}"
    outp=`"${BIN_CM}"`
    echo $effe $outp
    mv "${TEMP_OUTPUT}" "${OUTPUT_DIR}/$i.dat"
done
