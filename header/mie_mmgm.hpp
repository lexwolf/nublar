#pragma once

#include <cmath>
#include <complex>
#include <nano_geo_matrix/bessel/myBessel.hpp>
#include <nano_geo_matrix/mie/geometry/single.hpp>
#include "distributions.hpp"

namespace nublar {

inline std::complex<double> mie_coefficient_a1(int order,
                                               std::complex<double> eps1,
                                               std::complex<double> eps2,
                                               double radius,
                                               double wavelength) {
    if (order < 1 || radius == 0.0 || wavelength == 0.0) {
        return {0.0, 0.0};
    }

    const double scaled_wavelength = wavelength / radius;
    return ::mie_coefficient(order, eps1, eps2, 0.0, radius, scaled_wavelength).first;
}

inline std::complex<double> mmgm_integrand(double average_radius,
                                           std::complex<double> eps1,
                                           std::complex<double> eps2,
                                           double radius,
                                           double wavelength,
                                           const DistributionSpec& distribution) {
    const double probability = distribution_value(radius, average_radius, distribution);
    const std::complex<double> a1 = mie_coefficient_a1(1, eps1, eps2, radius, wavelength);
    return probability * a1;
}

inline std::complex<double> trapezoidal_integration(double average_radius,
                                                    std::complex<double> eps1,
                                                    std::complex<double> eps2,
                                                    double wavelength,
                                                    const DistributionSpec& distribution) {
    const double step = 0.05 * average_radius;
    const double radius_max = 10.0 * average_radius;
    const int num_steps = static_cast<int>(radius_max / step);
    std::complex<double> integral = 0.0;

    integral += mmgm_integrand(average_radius, eps1, eps2, 0.0, wavelength, distribution) / 2.0;
    integral += mmgm_integrand(average_radius, eps1, eps2, radius_max, wavelength, distribution) / 2.0;

    for (int i = 1; i < num_steps; ++i) {
        const double radius = i * step;
        integral += mmgm_integrand(average_radius, eps1, eps2, radius, wavelength, distribution);
    }

    return integral * step;
}

inline std::complex<double> mmgm_right_hand(double average_radius,
                                            std::complex<double> eps1,
                                            std::complex<double> eps2,
                                            double wavelength,
                                            double volume_fraction,
                                            const DistributionSpec& distribution) {
    const std::complex<double> integral = trapezoidal_integration(
        average_radius, eps1, eps2, wavelength, distribution);

    return (3.0 * img * std::pow(wavelength, 3) * volume_fraction
            / (16.0 * std::pow(M_PI, 3) * std::pow(eps2, 1.5) * std::pow(average_radius, 3)))
           * integral;
}

}  // namespace nublar
