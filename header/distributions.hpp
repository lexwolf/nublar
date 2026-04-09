#pragma once

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

namespace nublar {

struct DistributionSpec {
    std::string type = "lognormal";
    double sigma_ln = 0.25;
};

inline double maxwell_boltzmann(double radius, double scale) {
    return std::sqrt(2.0 / M_PI) * (std::pow(radius, 2) / std::pow(scale, 3))
           * std::exp(-std::pow(radius, 2) / (2.0 * std::pow(scale, 2)));
}

inline double log_normal(double radius, double average_radius, double sigma_ln) {
    if (radius <= 0.0) {
        return 0.0;
    }

    const double mu = std::log(average_radius / std::sqrt(1.0 + sigma_ln * sigma_ln));
    const double coeff = 1.0 / (radius * sigma_ln * std::sqrt(2.0 * M_PI));
    const double expo = std::exp(-(std::pow(std::log(radius) - mu, 2))
                                 / (2.0 * sigma_ln * sigma_ln));
    return coeff * expo;
}

inline double geometric_sigma_to_log_sigma(double sigma_geo) {
    if (sigma_geo <= 1.0) {
        std::cerr << "Geometric sigma must be > 1.0" << std::endl;
        std::exit(-1);
    }

    return std::log(sigma_geo);
}

inline double distribution_value(double radius,
                                 double average_radius,
                                 const DistributionSpec& spec) {
    if (spec.type == "maxwell") {
        const double scale = (average_radius / 2.0) * std::sqrt(M_PI / 2.0);
        return maxwell_boltzmann(radius, scale);
    }

    if (spec.type == "lognormal") {
        return log_normal(radius, average_radius, spec.sigma_ln);
    }

    std::cerr << "Unknown distribution type: " << spec.type << std::endl;
    std::exit(-1);
}

inline void write_distribution_file(const std::string& output_path,
                                    double average_radius,
                                    const DistributionSpec& spec) {
    if (average_radius <= 0.0) {
        std::cerr << "Warning: Rave=0, skipping distribution output." << std::endl;
        return;
    }

    std::ofstream outfile(output_path);
    if (!outfile.is_open()) {
        std::cerr << "Error opening distribution output file: " << output_path << std::endl;
        std::exit(1);
    }

    const double radius_max = 10.0 * average_radius;
    const double step = 0.05 * average_radius;

    for (double radius = 0.0; radius <= radius_max; radius += step) {
        outfile << radius << " "
                << distribution_value(radius, average_radius, spec) << std::endl;
    }
}

inline std::string distribution_output_path(const std::string& project_root,
                                            double average_radius,
                                            const DistributionSpec& spec) {
    std::ostringstream filename;
    filename << project_root << "/data/output/" << spec.type
             << "__Rave=" << std::fixed << std::setprecision(2) << average_radius;
    if (spec.type == "lognormal") {
        filename << "_sigma=" << spec.sigma_ln;
    }
    filename << ".dat";
    return filename.str();
}

}  // namespace nublar
