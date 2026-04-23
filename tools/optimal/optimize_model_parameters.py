#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from model import mg_lib  # noqa: E402


class OptimizerError(RuntimeError):
    """Raised when the optimizer orchestration fails."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optimize Nublar transmittance model parameters."
    )
    model_group = parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument("--mg", action="store_true", help="Run v1 MG grid search")
    parser.add_argument("--template-json", type=Path, default=Path("data/input/sample.json"))
    parser.add_argument("--bounds-json", type=Path, default=Path("data/input/optimal/bounds.json"))
    parser.add_argument("--spectra-dir", type=Path, default=Path("data/experimental/final/transmittance"))
    parser.add_argument("--transmittance-exe", type=Path, default=Path("bin/transmittance"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/output/optimal/mg"))
    parser.add_argument("--gnuplot-dir", type=Path, default=Path("scripts/gnuplot/optimal/mg"))
    parser.add_argument("--image-dir", type=Path, default=Path("img/optimal/mg"))
    parser.add_argument("--tmp-dir", type=Path, default=Path("data/output/optimal/mg/tmp"))
    return parser.parse_args()


def read_experimental_spectrum(path: Path) -> mg_lib.Spectrum:
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
    return mg_lib.Spectrum(path=path, wavelengths_nm=wavelengths, transmittance=transmittance)


def validate_uniform_grid(spectrum: mg_lib.Spectrum) -> None:
    wavelengths = spectrum.wavelengths_nm
    if len(wavelengths) < 2:
        raise OptimizerError(f"Spectrum has too few points: {spectrum.path}")
    step = wavelengths[1] - wavelengths[0]
    if step <= 0.0:
        raise OptimizerError(f"Spectrum grid is not increasing: {spectrum.path}")
    for previous, current in zip(wavelengths, wavelengths[1:], strict=False):
        if abs((current - previous) - step) > 1e-9:
            raise OptimizerError(f"Spectrum grid is not uniform: {spectrum.path}")


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


def write_gnuplot_script(
    *,
    path: Path,
    image_path: Path,
    experimental: mg_lib.Spectrum,
    theoretical_path: Path,
    best: mg_lib.MgCandidate,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    title = (
        f"MG fit {experimental.basename}: "
        f"effe={best.effe:.5g}, d={best.thickness_nm:.5g} nm, SSE={best.sse:.5g}"
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
                "set key outside right",
                "plot \\",
                (
                    f"  '{gnuplot_relative(path, experimental.path)}' using 1:3 "
                    "with lines lw 2 title 'experimental', \\"
                ),
                (
                    f"  '{gnuplot_relative(path, theoretical_path)}' using 1:3 "
                    "with lines lw 2 title 'mg best fit'"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_result_json(
    *,
    path: Path,
    experimental: mg_lib.Spectrum,
    theoretical_path: Path,
    gnuplot_path: Path,
    image_path: Path,
    best: mg_lib.MgCandidate,
    bounds: mg_lib.MgBounds,
) -> None:
    grid_min, grid_max, grid_step, _ = experimental.grid
    mse = best.sse / best.objective_points
    rmse = math.sqrt(mse)
    result = {
        "model": "mg",
        "experimental_file": project_relative(experimental.path),
        "theoretical_file": project_relative(theoretical_path),
        "gnuplot_script": project_relative(gnuplot_path),
        "image_file": project_relative(image_path),
        "best_parameters": {
            "effe": best.effe,
            "thickness_nm": best.thickness_nm,
        },
        "objective": {
            "name": "sse_transmittance",
            "sse": best.sse,
            "mse": mse,
            "rmse": rmse,
            "finite_points": best.objective_points,
            "invalid_points": best.invalid_points,
            "n_parameters": 2,
        },
        "grid_search": {
            "effe_points": bounds.effe_points,
            "thickness_points": bounds.thickness_points,
            "total_evaluations": bounds.effe_points * bounds.thickness_points,
            "bounds": asdict(bounds),
        },
        "wavelength_grid_nm": {
            "min": grid_min,
            "max": grid_max,
            "step": grid_step,
        },
    }
    if best.invalid_points > 0:
        result["warnings"] = ["non_finite_points_present"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def run_gnuplot(script_path: Path) -> None:
    if shutil.which("gnuplot") is None:
        raise OptimizerError("gnuplot is required but was not found on PATH")
    subprocess.run(["gnuplot", script_path.name], check=True, cwd=script_path.parent)


def regular_reference_grid(spectra: Iterable[mg_lib.Spectrum]) -> tuple[float, float, float, int]:
    for spectrum in spectra:
        return spectrum.grid
    raise OptimizerError("No spectra found")


def run_mg(args: argparse.Namespace) -> int:
    if not args.transmittance_exe.exists():
        raise OptimizerError(
            f"Missing forward executable: {args.transmittance_exe}. Run `make bin/transmittance`."
        )

    template = mg_lib.load_template(args.template_json)
    bounds = mg_lib.read_bounds(args.bounds_json)
    spectra_paths = discover_spectra(args.spectra_dir)
    spectra = [read_experimental_spectrum(path) for path in spectra_paths]
    for spectrum in spectra:
        validate_uniform_grid(spectrum)

    reference_grid = regular_reference_grid(spectra)
    print(
        "MG v1 grid: "
        f"{bounds.effe_points} x {bounds.thickness_points} = "
        f"{bounds.effe_points * bounds.thickness_points} evaluations per spectrum"
    )

    fitted = 0
    skipped = 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.gnuplot_dir.mkdir(parents=True, exist_ok=True)
    args.image_dir.mkdir(parents=True, exist_ok=True)
    args.tmp_dir.mkdir(parents=True, exist_ok=True)

    for spectrum in spectra:
        if not mg_lib.grids_compatible(spectrum.grid, reference_grid):
            print(
                f"WARNING: skipping {spectrum.path} because its grid {spectrum.grid} "
                f"differs from the v1 reference grid {reference_grid}",
                file=sys.stderr,
            )
            skipped += 1
            continue

        print(f"==> Fitting {spectrum.path}")
        stem = f"optimal_{spectrum.basename}"
        theoretical_path = args.output_dir / f"{stem}.dat"
        result_path = args.output_dir / f"{stem}.json"
        gnuplot_path = args.gnuplot_dir / f"{stem}.gp"
        image_path = args.image_dir / f"{stem}.png"

        best = mg_lib.optimize_spectrum(
            transmittance_exe=args.transmittance_exe,
            template=template,
            bounds=bounds,
            experimental=spectrum,
            tmp_dir=args.tmp_dir,
            final_spectrum_path=theoretical_path,
        )
        write_result_json(
            path=result_path,
            experimental=spectrum,
            theoretical_path=theoretical_path,
            gnuplot_path=gnuplot_path,
            image_path=image_path,
            best=best,
            bounds=bounds,
        )
        write_gnuplot_script(
            path=gnuplot_path,
            image_path=image_path,
            experimental=spectrum,
            theoretical_path=theoretical_path,
            best=best,
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
    if args.mg:
        return run_mg(args)
    raise OptimizerError("No supported model selected")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OptimizerError, mg_lib.MgOptimizationError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
