# Path Repair and Validation Report

## Files changed

- `Makefile`
- `src/mie.cxx`
- `src/clausius-mossotti.cxx`
- `scripts/bash/10-30.bash`
- `scripts/bash/cmp_ctr.bash`
- `scripts/bash/compare.bash`
- `scripts/bash/effe.bash`
- `scripts/bash/readata.bash`
- `scripts/bash/sweep_ds.bash`
- `scripts/bash/sweep_f.bash`
- `scripts/convert/convert.bash`
- `scripts/convert/convertall.bash`

## Old-path assumptions repaired

- Script execution from non-root directory:
  - Added `SCRIPT_DIR` / `ROOT_DIR` resolution and `cd "$ROOT_DIR"` in bash and convert scripts.
- Binary/source/header path assumptions in script-side compile commands:
  - Added `-Iinclude` and `-std=c++17`.
  - Kept compile outputs in `bin/` and sources in `src/`.
- Runtime file paths inside C++ executables:
  - `mie` and `cm` now resolve project root from executable path and use absolute paths to `data/input/` and `data/output/`.
- Output folder preconditions:
  - `scripts/bash/effe.bash` now ensures `data/output/effe/` exists.
- Legacy relative output target in `sweep_f.bash` second plotting block:
  - `comparison.png` -> `img/comparison.png`.

## Static inspection highlights

Searched for legacy assumptions:

- `./cm`, `./genz`, `./getenz`, `./getmax`, `./gmax`, `./mie`
- `headers/`, `in/`, `out/`, `Experiments/`

No active old layout references remain in executable code paths.
Remaining `convert/` matches refer to the valid new path `data/processed/convert/` and `scripts/convert/`.

## Validation results

### Build

- `make -B` succeeded.
- Rebuilt binaries: `bin/mie`, `bin/getmax`, `bin/getenz`, `bin/cm`, plus aliases `bin/gmax`, `bin/genz`.

### Script smoke checks

- From outside repo root (`/tmp`):
  - `bash /.../scripts/bash/sweep_f.bash -h` -> OK
  - `bash /.../scripts/bash/sweep_ds.bash -h` -> OK
  - `bash /.../scripts/bash/10-30.bash` (usage path) -> OK
  - `bash /.../scripts/bash/compare.bash` (usage path) -> OK
  - `bash /.../scripts/convert/convertall.bash` -> OK
  - `bash /.../scripts/bash/readata.bash` -> OK (pipeline truncated output caused expected broken-pipe warnings when piped to `head` during test)

### Binary smoke checks

- From `/tmp`:
  - `/.../bin/mie 1.00 0.123 lognormal -sg 1.20 -pf` -> OK
  - `/.../bin/getmax /.../data/output/Rave=1.00__f=0.123__lognormal__sg=1.20.dat 3` -> OK

## Remaining issues

- `scripts/bash/sweep_f.bash` contains duplicated workflow blocks (pre-existing). Path handling is repaired, but duplicated execution remains and can rerun work in a single invocation.
- Standalone direct invocation of static gnuplot files still assumes project-root working directory; main bash workflows now enforce root before calling gnuplot.
