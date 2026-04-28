#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Protocol

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from model import bruggeman_lib, mg_lib, mmgm_single_lib  # noqa: E402

VERY_LARGE_SSE = 1.0e99
LOGNORMAL_P95_Z = 1.6448536269514722
LOGNORMAL_P99_Z = 2.3263478740408408


class OptimizerError(RuntimeError):
    """Raised when the optimizer orchestration fails."""


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
class FitWindow:
    min_nm: float
    max_nm: float


@dataclass(frozen=True)
class ThicknessTailConstraint:
    enabled: bool = False
    percentile: float = 0.95
    factor: float = 2.0
    mode: str = "reject"


@dataclass(frozen=True)
class ModelBounds:
    effe_min: float
    effe_max: float
    thickness_min_nm: float
    thickness_max_nm: float
    effe_points: int
    thickness_points: int
    thickness_transform: str
    fit_window: FitWindow
    rave_min_nm: float | None = None
    rave_max_nm: float | None = None
    rave_transform: str = "none"
    sig_l_min: float | None = None
    sig_l_max: float | None = None
    sig_l_transform: str = "none"
    optimizer_method: str = "grid"
    population_size: int = 16
    max_generations: int = 40
    seed: int = 12345
    thickness_tail_constraint: ThicknessTailConstraint = ThicknessTailConstraint()


@dataclass(frozen=True)
class Candidate:
    effe: float
    thickness_nm: float
    sse: float
    spectrum_path: Path
    objective_points: int
    invalid_points: int
    rave_nm: float | None = None
    sig_l: float | None = None


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

    def result_parameters(
        self,
        effe: float,
        thickness_nm: float,
        rave_nm: float | None = None,
        sig_l: float | None = None,
    ) -> dict[str, float]: ...


MODEL_LIBS: dict[str, ModelLib] = {
    mg_lib.MODEL_NAME: mg_lib,
    bruggeman_lib.MODEL_NAME: bruggeman_lib,
    "mmgm_spheres_single": mmgm_single_lib,
    "mmgm_holes_single": mmgm_single_lib,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optimize Nublar transmittance model parameters."
    )
    model_group = parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument(
        "--mg",
        action="store_true",
        help="Run v1 MG spheres grid search",
    )
    model_group.add_argument(
        "--mg-spheres",
        action="store_true",
        help="Run v1 MG spheres grid search",
    )
    model_group.add_argument(
        "--mg-holes",
        action="store_true",
        help="Run v1 MG holes grid search",
    )
    model_group.add_argument(
        "--bruggeman",
        action="store_true",
        help="Run v1 Bruggeman spheres grid search",
    )
    model_group.add_argument(
        "--bruggeman-spheres",
        action="store_true",
        help="Run v1 Bruggeman spheres grid search",
    )
    model_group.add_argument(
        "--bruggeman-holes",
        action="store_true",
        help="Run v1 Bruggeman holes grid search",
    )
    model_group.add_argument(
        "--mmgm-spheres-single",
        action="store_true",
        help="Run v1 MMGM spheres single-lognormal optimization",
    )
    model_group.add_argument(
        "--mmgm-holes-single",
        action="store_true",
        help="Run v1 MMGM holes single-lognormal optimization",
    )
    parser.add_argument("--template-json", type=Path, default=Path("data/input/sample.json"))
    parser.add_argument("--bounds-json", type=Path, default=Path("data/input/optimal/bounds.json"))
    parser.add_argument("--spectra-dir", type=Path, default=Path("data/experimental/final/transmittance"))
    parser.add_argument("--transmittance-exe", type=Path, default=Path("bin/transmittance"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/output/optimal"))
    parser.add_argument("--gnuplot-dir", type=Path, default=Path("scripts/gnuplot/optimal"))
    parser.add_argument("--image-dir", type=Path, default=Path("img/optimal"))
    parser.add_argument("--tmp-dir", type=Path, default=None)
    parser.add_argument(
        "--check-geometry-invariance",
        action="store_true",
        help="Run the Bruggeman spheres/holes geometry invariance diagnostic",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random seed for stochastic optimizers (MMGM only)",
    )
    parser.add_argument(
        "--max-generations",
        type=int,
        default=None,
        help="Override max generations for stochastic optimizers (MMGM only)",
    )
    return parser.parse_args()


def selected_model(args: argparse.Namespace) -> ModelSelection:
    if args.mg or args.mg_spheres:
        return ModelSelection(model="mg", geometry="spheres")
    if args.mg_holes:
        return ModelSelection(model="mg", geometry="holes")
    if args.bruggeman or args.bruggeman_spheres:
        return ModelSelection(model="bruggeman", geometry="spheres")
    if args.bruggeman_holes:
        return ModelSelection(model="bruggeman", geometry="holes")
    if args.mmgm_spheres_single:
        return ModelSelection(model="mmgm_spheres_single", geometry="spheres")
    if args.mmgm_holes_single:
        return ModelSelection(model="mmgm_holes_single", geometry="holes")
    raise OptimizerError("No supported model selected")


def output_paths(
    args: argparse.Namespace,
    selection: ModelSelection,
    model: ModelLib,
) -> OutputPaths:
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


def model_lib(selection: ModelSelection) -> ModelLib:
    try:
        return MODEL_LIBS[selection.model]
    except KeyError as exc:
        raise OptimizerError(f"No model library registered for {selection.model}") from exc


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


def read_thickness_tail_constraint(model: dict[str, Any]) -> ThicknessTailConstraint:
    raw = model.get("constraints", {}).get("thickness_tail", {})
    if not raw:
        return ThicknessTailConstraint()

    constraint = ThicknessTailConstraint(
        enabled=bool(raw.get("enabled", False)),
        percentile=float(raw.get("percentile", 0.95)),
        factor=float(raw.get("factor", 2.0)),
        mode=str(raw.get("mode", "reject")),
    )
    if constraint.percentile not in {0.95, 0.99}:
        raise OptimizerError(
            "Invalid thickness_tail percentile: "
            f"{constraint.percentile}. Supported values are 0.95 and 0.99."
        )
    if constraint.factor <= 0.0:
        raise OptimizerError(
            f"Invalid thickness_tail factor: {constraint.factor}. Must be positive."
        )
    if constraint.mode != "reject":
        raise OptimizerError(
            f"Invalid thickness_tail mode: {constraint.mode}. Only 'reject' is supported."
        )
    return constraint


def read_bounds(path: Path, model_name: str) -> ModelBounds:
    raw = json.loads(_strip_markdown_fence(path.read_text(encoding="utf-8")))
    objective = raw["global"]["objective"]
    fit_window_raw = objective["fit_window_nm"]
    model = raw["models"][model_name]
    params = model["native_fit_parameters"]
    grid = model.get("optimizer", {}).get("grid", {})
    differential_evolution = model.get("optimizer", {}).get("differential_evolution", {})

    effe_points = int(grid.get("v1_effe_points", grid.get("effe_points", 9)))
    thickness_points = int(grid.get("v1_thickness_points", grid.get("thickness_points", 9)))
    fit_window = FitWindow(
        min_nm=float(fit_window_raw["min"]),
        max_nm=float(fit_window_raw["max"]),
    )
    if fit_window.min_nm > fit_window.max_nm:
        raise OptimizerError(
            "Invalid objective fit window: "
            f"{fit_window.min_nm} > {fit_window.max_nm}"
        )

    rave = params.get("rave_nm")
    sig_l = params.get("sig_l")
    optimizer_method = str(model.get("optimizer", {}).get("global_method", "grid"))
    thickness_tail_constraint = read_thickness_tail_constraint(model)

    return ModelBounds(
        effe_min=float(params["effe"]["min"]),
        effe_max=float(params["effe"]["max"]),
        thickness_min_nm=float(params["thickness_nm"]["min"]),
        thickness_max_nm=float(params["thickness_nm"]["max"]),
        effe_points=effe_points,
        thickness_points=thickness_points,
        thickness_transform=str(params["thickness_nm"].get("transform", "none")),
        fit_window=fit_window,
        rave_min_nm=(float(rave["min"]) if rave else None),
        rave_max_nm=(float(rave["max"]) if rave else None),
        rave_transform=(str(rave.get("transform", "none")) if rave else "none"),
        sig_l_min=(float(sig_l["min"]) if sig_l else None),
        sig_l_max=(float(sig_l["max"]) if sig_l else None),
        sig_l_transform=(str(sig_l.get("transform", "none")) if sig_l else "none"),
        optimizer_method=optimizer_method,
        population_size=int(
            differential_evolution.get(
                "v1_population_size",
                differential_evolution.get("population_size", 16),
            )
        ),
        max_generations=int(
            differential_evolution.get(
                "v1_max_generations",
                differential_evolution.get("max_generations", 40),
            )
        ),
        seed=int(differential_evolution.get("seed", 12345)),
        thickness_tail_constraint=thickness_tail_constraint,
    )


def linspace(minimum: float, maximum: float, count: int) -> list[float]:
    if count < 2:
        return [minimum]
    step = (maximum - minimum) / float(count - 1)
    return [minimum + i * step for i in range(count)]


def logspace(minimum: float, maximum: float, count: int) -> list[float]:
    if minimum <= 0.0 or maximum <= 0.0:
        raise OptimizerError("Log-spaced bounds must be positive")
    return [
        math.exp(value)
        for value in linspace(math.log(minimum), math.log(maximum), count)
    ]


def transform_value(minimum: float, maximum: float, transform: str, unit_value: float) -> float:
    if transform == "log":
        if minimum <= 0.0 or maximum <= 0.0:
            raise OptimizerError("Log-spaced bounds must be positive")
        return math.exp(math.log(minimum) + unit_value * (math.log(maximum) - math.log(minimum)))
    return minimum + unit_value * (maximum - minimum)


def build_grid(bounds: ModelBounds) -> tuple[list[float], list[float]]:
    effe_values = linspace(bounds.effe_min, bounds.effe_max, bounds.effe_points)
    if bounds.thickness_transform == "log":
        thickness_values = logspace(
            bounds.thickness_min_nm,
            bounds.thickness_max_nm,
            bounds.thickness_points,
        )
    else:
        thickness_values = linspace(
            bounds.thickness_min_nm,
            bounds.thickness_max_nm,
            bounds.thickness_points,
        )
    return effe_values, thickness_values


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
    rave_nm: float | None = None,
    sig_l: float | None = None,
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
        if rave_nm is None or sig_l is None:
            model_lib.configure_effective_medium(
                layer["effective_medium"],
                geometry=geometry,
                effe=effe,
            )
        else:
            model_lib.configure_effective_medium(
                layer["effective_medium"],
                geometry=geometry,
                effe=effe,
                rave_nm=rave_nm,
                sig_l=sig_l,
            )
        return model

    raise OptimizerError("Template JSON has no effective_medium layer")


def read_experimental_spectrum(path: Path) -> Spectrum:
    """Read an experimental spectrum.

    Expected format: wavelength [col 0], transmittance [col 2].
    """
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


def common_plot_window(spectra: list[Spectrum]) -> PlotWindow:
    if not spectra:
        raise OptimizerError("No spectra found")
    common_min = max(spectrum.grid[0] for spectrum in spectra)
    common_max = min(spectrum.grid[1] for spectrum in spectra)
    if common_min >= common_max:
        raise OptimizerError(
            "No positive common wavelength range exists across the transmittance spectra"
        )
    return PlotWindow(min_nm=common_min, max_nm=common_max)


def discover_spectra(spectra_dir: Path) -> list[Path]:
    if not spectra_dir.is_dir():
        raise OptimizerError(f"Missing spectra directory: {spectra_dir}")
    return [
        path
        for path in sorted(spectra_dir.glob("*.dat"))
        if path.name != "transmittance_manifest.dat"
    ]


def project_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def gnuplot_relative(path: Path, target_path: Path) -> str:
    return os.path.relpath(target_path.resolve(), start=path.parent.resolve())


def trial_stem(experimental_basename: str) -> str:
    return f"{experimental_basename}_trial"


def output_stem(experimental_basename: str) -> str:
    return f"optimal_{experimental_basename}"


def read_model_spectrum(path: Path) -> Spectrum:
    """Read model output.

    Expected format: wavelength [col 0], transmittance [col 2].
    """
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


def evaluate_candidate(
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
    check_geometry_invariance: bool,
    rave_nm: float | None = None,
    sig_l: float | None = None,
) -> Candidate:
    prepared_model = prepare_trial_model(
        template=template,
        model_lib=model,
        spectrum=experimental,
        geometry=geometry,
        effe=effe,
        thickness_nm=thickness_nm,
        rave_nm=rave_nm,
        sig_l=sig_l,
    )
    write_trial_json(trial_json_path, prepared_model)
    trial_spectrum_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        transmittance_exe.as_posix(),
        trial_json_path.as_posix(),
        "--output",
        trial_spectrum_path.as_posix(),
    ]
    if check_geometry_invariance:
        command.append("--check-geometry-invariance")
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)

    theoretical = read_model_spectrum(trial_spectrum_path)
    sse, valid_points, invalid_points = sse_transmittance(
        experimental, theoretical, fit_window
    )
    return Candidate(
        effe=effe,
        thickness_nm=thickness_nm,
        sse=sse,
        spectrum_path=trial_spectrum_path,
        objective_points=valid_points,
        invalid_points=invalid_points,
        rave_nm=rave_nm,
        sig_l=sig_l,
    )


def optimize_spectrum(
    *,
    transmittance_exe: Path,
    template: dict[str, Any],
    bounds: ModelBounds,
    model: ModelLib,
    geometry: str,
    experimental: Spectrum,
    tmp_dir: Path,
    final_spectrum_path: Path,
    check_geometry_invariance: bool,
) -> Candidate:
    effe_values, thickness_values = build_grid(bounds)
    total = len(effe_values) * len(thickness_values)
    best: Candidate | None = None
    trial_name = trial_stem(experimental.basename)
    trial_json_path = tmp_dir / f"{trial_name}.json"
    trial_spectrum_path = tmp_dir / f"{trial_name}.dat"

    evaluation = 0
    for effe_index, effe in enumerate(effe_values, start=1):
        print(
            f"    effe row {effe_index}/{len(effe_values)} "
            f"(effe={effe:.6g}, evaluations {evaluation}/{total})",
            flush=True,
        )
        for thickness_nm in thickness_values:
            evaluation += 1
            candidate = evaluate_candidate(
                transmittance_exe=transmittance_exe,
                template=template,
                model=model,
                experimental=experimental,
                geometry=geometry,
                fit_window=bounds.fit_window,
                effe=effe,
                thickness_nm=thickness_nm,
                trial_json_path=trial_json_path,
                trial_spectrum_path=trial_spectrum_path,
                check_geometry_invariance=check_geometry_invariance,
            )
            if best is None or candidate.sse < best.sse:
                best = Candidate(
                    effe=candidate.effe,
                    thickness_nm=candidate.thickness_nm,
                    sse=candidate.sse,
                    spectrum_path=final_spectrum_path,
                    objective_points=candidate.objective_points,
                    invalid_points=candidate.invalid_points,
                )
                final_spectrum_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate.spectrum_path, final_spectrum_path)
                print(
                    "      new best: "
                    f"effe={best.effe:.6g}, thickness_nm={best.thickness_nm:.6g}, "
                    f"SSE={best.sse:.8g}",
                    flush=True,
                )

    if best is None:
        raise OptimizerError(f"No candidates evaluated for {experimental.path}")
    return best


def require_mmgm_single_bounds(bounds: ModelBounds) -> None:
    missing = []
    if bounds.rave_min_nm is None or bounds.rave_max_nm is None:
        missing.append("rave_nm")
    if bounds.sig_l_min is None or bounds.sig_l_max is None:
        missing.append("sig_l")
    if missing:
        raise OptimizerError(
            "MMGM single-lognormal bounds are missing parameter(s): "
            + ", ".join(missing)
        )


def lognormal_radius_descriptors(
    *, rave_nm: float, sig_l: float, thickness_nm: float
) -> dict[str, float]:
    mu_l = math.log(rave_nm) - 0.5 * sig_l * sig_l
    r_p95 = math.exp(mu_l + LOGNORMAL_P95_Z * sig_l)
    r_p99 = math.exp(mu_l + LOGNORMAL_P99_Z * sig_l)
    return {
        "mean_radius_nm": rave_nm,
        "median_radius_nm": math.exp(mu_l),
        "mode_radius_nm": math.exp(mu_l - sig_l * sig_l),
        "r_p95_nm": r_p95,
        "r_p99_nm": r_p99,
        "thickness_over_2rp95": thickness_nm / (2.0 * r_p95),
        "thickness_over_2rp99": thickness_nm / (2.0 * r_p99),
    }


def lognormal_radius_percentile(rave_nm: float, sig_l: float, percentile: float) -> float:
    z_value = {
        0.95: LOGNORMAL_P95_Z,
        0.99: LOGNORMAL_P99_Z,
    }[percentile]
    mu_l = math.log(rave_nm) - 0.5 * sig_l * sig_l
    return math.exp(mu_l + z_value * sig_l)


def violates_thickness_tail_constraint(
    thickness_nm: float,
    rave_nm: float,
    sig_l: float,
    bounds: ModelBounds,
) -> bool:
    constraint = bounds.thickness_tail_constraint
    if not constraint.enabled:
        return False
    radius_nm = lognormal_radius_percentile(rave_nm, sig_l, constraint.percentile)
    return thickness_nm > constraint.factor * radius_nm


def mmgm_single_parameters_from_unit_vector(
    unit_values: list[float] | tuple[float, float, float, float],
    bounds: ModelBounds,
) -> tuple[float, float, float, float]:
    require_mmgm_single_bounds(bounds)
    assert bounds.rave_min_nm is not None
    assert bounds.rave_max_nm is not None
    assert bounds.sig_l_min is not None
    assert bounds.sig_l_max is not None
    effe = transform_value(bounds.effe_min, bounds.effe_max, "none", unit_values[0])
    thickness_nm = transform_value(
        bounds.thickness_min_nm,
        bounds.thickness_max_nm,
        bounds.thickness_transform,
        unit_values[1],
    )
    rave_nm = transform_value(
        bounds.rave_min_nm,
        bounds.rave_max_nm,
        bounds.rave_transform,
        unit_values[2],
    )
    sig_l = transform_value(
        bounds.sig_l_min,
        bounds.sig_l_max,
        bounds.sig_l_transform,
        unit_values[3],
    )
    return effe, thickness_nm, rave_nm, sig_l


def optimize_mmgm_single_spectrum(
    *,
    transmittance_exe: Path,
    template: dict[str, Any],
    bounds: ModelBounds,
    model: ModelLib,
    geometry: str,
    experimental: Spectrum,
    tmp_dir: Path,
    final_spectrum_path: Path,
) -> Candidate:
    require_mmgm_single_bounds(bounds)
    best: Candidate | None = None
    trial_name = trial_stem(experimental.basename)
    trial_json_path = tmp_dir / f"{trial_name}.json"
    trial_spectrum_path = tmp_dir / f"{trial_name}.dat"

    def evaluate_unit_vector(unit_values: list[float] | tuple[float, float, float, float]) -> float:
        nonlocal best
        effe, thickness_nm, rave_nm, sig_l = mmgm_single_parameters_from_unit_vector(
            unit_values, bounds
        )
        if violates_thickness_tail_constraint(thickness_nm, rave_nm, sig_l, bounds):
            return VERY_LARGE_SSE
        candidate = evaluate_candidate(
            transmittance_exe=transmittance_exe,
            template=template,
            model=model,
            experimental=experimental,
            geometry=geometry,
            fit_window=bounds.fit_window,
            effe=effe,
            thickness_nm=thickness_nm,
            trial_json_path=trial_json_path,
            trial_spectrum_path=trial_spectrum_path,
            check_geometry_invariance=False,
            rave_nm=rave_nm,
            sig_l=sig_l,
        )
        if best is None or candidate.sse < best.sse:
            best = Candidate(
                effe=candidate.effe,
                thickness_nm=candidate.thickness_nm,
                sse=candidate.sse,
                spectrum_path=final_spectrum_path,
                objective_points=candidate.objective_points,
                invalid_points=candidate.invalid_points,
                rave_nm=candidate.rave_nm,
                sig_l=candidate.sig_l,
            )
            final_spectrum_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate.spectrum_path, final_spectrum_path)
            print(
                "      new best: "
                f"effe={best.effe:.6g}, thickness_nm={best.thickness_nm:.6g}, "
                f"rave_nm={best.rave_nm:.6g}, sig_l={best.sig_l:.6g}, "
                f"SSE={best.sse:.8g}",
                flush=True,
            )
        return candidate.sse

    try:
        from scipy.optimize import differential_evolution
    except ImportError:
        total = bounds.population_size * (bounds.max_generations + 1)
        print(
            "    SciPy not found; using deterministic fallback sampling "
            f"with {total} evaluations",
            flush=True,
        )
        rng = random.Random(bounds.seed)
        strata_by_dimension = []
        for _ in range(4):
            strata = list(range(total))
            rng.shuffle(strata)
            strata_by_dimension.append(strata)
        for evaluation in range(total):
            unit_values = [
                (strata_by_dimension[dimension][evaluation] + rng.random()) / total
                for dimension in range(4)
            ]
            evaluate_unit_vector(unit_values)
    else:
        print(
            "    SciPy differential_evolution: "
            f"population_size={bounds.population_size}, "
            f"max_generations={bounds.max_generations}, seed={bounds.seed}",
            flush=True,
        )
        scipy_popsize = max(1, math.ceil(bounds.population_size / 4.0))
        differential_evolution(
            lambda x: evaluate_unit_vector(tuple(float(value) for value in x)),
            bounds=[(0.0, 1.0)] * 4,
            maxiter=bounds.max_generations,
            popsize=scipy_popsize,
            seed=bounds.seed,
            polish=False,
            updating="immediate",
            workers=1,
        )

    if best is None:
        raise OptimizerError(f"No candidates evaluated for {experimental.path}")
    return best


def write_gnuplot_script(
    *,
    path: Path,
    image_path: Path,
    experimental: Spectrum,
    theoretical_path: Path,
    best: Candidate,
    model: ModelLib,
    geometry: str,
    fit_window: FitWindow,
    plot_window: PlotWindow,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    parameter_summary = f"effe={best.effe:.5g}, d={best.thickness_nm:.5g} nm"
    if best.rave_nm is not None and best.sig_l is not None:
        parameter_summary += f", rave={best.rave_nm:.5g} nm, sigL={best.sig_l:.5g}"
    title = (
        f"{model.DISPLAY_NAME} {geometry} fit {experimental.basename}: "
        f"{parameter_summary}, SSE={best.sse:.5g}"
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
                    f"with lines lw 2 title '{model.MODEL_NAME} {geometry} best fit'"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )


def optimizer_summary(bounds: ModelBounds, n_parameters: int) -> dict[str, Any]:
    if n_parameters == 4:
        scipy_popsize = max(1, math.ceil(bounds.population_size / 4.0))
        return {
            "method": "differential_evolution_or_fallback_sampling",
            "population_size": bounds.population_size,
            "max_generations": bounds.max_generations,
            "seed": bounds.seed,
            "estimated_total_evaluations": scipy_popsize
            * n_parameters
            * (bounds.max_generations + 1),
            "bounds": asdict(bounds),
        }
    return {
        "method": "grid",
        "effe_points": bounds.effe_points,
        "thickness_points": bounds.thickness_points,
        "total_evaluations": bounds.effe_points * bounds.thickness_points,
        "bounds": asdict(bounds),
    }


def write_result_json(
    *,
    path: Path,
    experimental: Spectrum,
    theoretical_path: Path,
    gnuplot_path: Path,
    image_path: Path,
    best: Candidate,
    bounds: ModelBounds,
    model: ModelLib,
    geometry: str,
    plot_window: PlotWindow,
) -> None:
    grid_min, grid_max, grid_step, full_spectrum_points = experimental.grid
    mse = best.sse / best.objective_points
    rmse = math.sqrt(mse)
    n_parameters = 4 if best.rave_nm is not None and best.sig_l is not None else 2
    result = {
        "model": model.MODEL_NAME,
        "geometry": geometry,
        "experimental_file": project_relative(experimental.path),
        "theoretical_file": project_relative(theoretical_path),
        "gnuplot_script": project_relative(gnuplot_path),
        "image_file": project_relative(image_path),
        "best_parameters": model.result_parameters(
            best.effe,
            best.thickness_nm,
            best.rave_nm,
            best.sig_l,
        ),
        "objective_window_nm": {
            "min": bounds.fit_window.min_nm,
            "max": bounds.fit_window.max_nm,
        },
        "plot_window_nm": {
            "min": plot_window.min_nm,
            "max": plot_window.max_nm,
        },
        "objective": {
            "name": "sse_transmittance",
            "sse": best.sse,
            "mse": mse,
            "rmse": rmse,
            "finite_points": best.objective_points,
            "invalid_points": best.invalid_points,
            "n_parameters": n_parameters,
        },
        "wavelength_grid_nm": {
            "min": grid_min,
            "max": grid_max,
            "step": grid_step,
        },
        "full_spectrum_points": full_spectrum_points,
    }
    if n_parameters == 2:
        result["grid_search"] = optimizer_summary(bounds, n_parameters)
    else:
        result["optimizer"] = optimizer_summary(bounds, n_parameters)
        assert best.rave_nm is not None
        assert best.sig_l is not None
        result["constraints"] = {
            "thickness_tail": asdict(bounds.thickness_tail_constraint),
        }
        result["distribution_descriptors"] = lognormal_radius_descriptors(
            rave_nm=best.rave_nm,
            sig_l=best.sig_l,
            thickness_nm=best.thickness_nm,
        )
    if best.invalid_points > 0:
        result["warnings"] = ["non_finite_points_present"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def run_gnuplot(script_path: Path) -> None:
    if shutil.which("gnuplot") is None:
        raise OptimizerError("gnuplot is required but was not found on PATH")
    subprocess.run(["gnuplot", script_path.name], check=True, cwd=script_path.parent)


def run_effective_medium(args: argparse.Namespace, selection: ModelSelection) -> int:
    if args.check_geometry_invariance and selection.model != bruggeman_lib.MODEL_NAME:
        print(
            "WARNING: --check-geometry-invariance is only supported for "
            "the bruggeman model",
            file=sys.stderr,
        )
        return 1

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
    spectra_paths = discover_spectra(args.spectra_dir)
    spectra = [read_experimental_spectrum(path) for path in spectra_paths]
    for spectrum in spectra:
        validate_uniform_grid(spectrum)
    plot_window = common_plot_window(spectra)
    paths = output_paths(args, selection, selected_lib)

    if selection.model in {"mmgm_spheres_single", "mmgm_holes_single"}:
        print(
            f"{selected_lib.DISPLAY_NAME} {selection.geometry} optimizer: "
            f"population_size={bounds.population_size}, "
            f"max_generations={bounds.max_generations}, seed={bounds.seed}"
        )
    else:
        print(
            f"{selected_lib.DISPLAY_NAME} {selection.geometry} grid: "
            f"{bounds.effe_points} x {bounds.thickness_points} = "
            f"{bounds.effe_points * bounds.thickness_points} evaluations per spectrum"
        )
    print(
        f"{selected_lib.DISPLAY_NAME} {selection.geometry} objective fit window: "
        f"{bounds.fit_window.min_nm:g}-{bounds.fit_window.max_nm:g} nm"
    )
    print(
        f"{selected_lib.DISPLAY_NAME} {selection.geometry} plot window: "
        f"{plot_window.min_nm:g}-{plot_window.max_nm:g} nm"
    )

    fitted = 0
    skipped = 0
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    paths.gnuplot_dir.mkdir(parents=True, exist_ok=True)
    paths.image_dir.mkdir(parents=True, exist_ok=True)
    paths.tmp_dir.mkdir(parents=True, exist_ok=True)

    for spectrum in spectra:
        if not covers_fit_window(spectrum, bounds.fit_window):
            print(
                f"WARNING: skipping {spectrum.path} because its grid {spectrum.grid} "
                f"does not cover the objective fit window "
                f"{bounds.fit_window.min_nm:g}-{bounds.fit_window.max_nm:g} nm",
                file=sys.stderr,
            )
            skipped += 1
            continue

        print(f"==> Fitting {spectrum.path}")
        stem = output_stem(spectrum.basename)
        theoretical_path = paths.output_dir / f"{stem}.dat"
        result_path = paths.output_dir / f"{stem}.json"
        gnuplot_path = paths.gnuplot_dir / f"{stem}.gp"
        image_path = paths.image_dir / f"{stem}.png"

        if selection.model in {"mmgm_spheres_single", "mmgm_holes_single"}:
            best = optimize_mmgm_single_spectrum(
                transmittance_exe=args.transmittance_exe,
                template=template,
                bounds=bounds,
                model=selected_lib,
                geometry=selection.geometry,
                experimental=spectrum,
                tmp_dir=paths.tmp_dir,
                final_spectrum_path=theoretical_path,
            )
        else:
            best = optimize_spectrum(
                transmittance_exe=args.transmittance_exe,
                template=template,
                bounds=bounds,
                model=selected_lib,
                geometry=selection.geometry,
                experimental=spectrum,
                tmp_dir=paths.tmp_dir,
                final_spectrum_path=theoretical_path,
                check_geometry_invariance=args.check_geometry_invariance,
            )
        write_result_json(
            path=result_path,
            experimental=spectrum,
            theoretical_path=theoretical_path,
            gnuplot_path=gnuplot_path,
            image_path=image_path,
            best=best,
            bounds=bounds,
            model=selected_lib,
            geometry=selection.geometry,
            plot_window=plot_window,
        )
        write_gnuplot_script(
            path=gnuplot_path,
            image_path=image_path,
            experimental=spectrum,
            theoretical_path=theoretical_path,
            best=best,
            model=selected_lib,
            geometry=selection.geometry,
            fit_window=bounds.fit_window,
            plot_window=plot_window,
        )
        run_gnuplot(gnuplot_path)
        print(
            f"    best {spectrum.basename}: effe={best.effe:.6g}, "
            f"thickness_nm={best.thickness_nm:.6g}, SSE={best.sse:.8g}"
        )
        print(f"    wrote {result_path}")
        fitted += 1

    print(f"Done. Fitted {fitted} spectrum/s; skipped {skipped}.")
    return 0


def main() -> int:
    args = parse_args()
    return run_effective_medium(args, selected_model(args))


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
