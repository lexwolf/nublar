#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.effe_proxy import compute_effe_proxy


DEFAULT_INPUT = Path("data/input/experimental/model_input.dat")
DEFAULT_OUTDIR = Path("data/output/effe_proxy")
DEFAULT_GNUPLOT = Path("scripts/gnuplot/output/effe_proxy")
DEFAULT_IMGDIR = Path("img/output/effe_proxy")
GEOMETRY_CHOICES = ("spheres", "holes")


class EffeProxyError(RuntimeError):
    """Raised when effe proxy exploration cannot proceed."""


@dataclass(frozen=True)
class Record:
    time_s: int
    coverage_fraction: float
    eq_thickness_nm: float
    mean_height_nm: float
    afm_rave_nm: float


@dataclass(frozen=True)
class ProxyResult:
    name: str
    label: str
    values: list[float]


@dataclass(frozen=True)
class ProxyDiagnostics:
    name: str
    min_value: float
    max_value: float
    reversals: int
    in_unit_interval: bool
    monotone_non_decreasing: bool
    monotone_non_increasing: bool


# Header aliases taken from data/input/experimental/model_input.dat.
FIELD_ALIASES: dict[str, list[str]] = {
    "time_s": ["time_s"],
    "coverage_fraction": ["coverage", "coverage_fraction"],
    "eq_thickness_nm": ["eq_thickness_nm", "equivalent_thickness_nm"],
    "mean_height_nm": ["mean_height_nm", "mean_island_height_nm"],
    "afm_rave_nm": ["afm_Rave_nm", "Rave_nm"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Explore alternative effe proxies from the geometry-specific experimental manifest, "
            "write comparison tables, and generate a gnuplot script."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input experimental manifest (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help=f"Directory for comparison tables (default: {DEFAULT_OUTDIR})",
    )
    parser.add_argument(
        "--gnuplot-dir",
        type=Path,
        default=DEFAULT_GNUPLOT,
        help=f"Directory for generated gnuplot script (default: {DEFAULT_GNUPLOT})",
    )
    parser.add_argument(
        "--img-dir",
        type=Path,
        default=DEFAULT_IMGDIR,
        help=f"Directory for generated plot target (default: {DEFAULT_IMGDIR})",
    )
    parser.add_argument(
        "--clip-unit-interval",
        action="store_true",
        help="Clip all proxy values into [0, 1] before writing outputs",
    )
    parser.add_argument(
        "--geometry",
        choices=GEOMETRY_CHOICES,
        default="spheres",
        help="Morphology convention used to select the default manifest and proxy set",
    )
    return parser.parse_args()


def require_input(path: Path) -> None:
    if not path.exists():
        raise EffeProxyError(
            f"Input file not found: {path}\n"
            "Please run python3 tools/build_experimental_input.py first."
        )


def resolved_input_path(args: argparse.Namespace) -> Path:
    if args.input != DEFAULT_INPUT:
        return args.input
    if args.geometry == "holes":
        return Path("data/input/experimental/model_input__geom=holes.dat")
    return args.input


def _parse_header_tokens(header_line: str) -> list[str]:
    stripped = header_line.strip()
    if not stripped.startswith("#"):
        raise EffeProxyError("Expected the first line of the manifest to start with '#'")
    return stripped[1:].strip().split()


def _find_field_index(header_tokens: list[str], canonical_name: str) -> int:
    aliases = FIELD_ALIASES[canonical_name]
    for alias in aliases:
        if alias in header_tokens:
            return header_tokens.index(alias)
    raise EffeProxyError(
        f"Could not locate required field '{canonical_name}' in header. "
        f"Accepted aliases: {', '.join(aliases)}"
    )


def load_records(path: Path) -> list[Record]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise EffeProxyError(f"Input file is empty: {path}")

    header_tokens = _parse_header_tokens(lines[0])
    indices = {name: _find_field_index(header_tokens, name) for name in FIELD_ALIASES}

    records: list[Record] = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        try:
            records.append(
                Record(
                    time_s=int(parts[indices["time_s"]]),
                    coverage_fraction=float(parts[indices["coverage_fraction"]]),
                    eq_thickness_nm=float(parts[indices["eq_thickness_nm"]]),
                    mean_height_nm=float(parts[indices["mean_height_nm"]]),
                    afm_rave_nm=float(parts[indices["afm_rave_nm"]]),
                )
            )
        except (IndexError, ValueError) as exc:
            raise EffeProxyError(f"Failed to parse data line: {line}") from exc

    if not records:
        raise EffeProxyError(f"No data rows found in: {path}")

    records.sort(key=lambda item: item.time_s)
    return records


def maybe_clip(value: float, clip: bool) -> float:
    if not clip:
        return value
    return max(0.0, min(1.0, value))


def build_proxy_results(records: list[Record], clip: bool, geometry: str) -> list[ProxyResult]:
    coverage = [maybe_clip(r.coverage_fraction, clip) for r in records]
    baseline = [
        maybe_clip(
            compute_effe_proxy(
                "eq_thickness_over_mean_height",
                r.coverage_fraction,
                r.eq_thickness_nm,
                r.mean_height_nm,
                r.afm_rave_nm,
            ),
            clip,
        )
        for r in records
    ]
    product = [
        maybe_clip(
            compute_effe_proxy(
                "coverage_times_eq_over_hmean",
                r.coverage_fraction,
                r.eq_thickness_nm,
                r.mean_height_nm,
                r.afm_rave_nm,
            ),
            clip,
        )
        for r in records
    ]
    geometric = [
        maybe_clip(
            compute_effe_proxy(
                "sqrt_coverage_times_eq_over_hmean",
                r.coverage_fraction,
                r.eq_thickness_nm,
                r.mean_height_nm,
                r.afm_rave_nm,
            ),
            clip,
        )
        for r in records
    ]
    results = [
        ProxyResult("coverage_fraction", "coverage fraction", coverage),
        ProxyResult(
            "eq_thickness_over_mean_height",
            "eq thickness / mean height",
            baseline,
        ),
        ProxyResult(
            "coverage_times_eq_over_hmean",
            "coverage * (eq thickness / mean height)",
            product,
        ),
        ProxyResult(
            "sqrt_coverage_times_eq_over_hmean",
            "sqrt(coverage * (eq thickness / mean height))",
            geometric,
        ),
    ]

    if geometry != "holes":
        thickness_over_rave = [
            maybe_clip(
                compute_effe_proxy(
                    "eq_thickness_over_Rave",
                    r.coverage_fraction,
                    r.eq_thickness_nm,
                    r.mean_height_nm,
                    r.afm_rave_nm,
                ),
                clip,
            )
            for r in records
        ]
        results.append(
            ProxyResult(
                "eq_thickness_over_Rave",
                "eq thickness / Rave",
                thickness_over_rave,
            )
        )

    for name, label in (
        ("hybrid_alpha25", "coverage^0.25 * baseline^0.75"),
        ("hybrid_alpha50", "coverage^0.50 * baseline^0.50"),
        ("hybrid_alpha75", "coverage^0.75 * baseline^0.25"),
    ):
        values = [
            maybe_clip(
                compute_effe_proxy(
                    name,
                    r.coverage_fraction,
                    r.eq_thickness_nm,
                    r.mean_height_nm,
                    r.afm_rave_nm,
                ),
                clip,
            )
            for r in records
        ]
        results.append(
            ProxyResult(
                name,
                label,
                values,
            )
        )

    return results


def count_reversals(values: list[float], tolerance: float = 1e-12) -> int:
    direction = 0
    reversals = 0
    for left, right in zip(values, values[1:]):
        delta = right - left
        if abs(delta) <= tolerance:
            continue
        new_direction = 1 if delta > 0.0 else -1
        if direction != 0 and new_direction != direction:
            reversals += 1
        direction = new_direction
    return reversals



def build_diagnostics(results: list[ProxyResult]) -> list[ProxyDiagnostics]:
    diagnostics: list[ProxyDiagnostics] = []
    for result in results:
        values = result.values
        min_value = min(values)
        max_value = max(values)
        diagnostics.append(
            ProxyDiagnostics(
                name=result.name,
                min_value=min_value,
                max_value=max_value,
                reversals=count_reversals(values),
                in_unit_interval=(min_value >= 0.0 and max_value <= 1.0),
                monotone_non_decreasing=all(b >= a for a, b in zip(values, values[1:])),
                monotone_non_increasing=all(b <= a for a, b in zip(values, values[1:])),
            )
        )
    return diagnostics


def write_comparison_dat(path: Path, records: list[Record], results: list[ProxyResult]) -> None:
    header_fields = [
        "time_s",
        "coverage_fraction",
        "eq_thickness_over_mean_height",
        "eq_thickness_nm",
        "mean_height_nm",
        "afm_Rave_nm",
    ] + [result.name for result in results if result.name not in {"coverage_fraction", "eq_thickness_over_mean_height"}]

    lines = ["# " + " ".join(header_fields)]
    for idx, record in enumerate(records):
        row = [
            str(record.time_s),
            f"{record.coverage_fraction:.10g}",
            f"{compute_effe_proxy('eq_thickness_over_mean_height', record.coverage_fraction, record.eq_thickness_nm, record.mean_height_nm, record.afm_rave_nm):.10g}",
            f"{record.eq_thickness_nm:.10g}",
            f"{record.mean_height_nm:.10g}",
            f"{record.afm_rave_nm:.10g}",
        ]
        for result in results:
            if result.name in {"coverage_fraction", "eq_thickness_over_mean_height"}:
                continue
            row.append(f"{result.values[idx]:.10g}")
        lines.append(" ".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")



def write_comparison_csv(path: Path, records: list[Record], results: list[ProxyResult]) -> None:
    fieldnames = [
        "time_s",
        "coverage_fraction",
        "eq_thickness_over_mean_height",
        "eq_thickness_nm",
        "mean_height_nm",
        "afm_Rave_nm",
    ] + [result.name for result in results if result.name not in {"coverage_fraction", "eq_thickness_over_mean_height"}]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for idx, record in enumerate(records):
            row = {
                "time_s": record.time_s,
                "coverage_fraction": record.coverage_fraction,
                "eq_thickness_over_mean_height": compute_effe_proxy(
                    "eq_thickness_over_mean_height",
                    record.coverage_fraction,
                    record.eq_thickness_nm,
                    record.mean_height_nm,
                    record.afm_rave_nm,
                ),
                "eq_thickness_nm": record.eq_thickness_nm,
                "mean_height_nm": record.mean_height_nm,
                "afm_Rave_nm": record.afm_rave_nm,
            }
            for result in results:
                if result.name in {"coverage_fraction", "eq_thickness_over_mean_height"}:
                    continue
                row[result.name] = result.values[idx]
            writer.writerow(row)



def write_diagnostics(path: Path, diagnostics: list[ProxyDiagnostics]) -> None:
    lines = [
        "# proxy_name min_value max_value reversals in_unit_interval monotone_non_decreasing monotone_non_increasing"
    ]
    for item in diagnostics:
        lines.append(
            f"{item.name} {item.min_value:.10g} {item.max_value:.10g} {item.reversals} "
            f"{int(item.in_unit_interval)} {int(item.monotone_non_decreasing)} {int(item.monotone_non_increasing)}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")



def write_gnuplot_script(
    path: Path,
    dat_path: Path,
    png_path: Path,
    results: list[ProxyResult],
    geometry: str,
) -> None:
    series = [result for result in results]
    plot_cmds: list[str] = []
    column = 2
    # dat columns start with time_s in column 1.
    for result in series:
        if result.name == "coverage_fraction":
            column = 2
        elif result.name == "eq_thickness_over_mean_height":
            column = 3
        else:
            # base columns before derived proxies: 1..6, then derived start at 7.
            derived_index = [
                r.name
                for r in results
                if r.name not in {"coverage_fraction", "eq_thickness_over_mean_height"}
            ].index(result.name)
            column = 7 + derived_index
        plot_cmds.append(
            f"    '{dat_path.as_posix()}' using 1:{column} with linespoints lw 2 pt 7 title '{result.name}'"
        )

    script = f"""set terminal pngcairo noenhanced size 1400,900
set output '{png_path.as_posix()}'

set title 'Candidate effe proxies vs deposition time ({geometry})'
set xlabel 'Deposition time (s)'
set ylabel 'Proxy value'
set grid
set key outside right top
set xtics 10

plot \\
{', \\\n'.join(plot_cmds)}
"""
    path.write_text(script, encoding="utf-8")



def print_summary(records: list[Record], diagnostics: list[ProxyDiagnostics]) -> None:
    times = ", ".join(str(record.time_s) for record in records)
    print(f"Loaded deposition times: {times}")
    print("Proxy diagnostics:")
    for item in diagnostics:
        print(
            f"  - {item.name}: min={item.min_value:.4f}, max={item.max_value:.4f}, "
            f"reversals={item.reversals}, unit_interval={'yes' if item.in_unit_interval else 'no'}"
        )



def main() -> int:
    args = parse_args()
    input_path = resolved_input_path(args)
    require_input(input_path)

    records = load_records(input_path)
    results = build_proxy_results(records, args.clip_unit_interval, args.geometry)
    diagnostics = build_diagnostics(results)

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.gnuplot_dir.mkdir(parents=True, exist_ok=True)
    args.img_dir.mkdir(parents=True, exist_ok=True)

    suffix = "" if args.geometry == "spheres" else f"__geom={args.geometry}"
    dat_path = args.outdir / f"effe_proxy_comparison{suffix}.dat"
    csv_path = args.outdir / f"effe_proxy_comparison{suffix}.csv"
    diag_path = args.outdir / f"effe_proxy_diagnostics{suffix}.dat"
    gp_path = args.gnuplot_dir / f"plot_effe_proxies{suffix}.gp"
    png_path = args.img_dir / f"effe_proxy_comparison{suffix}.png"

    write_comparison_dat(dat_path, records, results)
    write_comparison_csv(csv_path, records, results)
    write_diagnostics(diag_path, diagnostics)
    write_gnuplot_script(gp_path, dat_path, png_path, results, args.geometry)
    print_summary(records, diagnostics)

    print(f"Wrote: {dat_path}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {diag_path}")
    print(f"Wrote: {gp_path}")
    print(f"Plot target: {png_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EffeProxyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
