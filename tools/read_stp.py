#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.stp_io import STPFormatError, json_safe, load_stp


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
        args.save_json.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")

    if args.dump_header:
        print(json.dumps(json_safe(stp["metadata"]), indent=2))
    elif args.dump_summary or (not args.save_npy and not args.save_json):
        payload = {
            "path": stp["path"],
            "header_size_bytes": stp["header_size_bytes"],
            "byte_order": stp["byte_order"],
            "shape": stp["shape"],
            "scan": stp["scan"],
            "summary": stp["summary"],
        }
        print(json.dumps(json_safe(payload), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
