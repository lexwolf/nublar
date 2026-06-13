from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np


HEADER_SIZE_RE = re.compile(r"Image header size:\s*(\d+)", re.IGNORECASE)
SECTION_RE = re.compile(r"^\[(.+?)\]\s*$")
KEYVAL_RE = re.compile(r"^\s*([^:]+):\s*(.*?)\s*$")


class STPFormatError(RuntimeError):
    """Raised when a WSxM STP file cannot be parsed safely."""


def decode_header(blob: bytes) -> tuple[str, int]:
    """Return decoded header text and declared header size in bytes."""
    probe = blob[:4096]
    try:
        probe_text = probe.decode("latin-1")
    except UnicodeDecodeError as exc:
        raise STPFormatError("Could not decode STP header probe as latin-1") from exc

    match = HEADER_SIZE_RE.search(probe_text)
    if not match:
        raise STPFormatError("Could not find 'Image header size' in STP file")

    header_size = int(match.group(1))
    if header_size <= 0:
        raise STPFormatError(f"Invalid header size: {header_size}")

    header_bytes = blob[:header_size]
    try:
        header_text = header_bytes.decode("latin-1")
    except UnicodeDecodeError as exc:
        raise STPFormatError("Could not decode full STP header as latin-1") from exc

    if "[Header end]" not in header_text:
        raise STPFormatError("Header does not contain '[Header end]' marker")

    return header_text, header_size


def parse_typed_value(raw: str) -> Any:
    """Best-effort parsing for common WSxM header values."""
    text = raw.strip()
    if not text:
        return ""

    lowered = text.lower()
    if lowered in {"yes", "no"}:
        return lowered == "yes"

    parts = text.split()
    if not parts:
        return text

    number = parts[0].replace(",", ".")
    try:
        value = float(number)
        if len(parts) == 1:
            return value
        return {"value": value, "unit": " ".join(parts[1:])}
    except ValueError:
        return text


def parse_header_text(header_text: str) -> dict[str, dict[str, Any]]:
    """Parse a WSxM STP header into section/key/value dictionaries."""
    sections: dict[str, dict[str, Any]] = {"root": {}}
    current_section = "root"

    for line in header_text.splitlines():
        section_match = SECTION_RE.match(line.strip())
        if section_match:
            current_section = section_match.group(1).strip()
            sections.setdefault(current_section, {})
            continue

        kv_match = KEYVAL_RE.match(line)
        if kv_match:
            key = kv_match.group(1).strip()
            value = parse_typed_value(kv_match.group(2))
            sections[current_section][key] = value

    return sections


def extract_scalar(meta: dict[str, dict[str, Any]], section: str, key: str) -> Any:
    """Fetch a required header scalar."""
    try:
        return meta[section][key]
    except KeyError as exc:
        raise STPFormatError(f"Missing header field [{section}] {key}") from exc


def numeric_value(item: Any) -> float:
    """Convert a scalar header item or typed-value mapping to float."""
    if isinstance(item, dict) and "value" in item:
        return float(item["value"])
    return float(item)


def guess_endianness(payload: bytes, rows: int, cols: int) -> str:
    """Heuristically choose endianness for a double-valued payload."""
    expected = rows * cols
    little = np.frombuffer(payload, dtype="<f8", count=expected)
    big = np.frombuffer(payload, dtype=">f8", count=expected)

    def score(arr: np.ndarray) -> float:
        finite = np.isfinite(arr)
        frac_finite = finite.mean()
        if frac_finite == 0:
            return -np.inf

        arrf = arr[finite]
        if arrf.size == 0:
            return -np.inf

        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            arr64 = arrf.astype(np.float64, copy=False)

            try:
                zmin = float(np.nanmin(arr64))
                zmax = float(np.nanmax(arr64))
                spread = zmax - zmin
                mean_abs = float(np.nanmean(np.abs(arr64)))
            except (FloatingPointError, OverflowError, ValueError):
                return -np.inf

        if not np.isfinite(spread) or not np.isfinite(mean_abs):
            return -np.inf

        penalty = 0.0
        if mean_abs > 1e6:
            penalty += 100.0
        if spread > 1e7:
            penalty += 100.0

        return frac_finite * 10.0 - penalty - abs(np.log10(max(mean_abs, 1e-12)))

    return "<" if score(little) >= score(big) else ">"


def load_stp(path: str | Path) -> dict[str, Any]:
    """Load a WSxM STP file into metadata, scan geometry, and Z array."""
    path = Path(path)
    blob = path.read_bytes()
    header_text, header_size = decode_header(blob)
    metadata = parse_header_text(header_text)

    rows = int(numeric_value(extract_scalar(metadata, "General Info", "Number of rows")))
    cols = int(numeric_value(extract_scalar(metadata, "General Info", "Number of columns")))
    dtype_name = str(extract_scalar(metadata, "General Info", "Image Data Type")).strip().lower()

    if dtype_name != "double":
        raise STPFormatError(f"Only 'double' data are currently supported, got: {dtype_name}")

    payload = blob[header_size:]
    expected_bytes = rows * cols * 8
    if len(payload) < expected_bytes:
        raise STPFormatError(
            f"Binary payload too short: got {len(payload)} bytes, expected at least {expected_bytes}"
        )
    if len(payload) > expected_bytes:
        payload = payload[:expected_bytes]

    endian = guess_endianness(payload, rows, cols)
    z = np.frombuffer(payload, dtype=f"{endian}f8", count=rows * cols).reshape(rows, cols)

    x_amp = extract_scalar(metadata, "Control", "X Amplitude")
    y_amp = extract_scalar(metadata, "Control", "Y Amplitude")
    z_amp = extract_scalar(metadata, "General Info", "Z Amplitude")

    x_size = numeric_value(x_amp)
    y_size = numeric_value(y_amp)
    x_unit = x_amp.get("unit", "") if isinstance(x_amp, dict) else ""
    y_unit = y_amp.get("unit", "") if isinstance(y_amp, dict) else ""
    z_unit = z_amp.get("unit", "") if isinstance(z_amp, dict) else ""

    return {
        "path": str(path),
        "header_size_bytes": header_size,
        "byte_order": "little" if endian == "<" else "big",
        "metadata": metadata,
        "shape": {"rows": rows, "cols": cols},
        "scan": {
            "x_size": x_size,
            "x_unit": x_unit,
            "y_size": y_size,
            "y_unit": y_unit,
            "z_unit": z_unit,
            "dx": x_size / cols,
            "dy": y_size / rows,
            "dx_nm": (x_size * 1000.0 / cols) if x_unit == "µm" else None,
            "dy_nm": (y_size * 1000.0 / rows) if y_unit == "µm" else None,
        },
        "z": z,
        "summary": {
            "z_min": float(np.nanmin(z)),
            "z_max": float(np.nanmax(z)),
            "z_mean": float(np.nanmean(z)),
            "z_std": float(np.nanstd(z)),
        },
    }


def json_safe(obj: Any) -> Any:
    """Convert numpy-heavy payloads into JSON-serializable objects."""
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

