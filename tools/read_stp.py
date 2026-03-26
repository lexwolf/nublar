#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path
from typing import Any

import numpy as np


HEADER_SIZE_RE = re.compile(r"Image header size:\s*(\d+)", re.IGNORECASE)
SECTION_RE = re.compile(r"^\[(.+?)\]\s*$")
KEYVAL_RE = re.compile(r"^\s*([^:]+):\s*(.*?)\s*$")


class STPFormatError(RuntimeError):
    pass


def _decode_header(blob: bytes) -> tuple[str, int]:
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


def _parse_typed_value(raw: str) -> Any:
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

    # Try numeric prefix + optional unit
    number = parts[0].replace(",", ".")
    try:
        value = float(number)
        if len(parts) == 1:
            return value
        return {"value": value, "unit": " ".join(parts[1:])}
    except ValueError:
        return text


def parse_header_text(header_text: str) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    current_section = "root"
    sections[current_section] = {}

    for line in header_text.splitlines():
        section_match = SECTION_RE.match(line.strip())
        if section_match:
            current_section = section_match.group(1).strip()
            sections.setdefault(current_section, {})
            continue

        kv_match = KEYVAL_RE.match(line)
        if kv_match:
            key = kv_match.group(1).strip()
            value = _parse_typed_value(kv_match.group(2))
            sections[current_section][key] = value

    return sections


def _extract_scalar(meta: dict[str, dict[str, Any]], section: str, key: str) -> Any:
    try:
        return meta[section][key]
    except KeyError as exc:
        raise STPFormatError(f"Missing header field [{section}] {key}") from exc


def _numeric_value(item: Any) -> float:
    if isinstance(item, dict) and "value" in item:
        return float(item["value"])
    return float(item)


def _guess_endianness(payload: bytes, rows: int, cols: int) -> str:
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
    path = Path(path)
    blob = path.read_bytes()
    header_text, header_size = _decode_header(blob)
    metadata = parse_header_text(header_text)

    rows = int(_numeric_value(_extract_scalar(metadata, "General Info", "Number of rows")))
    cols = int(_numeric_value(_extract_scalar(metadata, "General Info", "Number of columns")))
    dtype_name = str(_extract_scalar(metadata, "General Info", "Image Data Type")).strip().lower()

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

    endian = _guess_endianness(payload, rows, cols)
    z = np.frombuffer(payload, dtype=f"{endian}f8", count=rows * cols).reshape(rows, cols)

    x_amp = _extract_scalar(metadata, "Control", "X Amplitude")
    y_amp = _extract_scalar(metadata, "Control", "Y Amplitude")
    z_amp = _extract_scalar(metadata, "General Info", "Z Amplitude")

    x_size = _numeric_value(x_amp)
    y_size = _numeric_value(y_amp)
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


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(description="Read WSxM .stp AFM files")
    parser.add_argument("stp_file", type=Path, help="Path to the .stp file")
    parser.add_argument(
        "--dump-header",
        action="store_true",
        help="Print parsed header metadata as JSON",
    )
    parser.add_argument(
        "--dump-summary",
        action="store_true",
        help="Print compact JSON summary",
    )
    parser.add_argument(
        "--save-npy",
        type=Path,
        help="Optional output .npy path for the Z matrix",
    )
    parser.add_argument(
        "--save-json",
        type=Path,
        help="Optional output JSON path for metadata + summary (no matrix)",
    )
    args = parser.parse_args()

    stp = load_stp(args.stp_file)

    if args.save_npy:
        args.save_npy.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.save_npy, stp["z"])

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: v for k, v in stp.items() if k != "z"}
        args.save_json.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")

    if args.dump_header:
        print(json.dumps(_json_safe(stp["metadata"]), indent=2))
    elif args.dump_summary or (not args.save_npy and not args.save_json):
        payload = {
            "path": stp["path"],
            "header_size_bytes": stp["header_size_bytes"],
            "byte_order": stp["byte_order"],
            "shape": stp["shape"],
            "scan": stp["scan"],
            "summary": stp["summary"],
        }
        print(json.dumps(_json_safe(payload), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
