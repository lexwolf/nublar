#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MgOptimizationError(RuntimeError):
    """Raised when the MG grid search cannot complete."""


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
            raise MgOptimizationError(f"Spectrum has too few points: {self.path}")
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
class MgBounds:
    effe_min: float
    effe_max: float
    thickness_min_nm: float
    thickness_max_nm: float
    effe_points: int
    thickness_points: int
    thickness_transform: str
    fit_window: FitWindow


@dataclass(frozen=True)
class MgCandidate:
    effe: float
    thickness_nm: float
    sse: float
    spectrum_path: Path
    objective_points: int
    invalid_points: int


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


def read_bounds(path: Path, model_name: str = "mg") -> MgBounds:
    raw = json.loads(_strip_markdown_fence(path.read_text(encoding="utf-8")))
    objective = raw["global"]["objective"]
    fit_window_raw = objective["fit_window_nm"]
    model = raw["models"][model_name]
    params = model["native_fit_parameters"]
    grid = model.get("optimizer", {}).get("grid", {})

    effe_points = int(grid.get("v1_effe_points", grid.get("effe_points", 9)))
    thickness_points = int(grid.get("v1_thickness_points", grid.get("thickness_points", 9)))
    fit_window = FitWindow(
        min_nm=float(fit_window_raw["min"]),
        max_nm=float(fit_window_raw["max"]),
    )
    if fit_window.min_nm > fit_window.max_nm:
        raise MgOptimizationError(
            "Invalid objective fit window: "
            f"{fit_window.min_nm} > {fit_window.max_nm}"
        )

    return MgBounds(
        effe_min=float(params["effe"]["min"]),
        effe_max=float(params["effe"]["max"]),
        thickness_min_nm=float(params["thickness_nm"]["min"]),
        thickness_max_nm=float(params["thickness_nm"]["max"]),
        effe_points=effe_points,
        thickness_points=thickness_points,
        thickness_transform=str(params["thickness_nm"].get("transform", "none")),
        fit_window=fit_window,
    )


def linspace(minimum: float, maximum: float, count: int) -> list[float]:
    if count < 2:
        return [minimum]
    step = (maximum - minimum) / float(count - 1)
    return [minimum + i * step for i in range(count)]


def logspace(minimum: float, maximum: float, count: int) -> list[float]:
    if minimum <= 0.0 or maximum <= 0.0:
        raise MgOptimizationError("Log-spaced bounds must be positive")
    return [math.exp(value) for value in linspace(math.log(minimum), math.log(maximum), count)]


def build_grid(bounds: MgBounds) -> tuple[list[float], list[float]]:
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


def inject_effective_medium_parameters(
    template: dict[str, Any],
    spectrum: Spectrum,
    model_name: str,
    geometry: str,
    effe: float,
    thickness_nm: float,
) -> dict[str, Any]:
    if model_name not in {"mg", "bruggeman"}:
        raise MgOptimizationError(f"Unsupported effective-medium model: {model_name}")
    if geometry not in {"spheres", "holes"}:
        raise MgOptimizationError(f"Unsupported effective-medium geometry: {geometry}")
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
        effective_medium = layer["effective_medium"]
        effective_medium["model"] = model_name
        effective_medium["geometry"] = geometry
        effective_medium["filling_fraction"] = effe
        effective_medium.pop("distribution", None)
        return model

    raise MgOptimizationError("Template JSON has no effective_medium layer")


def write_trial_json(path: Path, model: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")


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
            raise MgOptimizationError(f"Non-finite model wavelength in {path}: {line}")
        wavelengths.append(wavelength)
        transmittance.append(value)
    if not wavelengths:
        raise MgOptimizationError(f"No model spectrum rows found in {path}")
    if len(wavelengths) < 0.5 * total_data_lines:
        raise MgOptimizationError(
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
        raise MgOptimizationError(
            "Experimental/model wavelength grids differ in length: "
            f"{experimental.path} vs {theoretical.path}"
        )
    if not grids_compatible(experimental.grid, theoretical.grid):
        raise MgOptimizationError(
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
            raise MgOptimizationError(
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
        raise MgOptimizationError(
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
    experimental: Spectrum,
    model_name: str,
    geometry: str,
    fit_window: FitWindow,
    effe: float,
    thickness_nm: float,
    trial_json_path: Path,
    trial_spectrum_path: Path,
) -> MgCandidate:
    model = inject_effective_medium_parameters(
        template, experimental, model_name, geometry, effe, thickness_nm
    )
    write_trial_json(trial_json_path, model)
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
    sse, valid_points, invalid_points = sse_transmittance(
        experimental, theoretical, fit_window
    )
    return MgCandidate(
        effe=effe,
        thickness_nm=thickness_nm,
        sse=sse,
        spectrum_path=trial_spectrum_path,
        objective_points=valid_points,
        invalid_points=invalid_points,
    )


def optimize_spectrum(
    *,
    transmittance_exe: Path,
    template: dict[str, Any],
    bounds: MgBounds,
    model_name: str,
    geometry: str,
    experimental: Spectrum,
    tmp_dir: Path,
    final_spectrum_path: Path,
) -> MgCandidate:
    effe_values, thickness_values = build_grid(bounds)
    total = len(effe_values) * len(thickness_values)
    best: MgCandidate | None = None
    trial_json_path = tmp_dir / f"{experimental.basename}_trial.json"
    trial_spectrum_path = tmp_dir / f"{experimental.basename}_trial.dat"

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
                experimental=experimental,
                model_name=model_name,
                geometry=geometry,
                fit_window=bounds.fit_window,
                effe=effe,
                thickness_nm=thickness_nm,
                trial_json_path=trial_json_path,
                trial_spectrum_path=trial_spectrum_path,
            )
            if best is None or candidate.sse < best.sse:
                best = MgCandidate(
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
        raise MgOptimizationError(f"No candidates evaluated for {experimental.path}")
    return best
