# JSON Transmittance Migration Note

Old transmittance workflows used:

```text
AFM-derived table -> model_input.dat -> bin/transmittance [physics flags]
```

The new workflow is:

```text
AFM-derived summaries or a hand-written template -> solver JSON -> bin/transmittance
```

## Direct Solver Runs

Old:

```bash
./bin/transmittance data/input/experimental/model_input.dat 0 1100000 1 1 1
```

New:

```bash
./bin/transmittance data/input/sample.json --output data/output/transmittance/sample.dat
```

The solver no longer accepts physics override flags such as model, geometry, filling fraction, or thickness. Edit the JSON file instead.

## AFM-Derived Runs

Old:

```bash
python3 tools/experimental/build_experimental_input.py ...
./bin/transmittance data/input/experimental/model_input.dat ...
```

New:

```bash
python3 tools/experimental/build_transmittance_models.py ...
./bin/transmittance data/input/experimental/transmittance_models/20s.json \
  --output data/output/transmittance/silver_nanoisland_20s.dat
```

For the full comparison workflow, continue using:

```bash
bash scripts/bash/run_transmittance_pipeline.sh
```

That script now generates JSON models and preserves the previous calculated spectrum filenames where practical.

## Sweeps

Old sweep scripts passed override flags to the solver.

New sweep scripts start from a JSON template, edit fields such as:

- `stack.layers[].thickness_nm`
- `stack.layers[].effective_medium.model`
- `stack.layers[].effective_medium.geometry`
- `stack.layers[].effective_medium.filling_fraction`
- MMGM distribution fields

Then they run:

```bash
./bin/transmittance model.json --output spectrum.dat
```
