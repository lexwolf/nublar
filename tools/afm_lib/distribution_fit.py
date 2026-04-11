from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class LognormalComponent:
    weight: float
    mu_ln: float
    sigma_ln: float
    mean_nm: float
    std_nm: float


@dataclass
class TwoLognormalFitResult:
    component_1: LognormalComponent
    component_2: LognormalComponent
    mixture_mean_nm: float
    mixture_std_nm: float
    log_likelihood: float
    bic: float
    converged: bool
    n_iter: int
    n_samples: int


def _normal_pdf(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    sigma = max(float(sigma), 1e-6)
    coeff = 1.0 / (sigma * math.sqrt(2.0 * math.pi))
    z = (x - mu) / sigma
    return coeff * np.exp(-0.5 * z * z)


def _component_from_params(weight: float, mu_ln: float, sigma_ln: float) -> LognormalComponent:
    sigma_ln = max(float(sigma_ln), 1e-6)
    mean_nm = math.exp(mu_ln + 0.5 * sigma_ln * sigma_ln)
    variance_nm = (math.exp(sigma_ln * sigma_ln) - 1.0) * math.exp(
        2.0 * mu_ln + sigma_ln * sigma_ln
    )
    return LognormalComponent(
        weight=float(weight),
        mu_ln=float(mu_ln),
        sigma_ln=sigma_ln,
        mean_nm=float(mean_nm),
        std_nm=float(math.sqrt(max(variance_nm, 0.0))),
    )


def _fit_with_init(
    log_radii: np.ndarray,
    init_weight: float,
    init_mu1: float,
    init_sigma1: float,
    init_mu2: float,
    init_sigma2: float,
    max_iter: int,
    tol: float,
) -> tuple[float, float, float, float, float, bool, int, float]:
    weight = float(np.clip(init_weight, 1e-3, 1.0 - 1e-3))
    mu1 = float(init_mu1)
    mu2 = float(init_mu2)
    sigma1 = max(float(init_sigma1), 1e-3)
    sigma2 = max(float(init_sigma2), 1e-3)
    prev_loglik = -math.inf
    converged = False

    for iteration in range(1, max_iter + 1):
        p1 = weight * _normal_pdf(log_radii, mu1, sigma1)
        p2 = (1.0 - weight) * _normal_pdf(log_radii, mu2, sigma2)
        total = np.clip(p1 + p2, 1e-300, None)
        gamma = p1 / total

        n1 = float(np.sum(gamma))
        n2 = float(log_radii.size - n1)
        weight = float(np.clip(n1 / log_radii.size, 1e-3, 1.0 - 1e-3))

        mu1 = float(np.sum(gamma * log_radii) / max(n1, 1e-12))
        mu2 = float(np.sum((1.0 - gamma) * log_radii) / max(n2, 1e-12))
        sigma1 = math.sqrt(float(np.sum(gamma * (log_radii - mu1) ** 2) / max(n1, 1e-12)))
        sigma2 = math.sqrt(float(np.sum((1.0 - gamma) * (log_radii - mu2) ** 2) / max(n2, 1e-12)))
        sigma1 = max(sigma1, 1e-3)
        sigma2 = max(sigma2, 1e-3)

        loglik = float(np.sum(np.log(total)))
        if abs(loglik - prev_loglik) < tol:
            converged = True
            prev_loglik = loglik
            break
        prev_loglik = loglik

    return weight, mu1, sigma1, mu2, sigma2, converged, iteration, prev_loglik


def fit_two_lognormal_mixture(
    radii_nm: list[float] | np.ndarray,
    *,
    max_iter: int = 500,
    tol: float = 1e-8,
) -> TwoLognormalFitResult:
    radii = np.asarray([float(r) for r in radii_nm if float(r) > 0.0], dtype=float)
    if radii.size < 4:
        raise ValueError("Need at least four positive radii to fit a two-lognormal mixture")

    log_radii = np.log(radii)
    mean_log = float(np.mean(log_radii))
    std_log = float(np.std(log_radii))
    std_seed = max(std_log, 0.15)
    q25, q40, q50, q60, q75 = np.quantile(log_radii, [0.25, 0.40, 0.50, 0.60, 0.75])

    seeds = [
        (0.50, q25, std_seed * 0.6, q75, std_seed * 0.6),
        (0.35, q25, std_seed * 0.8, q60, std_seed * 0.8),
        (0.65, q40, std_seed * 0.8, q75, std_seed * 0.8),
        (0.50, mean_log - 0.5 * std_seed, std_seed, mean_log + 0.5 * std_seed, std_seed),
        (0.50, q40, std_seed * 0.5, q60, std_seed * 0.5),
    ]

    best: tuple[float, float, float, float, float, bool, int, float] | None = None
    for seed in seeds:
        result = _fit_with_init(log_radii, *seed, max_iter=max_iter, tol=tol)
        if best is None or result[-1] > best[-1]:
            best = result

    assert best is not None
    weight, mu1, sigma1, mu2, sigma2, converged, n_iter, loglik = best

    components = sorted(
        (
            _component_from_params(weight, mu1, sigma1),
            _component_from_params(1.0 - weight, mu2, sigma2),
        ),
        key=lambda component: component.mean_nm,
    )

    mixture_mean = sum(component.weight * component.mean_nm for component in components)
    second_moment = sum(
        component.weight * (component.std_nm ** 2 + component.mean_nm ** 2)
        for component in components
    )
    mixture_var = max(second_moment - mixture_mean**2, 0.0)
    num_params = 5
    bic = num_params * math.log(radii.size) - 2.0 * loglik

    return TwoLognormalFitResult(
        component_1=components[0],
        component_2=components[1],
        mixture_mean_nm=float(mixture_mean),
        mixture_std_nm=float(math.sqrt(mixture_var)),
        log_likelihood=float(loglik),
        bic=float(bic),
        converged=converged,
        n_iter=int(n_iter),
        n_samples=int(radii.size),
    )
