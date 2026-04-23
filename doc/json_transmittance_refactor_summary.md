# JSON Transmittance Refactor Summary

The transmittance solver now treats a JSON model file as its only physics input.

## What Changed

- `bin/transmittance` reads `data/input/sample.json` by default, or a JSON path passed as its positional argument.
- The only non-diagnostic solver option is `--output PATH`.
- Physics choices that used to be command-line arguments are now JSON fields:
  - wavelength grid
  - stack media and layer order
  - layer thicknesses
  - coherent/incoherent layer treatment
  - effective-medium model
  - effective-medium geometry
  - filling fraction
  - MMGM radius distribution parameters
- `model_input.dat` is no longer used by the transmittance solver.
- `tools/experimental/build_transmittance_models.py` builds solver-facing JSON files directly from AFM-derived morphology summaries.
- `scripts/bash/run_transmittance_pipeline.sh` now runs:

```text
AFM summaries -> JSON model files -> bin/transmittance -> comparison manifest/plot
```

## Solver Schema

The canonical example is:

```text
data/input/sample.json
```

The supported effective-medium models are:

- `mg`
- `bruggeman`
- `mmgm`

For `mmgm`, the JSON must explicitly include a `distribution` object with type `lognormal` or `two_lognormal`.

`rave_nm` is still required for MMGM because the current MMGM integration uses it as the radius scale for the integration step, radius cutoff, and prefactor.

## Current Stack Contract

The parser accepts a stack definition, but the numerical treatment intentionally preserves the existing physics:

```text
air | coherent front stack | incoherent glass substrate | air
```

The current implementation requires exactly one effective-medium layer and exactly one incoherent dielectric substrate layer.
