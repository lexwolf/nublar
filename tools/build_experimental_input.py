#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.dataset import (  # noqa: E402
    gather_json_files,
    load_filtered_payload_records,
    mean_std,
    normalize_suffix,
    write_csv,
    write_dat_lines,
)
from afm_lib.distribution_fit import fit_two_lognormal_mixture  # noqa: E402
from afm_lib.effe_proxy import (  # noqa: E402
    EFFE_PROXY_CHOICES,
    compute_effe_proxy,
    get_effe_proxy_formula_string,
)
from afm_lib.radius_proxy import (  # noqa: E402
    MANIFEST_RAVE_FIELD_FOR_RADIUS_PROXY,
    RADIUS_PROXY_CHOICES,
    SUMMARY_FIELD_FOR_RADIUS_PROXY,
)


TIME_RE = re.compile(r"_(\d+)s(?:_|\.|$)", re.IGNORECASE)


class ExperimentalInputError(RuntimeError):
    """Raised when experimental model input generation fails."""


@dataclass
class TransmittanceSummary:
    path: Path
    sample_label: str
    time_s: int
    n_lambda: int
    lamin_nm: float
    lamax_nm: float
    dlam_nm: float
    lambda_grid_is_uniform: bool


@dataclass
class ThicknessProxyResult:
    value_nm: float
    std_nm: float
    formula: str


THICKNESS_PROXY_CHOICES = (
    "equivalent_thickness_nm",
    "sphere_r95_diameter",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a solver-facing experimental model input table by joining "
            "AFM-derived morphology and two-lognormal fits with processed transmittance metadata."
        )
    )
    parser.add_argument(
        "afm_inputs",
        nargs="*",
        type=Path,
        help=(
            "AFM feature JSON files and/or directories containing them. "
            "If omitted, uses data/experimental/intermediate/afm_batch."
        ),
    )
    parser.add_argument(
        "--include-suffixes",
        default="001,003",
        help=(
            "Comma-separated AFM scan suffixes to include: 001,002,003,image "
            "(default: 001,003)"
        ),
    )
    parser.add_argument(
        "--transmittance-dir",
        type=Path,
        default=Path("data/experimental/final/transmittance"),
        help=(
            "Directory containing processed transmittance DAT files "
            "(default: data/experimental/final/transmittance)"
        ),
    )
    parser.add_argument(
        "--radius-proxy",
        choices=RADIUS_PROXY_CHOICES,
        default="volume_equivalent_radius_nm",
        help=(
            "Per-island radius proxy used for the two-lognormal fit and exported Rave "
            "(default: volume_equivalent_radius_nm)"
        ),
    )
    parser.add_argument(
        "--effe-proxy",
        choices=EFFE_PROXY_CHOICES,
        default="eq_thickness_over_mean_height",
        help=(
            "Active effe proxy written into the manifest "
            "(default: eq_thickness_over_mean_height)"
        ),
    )
    parser.add_argument(
        "--thickness-proxy",
        choices=THICKNESS_PROXY_CHOICES,
        default="equivalent_thickness_nm",
        help=(
            "Thickness proxy written into the solver-facing equivalent_thickness slot "
            "(default: equivalent_thickness_nm)"
        ),
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/input/experimental"),
        help="Output directory for the solver-facing manifest (default: data/input/experimental)",
    )
    parser.add_argument(
        "--basename",
        default="model_input",
        help="Base name for output files (default: model_input)",
    )
    return parser.parse_args()


def parse_time_s(path: Path) -> int:
    match = TIME_RE.search(path.name)
    if not match:
        raise ExperimentalInputError(f"Could not parse deposition time from filename: {path}")
    return int(match.group(1))


def parse_transmittance_file(path: Path) -> TransmittanceSummary:
    sample_label = ""
    wavelengths: list[float] = []

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if stripped.startswith("# sample_label "):
                sample_label = stripped[len("# sample_label "):].strip()
            continue

        parts = stripped.split()
        wavelengths.append(float(parts[0]))

    if not wavelengths:
        raise ExperimentalInputError(f"No wavelength grid found in transmittance file: {path}")

    if sample_label == "":
        sample_label = path.stem

    diffs = [b - a for a, b in zip(wavelengths, wavelengths[1:])]
    if diffs:
        dlam = sorted(diffs)[len(diffs) // 2]
        max_deviation = max(abs(delta - dlam) for delta in diffs)
        is_uniform = max_deviation <= 1e-9
    else:
        dlam = 0.0
        is_uniform = True

    return TransmittanceSummary(
        path=path,
        sample_label=sample_label,
        time_s=parse_time_s(path),
        n_lambda=len(wavelengths),
        lamin_nm=wavelengths[0],
        lamax_nm=wavelengths[-1],
        dlam_nm=dlam,
        lambda_grid_is_uniform=is_uniform,
    )


def gather_transmittance_summaries(base_dir: Path) -> dict[int, TransmittanceSummary]:
    if not base_dir.exists():
        raise ExperimentalInputError(f"Transmittance directory does not exist: {base_dir}")

    summaries: dict[int, TransmittanceSummary] = {}
    for path in sorted(base_dir.glob("*.dat")):
        if not TIME_RE.search(path.name):
            continue
        summary = parse_transmittance_file(path)
        if summary.time_s in summaries:
            raise ExperimentalInputError(
                f"Duplicate transmittance spectrum for {summary.time_s}s: "
                f"{summaries[summary.time_s].path} and {path}"
            )
        summaries[summary.time_s] = summary

    if not summaries:
        raise ExperimentalInputError(f"No transmittance DAT files found in: {base_dir}")
    return summaries


def empirical_percentile(values: list[float], percentile: float) -> float:
    if not values:
        raise ExperimentalInputError("Cannot compute percentile of an empty sample")
    if not 0.0 <= percentile <= 100.0:
        raise ExperimentalInputError(f"Invalid percentile: {percentile}")

    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (percentile / 100.0) * (len(sorted_values) - 1)
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    if lower_index == upper_index:
        return lower_value
    weight = position - lower_index
    return lower_value + weight * (upper_value - lower_value)


def compute_thickness_proxy(
    thickness_proxy_name: str,
    entries: list[dict[str, Any]],
    radius_proxy_name: str,
) -> ThicknessProxyResult:
    thickness_vals = [float(e["summary"]["equivalent_thickness_nm"]) for e in entries]
    afm_thickness_mu, afm_thickness_std = mean_std(thickness_vals)

    if thickness_proxy_name == "equivalent_thickness_nm":
        return ThicknessProxyResult(
            value_nm=afm_thickness_mu,
            std_nm=afm_thickness_std,
            formula="mean(summary.equivalent_thickness_nm)",
        )

    if thickness_proxy_name == "sphere_r95_diameter":
        pooled_radii = [
            float(record[radius_proxy_name])
            for entry in entries
            for record in entry["islands"]
            if float(record[radius_proxy_name]) > 0.0
        ]
        if len(pooled_radii) < 4:
            raise ExperimentalInputError(
                "Not enough pooled radii to compute thickness proxy "
                f"{thickness_proxy_name} for radius proxy {radius_proxy_name}"
            )
        radius_p95_nm = empirical_percentile(pooled_radii, 95.0)
        return ThicknessProxyResult(
            value_nm=2.0 * radius_p95_nm,
            std_nm=0.0,
            formula=f"2*R95({radius_proxy_name})",
        )

    raise ExperimentalInputError(f"Unsupported thickness proxy: {thickness_proxy_name}")


def validate_proxy_combination(thickness_proxy_name: str, effe_proxy_name: str) -> None:
    if thickness_proxy_name != "sphere_r95_diameter":
        return

    if effe_proxy_name == "eq_thickness_over_Rave":
        raise ExperimentalInputError(
            "Incompatible proxy combination: thickness proxy sphere_r95_diameter "
            "cannot be combined with effe proxy eq_thickness_over_Rave because the "
            "thickness is already derived from the selected radius proxy."
        )

    if effe_proxy_name in {"hybrid_alpha25", "hybrid_alpha50", "hybrid_alpha75"}:
        print(
            "WARNING: thickness proxy sphere_r95_diameter introduces radius-derived "
            f"circularity into {effe_proxy_name}; this combination is allowed but "
            "should be interpreted cautiously.",
            file=sys.stderr,
        )


def build_rows(
    afm_grouped: dict[int, list[dict[str, Any]]],
    transmittance: dict[int, TransmittanceSummary],
    radius_proxy: str,
    effe_proxy_name: str,
    thickness_proxy_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    common_times = sorted(set(afm_grouped) & set(transmittance))
    if not common_times:
        raise ExperimentalInputError(
            "No deposition times are shared between AFM summaries and transmittance spectra"
        )

    missing_trans = sorted(set(afm_grouped) - set(transmittance))
    missing_afm = sorted(set(transmittance) - set(afm_grouped))
    if missing_afm:
        raise ExperimentalInputError(
            f"Missing AFM summaries for times: {', '.join(map(str, missing_afm))}"
        )
    if missing_trans:
        raise ExperimentalInputError(
            f"Missing transmittance spectra for times: {', '.join(map(str, missing_trans))}"
        )

    validate_proxy_combination(thickness_proxy_name, effe_proxy_name)

    for time_s in common_times:
        entries = afm_grouped[time_s]
        trans = transmittance[time_s]

        coverage_vals = [float(e["summary"]["coverage_fraction"]) for e in entries]
        density_vals = [float(e["summary"]["number_density_per_um2"]) for e in entries]
        height_vals = [float(e["summary"]["mean_island_height_nm"]) for e in entries]
        afm_thickness_vals = [float(e["summary"]["equivalent_thickness_nm"]) for e in entries]
        afm_rave_vals = [
            float(e["summary"][SUMMARY_FIELD_FOR_RADIUS_PROXY[radius_proxy]])
            for e in entries
        ]
        pooled_radii = [
            float(record[radius_proxy])
            for e in entries
            for record in e["islands"]
            if float(record[radius_proxy]) > 0.0
        ]
        if len(pooled_radii) < 4:
            raise ExperimentalInputError(
                f"Not enough pooled radii to fit a two-lognormal mixture for {time_s}s"
            )

        coverage_mu, coverage_std = mean_std(coverage_vals)
        afm_thickness_mu, afm_thickness_std = mean_std(afm_thickness_vals)
        density_mu, density_std = mean_std(density_vals)
        height_mu, height_std = mean_std(height_vals)
        afm_rave_mu, afm_rave_std = mean_std(afm_rave_vals)
        selected_thickness = compute_thickness_proxy(thickness_proxy_name, entries, radius_proxy)
        rave_by_proxy = {
            manifest_field: mean_std(
                [
                    float(e["summary"][SUMMARY_FIELD_FOR_RADIUS_PROXY[proxy_name]])
                    for e in entries
                ]
            )[0]
            for proxy_name, manifest_field in MANIFEST_RAVE_FIELD_FOR_RADIUS_PROXY.items()
        }
        effe_proxy = compute_effe_proxy(
            effe_proxy_name,
            coverage_mu,
            selected_thickness.value_nm,
            height_mu,
            afm_rave_mu,
        )

        fit = fit_two_lognormal_mixture(pooled_radii)

        rows.append(
            {
                "time_s": time_s,
                "n_afm_scans": len(entries),
                "afm_sources": ";".join(sorted(e["_source"] for e in entries)),
                "coverage_fraction": coverage_mu,
                "coverage_fraction_std": coverage_std,
                "effe_proxy": effe_proxy,
                "effe_proxy_name": effe_proxy_name,
                "effe_proxy_formula": get_effe_proxy_formula_string(effe_proxy_name),
                "thickness_proxy_name": thickness_proxy_name,
                "thickness_proxy_formula": selected_thickness.formula,
                "afm_Rave_nm": afm_rave_mu,
                "afm_Rave_nm_std": afm_rave_std,
                "radius_proxy_name": radius_proxy,
                "distribution_type": "two_lognormal",
                "distribution_axis_name": radius_proxy,
                "distribution_fit_status": "ok",
                "distribution_fit_path": "afm_raw_radii",
                "distribution_log_likelihood": fit.log_likelihood,
                "distribution_bic": fit.bic,
                "distribution_fit_converged": int(fit.converged),
                "distribution_fit_iterations": fit.n_iter,
                "distribution_sample_count": fit.n_samples,
                "mixture_weight_1": fit.component_1.weight,
                "muL1": fit.component_1.mu_ln,
                "sigL1": fit.component_1.sigma_ln,
                "component_1_mean_nm": fit.component_1.mean_nm,
                "component_1_std_nm": fit.component_1.std_nm,
                "mixture_weight_2": fit.component_2.weight,
                "muL2": fit.component_2.mu_ln,
                "sigL2": fit.component_2.sigma_ln,
                "component_2_mean_nm": fit.component_2.mean_nm,
                "component_2_std_nm": fit.component_2.std_nm,
                "distribution_mean_nm": fit.mixture_mean_nm,
                "distribution_std_nm": fit.mixture_std_nm,
                "equivalent_thickness_nm": selected_thickness.value_nm,
                "equivalent_thickness_nm_std": selected_thickness.std_nm,
                "afm_equivalent_thickness_nm": afm_thickness_mu,
                "afm_equivalent_thickness_nm_std": afm_thickness_std,
                "number_density_per_um2": density_mu,
                "number_density_per_um2_std": density_std,
                "mean_island_height_nm": height_mu,
                "mean_island_height_nm_std": height_std,
                "n_lambda": trans.n_lambda,
                "lamin_nm": trans.lamin_nm,
                "lamax_nm": trans.lamax_nm,
                "dlam_nm": trans.dlam_nm,
                "lambda_grid_is_uniform": int(trans.lambda_grid_is_uniform),
                "transmittance_dat": trans.path.as_posix(),
                "transmittance_label": trans.sample_label,
                **rave_by_proxy,
            }
        )

    return rows


CSV_FIELDNAMES = [
    "time_s",
    "n_afm_scans",
    "afm_sources",
    "coverage_fraction",
    "coverage_fraction_std",
    "effe_proxy",
    "effe_proxy_name",
    "effe_proxy_formula",
    "thickness_proxy_name",
    "thickness_proxy_formula",
    "afm_Rave_nm",
    "afm_Rave_nm_std",
    "radius_proxy_name",
    "distribution_type",
    "distribution_axis_name",
    "distribution_fit_status",
    "distribution_fit_path",
    "distribution_log_likelihood",
    "distribution_bic",
    "distribution_fit_converged",
    "distribution_fit_iterations",
    "distribution_sample_count",
    "mixture_weight_1",
    "muL1",
    "sigL1",
    "component_1_mean_nm",
    "component_1_std_nm",
    "mixture_weight_2",
    "muL2",
    "sigL2",
    "component_2_mean_nm",
    "component_2_std_nm",
    "distribution_mean_nm",
    "distribution_std_nm",
    "equivalent_thickness_nm",
    "equivalent_thickness_nm_std",
    "afm_equivalent_thickness_nm",
    "afm_equivalent_thickness_nm_std",
    "number_density_per_um2",
    "number_density_per_um2_std",
    "mean_island_height_nm",
    "mean_island_height_nm_std",
    "n_lambda",
    "lamin_nm",
    "lamax_nm",
    "dlam_nm",
    "lambda_grid_is_uniform",
    "transmittance_dat",
    "transmittance_label",
    "Rave_equivalent_radius_nm",
    "Rave_volume_equivalent_radius_nm",
    "Rave_height_equivalent_radius_mean_nm",
    "Rave_height_equivalent_radius_p95_nm",
]


def write_model_input_dat(rows: list[dict[str, Any]], path: Path) -> None:
    header = (
        "# time_s n_afm_scans coverage coverage_std effe_proxy effe_proxy_name effe_proxy_formula "
        "afm_Rave_nm afm_Rave_nm_std radius_proxy_name dist_type axis_name fit_status fit_path "
        "log_likelihood bic fit_converged fit_iterations fit_samples "
        "w1 muL1 sigL1 mean1_nm std1_nm "
        "w2 muL2 sigL2 mean2_nm std2_nm "
        "dist_mean_nm dist_std_nm "
        "eq_thickness_nm eq_thickness_nm_std density_um2 density_um2_std "
        "mean_height_nm mean_height_nm_std "
        "n_lambda lamin_nm lamax_nm dlam_nm lambda_grid_is_uniform "
        "transmittance_label transmittance_dat afm_sources "
        "Rave_equivalent_radius_nm Rave_volume_equivalent_radius_nm "
        "Rave_height_equivalent_radius_mean_nm Rave_height_equivalent_radius_p95_nm "
        "thickness_proxy_name thickness_proxy_formula "
        "afm_eq_thickness_nm afm_eq_thickness_nm_std\n"
    )
    lines = [
        (
            "{time_s} {n_afm_scans} "
            "{coverage_fraction:.10g} {coverage_fraction_std:.10g} "
            "{effe_proxy:.10g} {effe_proxy_name} {effe_proxy_formula} "
            "{afm_Rave_nm:.10g} {afm_Rave_nm_std:.10g} "
            "{radius_proxy_name} "
            "{distribution_type} {distribution_axis_name} {distribution_fit_status} {distribution_fit_path} "
            "{distribution_log_likelihood:.10g} {distribution_bic:.10g} "
            "{distribution_fit_converged} {distribution_fit_iterations} {distribution_sample_count} "
            "{mixture_weight_1:.10g} {muL1:.10g} {sigL1:.10g} {component_1_mean_nm:.10g} {component_1_std_nm:.10g} "
            "{mixture_weight_2:.10g} {muL2:.10g} {sigL2:.10g} {component_2_mean_nm:.10g} {component_2_std_nm:.10g} "
            "{distribution_mean_nm:.10g} {distribution_std_nm:.10g} "
            "{equivalent_thickness_nm:.10g} {equivalent_thickness_nm_std:.10g} "
            "{number_density_per_um2:.10g} {number_density_per_um2_std:.10g} "
            "{mean_island_height_nm:.10g} {mean_island_height_nm_std:.10g} "
            "{n_lambda} {lamin_nm:.10g} {lamax_nm:.10g} {dlam_nm:.10g} {lambda_grid_is_uniform} "
            "{transmittance_label} {transmittance_dat} {afm_sources} "
            "{Rave_equivalent_radius_nm:.10g} {Rave_volume_equivalent_radius_nm:.10g} "
            "{Rave_height_equivalent_radius_mean_nm:.10g} {Rave_height_equivalent_radius_p95_nm:.10g} "
            "{thickness_proxy_name} {thickness_proxy_formula} "
            "{afm_equivalent_thickness_nm:.10g} {afm_equivalent_thickness_nm_std:.10g}\n"
        ).format(**row)
        for row in rows
    ]
    write_dat_lines(path, header, lines)


def main() -> int:
    try:
        args = parse_args()

        suffixes = {normalize_suffix(s) for s in args.include_suffixes.split(",")}
        afm_files = gather_json_files(args.afm_inputs)
        afm_grouped = load_filtered_payload_records(afm_files, suffixes)
        transmittance = gather_transmittance_summaries(args.transmittance_dir)
        rows = build_rows(
            afm_grouped,
            transmittance,
            args.radius_proxy,
            args.effe_proxy,
            args.thickness_proxy,
        )

        args.outdir.mkdir(parents=True, exist_ok=True)
        csv_path = args.outdir / f"{args.basename}.csv"
        dat_path = args.outdir / f"{args.basename}.dat"

        write_csv(rows, csv_path, CSV_FIELDNAMES)
        write_model_input_dat(rows, dat_path)

        print(f"Wrote: {csv_path}")
        print(f"Wrote: {dat_path}")
        return 0
    except ExperimentalInputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
