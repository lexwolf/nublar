#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"
g++ -std=c++17 -Iinclude src/clausius-mossotti.cxx -lgsl -o bin/cm

is_number() {
    # Use regular expression to match the number pattern
    if [[ $1 =~ ^[+-]?[0-9]+([.][0-9]+)?$ ]]; then
        return 0 # Return success (0) if it's a number
    else
        return 1 # Return failure (non-zero) if it's not a number
    fi
}

if [ "$2" == "" ]; then
    echo "> Usage "$0" <datafile> <filling fraction>"
    exit
fi


if is_number "$2"; then
    echo "> comparing the deposition time "$times" seconds with a filling fraction f = "$2
    echo "300" "1000" $2 > "data/input/islas.dat"
    ./bin/cm
    cp "data/output/nublar.dat" "data/output/clausius-mossotti.dat"
    cp $1 "data/output/experimental.dat"
else
   echo "> Error: filling fraction must be a number"; 
   exit
fi
