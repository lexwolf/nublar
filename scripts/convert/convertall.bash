#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"
for i in `ls data/processed/convert/original`; do
    bash scripts/convert/convert.bash "data/processed/convert/original/$i" "data/processed/convert/converted/${i%.*}.dat"
done
