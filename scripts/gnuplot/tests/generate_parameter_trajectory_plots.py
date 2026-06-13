#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any


PARAMETERS = [
    ("rave_nm", "Rave(t)", 7, "Rave (nm)", 2),
    ("sig_l", "sigL(t)", 8, "sigL", 3),
    ("thickness_nm", "thickness(t)", 5, "thickness (nm)", 4),
    ("effe", "effe(t)", 4, "effe", None),
    ("h_ag_nm", "hAg(t)", 6, "hAg (nm)", None),
]
COLORS = [
    "#5DA5DA",
    "#1F77B4",
    "#FAA43A",
    "#D55E00",
    "#60BD68",
    "#2CA02C",
    "#B276B2",
    "#9467BD",
]
DASHTYPES = [1, 2, 3, 4, 5, 6, 7, 8]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate MMGM parameter trajectory gnuplot scripts.")
    parser.add_argument("--data-dir", type=Path, default=None, help="Directory containing trajectory_manifest.json.")
    parser.add_argument("--root", type=Path, default=None, help="Campaign root. Used with --output-dir for compatibility.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory containing trajectory_manifest.json.")
    parser.add_argument(
        "--gnuplot-dir",
        type=Path,
        default=Path("scripts/gnuplot/tests/trajectory_diagnostics"),
        help="Directory for generated gnuplot scripts.",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("img/tests/trajectory_diagnostics"),
        help="Directory for generated PNG images.",
    )
    parser.add_argument("--no-run", action="store_true", help="Only generate scripts; do not run gnuplot.")
    return parser.parse_args()


def gnuplot_quote(path: Path | str) -> str:
    return "'" + str(path).replace("\\", "\\\\").replace("'", "\\'") + "'"


def load_manifest(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "trajectory_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def finite(value: Any) -> bool:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(parsed)


def style_maps(strategy: dict[str, Any]) -> tuple[dict[int, str], dict[int, int]]:
    generations = sorted({int(run["generation"]) for run in strategy["runs"]})
    seeds = sorted({int(run["seed"]) for run in strategy["runs"]})
    color_by_generation = {
        generation: COLORS[index % len(COLORS)]
        for index, generation in enumerate(generations)
    }
    dashtype_by_seed = {
        seed: DASHTYPES[index % len(DASHTYPES)]
        for index, seed in enumerate(seeds)
    }
    return color_by_generation, dashtype_by_seed


def reference_has_parameter(reference_file: Path, ref_column: int | None) -> bool:
    if ref_column is None or not reference_file.exists():
        return False
    with reference_file.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < ref_column:
                continue
            if finite(parts[ref_column - 1]):
                return True
    return False


def run_plot_expression(
    trajectory_file: Path,
    generation: int,
    seed: int,
    value_column: int,
    color: str,
    dashtype: int,
    title: str = "",
    linewidth: float = 1.4,
    points: bool = False,
) -> str:
    plot_style = "linespoints pt 7 ps 1.15" if points else "lines"
    title_expr = f"title {gnuplot_quote(title)}" if title else "notitle"
    return (
        f"{gnuplot_quote(trajectory_file)} using "
        f"($1=={generation} && $2=={seed} ? $3 : 1/0):{value_column} "
        f"with {plot_style} lw {linewidth:g} dt {dashtype} lc rgb {gnuplot_quote(color)} {title_expr}"
    )


def reference_expression(reference_file: Path, ref_column: int, title: str = "prior ref") -> str:
    return (
        f"{gnuplot_quote(reference_file)} using 1:{ref_column} "
        f"with linespoints lw 2 dt 2 pt 6 ps 1 lc rgb 'black' title {gnuplot_quote(title)}"
    )


def panel_plot_commands(
    strategy: dict[str, Any],
    trajectory_file: Path,
    reference_file: Path,
    parameter: tuple[str, str, int, str, int | None],
    color_by_generation: dict[int, str],
    dashtype_by_seed: dict[int, int],
) -> list[str]:
    _, panel_title, value_column, ylabel, ref_column = parameter
    commands = [
        f"set title {gnuplot_quote(panel_title)}",
        f"set ylabel {gnuplot_quote(ylabel)}",
        "set xlabel 'deposition time (s)'",
        "set grid",
    ]
    plots: list[str] = []
    for generation in sorted(color_by_generation):
        for seed in sorted(dashtype_by_seed):
            plots.append(
                run_plot_expression(
                    trajectory_file,
                    generation,
                    seed,
                    value_column,
                    color_by_generation[generation],
                    dashtype_by_seed[seed],
                )
            )
    best = strategy.get("best_run")
    if isinstance(best, dict):
        generation = int(best["generation"])
        seed = int(best["seed"])
        plots.append(
            run_plot_expression(
                trajectory_file,
                generation,
                seed,
                value_column,
                "red",
                1,
                title="best SSE",
                linewidth=3.5,
                points=True,
            )
        )
    if reference_has_parameter(reference_file, ref_column):
        assert ref_column is not None
        plots.append(reference_expression(reference_file, ref_column))
    commands.append("plot " + ", \\\n     ".join(plots))
    commands.append("unset title")
    return commands


def legend_commands(
    color_by_generation: dict[int, str],
    dashtype_by_seed: dict[int, int],
) -> list[str]:
    plots: list[str] = ["0 with lines lc rgb 'white' notitle"]
    for generation, color in color_by_generation.items():
        plots.append(f"NaN with lines lw 3 lc rgb {gnuplot_quote(color)} title {gnuplot_quote(f'gen {generation}')}")
    for seed, dashtype in dashtype_by_seed.items():
        plots.append(f"NaN with lines lw 2 dt {dashtype} lc rgb '#555555' title {gnuplot_quote(f'seed {seed}')}")
    plots.append("NaN with linespoints lw 3.5 pt 7 ps 1.15 lc rgb 'red' title 'best SSE'")
    plots.append("NaN with linespoints lw 2 dt 2 pt 6 ps 1 lc rgb 'black' title 'AFM ref'")
    return [
        "unset xlabel",
        "unset ylabel",
        "unset tics",
        "unset border",
        "set title 'Legend'",
        "plot " + ", \\\n     ".join(plots),
        "unset title",
        "set border",
        "set tics",
    ]


def write_strategy_script(
    *,
    strategy: dict[str, Any],
    gnuplot_dir: Path,
    image_dir: Path,
) -> Path:
    safe_name = strategy["safe_name"]
    trajectory_file = Path(strategy["trajectory_file"])
    reference_file = Path(strategy["reference_file"])
    script_path = gnuplot_dir / f"plot_parameter_trajectories_{safe_name}.gp"
    image_path = image_dir / f"{safe_name}.png"
    color_by_generation, dashtype_by_seed = style_maps(strategy)

    lines = [
        "set terminal pngcairo size 1600,1000 enhanced font 'Arial,12'",
        f"set output {gnuplot_quote(image_path)}",
        "set datafile missing 'NaN'",
        "set key outside right top font 'Arial,9'",
        "set multiplot layout 2,3 margins 0.07,0.90,0.08,0.92 spacing 0.08,0.12",
    ]
    for parameter in PARAMETERS:
        lines.extend(
            panel_plot_commands(
                strategy,
                trajectory_file,
                reference_file,
                parameter,
                color_by_generation,
                dashtype_by_seed,
            )
        )
    lines.extend(legend_commands(color_by_generation, dashtype_by_seed))
    lines.extend(["unset multiplot", "set output"])
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return script_path


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir or args.output_dir
    if data_dir is None:
        raise SystemExit("Provide --data-dir or --output-dir")
    manifest = load_manifest(data_dir)
    args.gnuplot_dir.mkdir(parents=True, exist_ok=True)
    args.image_dir.mkdir(parents=True, exist_ok=True)

    scripts: list[Path] = []
    for strategy in manifest.get("strategies", []):
        if not isinstance(strategy, dict):
            continue
        script_path = write_strategy_script(
            strategy=strategy,
            gnuplot_dir=args.gnuplot_dir,
            image_dir=args.image_dir,
        )
        scripts.append(script_path)
        print(f"Wrote {script_path}")

    if args.no_run:
        return 0
    if shutil.which("gnuplot") is None:
        raise SystemExit("gnuplot is required but was not found on PATH")
    for script_path in scripts:
        subprocess.run(["gnuplot", script_path.as_posix()], check=True)
        print(f"Ran {script_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
