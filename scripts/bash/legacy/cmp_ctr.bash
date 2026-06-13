#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$ROOT_DIR"
bash scripts/bash/effe.bash    > data/output/effe.dat
bash scripts/bash/readata.bash > data/output/expe.dat
