# AFM Morphology Radius Plan

## Goal

Define a physically better scalar size description for the experimental nanoislands before using the morphology as input for MMGM-style optical modeling.

The current direct AFM workflow already provides:

- lateral footprint-derived equivalent radius
- mean island height
- island volume
- coverage fraction
- number density

The open issue is which scalar radius should be used as the effective sphere radius in the optical model.

## Problem Statement

Using only the lateral footprint radius can be misleading for flattened nanoislands.

Example:

- lateral equivalent radius can be tens of nm
- vertical size can be only a few nm

That morphology is not sphere-like, so a direct footprint-to-sphere mapping is weak.

The alternative experimental analysis appears to fit a distribution over `Z_nm`, which is likely a height-like observable. That may be closer to the vertical island scale, but it is still not automatically the right spherical radius either.

The main requirement is therefore:

- extract robust per-island height descriptors from raw AFM data
- combine lateral and vertical information into better scalar size proxies
- keep the raw-data provenance explicit

## Proposed Per-Island Quantities

These fields should be present for every segmented island in the AFM feature JSON payload.

### Already Present

- `label`
- `area_px`
- `area_um2`
- `equivalent_radius_nm`
- `max_height_nm`
- `mean_height_nm`
- `volume_nm3`
- `centroid_x_um`
- `centroid_y_um`

## Proposed Additions

### Height Descriptors

- `min_height_nm`
  - minimum value of `z_rel` within the island mask
  - mostly diagnostic

- `p50_height_nm`
  - median height within the island mask
  - robust central vertical scale

- `p95_height_nm`
  - 95th percentile of height within the island mask
  - robust proxy for near-peak height

- `height_range_nm`
  - `max_height_nm - min_height_nm`
  - useful to detect odd masks or rough islands

### Radius Proxies

- `height_equivalent_radius_mean_nm`
  - `mean_height_nm / 2`
  - sphere radius whose diameter equals the mean island height

- `height_equivalent_radius_p95_nm`
  - `p95_height_nm / 2`
  - less noise-sensitive than `max_height_nm / 2`

- `volume_equivalent_radius_nm`
  - `(3 * volume_nm3 / (4 * pi))^(1/3)`
  - sphere radius of equal material volume

This last quantity is the most important proposed addition.

## How Height Should Be Extracted

Height should not be defined from the full image global excursion:

- not `z_max - z_min` of the whole AFM map

That quantity is too sensitive to:

- residual tilt
- isolated outliers
- large-scale waviness
- unrelated background variation

Instead, height should be extracted per island after the existing preprocessing pipeline.

### Proposed Height Workflow

1. Load raw AFM topography `z_raw`.
2. Apply row leveling.
3. Apply plane flattening.
4. Apply smoothing.
5. Estimate a baseline.
6. Build relative height map:

   `z_rel = z_smooth - baseline`

7. Segment islands on `z_rel`.
8. For each island, compute height descriptors from the `z_rel` values only inside that island mask.

This gives a local height above the estimated substrate/background level, which is the relevant quantity for morphology reduction.

## Preferred Scalar Size Candidate

### Current Candidate

- `equivalent_radius_nm`
  - footprint-derived

### Proposed Better Candidate

- `volume_equivalent_radius_nm`

Reason:

- uses both lateral footprint and vertical extent
- less arbitrary than height-only or footprint-only reductions
- maps naturally onto an equivalent spherical particle volume

### Sensitivity Candidates

These should also be computed and compared:

- `equivalent_radius_nm`
- `height_equivalent_radius_mean_nm`
- `height_equivalent_radius_p95_nm`
- `volume_equivalent_radius_nm`

## Distribution Fitting Plan

The fitting stage should operate directly on AFM-derived per-island quantities, not on external processed fit exports.

For each deposition time:

1. pool island values from the selected scans
2. fit a two-lognormal mixture to:
   - `equivalent_radius_nm`
   - `volume_equivalent_radius_nm`
3. optionally fit:
   - `height_equivalent_radius_mean_nm`
   - `height_equivalent_radius_p95_nm`

The current preferred modeling input should become:

- two-lognormal fit on `volume_equivalent_radius_nm`

The footprint-based fit should be retained as a comparison baseline.

## Proposed JSON Schema Extension

For each island record:

```text
label
area_px
area_um2
equivalent_radius_nm
max_height_nm
mean_height_nm
volume_nm3
centroid_x_um
centroid_y_um
min_height_nm
p50_height_nm
p95_height_nm
height_range_nm
height_equivalent_radius_mean_nm
height_equivalent_radius_p95_nm
volume_equivalent_radius_nm
```

No existing fields should be removed.

## Proposed Manifest Fields

At the deposition-time aggregation level, the solver-facing manifest should eventually include:

- `distribution_axis_name`
- `distribution_source`
- `distribution_type`
- `mixture_weight_1`
- `muL1`
- `sigL1`
- `mixture_weight_2`
- `muL2`
- `sigL2`
- `distribution_mean_nm`
- `distribution_std_nm`

and it should clearly specify which scalar size was used:

- `radius_proxy_name`

Possible values:

- `footprint_equivalent_radius_nm`
- `volume_equivalent_radius_nm`
- `height_equivalent_radius_mean_nm`
- `height_equivalent_radius_p95_nm`

## Implementation Stages

### Stage 1

Extend AFM per-island extraction in `tools/experimental/afm_lib/features.py`:

- add the height percentile fields
- add `volume_equivalent_radius_nm`
- add height-equivalent radius proxies

### Stage 2

Update `tools/experimental/extract_afm_features.py` outputs:

- keep JSON backward-compatible
- include the new island-level fields

### Stage 3

Update the AFM aggregation tools:

- `tools/experimental/build_afm_to_emt_input.py`
- `tools/experimental/build_experimental_input.py`

to allow choosing the radius proxy used for two-lognormal fitting.

Recommended default for model studies:

- `volume_equivalent_radius_nm`

### Stage 4

Compare proxy choices against optics:

- footprint-based mixture
- volume-equivalent mixture
- height-based mixture

and evaluate which one gives the most defensible transmission fit.

## Current Recommendation

Before changing the optical model:

1. add the new per-island height and volume-equivalent fields
2. fit the two-lognormal mixture on `volume_equivalent_radius_nm`
3. retain the footprint-based mixture as a comparison

This keeps the pipeline close to raw AFM data while improving the physical meaning of the scalar radius used in the effective-medium model.
