# Thickness Proxy Update Report

## Modified Files

- `tools/experimental/build_experimental_input.py`
- `scripts/bash/run_transmittance_pipeline.sh`

## Summary

The experimental-input pipeline now supports an explicit thickness proxy selector via:

```bash
--thickness-proxy
```

The previous behavior is preserved as the default:

- `equivalent_thickness_nm`

A new radius-consistency thickness option was added:

- `sphere_r95_diameter`

The solver-facing thickness value is still exported through the same numeric manifest slot currently used downstream (`equivalent_thickness_nm` / `eq_thickness_nm` in the `.dat` row), so the existing solver pipeline continues to consume the manifest without schema breakage in the critical numeric positions.

Additional provenance metadata is now exported:

- `thickness_proxy_name`
- `thickness_proxy_formula`
- `afm_equivalent_thickness_nm`
- `afm_equivalent_thickness_nm_std`

These metadata fields were appended after the existing solver-critical manifest fields.

## Exact Meaning Of `sphere_r95_diameter`

`sphere_r95_diameter` is defined as follows:

1. Use the currently selected `--radius-proxy`.
2. Pool all positive per-island radii from the selected AFM scans for a deposition time.
3. Compute the empirical 95th percentile radius from the pooled radii.
4. Set the slab thickness to:

```text
d = 2 * R95
```

Important implementation details:

- the calculation uses the empirical pooled radii
- it does not use fitted lognormal parameters
- this keeps the thickness close to the AFM-derived morphology

## Thickness Logic Refactor

Thickness computation was factored into a dedicated helper in `tools/experimental/build_experimental_input.py`:

```python
compute_thickness_proxy(
    thickness_proxy_name: str,
    entries: list[dict[str, Any]],
    radius_proxy_name: str,
) -> ThicknessProxyResult
```

This helper returns:

- the selected thickness value in nm
- a thickness std value
- a human-readable formula string

Behavior:

- `equivalent_thickness_nm`
  - thickness = mean of `summary["equivalent_thickness_nm"]`
- `sphere_r95_diameter`
  - thickness = `2 * empirical_percentile_95(pooled_radii)`

## Effect On `effe`

`compute_effe_proxy(...)` now receives the selected solver thickness, not always the AFM mean equivalent thickness.

This means:

- with `--thickness-proxy equivalent_thickness_nm`, behavior remains backward-compatible
- with `--thickness-proxy sphere_r95_diameter`, thickness-dependent `effe` proxies now use the radius-derived slab thickness

This change was intentional and matches the requested design.

## Compatibility Checks

Validation was added through:

```python
validate_proxy_combination(
    thickness_proxy_name: str,
    effe_proxy_name: str,
) -> None
```

### Hard Error

This combination now fails explicitly:

```bash
--thickness-proxy sphere_r95_diameter --effe-proxy eq_thickness_over_Rave
```

Reason:

- the thickness is already derived from the selected radius proxy
- `eq_thickness_over_Rave` would therefore become conceptually circular

### Hybrid Proxies

For the hybrid proxies:

- `hybrid_alpha25`
- `hybrid_alpha50`
- `hybrid_alpha75`

I implemented:

- explicit warnings to `stderr`
- not hard errors

The warning states that radius-derived circularity is introduced and the result should be interpreted cautiously.

### Still Allowed

These remain allowed with `sphere_r95_diameter`:

- `coverage_fraction`
- `eq_thickness_over_mean_height`
- `coverage_times_eq_over_hmean`
- `sqrt_coverage_times_eq_over_hmean`

## Pipeline Integration

To keep the pipeline cascading, `scripts/bash/run_transmittance_pipeline.sh` was updated to accept and pass through:

```bash
--thickness-proxy
```

The rest of the framework was not broadly refactored.

## Commands That Now Work

### Default Backward-Compatible Path

```bash
python3 tools/experimental/build_experimental_input.py
```

### New Thickness Logic With Allowed `effe`

```bash
python3 tools/experimental/build_experimental_input.py \
  --radius-proxy volume_equivalent_radius_nm \
  --thickness-proxy sphere_r95_diameter \
  --effe-proxy coverage_times_eq_over_hmean
```

### Pipeline Invocation With New Thickness Proxy

```bash
scripts/bash/run_transmittance_pipeline.sh \
  --radius-proxy volume_equivalent_radius_nm \
  --thickness-proxy sphere_r95_diameter \
  --effe-proxy coverage_fraction
```

## Command That Now Fails Intentionally

```bash
python3 tools/experimental/build_experimental_input.py \
  --radius-proxy volume_equivalent_radius_nm \
  --thickness-proxy sphere_r95_diameter \
  --effe-proxy eq_thickness_over_Rave
```

Expected outcome:

- clean error
- no Python traceback

## Tests Run

### A. Default Backward-Compatible Path

Ran:

```bash
python3 tools/experimental/build_experimental_input.py
```

Result:

- passed

### B. New Thickness Logic With Allowed `effe`

Ran:

```bash
python3 tools/experimental/build_experimental_input.py \
  --radius-proxy volume_equivalent_radius_nm \
  --thickness-proxy sphere_r95_diameter \
  --effe-proxy coverage_times_eq_over_hmean
```

Result:

- passed

### C. Incompatible Combination

Ran:

```bash
python3 tools/experimental/build_experimental_input.py \
  --radius-proxy volume_equivalent_radius_nm \
  --thickness-proxy sphere_r95_diameter \
  --effe-proxy eq_thickness_over_Rave
```

Result:

- failed as intended with a clear compatibility error

### D. Pipeline Smoke Test

Ran:

```bash
scripts/bash/run_transmittance_pipeline.sh \
  --radius-proxy volume_equivalent_radius_nm \
  --thickness-proxy sphere_r95_diameter \
  --effe-proxy coverage_fraction
```

Result:

- passed through manifest generation
- passed through transmittance dataset generation
- passed through transmittance solver execution
- passed through comparison gnuplot generation

## Important Note

I also tested:

```bash
scripts/bash/run_transmittance_pipeline.sh \
  --radius-proxy volume_equivalent_radius_nm \
  --thickness-proxy sphere_r95_diameter \
  --effe-proxy coverage_times_eq_over_hmean
```

This reached the existing C++ solver guard and failed with:

```text
Error: Manifest row has invalid Rave, thickness, or effe values
```

That is not caused by manifest parsing breakage. It is caused by the solver's current validation rule requiring:

```text
0 <= effe <= 1
```

Under the new thickness choice, `coverage_times_eq_over_hmean` can exceed `1`. I did not change solver semantics, per the requested constraints.
