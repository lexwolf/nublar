# nublar

`nublar` is a scientific project for effective-medium / Mie-based optical simulations of silver nano-island deposition, with scripts to sweep filling fraction or deposition-step scenarios and generate analysis plots.

## Repository layout

- `src/`: C++ simulation and analysis code.
- `include/`: project headers.
- `bin/`: compiled executables (`mie`, `getmax`, `getenz`, `cm`, aliases).
- `scripts/bash/`: orchestration and workflow scripts.
- `scripts/gnuplot/`: hand-written plotting scripts plus generated gnuplot files under mirrored subdirectories such as `scripts/gnuplot/output/` and `scripts/gnuplot/experimental/`.
- `scripts/convert/`: conversion utilities for imported data.
- `data/input/`: stable model input files.
- `data/output/`: generated spectra, summaries, mapping files, and intermediate results.
- `data/processed/convert/`: conversion dataset split into `original/` and `converted/`.
- `data/experimental/`: experimental material split into `raw/`, `processed/`, and `reports/`.
- `img/`: generated figures and static visual assets, mirrored by data domain when outputs are produced from tooling.
- `doc/`: papers, notes, and archived references.

## Build

Use the root Makefile:

```bash
make
```

This builds executables in `bin/`.

## Main runs

Sweep deposition by filling fraction:

```bash
bash scripts/bash/sweep_f.bash -c -r 0.1 0.35 -d 5
```

Sweep by deposition steps:

```bash
bash scripts/bash/sweep_ds.bash -c -n 5 -t 10
```

Compare Clausius-Mossotti with external experimental data:

```bash
bash scripts/bash/compare.bash <path-to-experimental-file> <filling-fraction>
```

## Data locations

- Input parameters/material tables: `data/input/`
- Numerical outputs: `data/output/`
- Legacy workflow figures: `img/output/`
- Legacy workflow generated gnuplot scripts: `scripts/gnuplot/output/`
- Imported + converted helper datasets: `data/processed/convert/`
- Experimental provenance:
  - raw AFM files: `data/experimental/raw/afm/`
  - generated AFM tables: `data/experimental/final/` and `data/experimental/intermediate/...`
  - generated AFM figures: `img/experimental/final/`, `img/experimental/intermediate/...`, and `img/experimental/afm/`
  - generated AFM gnuplot scripts: `scripts/gnuplot/experimental/final/`
  - processed distributions/transmittance: `data/experimental/processed/`
  - report documents: `data/experimental/reports/`

## Submodule setup

This repository uses `extern/nano_geo_matrix` as a git submodule.

After cloning, run:

```bash
git submodule update --init --recursive
```
