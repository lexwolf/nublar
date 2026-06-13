#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from afm_lib.plot_utils import plot_height_map
from afm_lib.stp_io import load_stp


def main() -> int:
    try:
        parser = argparse.ArgumentParser(description="Visualize STP AFM height map")
        parser.add_argument("stp_file", type=Path, help="Path to .stp file")
        parser.add_argument("--save", type=Path, help="Save output image (PNG)")
        parser.add_argument("--show-hist", action="store_true", help="Show height histogram")
        parser.add_argument("--transpose", action="store_true", help="Transpose map")
        parser.add_argument("--flip-x", action="store_true", help="Flip horizontally")
        parser.add_argument("--flip-y", action="store_true", help="Flip vertically")
        args = parser.parse_args()

        stp = load_stp(args.stp_file)
        z = stp["z"].copy()

        if args.transpose:
            z = z.T
        if args.flip_x:
            z = np.fliplr(z)
        if args.flip_y:
            z = np.flipud(z)

        scan = stp["scan"]

        fig, ax = plot_height_map(
            z,
            x_size=scan["x_size"],
            y_size=scan["y_size"],
            x_unit=scan["x_unit"],
            y_unit=scan["y_unit"],
            z_unit=scan["z_unit"],
            title=Path(stp["path"]).name,
        )

        if args.save:
            args.save.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(args.save, dpi=300)

        if args.show_hist:
            fig2, ax2 = plt.subplots()
            ax2.hist(z.flatten(), bins=100)
            ax2.set_xlabel(f"Height ({scan['z_unit']})")
            ax2.set_ylabel("Counts")
            ax2.set_title("Height distribution")
            plt.tight_layout()

        plt.show()

        return 0

    except KeyboardInterrupt:
        print("[INFO] Interrupted by user (Ctrl+C). Exiting gracefully.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
