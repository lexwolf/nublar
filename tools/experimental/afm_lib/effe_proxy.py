from __future__ import annotations

import math


EFFE_PROXY_CHOICES = (
    "coverage_fraction",
    "eq_thickness_over_mean_height",
    "coverage_times_eq_over_hmean",
    "sqrt_coverage_times_eq_over_hmean",
    "eq_thickness_over_Rave",
    "hybrid_alpha25",
    "hybrid_alpha50",
    "hybrid_alpha75",
)


EFFE_PROXY_FORMULAS: dict[str, str] = {
    "coverage_fraction": "coverage_fraction",
    "eq_thickness_over_mean_height": "equivalent_thickness_nm/mean_island_height_nm",
    "coverage_times_eq_over_hmean": "coverage_fraction*(equivalent_thickness_nm/mean_island_height_nm)",
    "sqrt_coverage_times_eq_over_hmean": "sqrt(coverage_fraction*(equivalent_thickness_nm/mean_island_height_nm))",
    "eq_thickness_over_Rave": "equivalent_thickness_nm/afm_Rave_nm",
    "hybrid_alpha25": "coverage_fraction^0.25*(equivalent_thickness_nm/mean_island_height_nm)^0.75",
    "hybrid_alpha50": "coverage_fraction^0.50*(equivalent_thickness_nm/mean_island_height_nm)^0.50",
    "hybrid_alpha75": "coverage_fraction^0.75*(equivalent_thickness_nm/mean_island_height_nm)^0.25",
}


def _clamp_non_negative(value: float) -> float:
    return max(0.0, value)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 0.0
    return numerator / denominator


def compute_effe_proxy(
    proxy_name: str,
    coverage_fraction: float,
    equivalent_thickness_nm: float,
    mean_island_height_nm: float,
    afm_Rave_nm: float,
) -> float:
    coverage = _clamp_non_negative(coverage_fraction)
    eq_thickness = _clamp_non_negative(equivalent_thickness_nm)
    mean_height = mean_island_height_nm
    rave = afm_Rave_nm

    if proxy_name == "coverage_fraction":
        return coverage

    if proxy_name == "eq_thickness_over_mean_height":
        return _safe_ratio(eq_thickness, mean_height)

    if proxy_name == "coverage_times_eq_over_hmean":
        baseline = _safe_ratio(eq_thickness, mean_height)
        return coverage * baseline

    if proxy_name == "sqrt_coverage_times_eq_over_hmean":
        baseline = _safe_ratio(eq_thickness, mean_height)
        return math.sqrt(max(coverage * baseline, 0.0))

    if proxy_name == "eq_thickness_over_Rave":
        return _safe_ratio(eq_thickness, rave)

    if proxy_name in {"hybrid_alpha25", "hybrid_alpha50", "hybrid_alpha75"}:
        if mean_height <= 0.0:
            return 0.0

        alpha = {
            "hybrid_alpha25": 0.25,
            "hybrid_alpha50": 0.50,
            "hybrid_alpha75": 0.75,
        }[proxy_name]
        baseline = _clamp_non_negative(_safe_ratio(eq_thickness, mean_height))
        return (coverage ** alpha) * (baseline ** (1.0 - alpha))

    raise ValueError(f"Unsupported effe proxy: {proxy_name}")


def get_effe_proxy_formula_string(proxy_name: str) -> str:
    try:
        return EFFE_PROXY_FORMULAS[proxy_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported effe proxy: {proxy_name}") from exc
