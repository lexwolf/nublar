# Migration Report

## Classification choices

- C++ source moved to `src/`.
- Headers moved to `include/`.
- ELF executables moved to `bin/`.
- Bash and gnuplot scripts moved to `scripts/bash/` and `scripts/gnuplot/`.
- Conversion scripts moved to `scripts/convert/`.
- Stable simulation inputs moved to `data/input/`.
- Generated numerical outputs moved to `data/output/`.
- Conversion datasets split into:
  - `data/processed/convert/original/`
  - `data/processed/convert/converted/`
- Experimental materials moved from `Experiments/` to:
  - `data/experimental/raw/afm/`
  - `data/experimental/processed/distributions/`
  - `data/experimental/processed/transmittance/`
  - `data/experimental/reports/`
- Existing `doc/` and `img/` retained and normalized.

## Ambiguous files and conservative handling

- `bin/genz` and `bin/getenz` are duplicate binaries; both kept.
- `bin/gmax` and `bin/getmax` are duplicate binaries; both kept.
- `img/sigma_geo=/N=2.png` has a non-standard path component but was preserved unchanged.
- `doc/used_stuff/isnum.bash` appears archival; kept in `doc/used_stuff/`.

## Updated path references

Updated references in:

- `src/*.cxx`
- `scripts/bash/*.bash`
- `scripts/gnuplot/*.gp`
- `scripts/convert/*.bash`
- `doc/Nublar_Cheatsheet.md`

Main path rewrites:

- `headers/` -> `include/`
- `in/` -> `data/input/`
- `out/` -> `data/output/`
- local executable calls (`./mie`, `./getmax`, `./getenz`, `./cm`, `./gmax`) -> `./bin/...`

## Remaining issues

- Build requires external libraries (`complex_bessel` and `gsl`) in the local system.
- Legacy scripts with duplicated logic (`scripts/bash/sweep_f.bash`) were not behaviorally rewritten to avoid changing scientific workflow.

## Folder-level move summary

- `*.cxx`: root -> `src/`
- `headers/*`: -> `include/`
- root executables (`cm`, `genz`, `getenz`, `getmax`, `gmax`, `mie`): -> `bin/`
- root `.bash`: -> `scripts/bash/`
- root `.gp`: -> `scripts/gnuplot/`
- `in/*`: -> `data/input/`
- `out/*`: -> `data/output/`
- `convert/convert*.bash`: -> `scripts/convert/`
- `convert/original/*`: -> `data/processed/convert/original/`
- `convert/data/*`: -> `data/processed/convert/converted/`
- `Experiments/NIs Ag/AFM_datigrezzi/*`: -> `data/experimental/raw/afm/`
- `Experiments/NIs Ag/Distribution of NIs/Height/*`: -> `data/experimental/processed/distributions/`
- `Experiments/NIs Ag/Trasmittanze/*`: -> `data/experimental/processed/transmittance/`
- `Experiments/NIs Ag/report nanoisole.docx`: -> `data/experimental/reports/`
