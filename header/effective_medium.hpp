#pragma once

#include <complex>
#include <cstdlib>
#include <iostream>

namespace nublar {

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

}  // namespace nublar
