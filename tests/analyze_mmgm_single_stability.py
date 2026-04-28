#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


DEFAULT_ROOT = Path("data/output/tests/mmgm_single_seed_stability")
DEFAULT_SUMMARY = DEFAULT_ROOT / "summary.csv"
DEFAULT_STABILITY = DEFAULT_ROOT / "stability_by_generation.csv"
PARAMETERS = ("effe", "thickness_nm", "rave_nm", "sig_l")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze MMGM single-lognormal seed-stability CSV outputs."
    )
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--stability", type=Path, default=DEFAULT_STABILITY)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"Missing input CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_float(row: dict[str, str], key: str, source: Path) -> float:
    value = row.get(key, "")
    if value == "":
        raise SystemExit(f"Missing {key} value in {source}")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid {key} value {value!r} in {source}") from exc
    if not math.isfinite(parsed):
        raise SystemExit(f"Non-finite {key} value {value!r} in {source}")
    return parsed


def parse_int(row: dict[str, str], key: str, source: Path) -> int:
    value = row.get(key, "")
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid {key} value {value!r} in {source}") from exc


def spectrum_label(spectrum: str) -> str:
    parts = spectrum.split("_")
    for part in parts:
        if part.endswith("s") and part[:-1].isdigit():
            return part
    return spectrum


def spectrum_sort_key(spectrum: str) -> tuple[int, str]:
    label = spectrum_label(spectrum)
    if label.endswith("s") and label[:-1].isdigit():
        return int(label[:-1]), spectrum
    return 10**9, spectrum


def rel_spread(min_value: float, max_value: float) -> float:
    mean_value = (min_value + max_value) / 2.0
    if mean_value == 0:
        return 0.0 if max_value == min_value else math.inf
    return (max_value - min_value) / abs(mean_value)


def format_percent(value: float) -> str:
    if math.isinf(value):
        return "inf %"
    return f"{100.0 * value:.1f} %"


def format_factor(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.2f}"


def parameter_spreads(row: dict[str, float]) -> dict[str, float]:
    return {
        parameter: rel_spread(row[f"{parameter}_min"], row[f"{parameter}_max"])
        for parameter in PARAMETERS
    }


def classify(row: dict[str, float]) -> tuple[str, str]:
    sse_spread = row["sse_rel_spread"]
    spreads = parameter_spreads(row)
    max_param_spread = max(spreads.values())

    if sse_spread > 0.05:
        return "UNSTABLE", "optimizer has not converged reproducibly"
    if sse_spread < 0.01 and all(value < 0.05 for value in spreads.values()):
        return "STABLE", "fit and parameters are reproducible"
    if sse_spread < 0.02 and any(value > 0.50 for value in spreads.values()):
        return "DEGENERATE", "likely multimodal distribution"
    if sse_spread < 0.02 and max_param_spread < 0.20:
        return "WEAKLY STABLE", "fit is reproducible with moderate parameter drift"
    return "UNSTABLE", "borderline spread outside stability thresholds"


def build_stability_index(
    stability_rows: list[dict[str, str]], stability_path: Path
) -> dict[str, dict[int, dict[str, float]]]:
    by_spectrum: dict[str, dict[int, dict[str, float]]] = defaultdict(dict)
    for raw_row in stability_rows:
        generation = parse_int(raw_row, "generation", stability_path)
        spectrum = raw_row.get("spectrum", "")
        if not spectrum:
            raise SystemExit(f"Missing spectrum value in {stability_path}")

        parsed = {
            "generation": float(generation),
            "n_runs": float(parse_int(raw_row, "n_runs", stability_path)),
            "sse_min": parse_float(raw_row, "sse_min", stability_path),
            "sse_max": parse_float(raw_row, "sse_max", stability_path),
            "sse_rel_spread": parse_float(raw_row, "sse_rel_spread", stability_path),
        }
        for parameter in PARAMETERS:
            parsed[f"{parameter}_min"] = parse_float(
                raw_row, f"{parameter}_min", stability_path
            )
            parsed[f"{parameter}_max"] = parse_float(
                raw_row, f"{parameter}_max", stability_path
            )
        by_spectrum[spectrum][generation] = parsed
    return by_spectrum


def validate_summary(
    summary_rows: list[dict[str, str]],
    stability: dict[str, dict[int, dict[str, float]]],
    summary_path: Path,
) -> None:
    if not summary_rows:
        raise SystemExit(f"No rows found in {summary_path}")
    summary_keys = {
        (row.get("spectrum", ""), parse_int(row, "generation", summary_path))
        for row in summary_rows
    }
    missing = [
        (spectrum, generation)
        for spectrum, generations in stability.items()
        for generation in generations
        if (spectrum, generation) not in summary_keys
    ]
    if missing:
        first_spectrum, first_generation = missing[0]
        raise SystemExit(
            "Stability CSV references rows absent from summary CSV: "
            f"{first_spectrum} generation {first_generation}"
        )


def append_global_overview(
    lines: list[str], stability: dict[str, dict[int, dict[str, float]]]
) -> None:
    lines.append("=== GLOBAL OVERVIEW ===")
    generations = sorted({generation for values in stability.values() for generation in values})
    for generation in generations:
        spreads = [
            values[generation]["sse_rel_spread"]
            for values in stability.values()
            if generation in values
        ]
        mean_spread = sum(spreads) / len(spreads)
        max_spread = max(spreads)
        lines.append(f"Generation {generation}:")
        lines.append(f"  mean SSE spread: {format_percent(mean_spread)}")
        lines.append(f"  max SSE spread: {format_percent(max_spread)}")
    lines.append("")


def append_per_spectrum(
    lines: list[str], stability: dict[str, dict[int, dict[str, float]]]
) -> dict[str, tuple[str, str]]:
    lines.append("=== PER-SPECTRUM DIAGNOSTICS ===")
    classifications = {}
    for spectrum in sorted(stability, key=spectrum_sort_key):
        generations = sorted(stability[spectrum])
        final_generation = generations[-1]
        final_row = stability[spectrum][final_generation]
        spreads = parameter_spreads(final_row)

        lines.append(f"Spectrum: {spectrum_label(spectrum)}")
        lines.append("  SSE spread:")
        for generation in generations:
            spread = stability[spectrum][generation]["sse_rel_spread"]
            lines.append(f"    gen{generation}: {format_percent(spread):>7}")
        lines.append("")
        lines.append(f"  Parameter ranges (gen{final_generation}):")
        for parameter in PARAMETERS:
            min_value = final_row[f"{parameter}_min"]
            max_value = final_row[f"{parameter}_max"]
            lines.append(
                f"    {parameter + ':':13} "
                f"[{min_value:.6g}, {max_value:.6g}]  "
                f"Δrel = {format_percent(spreads[parameter])}"
            )

        status, reason = classify(final_row)
        classifications[spectrum] = (status, reason)
        lines.append("")
        lines.append(f"Spectrum {spectrum_label(spectrum)} → {status} ({reason})")
        lines.append("")
    return classifications


def append_improvement(
    lines: list[str], stability: dict[str, dict[int, dict[str, float]]]
) -> None:
    lines.append("=== CROSS-GENERATION IMPROVEMENT ===")
    for spectrum in sorted(stability, key=spectrum_sort_key):
        generations = sorted(stability[spectrum])
        if len(generations) < 2:
            continue
        first_generation = generations[0]
        final_generation = generations[-1]
        first_spread = stability[spectrum][first_generation]["sse_rel_spread"]
        final_spread = stability[spectrum][final_generation]["sse_rel_spread"]
        if final_spread == 0:
            factor = math.inf if first_spread > 0 else 1.0
        else:
            factor = first_spread / final_spread
        lines.append(f"{spectrum_label(spectrum)}:")
        lines.append("  SSE spread improvement:")
        lines.append(
            f"    {first_generation} → {final_generation}: "
            f"factor {format_factor(factor)} reduction"
        )
    lines.append("")


def append_final_diagnosis(
    lines: list[str], classifications: dict[str, tuple[str, str]]
) -> None:
    stable = [
        spectrum_label(spectrum)
        for spectrum, (status, _) in classifications.items()
        if status == "STABLE"
    ]
    degenerate = [
        spectrum_label(spectrum)
        for spectrum, (status, _) in classifications.items()
        if status == "DEGENERATE"
    ]
    unstable = [
        spectrum_label(spectrum)
        for spectrum, (status, _) in classifications.items()
        if status == "UNSTABLE"
    ]

    lines.append("=== FINAL DIAGNOSIS ===")
    lines.append("")
    lines.append(f"Stable spectra: {stable}")
    lines.append(f"Degenerate spectra: {degenerate}")
    lines.append(f"Unstable spectra: {unstable}")
    lines.append("")
    lines.append("Recommendation:")
    lines.append("")
    total = len(classifications)
    if unstable:
        lines.append("- UNSTABLE present -> increase generations or tighten bounds")
    elif len(degenerate) >= max(1, total // 2):
        lines.append("- Many DEGENERATE -> double-lognormal strongly recommended")
    elif len(stable) >= max(1, math.ceil(0.75 * total)):
        lines.append("- Most spectra STABLE -> proceed to double-lognormal")
    elif degenerate:
        lines.append("- Some DEGENERATE -> double-lognormal is recommended")
    else:
        lines.append("- Mixed weak stability -> inspect parameter ranges before expanding model")


def build_report(summary_path: Path, stability_path: Path) -> str:
    summary_rows = read_csv(summary_path)
    stability_rows = read_csv(stability_path)
    stability = build_stability_index(stability_rows, stability_path)
    if not stability:
        raise SystemExit(f"No rows found in {stability_path}")
    validate_summary(summary_rows, stability, summary_path)

    lines: list[str] = []
    append_global_overview(lines, stability)
    classifications = append_per_spectrum(lines, stability)
    append_improvement(lines, stability)
    append_final_diagnosis(lines, classifications)
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    report = build_report(args.summary, args.stability)
    print(report, end="")

    report_path = args.summary.parent / "report.txt"
    report_path.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
