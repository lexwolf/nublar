from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


TIME_RE = re.compile(r"Nis_Ag_(\d+)s_.*_features\.json$")
DEFAULT_BATCH_ROOT = Path("data/experimental/intermediate/afm_batch")


class DatasetError(RuntimeError):
    """Raised when AFM dataset aggregation fails."""


def ensure_data_dir(path: Path) -> Path:
    """Resolve and validate that a path lives under the top-level data tree."""
    parts = path.parts
    if not parts or parts[0] != "data":
        raise DatasetError(f"Output path must live under data/: {path}")
    return path


def image_dir_for_data_dir(data_dir: Path) -> Path:
    """Mirror a data domain under img/ for generated figures."""
    data_dir = ensure_data_dir(data_dir)
    return Path("img", *data_dir.parts[1:])


def gnuplot_dir_for_data_dir(data_dir: Path) -> Path:
    """Mirror a data domain under scripts/gnuplot/ for generated plot scripts."""
    data_dir = ensure_data_dir(data_dir)
    return Path("scripts", "gnuplot", *data_dir.parts[1:])


def normalize_suffix(token: str) -> str:
    """Normalize accepted scan suffix selectors."""
    text = token.strip().lower()
    if text in {"image", "img", "image1", "image_1"}:
        return "image"
    if text in {"001", "002", "003"}:
        return text
    raise DatasetError(f"Unsupported suffix token: {token}")


def extract_time_s(path: Path) -> int:
    """Parse deposition time in seconds from a feature JSON filename."""
    match = TIME_RE.search(path.name)
    if not match:
        raise DatasetError(f"Could not parse deposition time from filename: {path}")
    return int(match.group(1))


def extract_source_label(path: Path) -> str:
    """Parse the scan source label from a feature JSON filename."""
    name = path.name
    if "Image_1" in name:
        return "image"
    for suffix in ("001", "002", "003"):
        if f"_{suffix}_" in name or name.endswith(f"_{suffix}_features.json"):
            return suffix
    raise DatasetError(f"Could not parse source label from filename: {path}")


def gather_json_files(inputs: list[Path], default_root: Path = DEFAULT_BATCH_ROOT) -> list[Path]:
    """Collect feature JSON files from paths or from the default batch root."""
    if not inputs:
        if not default_root.exists():
            raise DatasetError(
                "No inputs provided and default batch directory does not exist: "
                f"{default_root}"
            )
        return sorted(default_root.rglob("*_features.json"))

    files: list[Path] = []
    for path in inputs:
        if path.is_dir():
            files.extend(sorted(path.rglob("*_features.json")))
        elif path.is_file():
            files.append(path)
        else:
            raise DatasetError(f"Input path does not exist: {path}")

    if not files:
        raise DatasetError("No feature JSON files found in the provided inputs")
    return sorted(files)


def load_feature_payload(path: Path) -> dict[str, Any]:
    """Load one per-scan AFM feature JSON payload."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload


def load_summary(path: Path) -> dict[str, Any]:
    """Load the summary section from one feature JSON payload."""
    payload = load_feature_payload(path)
    if "summary" not in payload:
        raise DatasetError(f"Missing 'summary' section in: {path}")
    return payload["summary"]


def mean_std(values: list[float]) -> tuple[float, float]:
    """Population mean/std helper matching the current scripts."""
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    return float(mean(values)), float(pstdev(values))


def group_summaries_by_time(
    files: list[Path],
    allowed_sources: set[str],
) -> dict[int, list[dict[str, Any]]]:
    """Group feature summaries by deposition time after source filtering."""
    grouped: dict[int, list[dict[str, Any]]] = {}
    for path in files:
        source = extract_source_label(path)
        if source not in allowed_sources:
            continue
        summary = dict(load_summary(path))
        summary["_source"] = source
        summary["_path"] = str(path)
        grouped.setdefault(extract_time_s(path), []).append(summary)

    if not grouped:
        raise DatasetError("No JSON summaries matched the requested suffix selection")
    return grouped


def load_filtered_payload_records(
    files: list[Path],
    allowed_sources: set[str],
) -> dict[int, list[dict[str, Any]]]:
    """Group full feature payload records by deposition time after source filtering."""
    grouped: dict[int, list[dict[str, Any]]] = {}
    for path in files:
        source = extract_source_label(path)
        if source not in allowed_sources:
            continue

        payload = load_feature_payload(path)
        if "summary" not in payload or "islands" not in payload:
            raise DatasetError(f"Missing 'summary' or 'islands' in: {path}")

        record = {
            "_path": str(path),
            "_source": source,
            "summary": dict(payload["summary"]),
            "islands": payload["islands"],
        }
        grouped.setdefault(extract_time_s(path), []).append(record)

    if not grouped:
        raise DatasetError("No JSON summaries matched the requested suffix selection")
    return grouped


def write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str]) -> None:
    """Write rows to CSV with an explicit field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_text(path: Path, text: str) -> None:
    """Write a text file, ensuring parent directories exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_dat_lines(path: Path, header: str, lines: list[str]) -> None:
    """Write a plain-text DAT table from a prepared header and lines."""
    write_text(path, header + "".join(lines))


def write_gnuplot_script(path: Path, template: str, dat_path: Path, png_name: str, label: str) -> None:
    """Write a gnuplot script using a shared template formatter."""
    script = template.format(dat_name=dat_path.as_posix(), png_name=png_name, label=label)
    write_text(path, script)
