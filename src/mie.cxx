#include <iostream>
#include <fstream>
#include <complex>
#include <cmath>
#include <vector>
#include <sstream>
#include <string>
#include <iomanip>
#include <filesystem>
#include <nano_geo_matrix/bessel/myBessel.hpp>
#include <nano_geo_matrix/mie/geometry/single.hpp>

/*
Example compilation:

NGM_ROOT=$(realpath ../extern/nano_geo_matrix)

g++ -std=c++17 -Wall \
  -I../include \
  -I"$NGM_ROOT/include" \
  -I"$NGM_ROOT/modules/cup" \
  -L/usr/local/lib mie.cxx -o ../bin/mie -lcomplex_bessel -larmadillo
*/

// ------------------ Mixing Rules ------------------
static std::string g_project_root = ".";

std::complex<double> Maxwell_Garnett(double effe,
                                     std::complex<double> eps1,
                                     std::complex<double> eps2) {
    std::complex<double> eps_eff;
    double small_number_cutoff = 1e-6;

    if (effe < 0 || effe > 1) {
        std::cerr << "WARNING: volume fraction out of range!" << std::endl;
        exit(-11);
    }
    std::complex<double> factor_up   = 2.*(1.-effe)*eps2+(1.+2.*effe)*eps1;
    std::complex<double> factor_down = (2.+effe)*eps2+(1.-effe)*eps1;
    if (norm(factor_down) < small_number_cutoff) {
        std::cerr << "WARNING: effective medium is singular" << std::endl;
        exit(-22);
    } else {
        eps_eff = eps2*factor_up/factor_down;
    }
    return eps_eff;
}

// ------------------ File Reader ------------------

void read_file(const std::string &filename,
               std::vector<double> &z,
               std::vector<std::complex<double>> &datos) {
    std::ifstream infile(filename);
    if (!infile.is_open()) {
        std::cerr << "Error opening file: " << filename << std::endl;
        exit(1);
    }
    std::string line;
    while (std::getline(infile, line)) {
        std::istringstream iss(line);
        double z_value, real_part, imag_part;
        char discard;
        if (!(iss >> z_value >> discard >> real_part >> discard >> imag_part >> discard)) {
            continue;
        }
        z.push_back(z_value);
        datos.emplace_back(real_part, imag_part);
    }
    infile.close();
}

// ------------------ Distributions ------------------

// Maxwell–Boltzmann distribution
double Maxwell_Boltzmann(double R, double a) {
    return std::sqrt(2. / M_PI) * (std::pow(R, 2) / std::pow(a, 3))
           * std::exp(-std::pow(R, 2) / (2. * std::pow(a, 2)));
}

// Lognormal distribution using σ_ln
double LogNormal(double R, double Rave, double sigma_ln) {
    if (R <= 0) return 0.0;
    double mu = std::log(Rave / std::sqrt(1.0 + sigma_ln * sigma_ln));
    double coeff = 1.0 / (R * sigma_ln * std::sqrt(2.0 * M_PI));
    double expo  = std::exp(-(std::pow(std::log(R) - mu, 2))
                     / (2.0 * sigma_ln * sigma_ln));
    return coeff * expo;
}

// ------------------ Lognormal parameter conversion ------------------

// Convert geometric sigma (σ_geo) to log-space sigma (σ_ln).
// σ_geo is the multiplicative geometric standard deviation (Battie: ~1.20).
// σ_ln = ln(σ_geo)
double geo_to_ln(double sigma_geo) {
    if (sigma_geo <= 1.0) {
        std::cerr << "Geometric sigma must be > 1.0" << std::endl;
        exit(-1);
    }
    return std::log(sigma_geo);
}

// Unified distribution selector
double distribution(double R, double Rave,
                    const std::string &dist_type, double sigma_ln=0.25) {
    if (dist_type == "maxwell") {
        double a = (Rave / 2.) * std::sqrt(M_PI / 2.);
        return Maxwell_Boltzmann(R, a);
    } else if (dist_type == "lognormal") {
        return LogNormal(R, Rave, sigma_ln);
    } else {
        std::cerr << "Unknown distribution type: " << dist_type << std::endl;
        exit(-1);
    }
}

// Write chosen distribution to file
void write_distribution(double Rave, const std::string &dist_type,
                        double sigma_ln=0.25) {
    if (Rave <= 0.0) {
        std::cerr << "Warning: Rave=0, skipping distribution output." << std::endl;
        return;
    }
    std::ostringstream filename;
    filename << g_project_root << "/data/output/" << dist_type
             << "__Rave=" << std::fixed << std::setprecision(2) << Rave;
    if (dist_type == "lognormal") filename << "_sigma=" << sigma_ln;
    filename << ".dat";

    std::ofstream outfile(filename.str());
    if (!outfile.is_open()) {
        std::cerr << "Error opening distribution output file." << std::endl;
        exit(1);
    }

    double Rmax = 10.0 * Rave;
    double step = 0.05 * Rave;

    for (double R = 0; R <= Rmax; R += step) {
        double P = distribution(R, Rave, dist_type, sigma_ln);
        outfile << R << " " << P << std::endl;
    }
    outfile.close();
}

// ------------------ Mie Coefficient ------------------

std::complex<double> mie_coefficient_a1(int order,
                                        std::complex<double> eps1,
                                        std::complex<double> eps2,
                                        double erre, double lam) {
    if (order < 1 || erre == 0.0 || lam == 0.0) {
        return std::complex<double>(0.0, 0.0);
    }

    // The subsystem implementation uses x = 2*pi*n2/lam and does not use rho.
    // Preserve this file's historical x = 2*pi*erre*n2/lam by rescaling lam.
    const double scaled_lam = lam / erre;
    return ::mie_coefficient(order, eps1, eps2, 0.0, erre, scaled_lam).first;
}

// Integrand for MMGM
std::complex<double> function(double Rave, std::complex<double> eps1,
                              std::complex<double> eps2, double erre,
                              double lam, const std::string &dist_type,
                              double sigma_ln) {
    double P = distribution(erre, Rave, dist_type, sigma_ln);
    std::complex<double> a1 = mie_coefficient_a1(1, eps1, eps2, erre, lam);
    return P * a1;
}

// Trapezoidal integration
std::complex<double> trapezoidalIntegration(double Rave,
                                            std::complex<double> eps1,
                                            std::complex<double> eps2,
                                            double lam,
                                            const std::string &dist_type,
                                            double sigma_ln) {
    double h = 0.05 * Rave;
    double Rmax = 10. * Rave;
    int n = static_cast<int>(Rmax / h);
    std::complex<double> integral = 0.0;

    integral += function(Rave, eps1, eps2, 0, lam, dist_type, sigma_ln) / 2.0;
    integral += function(Rave, eps1, eps2, Rmax, lam, dist_type, sigma_ln) / 2.0;
    for (int i = 1; i < n; ++i) {
        double erre = i * h;
        integral += function(Rave, eps1, eps2, erre, lam, dist_type, sigma_ln);
    }
    integral *= h;
    return integral;
}

// Right-hand side of MMGM relation
std::complex<double> right_hand(double Rave, std::complex<double> eps1,
                                std::complex<double> eps2, double lam,
                                double effe,
                                const std::string &dist_type,
                                double sigma_ln) {
    std::complex<double> II = trapezoidalIntegration(Rave, eps1, eps2,
                                                     lam, dist_type, sigma_ln);
    std::complex<double> RH = (3. * img * std::pow(lam, 3) * effe
        / (16. * std::pow(M_PI, 3) * std::pow(eps2, 1.5) * std::pow(Rave, 3)))
        * II;
    return RH;
}

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
    std::error_code ec;
    std::filesystem::path exec_path = std::filesystem::weakly_canonical(
        std::filesystem::absolute(argv[0]), ec);
    if (!ec && exec_path.has_parent_path()) {
        g_project_root = exec_path.parent_path().parent_path().string();
    }

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

    double sigma_ln = geo_to_ln(sigma_geo);

    // Write chosen distribution
    write_distribution(Rave, dist_type, sigma_ln);

    // Read input file
    std::vector<double> lam;
    std::vector<std::complex<double>> eps1;
    std::complex<double> eps2(1.0006, 0.0);
    read_file(g_project_root + "/data/input/permitividad_UNICAL_parentesis.dat", lam, eps1);

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
    for (size_t i = 0; i < lam.size(); ++i) {
        RH = right_hand(Rave, eps1[i], eps2, lam[i], effe, dist_type, sigma_ln);
        eps_eff = (1. + 2. * RH) * eps2 / (1. - RH);
        eps_MG  = Maxwell_Garnett(effe, eps1[i], eps2);
        outfile << lam[i] << " "
                << eps_eff.real() << " " << eps_eff.imag() << " "
                << eps_MG.real()  << " " << eps_MG.imag()  << std::endl;
    }
    outfile.close();

    if (print_filename) {
        std::cout << filename.str() << std::endl;
    }

    return 0;
}
