#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DistributionPlotError(RuntimeError):
    """Raised when the active model has no plottable radius distribution."""


@dataclass
class LognormalComponent:
    label: str
    weight: float
    mu_l: float
    sig_l: float

    @property
    def mean_nm(self) -> float:
        return math.exp(self.mu_l + 0.5 * self.sig_l * self.sig_l)

    @property
    def variance_nm2(self) -> float:
        return (math.exp(self.sig_l * self.sig_l) - 1.0) * math.exp(
            2.0 * self.mu_l + self.sig_l * self.sig_l
        )

    def pdf(self, radius_nm: float) -> float:
        if radius_nm <= 0.0:
            return 0.0
        prefactor = 1.0 / (radius_nm * self.sig_l * math.sqrt(2.0 * math.pi))
        exponent = -((math.log(radius_nm) - self.mu_l) ** 2) / (2.0 * self.sig_l * self.sig_l)
        return self.weight * prefactor * math.exp(exponent)


@dataclass
class DistributionModel:
    distribution_type: str
    rave_nm: float
    components: list[LognormalComponent]

    @property
    def weight_sum(self) -> float:
        return sum(component.weight for component in self.components)

    @property
    def mixture_mean_nm(self) -> float:
        if self.weight_sum <= 0.0:
            raise DistributionPlotError("Distribution weights must sum to a positive number.")
        weighted_sum = sum(component.weight * component.mean_nm for component in self.components)
        return weighted_sum / self.weight_sum

    def pdf_total(self, radius_nm: float) -> float:
        return sum(component.pdf(radius_nm) for component in self.components)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a DAT file and a gnuplot script for the radius distribution used by the "
            "active effective-medium model in a transmittance JSON input."
        )
    )
    parser.add_argument(
        "model_json",
        nargs="?",
        type=Path,
        default=Path("data/input/sample.json"),
        help="Solver JSON model to inspect (default: data/input/sample.json)",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/output/distributions"),
        help="Directory for the generated DAT file (default: data/output/distributions)",
    )
    parser.add_argument(
        "--gp-outdir",
        type=Path,
        default=Path("scripts/gnuplot/output/distributions"),
        help=(
            "Directory for the generated gnuplot script "
            "(default: scripts/gnuplot/output/distributions)"
        ),
    )
    parser.add_argument(
        "--png-out",
        type=Path,
        default=Path("img/output/distributions/last_distribution.png"),
        help=(
            "PNG path referenced by the generated gnuplot script "
            "(default: img/output/distributions/last_distribution.png)"
        ),
    )
    parser.add_argument(
        "--radius-max-nm",
        type=float,
        default=None,
        help=(
            "Optional explicit maximum radius for the plot grid. "
            "If omitted, a model-based range is chosen automatically."
        ),
    )
    parser.add_argument(
        "--n-points",
        type=int,
        default=1200,
        help="Number of radius points in the generated DAT file (default: 1200)",
    )
    parser.add_argument(
        "--run-gnuplot",
        action="store_true",
        help="Run gnuplot on the generated script after writing it.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DistributionPlotError(f"JSON model file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DistributionPlotError(f"Could not parse JSON model file {path}: {exc}") from exc


def find_effective_medium_layer(model: dict[str, Any]) -> dict[str, Any]:
    layers = model.get("stack", {}).get("layers", [])
    effective_layers = [layer for layer in layers if layer.get("kind") == "effective_medium"]
    if not effective_layers:
        raise DistributionPlotError("No effective_medium layer found in the JSON model.")
    if len(effective_layers) > 1:
        raise DistributionPlotError(
            "Expected exactly one effective_medium layer for the distribution plot."
        )
    return effective_layers[0]


def require_float(mapping: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key in mapping:
            return float(mapping[key])
    raise DistributionPlotError(f"Missing required distribution field. Tried: {', '.join(keys)}")


def parse_distribution_model(model: dict[str, Any]) -> DistributionModel:
    layer = find_effective_medium_layer(model)
    effective_medium = layer.get("effective_medium")
    if not isinstance(effective_medium, dict):
        raise DistributionPlotError("effective_medium block missing from effective_medium layer.")

    if effective_medium.get("model") != "mmgm":
        raise DistributionPlotError(
            "The active effective-medium model is not 'mmgm'; no radius distribution is used."
        )

    distribution = effective_medium.get("distribution")
    if not isinstance(distribution, dict):
        raise DistributionPlotError("The active MMGM model has no distribution block to plot.")

    dist_type = distribution.get("type")
    rave_nm = require_float(distribution, "rave_nm")

    if dist_type == "lognormal":
        component = LognormalComponent(
            label="single",
            weight=1.0,
            mu_l=require_float(distribution, "muL", "mu_l"),
            sig_l=require_float(distribution, "sigL", "sig_l"),
        )
        return DistributionModel(dist_type, rave_nm, [component])

    if dist_type == "two_lognormal":
        component_1 = LognormalComponent(
            label="component_1",
            weight=require_float(distribution, "w1"),
            mu_l=require_float(distribution, "muL1", "mu_l1"),
            sig_l=require_float(distribution, "sigL1", "sig_l1"),
        )
        component_2 = LognormalComponent(
            label="component_2",
            weight=require_float(distribution, "w2"),
            mu_l=require_float(distribution, "muL2", "mu_l2"),
            sig_l=require_float(distribution, "sigL2", "sig_l2"),
        )
        return DistributionModel(dist_type, rave_nm, [component_1, component_2])

    raise DistributionPlotError(
        f"Unsupported MMGM distribution type '{dist_type}'. "
        "Supported values are 'lognormal' and 'two_lognormal'."
    )


def choose_radius_max_nm(distribution: DistributionModel, explicit_max: float | None) -> float:
    if explicit_max is not None:
        if explicit_max <= 0.0:
            raise DistributionPlotError("--radius-max-nm must be positive.")
        return explicit_max

    candidate_maxima = [4.0 * distribution.rave_nm]
    for component in distribution.components:
        candidate_maxima.append(math.exp(component.mu_l + 4.0 * component.sig_l))
        candidate_maxima.append(component.mean_nm + 6.0 * math.sqrt(component.variance_nm2))
    radius_max = max(candidate_maxima)
    return max(radius_max, 1.5 * distribution.rave_nm)


def build_radius_grid(radius_max_nm: float, n_points: int) -> list[float]:
    if n_points < 10:
        raise DistributionPlotError("--n-points must be at least 10.")
    radius_min = max(1e-6, radius_max_nm / 5000.0)
    step = (radius_max_nm - radius_min) / (n_points - 1)
    return [radius_min + i * step for i in range(n_points)]


def write_distribution_dat(path: Path, distribution: DistributionModel, radii_nm: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mixture_mean = distribution.mixture_mean_nm
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# radius_nm p1 p2 p_total\n")
        handle.write(f"# distribution_type {distribution.distribution_type}\n")
        handle.write(f"# rave_nm {distribution.rave_nm:.10g}\n")
        if distribution.distribution_type == "lognormal":
            handle.write(f"# mean_nm {distribution.components[0].mean_nm:.10g}\n")
        else:
            handle.write(f"# mean1_nm {distribution.components[0].mean_nm:.10g}\n")
            handle.write(f"# mean2_nm {distribution.components[1].mean_nm:.10g}\n")
            handle.write(f"# mean_mix_nm {mixture_mean:.10g}\n")

        for radius_nm in radii_nm:
            p1 = distribution.components[0].pdf(radius_nm)
            p2 = distribution.components[1].pdf(radius_nm) if len(distribution.components) > 1 else 0.0
            p_total = p1 + p2
            handle.write(f"{radius_nm:.10g} {p1:.10g} {p2:.10g} {p_total:.10g}\n")


def gnuplot_arrow_block(distribution: DistributionModel, peak_height: float) -> str:
    lines = [
        f"set arrow 1 from {distribution.rave_nm:.10g}, graph 0 to {distribution.rave_nm:.10g}, {1.04 * peak_height:.10g} nohead lw 2 dt solid lc rgb 'black'",
        f"set label 1 'Rave' at {distribution.rave_nm:.10g}, {1.06 * peak_height:.10g} center tc rgb 'black'",
    ]

    if distribution.distribution_type == "lognormal":
        mean = distribution.components[0].mean_nm
        lines.extend([
            f"set arrow 2 from {mean:.10g}, graph 0 to {mean:.10g}, {0.92 * peak_height:.10g} nohead lw 1 dt 2 lc rgb '#1f77b4'",
            f"set label 2 '<R>' at {mean:.10g}, {0.94 * peak_height:.10g} center tc rgb '#1f77b4'",
        ])
    else:
        mean1 = distribution.components[0].mean_nm
        mean2 = distribution.components[1].mean_nm
        mean_mix = distribution.mixture_mean_nm
        lines.extend([
            f"set arrow 2 from {mean1:.10g}, graph 0 to {mean1:.10g}, {0.88 * peak_height:.10g} nohead lw 1 dt 2 lc rgb '#1f77b4'",
            f"set label 2 '<R>_1' at {mean1:.10g}, {0.90 * peak_height:.10g} center tc rgb '#1f77b4'",
            f"set arrow 3 from {mean2:.10g}, graph 0 to {mean2:.10g}, {0.78 * peak_height:.10g} nohead lw 1 dt 2 lc rgb '#d62728'",
            f"set label 3 '<R>_2' at {mean2:.10g}, {0.80 * peak_height:.10g} center tc rgb '#d62728'",
            f"set arrow 4 from {mean_mix:.10g}, graph 0 to {mean_mix:.10g}, {0.68 * peak_height:.10g} nohead lw 1 dt 1 lc rgb '#2ca02c'",
            f"set label 4 '<R>_mix' at {mean_mix:.10g}, {0.70 * peak_height:.10g} center tc rgb '#2ca02c'",
        ])
    return "\n".join(lines)


def build_gnuplot_script(
    dat_path: Path,
    gp_path: Path,
    png_path: Path,
    distribution: DistributionModel,
    peak_height: float,
) -> None:
    gp_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    if distribution.distribution_type == "lognormal":
        plot_lines = (
            f"plot '{dat_path.as_posix()}' using 1:4 with lines lw 3 lc rgb '#111111' title 'lognormal'"
        )
        title = "MMGM lognormal radius distribution"
    else:
        plot_lines = "\n".join([
            "plot \\",
            f"  '{dat_path.as_posix()}' using 1:2 with lines lw 2 dt 2 lc rgb '#1f77b4' title 'component 1', \\",
            f"  '{dat_path.as_posix()}' using 1:3 with lines lw 2 dt 2 lc rgb '#d62728' title 'component 2', \\",
            f"  '{dat_path.as_posix()}' using 1:4 with lines lw 4 lc rgb '#111111' title 'sum'",
        ])
        title = "MMGM two-lognormal radius distribution"

    script = f"""set terminal pngcairo size 1400,900 noenhanced
set output '{png_path.as_posix()}'

set title '{title}'
set xlabel 'Radius (nm)'
set ylabel 'P(R)'
set grid
set key outside right
set border lw 1.2
set xrange [0:*]
set yrange [0:{1.12 * peak_height:.10g}]

# Characteristic radii
{gnuplot_arrow_block(distribution, peak_height)}

{plot_lines}
"""
    gp_path.write_text(script, encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        model = load_json(args.model_json)
        distribution = parse_distribution_model(model)
        radius_max_nm = choose_radius_max_nm(distribution, args.radius_max_nm)
        radii_nm = build_radius_grid(radius_max_nm, args.n_points)

        dat_path = args.outdir / "last_distribution.dat"
        gp_path = args.gp_outdir / "plot_last_distribution.gp"

        peak_height = max(distribution.pdf_total(radius_nm) for radius_nm in radii_nm)
        if peak_height <= 0.0:
            raise DistributionPlotError("Computed distribution is identically zero; refusing to plot.")

        write_distribution_dat(dat_path, distribution, radii_nm)
        build_gnuplot_script(dat_path, gp_path, args.png_out, distribution, peak_height)

        print(f"Wrote: {dat_path}")
        print(f"Wrote: {gp_path}")
        print(f"PNG target: {args.png_out}")
        if distribution.distribution_type == "lognormal":
            print(
                "Markers: "
                f"Rave={distribution.rave_nm:.6g} nm, "
                f"<R>={distribution.components[0].mean_nm:.6g} nm"
            )
        else:
            print(
                "Markers: "
                f"Rave={distribution.rave_nm:.6g} nm, "
                f"<R>_1={distribution.components[0].mean_nm:.6g} nm, "
                f"<R>_2={distribution.components[1].mean_nm:.6g} nm, "
                f"<R>_mix={distribution.mixture_mean_nm:.6g} nm"
            )

        if args.run_gnuplot:
            subprocess.run(["gnuplot", str(gp_path)], check=True)
            print(f"Rendered: {args.png_out}")

        return 0
    except DistributionPlotError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

