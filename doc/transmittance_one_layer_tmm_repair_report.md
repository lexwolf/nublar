# Transmittance One-Layer TMM Repair Report

This note records the targeted one-layer repair workflow applied to [`src/transmittance.cxx`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx), using the analytic single-slab solution as the reference.

## Goal

The purpose of this step was:

- to make the one-layer TMM path agree with the independent analytic slab solution,
- to keep the change small and local,
- and to use the toy mode as a regression harness before trusting the real pipeline again.

This was not a broad rewrite of the optics code.

## Root Cause

The main issue was a **sign convention error in the slab characteristic matrix**.

The one-layer / coherent-stack TMM had been using off-diagonal terms of the form:

```cpp
a12 = +i sin(delta) / n
a21 = +i n sin(delta)
```

but for the convention consistent with the analytic slab formula, the matrix needed:

```cpp
a12 = -i sin(delta) / n
a21 = -i n sin(delta)
```

So the bug was primarily:

- **matrix convention / sign**

and not:

- MMGM,
- morphology,
- `effe`,
- `Rave`,
- or an arbitrary post-hoc intensity clamp.

## Modified File List

- [`src/transmittance.cxx`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx)

## What Was Changed

### 1. Repaired the general coherent stack routine

In [`coherent_stack_rt()`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx), the slab matrix off-diagonal signs were flipped from `+i` to `-i`.

### 2. Added a transparent one-layer TMM debug path

A dedicated helper was added:

- `single_slab_rt_tmm_debug(...)`

This explicitly computes for a single slab:

- `beta`
- `exp(i beta)`
- `exp(2 i beta)`
- `M11`
- `M12`
- `M21`
- `M22`
- `r_tmm`
- `t_tmm`
- `R_tmm`
- `T_tmm`
- `A_tmm`

### 3. Kept the analytic one-layer reference

The toy harness still computes the independent analytic single-slab result:

- `r_analytic`
- `t_analytic`
- `R_analytic`
- `T_analytic`
- `A_analytic`

### 4. Side-by-side toy comparison remains in place

The toy diagnostic output now includes:

- TMM results
- analytic results
- differences:
  - `dR`
  - `dT`
  - `dA`

This is now the regression test for the coherent one-layer optics core.

## Commands Used

### Toy verification

```bash
make bin/transmittance
./bin/transmittance --toy
```

### Optional real-case sanity rerun

```bash
scripts/bash/run_transmittance_pipeline.sh -c --xi 0.6
```

## Before / After Toy Diagnostics

## Before repair

### Toy Case A

TMM:

- `R = 0.0388007266`
- `T = 0.9734114842`
- `A = -0.0122122108`

Analytic:

- `R = 0.0412348538`
- `T = 0.9468468615`
- `A = 0.0119182847`

### Toy Case B

TMM:

- `R = 0.3122535129`
- `T = 0.8902970048`
- `A = -0.2025505177`

Analytic:

- `R = 0.2708214691`
- `T = 0.5930748089`
- `A = 0.1361037220`

## After repair

From [toy_front_stack_diagnostic.dat](/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/toy_front_stack_diagnostic.dat):

```text
ToyCaseA_weak_absorbing_dielectric ... R_tmm=0.0412348538 T_tmm=0.9468468615 A_tmm=0.0119182847 R_analytic=0.0412348538 T_analytic=0.9468468615 A_analytic=0.0119182847 dR=-0.0000000000 dT=0.0000000000 dA=0.0000000000
ToyCaseB_absorbing_metal_like ... R_tmm=0.2708214691 T_tmm=0.5930748089 A_tmm=0.1361037220 R_analytic=0.2708214691 T_analytic=0.5930748089 A_analytic=0.1361037220 dR=-0.0000000000 dT=0.0000000000 dA=-0.0000000000
```

## Pass / Fail Status of Toy Cases

Both toy cases now pass.

Runtime summary:

```text
[INFO] ToyCaseA_weak_absorbing_dielectric: TMM passed, analytic passed | TMM(R=0.0412349, T=0.946847, A=0.0119183) | analytic(R=0.0412349, T=0.946847, A=0.0119183)
[INFO] ToyCaseB_absorbing_metal_like: TMM passed, analytic passed | TMM(R=0.270821, T=0.593075, A=0.136104) | analytic(R=0.270821, T=0.593075, A=0.136104)
```

So:

- Toy Case A: **pass**
- Toy Case B: **pass**

## Effect on the Previously Problematic Real Case

After repairing the one-layer TMM convention, the real-case sanity rerun:

```bash
scripts/bash/run_transmittance_pipeline.sh -c --xi 0.6
```

showed a clear improvement.

The previously observed condition:

- `T_front > 1`
- `A_front < 0`

disappeared in the rerun.

Diagnostic result:

```text
NO_MATCHES
```

Per-file summary after repair:

```text
silver_nanoisland_10s.dat Tfront_max 0.9437639494 @ 321.0 nm Afront_min 0.0080454236 @ 321.0 nm count_Tfront_gt1 0
silver_nanoisland_20s.dat Tfront_max 0.9459464774 @ 321.0 nm Afront_min 0.0062915545 @ 321.0 nm count_Tfront_gt1 0
silver_nanoisland_30s.dat Tfront_max 0.9470163867 @ 321.0 nm Afront_min 0.0054290643 @ 321.0 nm count_Tfront_gt1 0
silver_nanoisland_40s.dat Tfront_max 0.9208454175 @ 321.0 nm Afront_min 0.0260854146 @ 321.0 nm count_Tfront_gt1 0
silver_nanoisland_50s.dat Tfront_max 0.9555659622 @ 798.0 nm Afront_min 0.0015677198 @ 798.0 nm count_Tfront_gt1 0
silver_nanoisland_60s.dat Tfront_max 0.9494852502 @ 848.0 nm Afront_min 0.0062821015 @ 848.0 nm count_Tfront_gt1 0
```

## Conclusion

The targeted one-layer repair succeeded.

What we learned:

- the one-layer TMM mismatch was caused by the matrix sign convention
- once repaired, the TMM and analytic one-slab solutions agree exactly for the toy cases
- both passive toy stacks now satisfy passivity
- the previously problematic real `xi = 0.6` case also improved substantially:
  - no more `T_front > 1`
  - no more `A_front < 0`

So this repair strongly indicates that the dominant pathology was in the coherent-stack core itself, specifically the one-layer characteristic-matrix convention.
