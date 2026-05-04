#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Final


MODEL_NAME: Final = "mg"
DISPLAY_NAME: Final = "MG"
SUPPORTED_GEOMETRIES = {"spheres", "holes"}


class MgModelError(RuntimeError):
    """Raised when MG-specific model preparation fails."""


def validate_geometry(geometry: str) -> None:
    if geometry not in SUPPORTED_GEOMETRIES:
        raise MgModelError(f"Unsupported MG geometry: {geometry}")


def configure_effective_medium(
    effective_medium: dict[str, Any],
    *,
    geometry: str,
    effe: float,
    rave_nm: float | None = None,
    sig_l: float | None = None,
) -> None:
    validate_geometry(geometry)
    effective_medium["model"] = MODEL_NAME
    effective_medium["geometry"] = geometry
    effective_medium["filling_fraction"] = effe
    effective_medium.pop("distribution", None)


def result_parameters(
    effe: float,
    thickness_nm: float,
    rave_nm: float | None = None,
    sig_l: float | None = None,
) -> dict[str, float]:
    return {
        "effe": effe,
        "thickness_nm": thickness_nm,
    }
