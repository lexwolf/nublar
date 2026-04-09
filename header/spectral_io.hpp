#pragma once

#include <complex>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace nublar {

struct ComplexSpectrum {
    std::vector<double> grid;
    std::vector<std::complex<double>> values;
};

inline ComplexSpectrum read_complex_spectrum_file(const std::string& filename) {
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        std::cerr << "Error opening file: " << filename << std::endl;
        std::exit(1);
    }

    ComplexSpectrum spectrum;
    std::string line;
    while (std::getline(infile, line)) {
        std::istringstream iss(line);
        double grid_value = 0.0;
        double real_part = 0.0;
        double imag_part = 0.0;
        char discard = '\0';
        if (!(iss >> grid_value >> discard >> real_part >> discard >> imag_part >> discard)) {
            continue;
        }

        spectrum.grid.push_back(grid_value);
        spectrum.values.emplace_back(real_part, imag_part);
    }

    return spectrum;
}

}  // namespace nublar
