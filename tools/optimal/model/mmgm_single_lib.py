#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any, Final


MODEL_NAME: Final = "mmgm_single"
DISPLAY_NAME: Final = "MMGM single-lognormal"
SUPPORTED_GEOMETRIES = {"spheres", "holes"}


class MmgmSingleModelError(RuntimeError):
    """Raised when MMGM single-lognormal model preparation fails."""


def validate_geometry(geometry: str) -> None:
    if geometry not in SUPPORTED_GEOMETRIES:
        raise MmgmSingleModelError(f"Unsupported MMGM single geometry: {geometry}")


def configure_effective_medium(
    effective_medium: dict[str, Any],
    *,
    geometry: str,
    effe: float,
    rave_nm: float | None = None,
    sig_l: float | None = None,
) -> None:
    """Configure single-lognormal MMGM.

    For single-lognormal MMGM, rave_nm is interpreted as the arithmetic mean
    radius of the lognormal distribution.
    """
    validate_geometry(geometry)
    if rave_nm is None or sig_l is None:
        raise MmgmSingleModelError("MMGM single-lognormal requires rave_nm and sig_l")

    # For single-lognormal MMGM, rave_nm is interpreted as the arithmetic mean
    # radius, so muL is shifted by -0.5 * sigL^2.
    mu_l = math.log(rave_nm) - 0.5 * sig_l * sig_l
    effective_medium["model"] = "mmgm"
    effective_medium["geometry"] = geometry
    effective_medium["filling_fraction"] = effe
    effective_medium["distribution"] = {
        "type": "lognormal",
        "rave_nm": rave_nm,
        "muL": mu_l,
        "sigL": sig_l,
    }


def result_parameters(
    effe: float,
    thickness_nm: float,
    rave_nm: float | None = None,
    sig_l: float | None = None,
) -> dict[str, float]:
    if rave_nm is None or sig_l is None:
        raise MmgmSingleModelError("MMGM single-lognormal requires rave_nm and sig_l")

    return {
        "effe": effe,
        "thickness_nm": thickness_nm,
        "rave_nm": rave_nm,
        "sig_l": sig_l,
    }
