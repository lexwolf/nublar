#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"
NGM_ROOT="$(realpath "${ROOT_DIR}/extern/nano_geo_matrix")"
NGM_INC="${NGM_ROOT}/include"
NGM_CUP="${NGM_ROOT}/modules/cup"
g++ -std=c++17 -Iinclude -I"${NGM_INC}" -I"${NGM_CUP}" -I/usr/include/eigen3 src/getmax.cxx -o bin/gmax
clmn=2;
for i in `ls data/processed/convert/converted`; do
    times=`echo $i| tr -d -c 0-90-9`
    outp=`./bin/gmax data/processed/convert/converted/$i $clmn`
    echo $times $outp
done
