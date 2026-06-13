#!/usr/bin/env python3
"""Build the curated MMGM report dataset from existing optimizer outputs."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
REPORT_DATA = ROOT / "data/output/report"
REPORT_RUNS = REPORT_DATA / "selected_runs"
REPORT_PERMITTIVITY = REPORT_DATA / "permittivity"
REPORT_IMG = ROOT / "img/report"
REPORT_FITS_IMG = REPORT_IMG / "selected_fits"
REPORT_GP = ROOT / "scripts/gnuplot/report"
REPORT_FITS_GP = REPORT_GP / "selected_fits"
EXPERIMENTAL_DIR = ROOT / "data/experimental/final/transmittance"
AFM_PRIOR = ROOT / "data/experimental/thesis/chap4-prior.dat"

TIMES = (10, 20, 30, 40, 50, 60)


@dataclass(frozen=True)
class Selection:
    time_s: int
    campaign: str
    generation: int
    seed: int
    selection_type: str
    source_dir: Path
    note: str

    @property
    def spectrum_stem(self) -> str:
        return f"ITO_Ag_{self.time_s}s_T_0"

    @property
    def source_json(self) -> Path:
        return self.source_dir / f"optimal_global_{self.spectrum_stem}.json"

    @property
    def source_dat(self) -> Path:
        return self.source_dir / f"optimal_global_{self.spectrum_stem}.dat"


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def rel_from(script: Path, target: Path) -> str:
    return Path(os.path.relpath(target.resolve(), script.parent.resolve())).as_posix()


def ensure_dirs() -> None:
    for path in (
        REPORT_DATA,
        REPORT_RUNS,
        REPORT_PERMITTIVITY,
        REPORT_IMG,
        REPORT_FITS_IMG,
        REPORT_GP,
        REPORT_FITS_GP,
    ):
        path.mkdir(parents=True, exist_ok=True)


def copy_with_notice(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"[missing optional] {rel(src)}")
        return
    if dst.exists():
        print(f"[replace] {rel(dst)} <- {rel(src)}")
    else:
        print(f"[copy] {rel(dst)} <- {rel(src)}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def selected_runs() -> list[Selection]:
    early = ROOT / (
        "data/output/tests/mmgm_early_global/mmgm_early_bounded_pop_64/"
        "gen_400/seed_111/mmgm_single/spheres"
    )
    transition = ROOT / (
        "data/output/tests/mmgm_transition_hag_window/free_hag_1.0_3.0_pop_64/"
        "gen_400/seed_54321/mmgm_single/spheres"
    )
    late = ROOT / (
        "data/output/tests/mmgm_single_optical_trusted_branch/"
        "optical_trusted_branch_pop_48/gen_300/seed_111/mmgm_single/spheres"
    )
    return [
        Selection(
            10,
            "data/output/tests/mmgm_early_global/mmgm_early_bounded_pop_64",
            400,
            111,
            "early",
            early,
            "early global MMGM branch, lowest total SSE among monotonic hAg early runs",
        ),
        Selection(
            20,
            "data/output/tests/mmgm_early_global/mmgm_early_bounded_pop_64",
            400,
            111,
            "early",
            early,
            "early global MMGM branch, monotonic hAg with 10s",
        ),
        Selection(
            30,
            "data/output/tests/mmgm_transition_hag_window/free_hag_1.0_3.0_pop_64",
            400,
            54321,
            "transition",
            transition,
            "transition hAg-window branch, selected as first physically meaningful low-SSE solution",
        ),
        Selection(
            40,
            "data/output/tests/mmgm_transition_hag_window/free_hag_1.0_3.0_pop_64",
            400,
            54321,
            "transition",
            transition,
            "transition hAg-window branch paired with selected 30s seed; avoids giant-radius/narrow-sigma branch",
        ),
        Selection(
            50,
            "data/output/tests/mmgm_single_optical_trusted_branch/optical_trusted_branch_pop_48",
            300,
            111,
            "late",
            late,
            "late global MMGM branch, lowest total SSE among globally coherent monotonic hAg runs",
        ),
        Selection(
            60,
            "data/output/tests/mmgm_single_optical_trusted_branch/optical_trusted_branch_pop_48",
            300,
            111,
            "late",
            late,
            "late global MMGM branch, monotonic hAg with 10s, 20s, and 50s",
        ),
    ]


def selected_paths(time_s: int) -> dict[str, Path]:
    stem = f"ITO_Ag_{time_s}s_T_0"
    return {
        "json": REPORT_RUNS / f"selected_{stem}.json",
        "dat": REPORT_RUNS / f"selected_{stem}.dat",
        "experimental": REPORT_RUNS / f"experimental_{stem}.dat",
        "image": REPORT_FITS_IMG / f"selected_fit_{time_s}s.png",
        "gp": REPORT_FITS_GP / f"selected_fit_{time_s}s.gp",
        "eps": REPORT_PERMITTIVITY / f"eps_slab_{time_s}s.dat",
    }


def build_selected_table(selections: Iterable[Selection]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for selection in selections:
        data = load_json(selection.source_json)
        params = data["best_parameters"]
        objective = data["objective"]
        rows.append(
            {
                "time_s": selection.time_s,
                "source_campaign": selection.campaign,
                "source_result_json": rel(selection.source_json),
                "selection_type": selection.selection_type,
                "seed": selection.seed,
                "generation": selection.generation,
                "SSE": objective["sse"],
                "effe": params["effe"],
                "thickness_nm": params["thickness_nm"],
                "hAg_nm": params["h_ag_nm"],
                "Rave_nm": params["rave_nm"],
                "sigL": params["sig_l"],
                "selection_note": selection.note,
            }
        )
    return rows


def write_selected_tables(rows: list[dict[str, object]]) -> None:
    columns = [
        "time_s",
        "source_campaign",
        "source_result_json",
        "selection_type",
        "seed",
        "generation",
        "SSE",
        "effe",
        "thickness_nm",
        "hAg_nm",
        "Rave_nm",
        "sigL",
        "selection_note",
    ]
    csv_path = REPORT_DATA / "selected_parameters.csv"
    json_path = REPORT_DATA / "selected_parameters.json"
    if csv_path.exists():
        print(f"[replace] {rel(csv_path)}")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    if json_path.exists():
        print(f"[replace] {rel(json_path)}")
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)
        handle.write("\n")


def copy_selected_artifacts(selections: Iterable[Selection]) -> None:
    for selection in selections:
        paths = selected_paths(selection.time_s)
        source_data = load_json(selection.source_json)
        copy_with_notice(selection.source_json, paths["json"])
        copy_with_notice(selection.source_dat, paths["dat"])
        copy_with_notice(ROOT / source_data["experimental_file"], paths["experimental"])
        copy_with_notice(ROOT / source_data["image_file"], paths["image"])
        copy_with_notice(ROOT / source_data["gnuplot_script"], paths["gp"])


def write_slab_permittivity(selections: Iterable[Selection]) -> None:
    for selection in selections:
        dst = selected_paths(selection.time_s)["eps"]
        if dst.exists():
            print(f"[replace] {rel(dst)}")
        with selection.source_dat.open(encoding="utf-8") as src, dst.open("w", encoding="utf-8") as out:
            out.write("# wavelength_nm Re_eps_eff Im_eps_eff\n")
            for line in src:
                if not line.strip() or line.startswith("#"):
                    continue
                fields = line.split()
                if len(fields) < 11 or fields[9].lower() == "nan" or fields[10].lower() == "nan":
                    continue
                out.write(f"{fields[0]} {fields[9]} {fields[10]}\n")


def load_afm_prior() -> dict[int, dict[str, float]]:
    rows: dict[int, dict[str, float]] = {}
    with AFM_PRIOR.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            time_s, radius, sig_l, thickness = line.split()[:4]
            rows[int(time_s)] = {
                "afm_radius_proxy_nm": float(radius),
                "afm_sigL_radius": float(sig_l),
                "afm_thickness_nm": float(thickness),
            }
    return rows


def write_afm_comparison(rows: list[dict[str, object]]) -> None:
    afm = load_afm_prior()
    path = REPORT_DATA / "selected_vs_afm_parameters.dat"
    if path.exists():
        print(f"[replace] {rel(path)}")
    with path.open("w", encoding="utf-8") as handle:
        handle.write(
            "# time_s MMGM_Rave_nm AFM_projected_area_radius_proxy_nm "
            "MMGM_sigL AFM_sigL_radius MMGM_thickness_nm AFM_thickness_nm "
            "MMGM_effe MMGM_hAg_nm\n"
        )
        for row in rows:
            time_s = int(row["time_s"])
            prior = afm[time_s]
            handle.write(
                f"{time_s} {row['Rave_nm']} {prior['afm_radius_proxy_nm']} "
                f"{row['sigL']} {prior['afm_sigL_radius']} "
                f"{row['thickness_nm']} {prior['afm_thickness_nm']} "
                f"{row['effe']} {row['hAg_nm']}\n"
            )


def gp_header(output: Path, size: str = "1500,950") -> list[str]:
    return [
        "set terminal pngcairo enhanced color size " + size + " font 'Arial,12'",
        f"set output '{rel_from(REPORT_GP / 'dummy.gp', output)}'",
        "set datafile commentschars '#'",
        "set grid",
        "set key outside right top",
        "set xlabel 'Wavelength (nm)'",
        "",
    ]


def write_fit_overlay_gp(script: Path, output: Path, by_regime: bool) -> None:
    if script.exists():
        print(f"[replace] {rel(script)}")
    colors = {
        10: "#1b9e77",
        20: "#66a61e",
        30: "#d95f02",
        40: "#e6ab02",
        50: "#7570b3",
        60: "#e7298a",
    }
    lines = [
        "set terminal pngcairo enhanced color size 1600,1000 font 'Arial,12'",
        f"set output '{rel_from(script, output)}'",
        "set datafile commentschars '#'",
        "set grid",
        "set xlabel 'Wavelength (nm)'",
        "set ylabel 'Transmittance'",
        "set xrange [300:800]",
        "set yrange [0:1.08]",
        "set key outside right top",
    ]
    if by_regime:
        lines += [
            "set multiplot layout 3,1 title 'Selected MMGM fits by regime'",
            "set key outside right top",
        ]
        groups = [("early", (10, 20)), ("transition", (30, 40)), ("late", (50, 60))]
    else:
        groups = [("all selected times", TIMES)]
    for title, times in groups:
        lines.append(f"set title '{title}'")
        plots = []
        for time_s in times:
            paths = selected_paths(time_s)
            plots.append(
                f"'{rel_from(script, paths['experimental'])}' using 1:3 "
                f"with points pointtype 7 pointsize 0.45 lc rgb '{colors[time_s]}' "
                f"title '{time_s}s exp'"
            )
            plots.append(
                f"'{rel_from(script, paths['dat'])}' using 1:3 "
                f"with lines linewidth 2.2 lc rgb '{colors[time_s]}' title '{time_s}s fit'"
            )
        lines.append("plot " + ", \\\n     ".join(plots))
    if by_regime:
        lines.append("unset multiplot")
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_parameter_gp(script: Path, output: Path) -> None:
    if script.exists():
        print(f"[replace] {rel(script)}")
    data = REPORT_DATA / "selected_vs_afm_parameters.dat"
    lines = [
        "set terminal pngcairo enhanced color size 1500,1050 font 'Arial,12'",
        f"set output '{rel_from(script, output)}'",
        "set datafile commentschars '#'",
        "set grid",
        "set key top left",
        "set xlabel 'Deposition time (s)'",
        "set xrange [5:65]",
        "set multiplot layout 2,2 title 'Selected MMGM parameters vs AFM/thesis priors'",
        "set ylabel 'Radius (nm)'",
        "set title 'AFM projected-area radius proxy vs MMGM optical Rave'",
        f"plot '{rel_from(script, data)}' using 1:2 with linespoints lw 2 pt 7 title 'MMGM optical Rave', \\",
        f"     '{rel_from(script, data)}' using 1:3 with linespoints lw 2 pt 5 title 'AFM projected-area radius proxy'",
        "set ylabel 'sigL'",
        "set title 'Lognormal width'",
        f"plot '{rel_from(script, data)}' using 1:4 with linespoints lw 2 pt 7 title 'MMGM sigL', \\",
        f"     '{rel_from(script, data)}' using 1:5 with linespoints lw 2 pt 5 title 'AFM/thesis sigL'",
        "set ylabel 'Thickness (nm)'",
        "set title 'Effective slab thickness'",
        f"plot '{rel_from(script, data)}' using 1:6 with linespoints lw 2 pt 7 title 'MMGM thickness', \\",
        f"     '{rel_from(script, data)}' using 1:7 with linespoints lw 2 pt 5 title 'AFM/thesis thickness'",
        "set ylabel 'Effective quantity'",
        "set title 'Filling fraction and Ag volume-per-area'",
        f"plot '{rel_from(script, data)}' using 1:8 with linespoints lw 2 pt 7 title 'effe', \\",
        f"     '{rel_from(script, data)}' using 1:9 with linespoints lw 2 pt 5 title 'hAg = effe * thickness (nm)'",
        "unset multiplot",
    ]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_permittivity_gp(script: Path, output: Path, by_regime: bool) -> None:
    if script.exists():
        print(f"[replace] {rel(script)}")
    colors = {
        10: "#1b9e77",
        20: "#66a61e",
        30: "#d95f02",
        40: "#e6ab02",
        50: "#7570b3",
        60: "#e7298a",
    }
    lines = [
        "set terminal pngcairo enhanced color size 1600,1000 font 'Arial,12'",
        f"set output '{rel_from(script, output)}'",
        "set datafile commentschars '#'",
        "set grid",
        "set xlabel 'Wavelength (nm)'",
        "set xrange [300:800]",
        "set key outside right top",
    ]
    if by_regime:
        lines.append("set multiplot layout 3,2 title 'Selected MMGM slab permittivity by regime'")
        groups = [("early", (10, 20)), ("transition", (30, 40)), ("late", (50, 60))]
        for title, times in groups:
            for col, ylabel in ((2, "Re epsilon_eff"), (3, "Im epsilon_eff")):
                lines += [f"set title '{title}: {ylabel}'", f"set ylabel '{ylabel}'"]
                plots = [
                    f"'{rel_from(script, selected_paths(time_s)['eps'])}' using 1:{col} "
                    f"with lines lw 2 lc rgb '{colors[time_s]}' title '{time_s}s'"
                    for time_s in times
                ]
                lines.append("plot " + ", \\\n     ".join(plots))
    else:
        lines.append("set multiplot layout 2,1 title 'Selected MMGM nanoisland slab permittivity'")
        for col, ylabel in ((2, "Re epsilon_eff"), (3, "Im epsilon_eff")):
            lines += [f"set title '{ylabel}(lambda)'", f"set ylabel '{ylabel}'"]
            plots = [
                f"'{rel_from(script, selected_paths(time_s)['eps'])}' using 1:{col} "
                f"with lines lw 2 lc rgb '{colors[time_s]}' title '{time_s}s'"
                for time_s in TIMES
            ]
            lines.append("plot " + ", \\\n     ".join(plots))
    lines.append("unset multiplot")
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_gnuplot(script: Path) -> None:
    print(f"[gnuplot] {rel(script)}")
    subprocess.run(["gnuplot", script.name], cwd=script.parent, check=True)


def write_readme(rows: list[dict[str, object]]) -> None:
    path = REPORT_DATA / "README.md"
    selected_lines = [
        f"- {int(row['time_s'])}s: seed {row['seed']}, generation {row['generation']}, "
        f"SSE {float(row['SSE']):.8g}; {row['selection_note']}"
        for row in rows
    ]
    text = f"""# Curated MMGM report dataset

This directory contains selected MMGM single-lognormal sphere results copied from existing optimizer outputs. No optimizer campaign is rerun by the curation script.

## Campaigns used

- Early regime, 10s and 20s: `data/output/tests/mmgm_early_global/mmgm_early_bounded_pop_64`.
- Transition regime, 30s and 40s: `data/output/tests/mmgm_transition_hag_window/free_hag_1.0_3.0_pop_64`.
- Late regime, 50s and 60s: `data/output/tests/mmgm_single_optical_trusted_branch/optical_trusted_branch_pop_48`.

## Selected runs

{chr(10).join(selected_lines)}

## Selection notes

MMGM single-lognormal spheres are used as the working model because this branch gives a coherent optical description with interpretable morphology parameters and monotonic Ag volume-per-area (`hAg = effe * thickness_nm`) in the early and late global selections.

Bruggeman outputs are not included as selected model outputs. They remain a tested comparison branch, but were less successful for the 50s-60s spectra and are therefore not used for the curated collaborator-facing dataset.

The 30s and 40s spectra are treated as transition-region fits. The selected transition run is constrained to the `hAg` window of 1.0-3.0 nm and is the first low-SSE solution that remains physically interpretable. The 30s spectrum has competing branches; several lower-rank alternatives move toward large-radius or narrow-sigma compensation, so those are not used as the curated branch.

The AFM/thesis radius column is a projected-area equivalent radius proxy, `r = sqrt(A/pi)`. It is related to, but not identical with, the MMGM optical `Rave` parameter.

## Generated files

- `selected_parameters.csv` and `selected_parameters.json`: selected run table.
- `selected_runs/`: copied JSON, fitted spectra, experimental references, fit images, and original fit gnuplot scripts.
- `selected_vs_afm_parameters.dat`: numeric MMGM-vs-AFM comparison data.
- `permittivity/eps_slab_*s.dat`: selected slab effective permittivity curves extracted from the selected theoretical spectra.
"""
    if path.exists():
        print(f"[replace] {rel(path)}")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    selections = selected_runs()
    rows = build_selected_table(selections)
    write_selected_tables(rows)
    copy_selected_artifacts(selections)
    write_slab_permittivity(selections)
    write_afm_comparison(rows)
    write_readme(rows)

    scripts = [
        (
            REPORT_GP / "plot_selected_mmgm_fits_all_times.gp",
            REPORT_IMG / "selected_mmgm_fits_all_times.png",
            lambda script, output: write_fit_overlay_gp(script, output, by_regime=False),
        ),
        (
            REPORT_GP / "plot_selected_mmgm_fits_by_regime.gp",
            REPORT_IMG / "selected_mmgm_fits_by_regime.png",
            lambda script, output: write_fit_overlay_gp(script, output, by_regime=True),
        ),
        (
            REPORT_GP / "plot_selected_parameter_comparison.gp",
            REPORT_IMG / "selected_parameter_comparison.png",
            write_parameter_gp,
        ),
        (
            REPORT_GP / "plot_selected_mmgm_slab_permittivity.gp",
            REPORT_IMG / "selected_mmgm_slab_permittivity.png",
            lambda script, output: write_permittivity_gp(script, output, by_regime=False),
        ),
        (
            REPORT_GP / "plot_selected_mmgm_slab_permittivity_by_regime.gp",
            REPORT_IMG / "selected_mmgm_slab_permittivity_by_regime.png",
            lambda script, output: write_permittivity_gp(script, output, by_regime=True),
        ),
    ]
    for script, output, writer in scripts:
        writer(script, output)
        run_gnuplot(script)

    required = [
        REPORT_DATA / "selected_parameters.csv",
        REPORT_DATA / "selected_parameters.json",
        REPORT_DATA / "README.md",
        REPORT_IMG / "selected_mmgm_fits_all_times.png",
        REPORT_IMG / "selected_parameter_comparison.png",
        REPORT_IMG / "selected_mmgm_slab_permittivity.png",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing required outputs: " + ", ".join(rel(path) for path in missing))
    print("[done] curated MMGM report dataset generated")


if __name__ == "__main__":
    main()
