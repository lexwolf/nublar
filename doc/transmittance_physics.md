# Transmittance Solver Physics

This note documents the physics implemented in [`src/transmittance.cxx`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx), the meaning of the input parameters read from the manifest, and the interpretation of every output column written to `data/output/transmittance/silver_nanoisland_<time>s.dat`.

It is meant to be a direct description of the current code, not an abstract optics overview.

## 1. Physical Picture

The calculation models the sample as:

`air | effective Ag nanoisland layer | ITO | glass | air`

with the following treatment:

- The **top stack** `air | effective nanoisland layer | ITO | glass` is treated **coherently** with a transfer-matrix method.
- The **glass substrate thickness** is treated **incoherently** through a Beer-Lambert attenuation factor.
- The **back interface** `glass | air` is treated as a single incoherent Fresnel interface.
- Optional **incoherent multiple reflections inside the substrate** are included.

This is the model described in the code comment near the top of [`src/transmittance.cxx`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx:25).

## 2. Main Observable

The final transmitted intensity written as `T_total` is:

```text
T_total = T_front * A_glass * T_back
          / (1 - R_front_glass * R_back * A_glass^2)
```

where:

- `T_front` is the coherent transmittance of the front stack seen from air.
- `A_glass` is the intensity attenuation due to propagation through the finite glass thickness.
- `T_back` is the transmittance of the back `glass -> air` interface.
- `R_front_glass` is the coherent reflectance of the front stack, but seen from the glass side.
- `R_back` is the reflectance of the `glass -> air` back interface.

So:

- `T_total` is the quantity closest to **the experimentally observable broadband transmittance**.
- The denominator corrects for **incoherent substrate recycling**: light can reflect at the back interface, return to the front stack, reflect again, and so on.

If substrate multiple reflections are disabled, the code reduces to:

```text
T_total = T_front * A_glass * T_back
```

## 3. Effective Nanoisland Layer

The silver nanoisland film is not modeled as discrete islands in the propagation calculation. Instead, it is replaced by an **effective medium** with complex permittivity:

```text
eps_eff(lambda)
```

computed by:

[`nublar::mmgm_effective_permittivity()`](/home/alessandro/GitHub/Academia/nublar/header/nano_island_permittivity.hpp:167)

This uses:

- the complex silver permittivity `eps_metal(omega)`
- the host permittivity `eps_host` (air in the current code)
- a morphology-derived effective filling factor `effe`
- an average radius proxy `Rave_nm`
- a **two-lognormal radius distribution**

The morphology parameters come from the manifest row loaded into `ExperimentalRow` in [`header/nano_island_permittivity.hpp`](/home/alessandro/GitHub/Academia/nublar/header/nano_island_permittivity.hpp:22).

### 3.1 Radius Distribution

The code assumes the radius distribution is:

```text
p(r) = w1 * LN(r; muL1, sigL1) + w2 * LN(r; muL2, sigL2)
```

where:

- `w1`, `w2` are mixture weights
- `muL1`, `sigL1` are the log-space parameters of component 1
- `muL2`, `sigL2` are the log-space parameters of component 2

This distribution enters the MMGM integral through the helper:

- [`two_lognormal_pdf()`](/home/alessandro/GitHub/Academia/nublar/header/nano_island_permittivity.hpp:95)

### 3.2 Role of `effe`

The code uses the scalar `effe` as the effective volume-fraction-like parameter passed into the MMGM effective-medium closure:

```text
rhs ~ volume_fraction * integral_over_size_distribution
eps_eff = eps_host * (1 + 2 rhs) / (1 - rhs)
```

In practice:

- `effe` is the morphology proxy chosen upstream in `build_experimental_input.py`
- it controls how strongly the nanoisland layer perturbs the host medium
- it is not a direct microscopic packing simulation; it is an effective parameter

## 4. Optical Subproblems

## 4.1 Refractive Index Choice

Whenever the code converts a permittivity `eps` to a refractive index `n = sqrt(eps)`, it uses:

- [`principal_refractive_index()`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx:78)

The branch is chosen so that:

- `Im(n) >= 0` for passive media
- if `Im(n)` is numerically zero, the code prefers `Re(n) > 0`

The code also clamps tiny negative `Im(eps)` values to zero before taking the square root. This was added to suppress non-physical branch flips caused by interpolation noise in weakly absorbing dielectrics like glass.

## 4.2 Coherent Front Stack

The front stack is:

`air | effective nanoisland layer | ITO | glass`

It is solved with a standard 2x2 transfer-matrix calculation in:

- [`coherent_stack_rt()`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx:118)

For each layer:

- `delta = (2 pi / lambda) * n_layer * thickness`
- the layer matrix is built from `cos(delta)` and `sin(delta)`
- matrices are multiplied through the stack

The code then extracts:

- amplitude reflection `r`
- amplitude transmission `t`
- intensity reflectance `R = |r|^2`
- intensity transmittance `T = (Re(n_out)/Re(n_in)) |t|^2`

Two coherent calculations are done:

- `front_from_air`: incidence from air into the front stack
- `front_from_glass`: incidence from glass into the same stack, with the layer order reversed

This second quantity is needed for the incoherent multiple-reflection correction.

## 4.3 Back Interface

The back interface is just:

`glass | air`

and is computed with the Fresnel interface function:

- [`interface_rt()`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx:105)

This gives:

- `R_back`
- `T_back`

These are intensity coefficients for the single interface only.

## 4.4 Glass Propagation

Propagation through the finite glass thickness uses:

- [`beer_attenuation_factor()`](/home/alessandro/GitHub/Academia/nublar/src/transmittance.cxx:167)

with:

```text
alpha = 4 pi kappa / lambda
A_glass = exp(-alpha * d_glass)
```

where:

- `kappa = Im(n_glass)`
- `d_glass` is the substrate thickness

So `A_glass` is **pure propagation loss inside the glass slab**. It does not include interface effects.

## 5. Wavelength / Energy Handling

The solver loops on a wavelength grid coming from the experimental manifest:

- `lamin_nm`
- `dlam_nm`
- `n_lambda`

For each wavelength:

```text
omega_eV = h c / lambda
```

using [`wavelength_nm_to_omega_ev()`](/home/alessandro/GitHub/Academia/nublar/header/nano_island_permittivity.hpp:44).

The code also computes the common valid spectral range shared by:

- silver optical table
- ITO optical table
- glass optical table

Outside that common range, the solver writes `NaN` values rather than extrapolating material data.

## 6. Input Parameters From the Manifest

Each row of `model_input.dat` provides one deposition condition. The transmittance solver actually uses:

- `time_s`
- `n_lambda`
- `effe`
- `rave_nm`
- `thickness_nm`
- `w1`, `mu_l1`, `sig_l1`
- `w2`, `mu_l2`, `sig_l2`
- `lamin_nm`, `lamax_nm`, `dlam_nm`

These are parsed into [`ExperimentalRow`](/home/alessandro/GitHub/Academia/nublar/header/nano_island_permittivity.hpp:22).

Physical meaning:

- `time_s`: deposition time label for the sample
- `effe`: effective filling-factor-like morphology parameter used by MMGM
- `rave_nm`: average radius proxy used in the MMGM closure
- `thickness_nm`: effective thickness of the nanoisland layer
- `w1`, `mu_l1`, `sig_l1`, `w2`, `mu_l2`, `sig_l2`: two-lognormal size-distribution parameters
- `lamin_nm`, `lamax_nm`, `dlam_nm`, `n_lambda`: wavelength grid used for the spectrum

## 7. Meaning of Every Output Quantity

Each output file begins with metadata headers, then writes the columns:

```text
lambda_nm omega_eV
T_total T_front T_back A_glass
R_front_air R_front_glass R_back
eps_eff_re eps_eff_im eps_ito_re eps_ito_im eps_glass_re eps_glass_im
```

Below is the physical meaning of each one.

### 7.1 Metadata Header

- `time_s`
  - Deposition-time label of the sample.
- `effe`
  - Effective morphology proxy actually used in the MMGM calculation.
- `Rave_nm`
  - Radius proxy used as the average radius in the MMGM closure.
- `effective_thickness_nm`
  - Thickness assigned to the effective nanoisland layer in the coherent stack.
- `ito_thickness_nm`
  - Thickness of the ITO layer used in the calculation.
- `glass_thickness_nm`
  - Thickness of the glass substrate used in the Beer-Lambert factor.
- `distribution two_lognormal ...`
  - Two-lognormal mixture parameters used for the island-size distribution.
- `omega_range_eV`
  - Common material-data energy interval where the calculation is considered valid.
- `model coherent_front_plus_incoherent_glass`
  - Human-readable label for the hybrid coherent/incoherent model.
- `incoherent_substrate_multiple_reflections`
  - `1` if the denominator correction is used, `0` otherwise.

### 7.2 Spectral Coordinates

- `lambda_nm`
  - Wavelength in nanometers. This is the primary x-axis for plotting the spectrum.
- `omega_eV`
  - Photon energy corresponding to the same point, in electronvolts.

### 7.3 Observable and Transport Terms

- `T_total`
  - **The observable transmittance predicted by the model.**
  - Includes the coherent front stack, propagation through the glass, transmission through the back interface, and the incoherent multiple-reflection correction if enabled.

- `T_front`
  - **Coherent thin-film transmittance of the front stack.**
  - Specifically: `air -> effective nanoisland layer -> ITO -> glass`.
  - This contains thin-film interference and absorption in the coherent top stack.

- `T_back`
  - **Transmittance of the single back interface `glass -> air`.**
  - This is not the whole substrate effect; it is only the Fresnel transmission of the exit interface.

- `A_glass`
  - **Beer-Lambert intensity attenuation through the glass substrate.**
  - If glass absorption is negligible, this stays close to 1.
  - This does not include reflections, only propagation loss.

### 7.4 Reflectance Terms

- `R_front_air`
  - **Reflectance of the coherent front stack as seen from the air side.**
  - This is the front-side reflection for illumination incident from air.

- `R_front_glass`
  - **Reflectance of the same coherent front stack as seen from the glass side.**
  - This is needed because internally reflected light inside the glass sees the front stack from the substrate side.

- `R_back`
  - **Reflectance of the single `glass -> air` back interface.**
  - This controls how much light is recycled back into the substrate.

### 7.5 Material Response Terms

- `eps_eff_re`, `eps_eff_im`
  - Real and imaginary parts of the effective permittivity of the nanoisland layer.
  - This is the electromagnetic response that replaces the explicit island ensemble in the propagation model.

- `eps_ito_re`, `eps_ito_im`
  - Real and imaginary parts of the ITO permittivity read from the material table at the current photon energy.

- `eps_glass_re`, `eps_glass_im`
  - Real and imaginary parts of the glass permittivity read from the material table at the current photon energy.

## 8. Practical Interpretation of the Outputs

The most useful way to read the output columns is:

- `T_total`
  - What you compare to experiment.

- `T_front`
  - What the coherent front-side structure is doing by itself.
  - If a feature is already present here, it comes from thin-film / effective-medium physics near the nanoislands and ITO.

- `A_glass`
  - How much intensity is lost simply by traversing the substrate material.

- `T_back`
  - The exit-interface transmission penalty at `glass -> air`.

- `R_front_air`
  - How reflective the front structure looks to incoming light.

- `R_front_glass`
  - How reflective the front structure looks to light that has already entered the substrate and is bouncing back.

- `R_back`
  - How much of the internally propagating light is reflected back at the rear surface.

- `eps_eff_*`
  - How the morphology-driven nanoisland effective medium is behaving spectrally.

## 9. Assumptions and Limitations

This is a useful first broadband model, but it makes important assumptions:

- The nanoisland film is replaced by a homogeneous effective layer.
- The top part of the sample is treated coherently, but the thick glass is treated incoherently.
- The substrate is modeled as a single homogeneous glass slab.
- The host medium for the effective-medium calculation is air.
- The morphology enters through `effe`, `Rave_nm`, and the two-lognormal size distribution, rather than through a full spatial electromagnetic simulation.

So the solver is best interpreted as:

- a physically structured effective-medium + thin-film model
- with substrate optics treated in a standard hybrid coherent/incoherent way
- intended for rapid comparison against experimental transmittance spectra

## 10. One-Line Summary of the Main Outputs

- `T_total` -> the model prediction to compare with experiment
- `T_front` -> coherent thin-film transmittance of `air | effective Ag layer | ITO | glass`
- `A_glass` -> Beer-Lambert attenuation through the glass substrate
- `T_back` -> transmittance of the `glass -> air` exit interface
- `R_front_air` -> reflectance of the front stack seen from air
- `R_front_glass` -> reflectance of the front stack seen from glass
- `R_back` -> reflectance of the `glass -> air` back interface
- `eps_eff_*` -> effective permittivity of the nanoisland layer
- `eps_ito_*` -> ITO permittivity
- `eps_glass_*` -> glass permittivity
