# Nublar Cheatsheet

This is a practical “how to run it” guide for the scripts and small utilities used in the **Nublar** workflow (deposition-step sweeps + post-processing of optical outputs).

---

## Directory layout (expected)

Typical working directory contains:

- `sweep_ds.bash` — main driver script (deposition sweep + summary + plot).
- `mie` / `mie.cxx` — computes spectra for a given morphology + filling fraction.
- `getmax` / `getmax.cxx` — extracts wavelength of maximum of a chosen column (typically Im(ε)).
- `getenz` / `getenz.cxx` — finds ENZ crossing wavelengths (zeros of Re(ε) via sign change + interpolation).
- Output folders created by the script:
  - `data/output/` — data products (raw mie spectra, mapping, summary, per-step `.results`, caption).
  - `img/` — generated PNG plots.
  - `data/output/subroutine_log/` — optional debug series when verbose mode is enabled.

Notes:
- The script expects `gnuplot` to be available for plot generation.
- The script uses `bc` for floating-point checks.

---

## 1) Build / compile

### Option A — compile from the sweep script
```bash
bash sweep_ds.bash --compile
```

### Option B — compile manually
```bash
g++ -Wall -L/usr/local/lib mie.cxx   -o mie   -lcomplex_bessel
g++ getmax.cxx -o getmax
g++ getenz.cxx -o getenz
```

---

## 2) Main workflow: `sweep_ds.bash`

### What it does
For each deposition step `ds = 1..N` it:
1. Computes cumulative thickness `d(ds)`.
2. Sets the size distribution width `σ_geo(ds)` using the chosen law.
3. Converts `σ_geo(ds)` into lognormal relative dispersion `k(ds)` and then into:
   - average radius `Rave(ds)`
   - size spread in nm `σ_nm(ds)`
4. Computes filling fraction `f(ds)` (normalized so step 1 equals `f0`, with optional packing penalty).
5. Runs `./bin/mie` to produce a spectrum file (one per step).
6. Post-processes with:
   - `./bin/getmax` → wavelength of max(Im ε)
   - `./bin/getenz` → ENZ wavelengths (zeros of Re ε)
7. Writes:
   - `data/output/mapping_ds.dat` (bookkeeping mapping from step → file/parameters)
   - `data/output/summary_ds.dat` (one line per step with the key extracted wavelengths)
   - `data/output/<mie_output>.results` (per-step mini-report)
8. Generates a 2×2 gnuplot figure in `img/` (unless `gnuplot` not found).
9. (If enabled) generates debug series in `data/output/subroutine_log/`.

---

### Key options
Run:
```bash
bash sweep_ds.bash -h
```
to see all options. The important ones:

- `-n, --steps N`  
  Number of deposition steps (default: 5)

- `-t, --thickness VAL`  
  Final thickness d∞ in nm

- `--d1 VAL`  
  **First measured thickness** d(1) in nm.  
  If `--d1 0` (default), uses the auto rule `d(ds)=d∞·ds/N`.  
  If `--d1 > 0`, uses linear interpolation from `d1` (step 1) to `d∞` (step N).

- `--alpha VAL`  
  Alpha in the morphology rule `d = Rave + alpha*sigma_nm`.

- `--sigma-law LAW`  
  `const | linear | gauss` for the evolution of `σ_geo(ds)`.

- `--sg-min VAL`, `--sg-peak VAL`, `--sg-mu VAL`, `--sg-w VAL`  
  Parameters controlling the `σ_geo(ds)` law.

- `--f0 VAL`  
  Baseline filling fraction for step 1.

- `--packing-beta VAL`  
  Optional penalty factor: `f → f / (1 + beta*(σ_geo-1)^2)`.

- `-z, --zero` and `-zf VAL`  
  Switch to the “baseline MG” mode: ignores `R, σ` and uses constant `f = f_zero`.  
  (Also changes which columns are used for Re/Im.)

- `-vb, --verbose-output` (alias `-so, --subroutine-output`)  
  Enables writing plottable debug `.dat` series for subroutines into:
  `data/output/subroutine_log/`

---

### Examples

**Default run**
```bash
bash sweep_ds.bash
```

**Match an experiment with a non-zero first measurement thickness**
```bash
bash sweep_ds.bash --d1 2.5 --thickness 10.0 --steps 5
```

**Tune morphology and filling fraction**
```bash
bash sweep_ds.bash --f0 0.25 --sg-min 1.6 --sg-peak 1.8 --d1 2.5
```

**Enable debug subroutine logs**
```bash
bash sweep_ds.bash -vb
# check: data/output/subroutine_log/sigma_geo_of_ds.dat
```

---

## 3) Output files you should care about

### `data/output/mapping_ds.dat`
Bookkeeping table mapping each step to the exact mie spectrum file and parameters.

Header:
```
# file ds d[nm] Rave[nm] sigma_geo sigma_nm[nm] f
```

### `data/output/summary_ds.dat`
One line per step with the extracted “headline” values:

Header:
```
# ds d[nm] Rave[nm] sigma_geo sigma_nm[nm] f lam_max[nm] ENZ1[nm] ENZ2[nm]
```

- `lam_max[nm]`: wavelength of the maximum of **Im(ε)** (chosen column).
- `ENZ1[nm]`, `ENZ2[nm]`: wavelengths where **Re(ε)=0** (low-energy and high-energy crossings, if present).

### Per-step results files
For each mie output file:
- `data/output/<mie_output_file>.results`  
contains the same step line plus a small header.

### Plot
- `img/deposition.png` (or `img/deposition_MG.png` in `--zero` mode)

### Optional debug logs
- `data/output/subroutine_log/sigma_geo_of_ds.dat`  
Format:
```
ds  sigma_geo(ds)
```

---

## 4) Utility programs

### `getenz`
Finds ENZ crossings: zeros of a chosen column via sign-change detection and linear interpolation.

**Usage**
```bash
./bin/getenz <filename> <column_index>
```

Example (Re(ε_eff) in column 2):
```bash
./bin/getenz "data/output/Rave=1.88__f=0.133__lognormal__sg=1.31.dat" 2
```

Output: one wavelength per line, e.g.
```
345.122
367.843
```

If you want the values on one line (for shell capture), use:
```bash
./bin/getenz file.dat 2 | xargs
```

---

### `getmax`
Returns the wavelength of the maximum of a selected column (typically Im(ε)).

**Usage**
```bash
./bin/getmax <filename> <column_index>
```

Example (Im(ε_eff) in column 3):
```bash
./bin/getmax data/output/somefile.dat 3
```

If `getmax` prints extra fields (e.g., peak value), but you only want the wavelength:
```bash
./bin/getmax file.dat 3 | awk '{print $1; exit}'
```

---

### `mie`
Computes spectra for a given morphology.

Called from `sweep_ds.bash` in these patterns:

**MGM mode**
```bash
./bin/mie <Rave> <f> lognormal -sg <sigma_geo> -pf
```

**MG baseline / “zero” mode**
```bash
./bin/mie 0 <f> lognormal -pf
```

The output is a text file with columns like:
```
lambda[nm]  Re(eps_eff)  Im(eps_eff)  Re(eps_MG)  Im(eps_MG)
```

---

## 5) Plotting with gnuplot

The script generates a gnuplot file (e.g. `plot_results_ds.gp`) and runs:
```bash
gnuplot plot_results_ds.gp
```

To regenerate plots without re-running the full sweep:
```bash
gnuplot plot_results_ds.gp
```

---

## 6) Common pitfalls & quick fixes

- **Summary file has “broken lines” / extra newlines**
  - Cause: a tool prints multiple lines; you captured it into a variable and echoed it.
  - Fix: pipe through `xargs` (flatten) or pick a single field via `awk`.

- **ENZ values look like small numbers (~5–15) instead of hundreds of nm**
  - Usually means you wrote Re(ε) values into the ENZ columns.
  - Confirm `getenz` column index is correct (2 or 4 depending on mode).

- **Plot legend is unreadable**
  - Replace curve titles with `step 1`, `step 2`, … and move details into `data/output/caption.tex`.

- **`bc` not found**
  ```bash
  sudo apt-get install bc
  ```

- **`gnuplot` not found**
  ```bash
  sudo apt-get install gnuplot
  ```

---

## 7) One command you recently used for tuning
```bash
bash sweep_ds.bash --f0 0.25 --sg-min 1.6 --sg-peak 1.8 --d1 2.5
```

---

## 8) Reproducibility notes
For reporting, record:
- the exact command line used (`--f0`, `--d1`, `--sg-min`, `--sg-peak`, etc.)
- the generated `data/output/summary_ds.dat` and `img/deposition*.png`
- the script version (commit hash if in git)
