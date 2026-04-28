#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Protocol, Sequence

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from model import bruggeman_lib, mg_lib, mmgm_single_lib  # noqa: E402

VERY_LARGE_SSE = 1.0e99


class OptimizerError(RuntimeError):
    """Raised when the global optimizer orchestration fails."""


@dataclass(frozen=True)
class PlotWindow:
    min_nm: float
    max_nm: float


@dataclass(frozen=True)
class OutputPaths:
    output_dir: Path
    gnuplot_dir: Path
    image_dir: Path
    tmp_dir: Path


@dataclass(frozen=True)
class Spectrum:
    path: Path
    wavelengths_nm: list[float]
    transmittance: list[float]

    @property
    def basename(self) -> str:
        return self.path.stem

    @property
    def grid(self) -> tuple[float, float, float, int]:
        if len(self.wavelengths_nm) < 2:
            raise OptimizerError(f"Spectrum has too few points: {self.path}")
        return (
            self.wavelengths_nm[0],
            self.wavelengths_nm[-1],
            self.wavelengths_nm[1] - self.wavelengths_nm[0],
            len(self.wavelengths_nm),
        )


@dataclass(frozen=True)
class TimedSpectrum:
    time_s: int
    spectrum: Spectrum


@dataclass(frozen=True)
class FitWindow:
    min_nm: float
    max_nm: float


@dataclass(frozen=True)
class ModelBounds:
    effe_min: float
    effe_max: float
    thickness_min_nm: float
    thickness_max_nm: float
    thickness_transform: str
    fit_window: FitWindow
    population_size: int = 24
    max_generations: int = 80
    seed: int = 12345


@dataclass(frozen=True)
class SpectrumFit:
    time_s: int
    experimental: Spectrum
    theoretical_path: Path
    effe: float
    thickness_nm: float
    h_ag_nm: float
    sse: float
    objective_points: int
    invalid_points: int


@dataclass(frozen=True)
class GlobalFit:
    total_sse: float
    spectra: list[SpectrumFit]

    @property
    def total_finite_points(self) -> int:
        return sum(fit.objective_points for fit in self.spectra)


@dataclass(frozen=True)
class ModelSelection:
    model: str
    geometry: str


class ModelLib(Protocol):
    MODEL_NAME: str
    DISPLAY_NAME: str

    def configure_effective_medium(
        self,
        effective_medium: dict[str, Any],
        *,
        geometry: str,
        effe: float,
        rave_nm: float | None = None,
        sig_l: float | None = None,
    ) -> None: ...


MODEL_LIBS: dict[str, ModelLib] = {
    mg_lib.MODEL_NAME: mg_lib,
    bruggeman_lib.MODEL_NAME: bruggeman_lib,
    "mmgm_spheres_single": mmgm_single_lib,
    "mmgm_holes_single": mmgm_single_lib,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Globally optimize Nublar transmittance model parameters with a "
            "monotonic silver-volume constraint."
        )
    )
    model_group = parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument("--mg-spheres", action="store_true")
    model_group.add_argument("--mg-holes", action="store_true")
    model_group.add_argument("--bruggeman-spheres", action="store_true")
    model_group.add_argument("--bruggeman-holes", action="store_true")
    model_group.add_argument("--mmgm-spheres-single", action="store_true")
    model_group.add_argument("--mmgm-holes-single", action="store_true")
    parser.add_argument("--template-json", type=Path, default=Path("data/input/sample.json"))
    parser.add_argument("--bounds-json", type=Path, default=Path("data/input/optimal/bounds.json"))
    parser.add_argument("--spectra-dir", type=Path, default=Path("data/experimental/final/transmittance"))
    parser.add_argument("--transmittance-exe", type=Path, default=Path("bin/transmittance"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/output/optimal_global"))
    parser.add_argument("--gnuplot-dir", type=Path, default=Path("scripts/gnuplot/optimal_global"))
    parser.add_argument("--image-dir", type=Path, default=Path("img/optimal_global"))
    parser.add_argument("--tmp-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-generations", type=int, default=None)
    parser.add_argument("--population-size", type=int, default=None)
    return parser.parse_args()


def selected_model(args: argparse.Namespace) -> ModelSelection:
    if args.mg_spheres:
        return ModelSelection(model="mg", geometry="spheres")
    if args.mg_holes:
        return ModelSelection(model="mg", geometry="holes")
    if args.bruggeman_spheres:
        return ModelSelection(model="bruggeman", geometry="spheres")
    if args.bruggeman_holes:
        return ModelSelection(model="bruggeman", geometry="holes")
    if args.mmgm_spheres_single:
        return ModelSelection(model="mmgm_spheres_single", geometry="spheres")
    if args.mmgm_holes_single:
        return ModelSelection(model="mmgm_holes_single", geometry="holes")
    raise OptimizerError("No supported model selected")


def model_lib(selection: ModelSelection) -> ModelLib:
    try:
        return MODEL_LIBS[selection.model]
    except KeyError as exc:
        raise OptimizerError(f"No model library registered for {selection.model}") from exc


def output_paths(args: argparse.Namespace, selection: ModelSelection, model: ModelLib) -> OutputPaths:
    output_dir = args.output_dir / model.MODEL_NAME / selection.geometry
    return OutputPaths(
        output_dir=output_dir,
        gnuplot_dir=args.gnuplot_dir / model.MODEL_NAME / selection.geometry,
        image_dir=args.image_dir / model.MODEL_NAME / selection.geometry,
        tmp_dir=(
            args.tmp_dir / model.MODEL_NAME / selection.geometry / "tmp"
            if args.tmp_dir
            else output_dir / "tmp"
        ),
    )


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def read_bounds(path: Path, model_name: str) -> ModelBounds:
    raw = json.loads(_strip_markdown_fence(path.read_text(encoding="utf-8")))
    objective = raw["global"]["objective"]
    fit_window_raw = objective["fit_window_nm"]
    params = raw["models"][model_name]["native_fit_parameters"]
    differential_evolution = (
        raw["models"][model_name].get("optimizer", {}).get("differential_evolution", {})
    )
    fit_window = FitWindow(
        min_nm=float(fit_window_raw["min"]),
        max_nm=float(fit_window_raw["max"]),
    )
    if fit_window.min_nm > fit_window.max_nm:
        raise OptimizerError(
            "Invalid objective fit window: "
            f"{fit_window.min_nm} > {fit_window.max_nm}"
        )
    return ModelBounds(
        effe_min=float(params["effe"]["min"]),
        effe_max=float(params["effe"]["max"]),
        thickness_min_nm=float(params["thickness_nm"]["min"]),
        thickness_max_nm=float(params["thickness_nm"]["max"]),
        thickness_transform=str(params["thickness_nm"].get("transform", "log")),
        fit_window=fit_window,
        population_size=int(differential_evolution.get("population_size", 24)),
        max_generations=int(differential_evolution.get("max_generations", 80)),
        seed=int(differential_evolution.get("seed", 12345)),
    )


def transform_value(minimum: float, maximum: float, transform: str, unit_value: float) -> float:
    if transform == "log":
        if minimum <= 0.0 or maximum <= 0.0:
            raise OptimizerError("Log-spaced bounds must be positive")
        return math.exp(math.log(minimum) + unit_value * (math.log(maximum) - math.log(minimum)))
    return minimum + unit_value * (maximum - minimum)


def load_template(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_trial_json(path: Path, model: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")


def prepare_trial_model(
    *,
    template: dict[str, Any],
    model_lib: ModelLib,
    spectrum: Spectrum,
    geometry: str,
    effe: float,
    thickness_nm: float,
) -> dict[str, Any]:
    model = json.loads(json.dumps(template))
    grid_min, grid_max, grid_step, _ = spectrum.grid
    model["wavelength_grid_nm"] = {
        "min": grid_min,
        "max": grid_max,
        "step": grid_step,
    }

    for layer in model["stack"]["layers"]:
        if layer.get("kind") != "effective_medium":
            continue
        layer["thickness_nm"] = thickness_nm
        model_lib.configure_effective_medium(
            layer["effective_medium"],
            geometry=geometry,
            effe=effe,
        )
        return model

    raise OptimizerError("Template JSON has no effective_medium layer")


def read_experimental_spectrum(path: Path) -> Spectrum:
    """Read an experimental spectrum: wavelength [col 0], transmittance [col 2]."""
    wavelengths: list[float] = []
    transmittance: list[float] = []
    total_data_lines = 0
    skipped_lines = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        total_data_lines += 1
        parts = stripped.split()
        if len(parts) < 3:
            skipped_lines += 1
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[2])
        except ValueError:
            skipped_lines += 1
            continue
        if not math.isfinite(wavelength) or not math.isfinite(value):
            raise OptimizerError(f"Non-finite experimental value in {path}: {line}")
        wavelengths.append(wavelength)
        transmittance.append(value)

    if not wavelengths:
        raise OptimizerError(f"No experimental spectrum rows found in {path}")
    if len(wavelengths) < 0.5 * total_data_lines:
        raise OptimizerError(
            f"Too many skipped experimental rows in {path}: "
            f"parsed {len(wavelengths)} of {total_data_lines} non-comment lines "
            f"(skipped {skipped_lines})"
        )
    return Spectrum(path=path, wavelengths_nm=wavelengths, transmittance=transmittance)


def validate_uniform_grid(spectrum: Spectrum) -> None:
    wavelengths = spectrum.wavelengths_nm
    if len(wavelengths) < 2:
        raise OptimizerError(f"Spectrum has too few points: {spectrum.path}")
    step = wavelengths[1] - wavelengths[0]
    if step <= 0.0:
        raise OptimizerError(f"Spectrum grid is not increasing: {spectrum.path}")
    for previous, current in zip(wavelengths, wavelengths[1:], strict=False):
        if abs((current - previous) - step) > 1e-9:
            raise OptimizerError(f"Spectrum grid is not uniform: {spectrum.path}")


def covers_fit_window(spectrum: Spectrum, fit_window: FitWindow) -> bool:
    grid_min, grid_max, _, _ = spectrum.grid
    return grid_min <= fit_window.min_nm and grid_max >= fit_window.max_nm


def common_plot_window(spectra: Sequence[Spectrum]) -> PlotWindow:
    if not spectra:
        raise OptimizerError("No spectra found")
    common_min = max(spectrum.grid[0] for spectrum in spectra)
    common_max = min(spectrum.grid[1] for spectrum in spectra)
    if common_min >= common_max:
        raise OptimizerError(
            "No positive common wavelength range exists across the transmittance spectra"
        )
    return PlotWindow(min_nm=common_min, max_nm=common_max)


def deposition_time_seconds(path: Path) -> int:
    match = re.search(r"(?:^|_)(\d+)s(?:_|$)", path.stem)
    if match is None:
        raise OptimizerError(
            f"Could not infer deposition/exposure time from spectrum filename: {path.name}"
        )
    return int(match.group(1))


def discover_spectra(spectra_dir: Path) -> list[Path]:
    if not spectra_dir.is_dir():
        raise OptimizerError(f"Missing spectra directory: {spectra_dir}")
    paths = [
        path
        for path in spectra_dir.glob("*.dat")
        if path.name != "transmittance_manifest.dat"
    ]
    return sorted(paths, key=lambda path: (deposition_time_seconds(path), path.name))


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def gnuplot_relative(path: Path, target_path: Path) -> str:
    return os.path.relpath(target_path.resolve(), start=path.parent.resolve())


def output_stem(experimental_basename: str) -> str:
    return f"optimal_global_{experimental_basename}"


def read_model_spectrum(path: Path) -> Spectrum:
    """Read model output: wavelength [col 0], transmittance [col 2]."""
    wavelengths: list[float] = []
    transmittance: list[float] = []
    total_data_lines = 0
    skipped_lines = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        total_data_lines += 1
        parts = stripped.split()
        if len(parts) < 3:
            skipped_lines += 1
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[2])
        except ValueError:
            skipped_lines += 1
            continue
        if not math.isfinite(wavelength):
            raise OptimizerError(f"Non-finite model wavelength in {path}: {line}")
        wavelengths.append(wavelength)
        transmittance.append(value)
    if not wavelengths:
        raise OptimizerError(f"No model spectrum rows found in {path}")
    if len(wavelengths) < 0.5 * total_data_lines:
        raise OptimizerError(
            f"Too many skipped model rows in {path}: "
            f"parsed {len(wavelengths)} of {total_data_lines} non-comment lines "
            f"(skipped {skipped_lines})"
        )
    return Spectrum(path=path, wavelengths_nm=wavelengths, transmittance=transmittance)


def grids_compatible(
    g1: tuple[float, float, float, int],
    g2: tuple[float, float, float, int],
    tol: float = 1e-6,
) -> bool:
    return (
        abs(g1[0] - g2[0]) < tol
        and abs(g1[1] - g2[1]) < tol
        and abs(g1[2] - g2[2]) < tol
        and g1[3] == g2[3]
    )


def finite_objective_points(
    experimental: Spectrum,
    theoretical: Spectrum,
    fit_window: FitWindow,
) -> tuple[int, int]:
    valid_points = 0
    invalid_points = 0
    for wavelength, exp_t, model_t in zip(
        experimental.wavelengths_nm,
        experimental.transmittance,
        theoretical.transmittance,
        strict=True,
    ):
        if wavelength < fit_window.min_nm or wavelength > fit_window.max_nm:
            continue
        if math.isfinite(exp_t) and math.isfinite(model_t):
            valid_points += 1
        else:
            invalid_points += 1
    return valid_points, invalid_points


def sse_transmittance(
    experimental: Spectrum,
    theoretical: Spectrum,
    fit_window: FitWindow,
) -> tuple[float, int, int]:
    if len(experimental.wavelengths_nm) != len(theoretical.wavelengths_nm):
        raise OptimizerError(
            "Experimental/model wavelength grids differ in length: "
            f"{experimental.path} vs {theoretical.path}"
        )
    if not grids_compatible(experimental.grid, theoretical.grid):
        raise OptimizerError(
            "Experimental/model wavelength grids differ: "
            f"{experimental.grid} vs {theoretical.grid}"
        )
    sse = 0.0
    n_points = 0
    for exp_w, exp_t, model_w, model_t in zip(
        experimental.wavelengths_nm,
        experimental.transmittance,
        theoretical.wavelengths_nm,
        theoretical.transmittance,
        strict=True,
    ):
        if abs(exp_w - model_w) > 1e-6:
            raise OptimizerError(
                f"Experimental/model wavelengths differ: {exp_w} vs {model_w}"
            )
        if exp_w < fit_window.min_nm or exp_w > fit_window.max_nm:
            continue
        if not math.isfinite(exp_t) or not math.isfinite(model_t):
            continue
        residual = model_t - exp_t
        sse += residual * residual
        n_points += 1
    if n_points == 0:
        raise OptimizerError(
            "No finite wavelength points available for SSE inside "
            f"{fit_window.min_nm}-{fit_window.max_nm} nm"
        )
    valid_points, invalid_points = finite_objective_points(
        experimental, theoretical, fit_window
    )
    return sse, valid_points, invalid_points


def parameters_from_unit_vector(
    unit_values: Sequence[float],
    bounds: ModelBounds,
) -> list[tuple[float, float]]:
    if len(unit_values) % 2 != 0:
        raise OptimizerError("MG/Bruggeman global parameter vector must have even length")
    parameters: list[tuple[float, float]] = []
    for index in range(0, len(unit_values), 2):
        effe = transform_value(bounds.effe_min, bounds.effe_max, "none", unit_values[index])
        thickness_nm = transform_value(
            bounds.thickness_min_nm,
            bounds.thickness_max_nm,
            bounds.thickness_transform,
            unit_values[index + 1],
        )
        parameters.append((effe, thickness_nm))
    return parameters


def h_ag_values(parameters: Sequence[tuple[float, float]]) -> list[float]:
    return [effe * thickness_nm for effe, thickness_nm in parameters]


def violates_monotonic_h_ag(parameters: Sequence[tuple[float, float]]) -> bool:
    values = h_ag_values(parameters)
    return any(left > right for left, right in zip(values, values[1:], strict=False))


def feasible_initial_population(
    *,
    n_spectra: int,
    bounds: ModelBounds,
    population_count: int,
) -> list[list[float]]:
    rng = random.Random(bounds.seed)
    population: list[list[float]] = [[0.5] * (2 * n_spectra)]
    while len(population) < population_count:
        thickness_unit = rng.random()
        thickness_nm = transform_value(
            bounds.thickness_min_nm,
            bounds.thickness_max_nm,
            bounds.thickness_transform,
            thickness_unit,
        )
        h_min = bounds.effe_min * thickness_nm
        h_max = bounds.effe_max * thickness_nm
        h_units = sorted(rng.random() for _ in range(n_spectra))
        candidate: list[float] = []
        for h_unit in h_units:
            h_ag_nm = h_min + h_unit * (h_max - h_min)
            effe = h_ag_nm / thickness_nm
            effe_unit = (effe - bounds.effe_min) / (bounds.effe_max - bounds.effe_min)
            candidate.extend([effe_unit, thickness_unit])
        population.append(candidate)
    return population


def evaluate_spectrum_candidate(
    *,
    transmittance_exe: Path,
    template: dict[str, Any],
    model: ModelLib,
    experimental: Spectrum,
    geometry: str,
    fit_window: FitWindow,
    effe: float,
    thickness_nm: float,
    trial_json_path: Path,
    trial_spectrum_path: Path,
) -> tuple[float, int, int]:
    prepared_model = prepare_trial_model(
        template=template,
        model_lib=model,
        spectrum=experimental,
        geometry=geometry,
        effe=effe,
        thickness_nm=thickness_nm,
    )
    write_trial_json(trial_json_path, prepared_model)
    trial_spectrum_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            transmittance_exe.as_posix(),
            trial_json_path.as_posix(),
            "--output",
            trial_spectrum_path.as_posix(),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    theoretical = read_model_spectrum(trial_spectrum_path)
    return sse_transmittance(experimental, theoretical, fit_window)


def optimize_global(
    *,
    transmittance_exe: Path,
    template: dict[str, Any],
    bounds: ModelBounds,
    model: ModelLib,
    geometry: str,
    spectra: Sequence[TimedSpectrum],
    paths: OutputPaths,
) -> GlobalFit:
    best: GlobalFit | None = None
    n_parameters = 2 * len(spectra)
    tmp_trial_dir = paths.tmp_dir / "trials"

    def evaluate_unit_vector(unit_values: Sequence[float]) -> float:
        nonlocal best
        parameters = parameters_from_unit_vector(unit_values, bounds)
        if violates_monotonic_h_ag(parameters):
            return VERY_LARGE_SSE

        fits: list[SpectrumFit] = []
        total_sse = 0.0
        for index, (timed_spectrum, (effe, thickness_nm)) in enumerate(
            zip(spectra, parameters, strict=True)
        ):
            trial_stem = f"{timed_spectrum.spectrum.basename}_global_trial_{index}"
            trial_json_path = tmp_trial_dir / f"{trial_stem}.json"
            trial_spectrum_path = tmp_trial_dir / f"{trial_stem}.dat"
            sse, valid_points, invalid_points = evaluate_spectrum_candidate(
                transmittance_exe=transmittance_exe,
                template=template,
                model=model,
                experimental=timed_spectrum.spectrum,
                geometry=geometry,
                fit_window=bounds.fit_window,
                effe=effe,
                thickness_nm=thickness_nm,
                trial_json_path=trial_json_path,
                trial_spectrum_path=trial_spectrum_path,
            )
            total_sse += sse
            fits.append(
                SpectrumFit(
                    time_s=timed_spectrum.time_s,
                    experimental=timed_spectrum.spectrum,
                    theoretical_path=paths.output_dir
                    / f"{output_stem(timed_spectrum.spectrum.basename)}.dat",
                    effe=effe,
                    thickness_nm=thickness_nm,
                    h_ag_nm=effe * thickness_nm,
                    sse=sse,
                    objective_points=valid_points,
                    invalid_points=invalid_points,
                )
            )

        if best is None or total_sse < best.total_sse:
            best = GlobalFit(total_sse=total_sse, spectra=fits)
            for index, (fit, timed_spectrum) in enumerate(zip(fits, spectra, strict=True)):
                trial_spectrum_path = (
                    tmp_trial_dir
                    / f"{timed_spectrum.spectrum.basename}_global_trial_{index}.dat"
                )
                fit.theoretical_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(trial_spectrum_path, fit.theoretical_path)
            print(
                "new global best:\n"
                f"  total_SSE={total_sse:.8g}\n"
                "  hAg=["
                + ", ".join(f"{fit.h_ag_nm:.6g}" for fit in fits)
                + "]",
                flush=True,
            )
        return total_sse

    try:
        from scipy.optimize import differential_evolution
    except ImportError as exc:
        raise OptimizerError(
            "SciPy is required for global optimization. Install scipy to use this tool."
        ) from exc

    scipy_popsize = max(1, math.ceil(bounds.population_size / float(n_parameters)))
    population_count = max(5, scipy_popsize * n_parameters)
    init_population = feasible_initial_population(
        n_spectra=len(spectra),
        bounds=bounds,
        population_count=population_count,
    )
    differential_evolution(
        lambda x: evaluate_unit_vector(tuple(float(value) for value in x)),
        bounds=[(0.0, 1.0)] * n_parameters,
        maxiter=bounds.max_generations,
        popsize=scipy_popsize,
        seed=bounds.seed,
        polish=False,
        init=init_population,
        updating="immediate",
        workers=1,
    )

    if best is None:
        raise OptimizerError("No valid monotonic global candidates were evaluated")
    return best


def write_gnuplot_script(
    *,
    path: Path,
    image_path: Path,
    experimental: Spectrum,
    theoretical_path: Path,
    fit: SpectrumFit,
    model: ModelLib,
    geometry: str,
    fit_window: FitWindow,
    plot_window: PlotWindow,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    title = (
        f"GLOBAL {model.DISPLAY_NAME} {geometry} fit {experimental.basename}: "
        f"effe={fit.effe:.5g}, d={fit.thickness_nm:.5g} nm, "
        f"hAg={fit.h_ag_nm:.5g} nm, SSE={fit.sse:.5g}"
    )
    path.write_text(
        "\n".join(
            [
                "set terminal pngcairo noenhanced size 1400,900",
                f"set output '{gnuplot_relative(path, image_path)}'",
                f"set title '{title}'",
                "set datafile commentschars '#'",
                "set grid",
                "set xlabel 'Wavelength (nm)'",
                "set ylabel 'Transmittance'",
                f"set xrange [{plot_window.min_nm:g}:{plot_window.max_nm:g}]",
                "set key outside right",
                (
                    f"set arrow from {fit_window.min_nm:g}, graph 0 to "
                    f"{fit_window.min_nm:g}, graph 1 nohead dashtype 2"
                ),
                (
                    f"set arrow from {fit_window.max_nm:g}, graph 0 to "
                    f"{fit_window.max_nm:g}, graph 1 nohead dashtype 2"
                ),
                f"set label 'fit window' at {fit_window.min_nm:g}, graph 0.95",
                "plot \\",
                (
                    f"  '{gnuplot_relative(path, experimental.path)}' using 1:3 "
                    "with lines lw 2 title 'experimental', \\"
                ),
                (
                    f"  '{gnuplot_relative(path, theoretical_path)}' using 1:3 "
                    f"with lines lw 2 title 'global {model.MODEL_NAME} {geometry} fit'"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_result_json(
    *,
    path: Path,
    experimental: Spectrum,
    theoretical_path: Path,
    gnuplot_path: Path,
    image_path: Path,
    fit: SpectrumFit,
    bounds: ModelBounds,
    model: ModelLib,
    geometry: str,
    plot_window: PlotWindow,
) -> None:
    grid_min, grid_max, grid_step, full_spectrum_points = experimental.grid
    mse = fit.sse / fit.objective_points
    rmse = math.sqrt(mse)
    result = {
        "model": model.MODEL_NAME,
        "geometry": geometry,
        "global_fit": True,
        "experimental_file": project_relative(experimental.path),
        "theoretical_file": project_relative(theoretical_path),
        "gnuplot_script": project_relative(gnuplot_path),
        "image_file": project_relative(image_path),
        "best_parameters": {
            "effe": fit.effe,
            "thickness_nm": fit.thickness_nm,
            "h_ag_nm": fit.h_ag_nm,
        },
        "objective_window_nm": {
            "min": bounds.fit_window.min_nm,
            "max": bounds.fit_window.max_nm,
        },
        "plot_window_nm": {
            "min": plot_window.min_nm,
            "max": plot_window.max_nm,
        },
        "objective": {
            "sse": fit.sse,
            "mse": mse,
            "rmse": rmse,
            "finite_points": fit.objective_points,
            "invalid_points": fit.invalid_points,
        },
        "wavelength_grid_nm": {
            "min": grid_min,
            "max": grid_max,
            "step": grid_step,
        },
        "full_spectrum_points": full_spectrum_points,
    }
    if fit.invalid_points > 0:
        result["warnings"] = ["non_finite_points_present"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def write_global_summary_json(
    *,
    path: Path,
    global_fit: GlobalFit,
    bounds: ModelBounds,
    model: ModelLib,
    geometry: str,
    n_parameters: int,
) -> None:
    result = {
        "model": model.MODEL_NAME,
        "geometry": geometry,
        "global_fit": True,
        "constraint": {
            "name": "monotonic_silver_volume_per_area",
            "quantity": "h_ag_nm = effe * thickness_nm",
            "enforced": True,
        },
        "objective": {
            "total_sse": global_fit.total_sse,
            "total_finite_points": global_fit.total_finite_points,
            "n_parameters": n_parameters,
        },
        "optimizer": {
            "method": "differential_evolution",
            "seed": bounds.seed,
            "max_generations": bounds.max_generations,
            "population_size": bounds.population_size,
            "scipy_popsize": max(1, math.ceil(bounds.population_size / float(n_parameters))),
            "bounds": asdict(bounds),
        },
        "spectra": [
            {
                "time_s": fit.time_s,
                "spectrum": fit.experimental.basename,
                "sse": fit.sse,
                "effe": fit.effe,
                "thickness_nm": fit.thickness_nm,
                "h_ag_nm": fit.h_ag_nm,
            }
            for fit in global_fit.spectra
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def run_gnuplot(script_path: Path) -> None:
    if shutil.which("gnuplot") is None:
        raise OptimizerError("gnuplot is required but was not found on PATH")
    subprocess.run(["gnuplot", script_path.name], check=True, cwd=script_path.parent)


def run_global_effective_medium(args: argparse.Namespace, selection: ModelSelection) -> int:
    if selection.model in {"mmgm_spheres_single", "mmgm_holes_single"}:
        raise OptimizerError(
            "Global MMGM single-lognormal mode is scaffolded but not implemented yet. "
            "Supported global modes are --mg-spheres, --mg-holes, "
            "--bruggeman-spheres, and --bruggeman-holes."
        )
    if not args.transmittance_exe.exists():
        raise OptimizerError(
            f"Missing forward executable: {args.transmittance_exe}. Run `make bin/transmittance`."
        )

    selected_lib = model_lib(selection)
    template = load_template(args.template_json)
    bounds = read_bounds(args.bounds_json, selection.model)
    if args.seed is not None:
        bounds = replace(bounds, seed=args.seed)
    if args.max_generations is not None:
        bounds = replace(bounds, max_generations=args.max_generations)
    if args.population_size is not None:
        bounds = replace(bounds, population_size=args.population_size)
    if bounds.population_size <= 0:
        raise OptimizerError("--population-size must be positive")
    if bounds.max_generations < 0:
        raise OptimizerError("--max-generations must be non-negative")

    spectra_paths = discover_spectra(args.spectra_dir)
    timed_spectra = [
        TimedSpectrum(
            time_s=deposition_time_seconds(path),
            spectrum=read_experimental_spectrum(path),
        )
        for path in spectra_paths
    ]
    for timed_spectrum in timed_spectra:
        validate_uniform_grid(timed_spectrum.spectrum)
        if not covers_fit_window(timed_spectrum.spectrum, bounds.fit_window):
            raise OptimizerError(
                f"{timed_spectrum.spectrum.path} grid {timed_spectrum.spectrum.grid} "
                f"does not cover the objective fit window "
                f"{bounds.fit_window.min_nm:g}-{bounds.fit_window.max_nm:g} nm"
            )
    if not timed_spectra:
        raise OptimizerError(f"No spectra found in {args.spectra_dir}")

    spectra_only = [timed_spectrum.spectrum for timed_spectrum in timed_spectra]
    plot_window = common_plot_window(spectra_only)
    paths = output_paths(args, selection, selected_lib)
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    paths.gnuplot_dir.mkdir(parents=True, exist_ok=True)
    paths.image_dir.mkdir(parents=True, exist_ok=True)
    paths.tmp_dir.mkdir(parents=True, exist_ok=True)

    n_parameters = 2 * len(timed_spectra)
    print(
        f"{selected_lib.DISPLAY_NAME} {selection.geometry} global fit:\n"
        f"  spectra: {len(timed_spectra)}\n"
        f"  parameters: {n_parameters}\n"
        "  constraint: hAg monotonic increasing\n"
        "  optimizer: differential_evolution, "
        f"seed={bounds.seed}, population_size={bounds.population_size}, "
        f"max_generations={bounds.max_generations}",
        flush=True,
    )

    global_fit = optimize_global(
        transmittance_exe=args.transmittance_exe,
        template=template,
        bounds=bounds,
        model=selected_lib,
        geometry=selection.geometry,
        spectra=timed_spectra,
        paths=paths,
    )

    for fit in global_fit.spectra:
        stem = output_stem(fit.experimental.basename)
        result_path = paths.output_dir / f"{stem}.json"
        gnuplot_path = paths.gnuplot_dir / f"{stem}.gp"
        image_path = paths.image_dir / f"{stem}.png"
        write_result_json(
            path=result_path,
            experimental=fit.experimental,
            theoretical_path=fit.theoretical_path,
            gnuplot_path=gnuplot_path,
            image_path=image_path,
            fit=fit,
            bounds=bounds,
            model=selected_lib,
            geometry=selection.geometry,
            plot_window=plot_window,
        )
        write_gnuplot_script(
            path=gnuplot_path,
            image_path=image_path,
            experimental=fit.experimental,
            theoretical_path=fit.theoretical_path,
            fit=fit,
            model=selected_lib,
            geometry=selection.geometry,
            fit_window=bounds.fit_window,
            plot_window=plot_window,
        )
        run_gnuplot(gnuplot_path)

    write_global_summary_json(
        path=paths.output_dir / "global_result.json",
        global_fit=global_fit,
        bounds=bounds,
        model=selected_lib,
        geometry=selection.geometry,
        n_parameters=n_parameters,
    )
    print(f"Done. Wrote {paths.output_dir / 'global_result.json'}")
    return 0


def main() -> int:
    args = parse_args()
    return run_global_effective_medium(args, selected_model(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OptimizerError,
        mg_lib.MgModelError,
        bruggeman_lib.BruggemanModelError,
        mmgm_single_lib.MmgmSingleModelError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
