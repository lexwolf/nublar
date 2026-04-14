#include <algorithm>
#include <cmath>
#include <complex>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <nano_geo_matrix/bessel/myBessel.hpp>
#include <nano_geo_matrix/quasi_static/geometry/single.hpp>
#define CUP_BACKEND_QUASI_STATIC
#include <cup.hpp>

#include "effective_medium.hpp"
#include "project_paths.hpp"

/*
Example compilation:

make bin/effective_eps
*/

namespace {

constexpr double kPlanckEvS = 4.135667696e-15;
constexpr double kLightSpeedMS = 299792458.0;
const std::complex<double> kImaginaryUnit(0.0, 1.0);

struct ExperimentalRow {
    int time_s = 0;
    int n_lambda = 0;
    double effe = 0.0;
    double rave_nm = 0.0;
    double w1 = 0.0;
    double mu_l1 = 0.0;
    double sig_l1 = 0.0;
    double w2 = 0.0;
    double mu_l2 = 0.0;
    double sig_l2 = 0.0;
    double lamin_nm = 0.0;
    double lamax_nm = 0.0;
    double dlam_nm = 0.0;
};

struct OmegaRange {
    double min_ev = 0.0;
    double max_ev = 0.0;
};

double wavelength_nm_to_omega_ev(double wavelength_nm)
{
    return kPlanckEvS * kLightSpeedMS / (wavelength_nm * 1.0e-9);
}

OmegaRange read_omega_range_from_material_table(const std::filesystem::path& data_path)
{
    std::ifstream input(data_path);
    if (!input.is_open()) {
        throw std::runtime_error("Could not open material table: " + data_path.string());
    }

    double lambda_nm = 0.0;
    double omega_ev = 0.0;
    double eps_re = 0.0;
    double eps_im = 0.0;
    double delta_re = 0.0;
    double delta_im = 0.0;

    OmegaRange range;
    bool first = true;
    while (input >> lambda_nm >> omega_ev >> eps_re >> eps_im >> delta_re >> delta_im) {
        if (first) {
            range.min_ev = omega_ev;
            range.max_ev = omega_ev;
            first = false;
        } else {
            range.min_ev = std::min(range.min_ev, omega_ev);
            range.max_ev = std::max(range.max_ev, omega_ev);
        }
    }

    if (first) {
        throw std::runtime_error("Material table is empty: " + data_path.string());
    }

    return range;
}

double lognormal_pdf_from_log_params(double radius_nm, double mu_ln, double sigma_ln)
{
    if (radius_nm <= 0.0 || sigma_ln <= 0.0) {
        return 0.0;
    }

    const double coeff = 1.0 / (radius_nm * sigma_ln * std::sqrt(2.0 * M_PI));
    const double exponent = -std::pow(std::log(radius_nm) - mu_ln, 2)
                            / (2.0 * sigma_ln * sigma_ln);
    return coeff * std::exp(exponent);
}

double two_lognormal_pdf(double radius_nm, const ExperimentalRow& row)
{
    return row.w1 * lognormal_pdf_from_log_params(radius_nm, row.mu_l1, row.sig_l1)
           + row.w2 * lognormal_pdf_from_log_params(radius_nm, row.mu_l2, row.sig_l2);
}

std::complex<double> mmgm_mixture_integrand(double average_radius_nm,
                                            std::complex<double> inclusion_eps,
                                            std::complex<double> host_eps,
                                            double radius_nm,
                                            double wavelength_nm,
                                            const ExperimentalRow& row)
{
    const double probability = two_lognormal_pdf(radius_nm, row);
    const std::complex<double> a1 = [&]() {
        if (radius_nm == 0.0 || wavelength_nm == 0.0) {
            return std::complex<double>(0.0, 0.0);
        }

        const std::complex<double> n1 = std::sqrt(inclusion_eps);
        const std::complex<double> n2 = std::sqrt(host_eps);
        const std::complex<double> m = n1 / n2;
        const std::complex<double> x = 2.0 * M_PI * n2 / (wavelength_nm / radius_nm);

        return (m * ψ(1, m * x) * ψp(1, x) - ψ(1, x) * ψp(1, m * x))
               / (m * ψ(1, m * x) * ξp(1, x) - ξ(1, x) * ψp(1, m * x));
    }();
    return probability * a1;
}

std::complex<double> trapezoidal_mmgm_mixture(double average_radius_nm,
                                              std::complex<double> inclusion_eps,
                                              std::complex<double> host_eps,
                                              double wavelength_nm,
                                              const ExperimentalRow& row)
{
    if (average_radius_nm <= 0.0) {
        return {0.0, 0.0};
    }

    const double step = 0.05 * average_radius_nm;
    const double radius_max = 10.0 * average_radius_nm;
    const int num_steps = static_cast<int>(radius_max / step);

    std::complex<double> integral = 0.0;
    integral += mmgm_mixture_integrand(
        average_radius_nm, inclusion_eps, host_eps, 0.0, wavelength_nm, row) / 2.0;
    integral += mmgm_mixture_integrand(
        average_radius_nm, inclusion_eps, host_eps, radius_max, wavelength_nm, row) / 2.0;

    for (int i = 1; i < num_steps; ++i) {
        const double radius_nm = i * step;
        integral += mmgm_mixture_integrand(
            average_radius_nm, inclusion_eps, host_eps, radius_nm, wavelength_nm, row);
    }

    return integral * step;
}

std::complex<double> mmgm_right_hand_mixture(double average_radius_nm,
                                             std::complex<double> inclusion_eps,
                                             std::complex<double> host_eps,
                                             double wavelength_nm,
                                             double volume_fraction,
                                             const ExperimentalRow& row)
{
    const std::complex<double> integral = trapezoidal_mmgm_mixture(
        average_radius_nm, inclusion_eps, host_eps, wavelength_nm, row);

    return (3.0 * kImaginaryUnit * std::pow(wavelength_nm, 3) * volume_fraction
            / (16.0 * std::pow(M_PI, 3) * std::pow(host_eps, 1.5) * std::pow(average_radius_nm, 3)))
           * integral;
}

ExperimentalRow parse_manifest_row(const std::string& line)
{
    std::istringstream iss(line);
    ExperimentalRow row;
    int n_afm_scans = 0;

    double coverage = 0.0;
    double coverage_std = 0.0;
    std::string effe_proxy_name;
    std::string effe_proxy_formula;
    double rave_std = 0.0;
    std::string radius_proxy_name;
    std::string dist_type;
    std::string axis_name;
    std::string fit_status;
    std::string fit_path;
    double log_likelihood = 0.0;
    double bic = 0.0;
    int fit_converged = 0;
    int fit_iterations = 0;
    int fit_samples = 0;
    double mean1 = 0.0;
    double std1 = 0.0;
    double mean2 = 0.0;
    double std2 = 0.0;
    double dist_mean = 0.0;
    double dist_std = 0.0;
    double eq_thickness = 0.0;
    double eq_thickness_std = 0.0;
    double density = 0.0;
    double density_std = 0.0;
    double mean_height = 0.0;
    double mean_height_std = 0.0;
    int lambda_grid_is_uniform = 0;
    std::string transmittance_label;
    std::string transmittance_dat;
    std::string afm_sources;

    iss >> row.time_s >> n_afm_scans;

    if (!iss) {
        throw std::runtime_error("Could not parse manifest row");
    }

    iss >> coverage
        >> coverage_std
        >> row.effe
        >> effe_proxy_name
        >> effe_proxy_formula
        >> row.rave_nm
        >> rave_std
        >> radius_proxy_name
        >> dist_type
        >> axis_name
        >> fit_status
        >> fit_path
        >> log_likelihood
        >> bic
        >> fit_converged
        >> fit_iterations
        >> fit_samples
        >> row.w1
        >> row.mu_l1
        >> row.sig_l1
        >> mean1
        >> std1
        >> row.w2
        >> row.mu_l2
        >> row.sig_l2
        >> mean2
        >> std2
        >> dist_mean
        >> dist_std
        >> eq_thickness
        >> eq_thickness_std
        >> density
        >> density_std
        >> mean_height
        >> mean_height_std
        >> row.n_lambda
        >> row.lamin_nm
        >> row.lamax_nm
        >> row.dlam_nm
        >> lambda_grid_is_uniform
        >> transmittance_label
        >> transmittance_dat
        >> afm_sources;

    if (!iss) {
        throw std::runtime_error("Manifest row is malformed: " + line);
    }

    if (dist_type != "two_lognormal") {
        throw std::runtime_error("Unsupported distribution type in manifest: " + dist_type);
    }

    if (row.rave_nm <= 0.0 || row.effe < 0.0 || row.effe > 1.0) {
        throw std::runtime_error("Manifest row has invalid Rave or effe values");
    }

    if (row.n_lambda <= 0 || row.dlam_nm <= 0.0) {
        throw std::runtime_error("Manifest row has invalid wavelength grid metadata");
    }

    return row;
}

std::vector<ExperimentalRow> read_manifest(const std::filesystem::path& manifest_path)
{
    std::ifstream input(manifest_path);
    if (!input.is_open()) {
        throw std::runtime_error("Could not open manifest: " + manifest_path.string());
    }

    std::vector<ExperimentalRow> rows;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }
        rows.push_back(parse_manifest_row(line));
    }

    if (rows.empty()) {
        throw std::runtime_error("Manifest contains no data rows: " + manifest_path.string());
    }

    return rows;
}

std::filesystem::path output_path_for_time(const std::string& project_root, int time_s)
{
    return std::filesystem::path(project_root)
           / "data/output/effective_permittivity"
           / ("silver_nanoisland_" + std::to_string(time_s) + "s.dat");
}

void write_spectrum(const std::string& project_root,
                    const ExperimentalRow& row,
                    nanosphere& sphere,
                    double host_eps,
                    const OmegaRange& omega_range)
{
    const std::filesystem::path output_path = output_path_for_time(project_root, row.time_s);
    std::filesystem::create_directories(output_path.parent_path());

    std::ofstream out(output_path);
    if (!out.is_open()) {
        throw std::runtime_error("Could not open output file: " + output_path.string());
    }

    out << "# time_s " << row.time_s << "\n";
    out << "# effe " << std::setprecision(16) << row.effe << "\n";
    out << "# Rave_nm " << row.rave_nm << "\n";
    out << "# distribution two_lognormal "
        << row.w1 << " " << row.mu_l1 << " " << row.sig_l1 << " "
        << row.w2 << " " << row.mu_l2 << " " << row.sig_l2 << "\n";
    out << "# omega_range_eV " << omega_range.min_ev << " " << omega_range.max_ev << "\n";
    out << "# columns: lambda_nm omega_eV "
        << "eps_cm_re eps_cm_im eps_mmgm_re eps_mmgm_im eps_metal_re eps_metal_im\n";

    out << std::fixed << std::setprecision(10);
    for (int i = 0; i < row.n_lambda; ++i) {
        const double wavelength_nm = row.lamin_nm + static_cast<double>(i) * row.dlam_nm;
        const double omega_ev = wavelength_nm_to_omega_ev(wavelength_nm);
        if (omega_ev < omega_range.min_ev || omega_ev > omega_range.max_ev) {
            const double nan = std::numeric_limits<double>::quiet_NaN();
            out << wavelength_nm << " "
                << omega_ev << " "
                << nan << " " << nan << " "
                << nan << " " << nan << " "
                << nan << " " << nan << "\n";
            continue;
        }

        const std::complex<double> eps_metal = sphere.metal(omega_ev);
        const std::complex<double> eps_cm = nublar::MaxwellGarnett(row.effe, eps_metal, host_eps);
        const std::complex<double> rhs = mmgm_right_hand_mixture(
            row.rave_nm, eps_metal, host_eps, wavelength_nm, row.effe, row);
        const std::complex<double> eps_mmgm = (1.0 + 2.0 * rhs) * host_eps / (1.0 - rhs);

        out << wavelength_nm << " "
            << omega_ev << " "
            << eps_cm.real() << " " << eps_cm.imag() << " "
            << eps_mmgm.real() << " " << eps_mmgm.imag() << " "
            << eps_metal.real() << " " << eps_metal.imag() << "\n";
    }

    std::cout << output_path << "\n";
}

}  // namespace

int main(int argc, char* argv[])
{
    try {
        const std::string project_root = nublar::resolve_project_root(argv[0]);
        const std::filesystem::path manifest_path = (argc >= 2)
            ? std::filesystem::path(argv[1])
            : std::filesystem::path(project_root) / "data/input/experimental/model_input.dat";

        std::vector<ExperimentalRow> rows = read_manifest(manifest_path);
        const OmegaRange omega_range = read_omega_range_from_material_table(
            std::filesystem::path(project_root)
            / "extern/nano_geo_matrix/modules/cup/data/materials/metals/silverUNICALeV.dat");

        nanosphere sphere;
        sphere.init();
        sphere.set_metal("silver", "spline", 0, "unical");
        const double host_eps = sphere.set_host("air");

        for (const ExperimentalRow& row : rows) {
            write_spectrum(project_root, row, sphere, host_eps, omega_range);
        }

        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "Error: " << exc.what() << std::endl;
        return 1;
    }
}
