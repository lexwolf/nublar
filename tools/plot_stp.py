#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from read_stp import load_stp


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

        fig, ax = plt.subplots(figsize=(6, 5))

        im = ax.imshow(
            z,
            cmap="viridis",
            origin="lower",
            extent=[0, scan["x_size"], 0, scan["y_size"]],
            aspect="equal",
        )

        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(f"Height ({scan['z_unit']})")

        ax.set_xlabel(f"X ({scan['x_unit']})")
        ax.set_ylabel(f"Y ({scan['y_unit']})")
        ax.set_title(Path(stp["path"]).name)

        plt.tight_layout()

        if args.save:
            args.save.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(args.save, dpi=300)

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
