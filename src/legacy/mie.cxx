#include <iostream>
#include <fstream>
#include <complex>
#include <vector>
#include <sstream>
#include <string>
#include <iomanip>
#include "distributions.hpp"
#include "effective_medium.hpp"
#include "mie_mmgm.hpp"
#include "project_paths.hpp"
#include "spectral_io.hpp"

/*
Example compilation:

NGM_ROOT=$(realpath ../extern/nano_geo_matrix)

g++ -std=c++17 -Wall \
  -I../header \
  -I../include \
  -I"$NGM_ROOT/include" \
  -I"$NGM_ROOT/modules/cup" \
  -L/usr/local/lib mie.cxx -o ../bin/mie -lcomplex_bessel -larmadillo
*/

static std::string g_project_root = ".";

// ------------------ Main ------------------

int main(int argc, char *argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0]
                  << " <Rave> <effe> [distribution=lognormal] [options]\n"
                  << "Options:\n"
                  << "  -pf, --print-filename   Print output filename\n"
                  << "  -sg, --sigma-geo VAL    Set geometric σ (default 1.20)\n";
        return 1;
    }

    double Rave = std::atof(argv[1]);
    double effe = std::atof(argv[2]);
    std::string dist_type = "lognormal"; // default
    if (argc >= 4 && argv[3][0] != '-') dist_type = argv[3];
    g_project_root = nublar::resolve_project_root(argv[0]);

    // --- Flags ---
    bool print_filename = false;
    double sigma_geo = 1.20; // default (Battie et al. 2014)

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-pf" || arg == "--print-filename") {
            print_filename = true;
        } else if ((arg == "-sg" || arg == "--sigma-geo") && i + 1 < argc) {
            sigma_geo = std::atof(argv[++i]);
        }
    }

    if (sigma_geo <= 1.0) {
        std::cerr << "Error: σ_geo must be > 1.0" << std::endl;
        return -1;
    }

    const nublar::DistributionSpec distribution{
        dist_type,
        nublar::geometric_sigma_to_log_sigma(sigma_geo)
    };

    // Write chosen distribution
    nublar::write_distribution_file(
        nublar::distribution_output_path(g_project_root, Rave, distribution),
        Rave,
        distribution);

    // Read input file
    const nublar::ComplexSpectrum spectrum = nublar::read_complex_spectrum_file(
        g_project_root + "/data/input/permitividad_UNICAL_parentesis.dat");
    std::complex<double> eps2(1.0006, 0.0);

    // Output file
    std::ostringstream filename;
    filename << g_project_root << "/data/output/Rave=" << std::fixed << std::setprecision(2) << Rave
             << "__f=" << std::fixed << std::setprecision(3) << effe
             << "__" << dist_type;
    if (dist_type == "lognormal") {
        filename << "__sg=" << std::fixed << std::setprecision(2) << sigma_geo;
    }
    filename << ".dat";

    std::ofstream outfile(filename.str());
    if (!outfile.is_open()) {
        std::cerr << "Error opening output file." << std::endl;
        return 1;
    }

    // Loop
    std::complex<double> RH, eps_eff, eps_MG;
    for (size_t i = 0; i < spectrum.grid.size(); ++i) {
        RH = nublar::mmgm_right_hand(
            Rave, spectrum.values[i], eps2, spectrum.grid[i], effe, distribution);
        eps_eff = (1. + 2. * RH) * eps2 / (1. - RH);
        eps_MG  = nublar::MaxwellGarnett(effe, spectrum.values[i], eps2);
        outfile << spectrum.grid[i] << " "
                << eps_eff.real() << " " << eps_eff.imag() << " "
                << eps_MG.real()  << " " << eps_MG.imag()  << std::endl;
    }
    outfile.close();

    if (print_filename) {
        std::cout << filename.str() << std::endl;
    }

    return 0;
}
