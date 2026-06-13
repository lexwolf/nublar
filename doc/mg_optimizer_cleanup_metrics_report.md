# MG Optimizer Cleanup and Metrics Report

This report summarizes the changes made to the first-version `mg` transmittance optimizer during the cleanup/robustness pass and the follow-up metrics upgrade.

## Scope

The changes were intentionally limited to the existing `mg` optimizer path:

- `tools/optimal/optimize_model_parameters.py`
- `tools/optimal/model/mg_lib.py`
- `data/input/optimal/bounds.json`

No new effective-medium models, optimizer algorithms, CLI options, directory layouts, plotting styles, or forward-solver invocation patterns were introduced.

## Cleanup and Robustness Changes

### Configuration-Driven Grid Size

The previous hidden safeguard that silently reduced large grid sizes inside `mg_lib.read_bounds()` was removed.

The optimizer now reads the v1 grid size explicitly from:

```json
"grid": {
  "v1_effe_points": 9,
  "v1_thickness_points": 9,
  "effe_points": 120,
  "thickness_points": 120
}
```

Behavior is now:

- use `v1_effe_points` and `v1_thickness_points` when present;
- otherwise fall back to `effe_points` and `thickness_points`;
- never silently cap or override the configured grid.

This makes the current coarse `9 x 9` v1 scan explicit and reproducible.

### Wavelength Grid Compatibility

A helper was added:

```python
grids_compatible(g1, g2, tol=1e-6)
```

It compares wavelength-grid minimum, maximum, step, and number of points with a small numerical tolerance. This replaced fragile exact tuple comparison in the orchestration layer and the previous hard-coded strict wavelength check in the objective evaluation.

The `60s` spectrum remains skipped because its grid is materially different from the regular spectra:

```text
(200.0, 848.0, 3.0, 217) vs (300.0, 798.0, 3.0, 167)
```

### DAT Parsing Diagnostics

Experimental and model spectrum readers now document the expected format:

```text
wavelength [col 0], transmittance [col 2]
```

They also fail clearly if fewer than half of the non-comment data rows can be parsed. This avoids silently fitting malformed or unexpected `.dat` files.

### Gnuplot Path Robustness

Generated `.gp` files now use paths relative to the gnuplot script location instead of paths relative to the Python launch directory.

The optimizer also runs `gnuplot` from the script directory, so generated plot scripts are less sensitive to the current working directory from which the Python optimizer was launched.

### Invalid-Point Diagnostics

The objective evaluation now tracks both:

- finite points used in SSE;
- invalid/non-finite points skipped from SSE.

The result JSON includes `invalid_points`, and when invalid points are present it adds:

```json
"warnings": [
  "non_finite_points_present"
]
```

## Metrics Upgrade

The result JSON objective block was made more explicit.

The ambiguous old field:

```json
"value": ...
```

was removed.

The optimizer now writes:

```json
"objective": {
  "name": "sse_transmittance",
  "sse": 3.058024579116812,
  "mse": 0.0184218348139567,
  "rmse": 0.13572705999157536,
  "finite_points": 166,
  "invalid_points": 1,
  "n_parameters": 2
}
```

The normalized metrics are computed from the finite objective points:

```text
mse  = sse / finite_points
rmse = sqrt(mse)
```

No chi-squared or reduced chi-squared value is reported, because the current v1 objective does not use experimental uncertainty weighting.

## Validation

The Python files were syntax-checked with:

```bash
python3 -m py_compile tools/optimal/optimize_model_parameters.py tools/optimal/model/mg_lib.py
```

The optimizer was rerun with:

```bash
python3 tools/optimal/optimize_model_parameters.py --mg
```

Observed result:

- 5 spectra fitted successfully;
- the `60s` spectrum was skipped for the expected wavelength-grid mismatch;
- generated JSON files now contain `sse`, `mse`, `rmse`, `finite_points`, `invalid_points`, and `n_parameters`;
- the old ambiguous `value` field is no longer present in the generated objective block.

## Current Behavior

The optimizer remains a deterministic v1 coarse grid search over:

- `effe`;
- `thickness_nm`.

The changes affect transparency, diagnostics, and output metrics only. They do not change the search algorithm, forward model, physics, or selected best-fit candidates.
