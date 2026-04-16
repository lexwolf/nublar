# Transmittance Toy-Mode Diagnostic Report

This note records the passive-stack toy diagnostic added to [`src/transmittance.cxx`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx) and the numerical results obtained from running it.

## Purpose

The goal of the toy mode is to test whether the coherent front-stack transfer-matrix machinery is internally consistent **without** involving:

- MMGM / effective-medium modeling
- AFM / morphology inputs
- `model_input.dat`
- the normal experimental transmittance pipeline

The question was:

> Does the coherent stack code give physically sensible `R`, `T`, and `A = 1 - R - T` for simple passive stacks?

If these toy stacks fail, then the problem is in the optics core itself rather than in the morphology-driven layer construction.

## Implementation Summary

The toy mode was added directly to [`src/transmittance.cxx`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx) as a special CLI path:

```bash
./bin/transmittance --toy
```

When `--toy` is passed:

- the solver does **not** read `model_input.dat`
- the solver does **not** use MMGM / manifest / morphology logic
- it runs hardcoded passive test cases through the same `coherent_stack_rt()` routine used by the real solver
- it writes a small diagnostic table

Output file:

- [toy_front_stack_diagnostic.dat](/home/alessandro/GitHub/Academia/nublar/data/output/transmittance/toy_front_stack_diagnostic.dat)

## Toy Cases

## Toy Case A — weakly absorbing dielectric slab

Stack:

```text
air | slab | glass
```

Parameters:

- `n_air = 1.0 + 0.0 i`
- `n_slab = 1.5 + 0.01 i`
- `d_slab = 50 nm`
- `n_glass = 1.5 + 0.0 i`
- `lambda = 500 nm`

This should be a completely passive, boring test.

## Toy Case B — passive absorbing / metal-like slab

Stack:

```text
air | slab | glass
```

Parameters:

- `n_air = 1.0 + 0.0 i`
- `n_slab = 0.3 + 2.0 i`
- `d_slab = 20 nm`
- `n_glass = 1.5 + 0.0 i`
- `lambda = 500 nm`

This is still passive, but more stressful numerically.

## Passivity Check

For each case the code computes:

```text
A_front = 1 - R - T
```

and flags a failure if any of the following occur:

- `R < 0`
- `T < 0`
- `T > 1`
- `A_front < 0`

## Commands Used

The exact commands run were:

```bash
make bin/transmittance
./bin/transmittance --toy
```

## Toy Diagnostic Output

The generated file contained:

```text
# Toy front-stack diagnostic using coherent_stack_rt()
# columns: case_label lambda_nm n_in_re n_in_im n_slab_re n_slab_im d_slab_nm n_out_re n_out_im r_re r_im t_re t_im R T A_front
ToyCaseA_weak_absorbing_dielectric 500.0000000000 1.0000000000 0.0000000000 1.5000000000 0.0100000000 50.0000000000 1.5000000000 0.0000000000 -0.1969338566 -0.0042169529 0.4729359654 -0.6521292526 0.0388007266 0.9734114842 -0.0122122108
ToyCaseB_absorbing_metal_like 500.0000000000 1.0000000000 0.0000000000 0.3000000000 2.0000000000 20.0000000000 1.5000000000 0.0000000000 -0.2397030973 0.5047731550 0.7396958511 0.2153633776 0.3122535129 0.8902970048 -0.2025505177
```

## Results

## Toy Case A

- `R = 0.0388007266`
- `T = 0.9734114842`
- `A_front = -0.0122122108`

Result:

- `T > 1`? No
- `A_front < 0`? Yes
- Passivity check: **failed**

## Toy Case B

- `R = 0.3122535129`
- `T = 0.8902970048`
- `A_front = -0.2025505177`

Result:

- `T > 1`? No
- `A_front < 0`? Yes
- Passivity check: **failed**

## Overall Conclusion

Both passive toy stacks failed.

Key observation:

- neither toy case produced `T > 1`
- both toy cases produced `A_front < 0`

This means the coherent stack machinery is already non-passive even for simple passive test stacks.

So the toy-mode result strongly suggests:

- the optics core itself is internally inconsistent
- the issue is **not** limited to MMGM / morphology / manifest-driven complexity
- the remaining bug is likely in:
  - transfer-matrix convention,
  - field/admittance convention,
  - or another core normalization/sign choice in the coherent stack implementation

## Modified File List

- [`src/transmittance.cxx`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx)
