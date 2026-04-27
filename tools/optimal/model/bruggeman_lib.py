#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


MODEL_NAME = "bruggeman"
DISPLAY_NAME = "Bruggeman"
SUPPORTED_GEOMETRIES = {"spheres", "holes"}


class BruggemanModelError(RuntimeError):
    """Raised when Bruggeman-specific model preparation fails."""


def validate_geometry(geometry: str) -> None:
    if geometry not in SUPPORTED_GEOMETRIES:
        raise BruggemanModelError(f"Unsupported Bruggeman geometry: {geometry}")


def configure_effective_medium(
    effective_medium: dict[str, Any],
    *,
    geometry: str,
    effe: float,
) -> None:
    validate_geometry(geometry)
    effective_medium["model"] = MODEL_NAME
    effective_medium["geometry"] = geometry
    effective_medium["filling_fraction"] = effe
    effective_medium.pop("distribution", None)


def result_parameters(effe: float, thickness_nm: float) -> dict[str, float]:
    return {
        "effe": effe,
        "thickness_nm": thickness_nm,
    }
