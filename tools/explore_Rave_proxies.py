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

from afm_lib.radius_proxy import MANIFEST_RAVE_FIELD_FOR_RADIUS_PROXY, RADIUS_PROXY_CHOICES


DEFAULT_INPUT = Path("data/input/experimental/model_input.dat")
DEFAULT_OUTDIR = Path("data/output/Rave_proxy")
DEFAULT_GNUPLOT = Path("scripts/gnuplot/output/Rave_proxy")
DEFAULT_IMGDIR = Path("img/output/Rave_proxy")


class RaveProxyError(RuntimeError):
    """Raised when Rave proxy exploration cannot proceed."""


@dataclass(frozen=True)
class Record:
    time_s: int
    values: dict[str, float]


@dataclass(frozen=True)
class ProxyDiagnostics:
    name: str
    min_value: float
    max_value: float
    reversals: int
    monotone_non_decreasing: bool
    monotone_non_increasing: bool
    normalized_range: float


FIELD_ALIASES: dict[str, list[str]] = {
    "time_s": ["time_s"],
    **{
        manifest_field: [manifest_field]
        for manifest_field in MANIFEST_RAVE_FIELD_FOR_RADIUS_PROXY.values()
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Explore candidate Rave proxies from data/input/experimental/model_input.dat, "
            "write comparison tables, and generate a gnuplot script."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--gnuplot-dir", type=Path, default=DEFAULT_GNUPLOT)
    parser.add_argument("--img-dir", type=Path, default=DEFAULT_IMGDIR)
    return parser.parse_args()


def require_input(path: Path) -> None:
    if not path.exists():
        raise RaveProxyError(
            f"Input file not found: {path}\n"
            "Please run python3 tools/build_experimental_input.py first."
        )


def _parse_header_tokens(header_line: str) -> list[str]:
    stripped = header_line.strip()
    if not stripped.startswith("#"):
        raise RaveProxyError("Expected the first line of the manifest to start with '#'")
    return stripped[1:].strip().split()


def _find_field_index(header_tokens: list[str], canonical_name: str) -> int:
    aliases = FIELD_ALIASES[canonical_name]
    for alias in aliases:
        if alias in header_tokens:
            return header_tokens.index(alias)
    raise RaveProxyError(
        f"Could not locate required field '{canonical_name}' in header. "
        f"Accepted aliases: {', '.join(aliases)}"
    )


def load_records(path: Path) -> list[Record]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise RaveProxyError(f"Input file is empty: {path}")

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
                    values={
                        proxy_name: float(parts[indices[manifest_field]])
                        for proxy_name, manifest_field in MANIFEST_RAVE_FIELD_FOR_RADIUS_PROXY.items()
                    },
                )
            )
        except (IndexError, ValueError) as exc:
            raise RaveProxyError(f"Failed to parse data line: {line}") from exc

    if not records:
        raise RaveProxyError(f"No data rows found in: {path}")

    records.sort(key=lambda item: item.time_s)
    return records


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


def build_diagnostics(records: list[Record]) -> list[ProxyDiagnostics]:
    diagnostics: list[ProxyDiagnostics] = []
    for proxy_name in RADIUS_PROXY_CHOICES:
        values = [record.values[proxy_name] for record in records]
        min_value = min(values)
        max_value = max(values)
        normalized_range = 0.0 if max_value == 0.0 else (max_value - min_value) / max_value
        diagnostics.append(
            ProxyDiagnostics(
                name=proxy_name,
                min_value=min_value,
                max_value=max_value,
                reversals=count_reversals(values),
                monotone_non_decreasing=all(b >= a for a, b in zip(values, values[1:])),
                monotone_non_increasing=all(b <= a for a, b in zip(values, values[1:])),
                normalized_range=normalized_range,
            )
        )
    return diagnostics


def write_comparison_dat(path: Path, records: list[Record]) -> None:
    header_fields = ["time_s", *RADIUS_PROXY_CHOICES]
    lines = ["# " + " ".join(header_fields)]
    for record in records:
        row = [str(record.time_s), *[f"{record.values[name]:.10g}" for name in RADIUS_PROXY_CHOICES]]
        lines.append(" ".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_comparison_csv(path: Path, records: list[Record]) -> None:
    fieldnames = ["time_s", *RADIUS_PROXY_CHOICES]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {"time_s": record.time_s, **record.values}
            writer.writerow(row)


def write_diagnostics(path: Path, diagnostics: list[ProxyDiagnostics]) -> None:
    lines = [
        "# proxy_name min_value max_value reversals monotone_non_decreasing monotone_non_increasing normalized_range"
    ]
    for item in diagnostics:
        lines.append(
            f"{item.name} {item.min_value:.10g} {item.max_value:.10g} {item.reversals} "
            f"{int(item.monotone_non_decreasing)} {int(item.monotone_non_increasing)} "
            f"{item.normalized_range:.10g}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gnuplot_script(path: Path, dat_path: Path, png_path: Path) -> None:
    plot_cmds = [
        f"    '{dat_path.as_posix()}' using 1:{idx + 2} with linespoints lw 2 pt 7 title '{name}'"
        for idx, name in enumerate(RADIUS_PROXY_CHOICES)
    ]
    script = f"""set terminal pngcairo size 1400,900 enhanced
set output '{png_path.as_posix()}'

set title 'Candidate Rave proxies vs deposition time'
set xlabel 'Deposition time (s)'
set ylabel 'Radius proxy value (nm)'
set grid
set key outside right top
set xtics 10

plot \\
{', \\\n'.join(plot_cmds)}
"""
    path.write_text(script, encoding="utf-8")


def main() -> int:
    args = parse_args()
    require_input(args.input)
    records = load_records(args.input)
    diagnostics = build_diagnostics(records)

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.gnuplot_dir.mkdir(parents=True, exist_ok=True)
    args.img_dir.mkdir(parents=True, exist_ok=True)

    dat_path = args.outdir / "Rave_proxy_comparison.dat"
    csv_path = args.outdir / "Rave_proxy_comparison.csv"
    diag_path = args.outdir / "Rave_proxy_diagnostics.dat"
    gp_path = args.gnuplot_dir / "plot_Rave_proxies.gp"
    png_path = args.img_dir / "Rave_proxy_comparison.png"

    write_comparison_dat(dat_path, records)
    write_comparison_csv(csv_path, records)
    write_diagnostics(diag_path, diagnostics)
    write_gnuplot_script(gp_path, dat_path, png_path)

    print(f"Wrote: {dat_path}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {diag_path}")
    print(f"Wrote: {gp_path}")
    print(f"Plot target: {png_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RaveProxyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
