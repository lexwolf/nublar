#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"
g++ -std=c++17 -Iinclude -Iextern/nano_geo_matrix/include -Iextern/nano_geo_matrix/modules/cup -I/usr/include/eigen3 src/getmax.cxx -o bin/gmax
clmn=2;
for i in `ls data/processed/convert/converted`; do
    times=`echo $i| tr -d -c 0-90-9`
    outp=`./bin/gmax data/processed/convert/converted/$i $clmn`
    echo $times $outp
done
