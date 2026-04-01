# AFM Raw Data — Silver Nanoislands

This directory contains raw AFM measurements of silver nano-islands used for morphology extraction and subsequent optical modeling.

## File Naming Convention

Files follow a structured naming pattern:

```text
Nis_Ag_{time}s_{scan_size}_{suffix}.stp
```

Where:

* **Nis** = Nano Islands
* **Ag** = Silver
* **{time}s** = deposition time in seconds (e.g. 10s, 20s, ..., 60s)
* **{scan_size}** = lateral scan size of the AFM image

  * `1um` → 1 µm × 1 µm scan
  * `2um` → 2 µm × 2 µm scan
* **{suffix}** = scan identifier (e.g. 001, 002, 003)

Examples:

* `Nis_Ag_10s_2um_001.stp`
* `Nis_Ag_30s_2um_003.stp`
* `Nis_Ag_50s_1um_001.stp`

---

## Scan Size (1 µm vs 2 µm)

* **2 µm scans**:

  * Larger field of view
  * More statistically representative of the surface morphology
  * Preferred for extraction of global parameters (coverage, density, radius)

* **1 µm scans**:

  * Higher local resolution
  * Useful for detailed inspection
  * More sensitive to local fluctuations and less representative of the global sample

👉 In the current workflow, **2 µm scans are used as the primary data source** for morphology extraction.

---

## Multiple Scans per Sample (001, 002, 003)

For each deposition time, multiple AFM scans are available:

* `001`, `002`, `003` correspond to **different spatial regions of the same sample**, not repeated measurements of the same spot.

### Interpretation

* Differences between scans reflect:

  * **real spatial heterogeneity** of the sample
  * plus possible **analysis sensitivity** (segmentation, thresholding, etc.)

* Some scans (e.g. `003`) may correspond to **edge or atypical regions** of the sample and can exhibit noticeably different morphology.

---

## Current Working Assumption

} The AFM scans labeled 001–003 correspond to different spatial regions of the same sample. Therefore, differences among them reflect both analysis sensitivity and genuine spatial heterogeneity. In the present workflow, scan 001 is used as the representative morphology input, while the spread across other scans is interpreted as a measure of inter-region variability rather than pure statistical uncertainty.

### Practical usage

* **Primary dataset**:

  * use `001` scans as representative morphology

* **Variability / robustness check**:

  * use `001 + 003` (or all scans) to estimate **inter-region variability**

* **Caution**:

  * do not interpret spread across scans purely as statistical error bars

---

## File Types

* `.stp` → raw AFM data (WSxM format)
* auxiliary files (e.g. `.001`, `.010`, etc.) → instrument-specific or intermediate formats, not used in the current pipeline

---

## Notes

* Some files labeled `Image 1` correspond to **processed/visualization-oriented data** and may include filtering or transformations. These are not used as primary inputs for quantitative analysis.
* Segmentation and feature extraction are performed on raw `.stp` data using the pipeline in `tools/`.

---

## Summary

This dataset provides:

* time-resolved morphology (10s → 60s)
* spatial variability across the sample
* multiple scan sizes (1 µm, 2 µm)

The current analysis pipeline prioritizes:

* 2 µm scans
* scan `001` as representative
* other scans for heterogeneity assessment

This choice should be revisited if more detailed spatial mapping or region-specific modeling is required.
