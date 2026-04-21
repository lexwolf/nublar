#pragma once

#include <cmath>
#include <complex>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <utility>

namespace nublar {

constexpr double kBruggemanPassiveTolerance = 1e-8;

inline std::complex<double> MaxwellGarnett(double volume_fraction,
                                           std::complex<double> inclusion_eps,
                                           std::complex<double> host_eps) {
    constexpr double small_number_cutoff = 1e-6;

    if (volume_fraction < 0.0 || volume_fraction > 1.0) {
        std::cerr << "WARNING: volume fraction out of range!" << std::endl;
        std::exit(-11);
    }

    const std::complex<double> factor_up =
        2.0 * (1.0 - volume_fraction) * host_eps
        + (1.0 + 2.0 * volume_fraction) * inclusion_eps;
    const std::complex<double> factor_down =
        (2.0 + volume_fraction) * host_eps
        + (1.0 - volume_fraction) * inclusion_eps;

    if (std::norm(factor_down) < small_number_cutoff) {
        std::cerr << "WARNING: effective medium is singular" << std::endl;
        std::exit(-22);
    }

    return host_eps * factor_up / factor_down;
}

inline std::pair<std::complex<double>, std::complex<double>>
BruggemanRoots(double volume_fraction,
               std::complex<double> inclusion_eps,
               std::complex<double> host_eps) {
    if (volume_fraction < 0.0 || volume_fraction > 1.0) {
        std::cerr << "WARNING: volume fraction out of range!" << std::endl;
        std::exit(-11);
    }

    if (volume_fraction == 0.0) {
        return {host_eps, host_eps};
    }
    if (volume_fraction == 1.0) {
        return {inclusion_eps, inclusion_eps};
    }

    const std::complex<double> B =
        (3.0 * volume_fraction - 1.0) * inclusion_eps
        + (2.0 - 3.0 * volume_fraction) * host_eps;

    const std::complex<double> discriminant =
        B * B + 8.0 * inclusion_eps * host_eps;

    const std::complex<double> root = std::sqrt(discriminant);

    return {
        0.25 * (B + root),
        0.25 * (B - root)
    };
}

inline bool BruggemanIsPassive(std::complex<double> eps,
                               double imag_tolerance = kBruggemanPassiveTolerance) {
    return eps.imag() >= -imag_tolerance;
}

inline std::complex<double> BruggemanSelectInitialRoot(
    double volume_fraction,
    const std::pair<std::complex<double>, std::complex<double>>& roots,
    std::complex<double> inclusion_eps,
    std::complex<double> host_eps,
    double imag_tolerance = kBruggemanPassiveTolerance) {
    const bool constituents_passive =
        BruggemanIsPassive(inclusion_eps, imag_tolerance)
        && BruggemanIsPassive(host_eps, imag_tolerance);
    const bool first_passive = BruggemanIsPassive(roots.first, imag_tolerance);
    const bool second_passive = BruggemanIsPassive(roots.second, imag_tolerance);

    if (constituents_passive && first_passive != second_passive) {
        return first_passive ? roots.first : roots.second;
    }

    const std::complex<double> target =
        (volume_fraction <= 0.5) ? host_eps : inclusion_eps;

    const double first_distance = std::norm(roots.first - target);
    const double second_distance = std::norm(roots.second - target);

    return (first_distance <= second_distance) ? roots.first : roots.second;
}

inline std::complex<double> BruggemanSelectContinuationRoot(
    const std::pair<std::complex<double>, std::complex<double>>& roots,
    std::complex<double> previous_eps_eff) {
    const double first_distance = std::norm(roots.first - previous_eps_eff);
    const double second_distance = std::norm(roots.second - previous_eps_eff);

    return (first_distance <= second_distance) ? roots.first : roots.second;
}

inline bool BruggemanSelectedRootViolatesPassivity(
    std::complex<double> selected_eps_eff,
    std::complex<double> inclusion_eps,
    std::complex<double> host_eps,
    double imag_tolerance = kBruggemanPassiveTolerance) {
    return BruggemanIsPassive(inclusion_eps, imag_tolerance)
        && BruggemanIsPassive(host_eps, imag_tolerance)
        && selected_eps_eff.imag() < -imag_tolerance;
}

inline std::complex<double> Bruggeman(double volume_fraction,
                                      std::complex<double> inclusion_eps,
                                      std::complex<double> host_eps) {
    const auto roots = BruggemanRoots(volume_fraction, inclusion_eps, host_eps);
    const std::complex<double> eps_eff =
        BruggemanSelectInitialRoot(volume_fraction, roots, inclusion_eps, host_eps);

    // Safety check against pathological numerical issues
    if (!std::isfinite(std::real(eps_eff)) || !std::isfinite(std::imag(eps_eff))) {
        std::cerr << "WARNING: Bruggeman effective medium is not finite" << std::endl;
        std::exit(-23);
    }

    return eps_eff;
}

}  // namespace nublar
