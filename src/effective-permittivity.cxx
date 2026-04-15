#include <complex>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include <nano_geo_matrix/quasi_static/geometry/single.hpp>
#define CUP_BACKEND_QUASI_STATIC
#include <cup.hpp>

#include "effective_medium.hpp"
#include "nano_island_permittivity.hpp"
#include "project_paths.hpp"

/*
Example compilation:

make bin/effective_eps
*/

namespace {

std::filesystem::path output_path_for_time(const std::string& project_root, int time_s)
{
    return std::filesystem::path(project_root)
           / "data/output/effective_permittivity"
           / ("silver_nanoisland_" + std::to_string(time_s) + "s.dat");
}

void write_spectrum(const std::string& project_root,
                    const nublar::ExperimentalRow& row,
                    nanosphere& sphere,
                    double host_eps,
                    const nublar::OmegaRange& omega_range)
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
        const double omega_ev = nublar::wavelength_nm_to_omega_ev(wavelength_nm);
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
        const std::complex<double> eps_mmgm = nublar::mmgm_effective_permittivity(
            row.rave_nm, eps_metal, host_eps, wavelength_nm, row.effe, row);

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

        std::vector<nublar::ExperimentalRow> rows = nublar::read_manifest(manifest_path);
        const nublar::OmegaRange omega_range = nublar::read_omega_range_from_material_table(
            std::filesystem::path(project_root)
            / "extern/nano_geo_matrix/modules/cup/data/materials/metals/silverUNICALeV.dat");

        nanosphere sphere;
        sphere.init();
        sphere.set_metal("silver", "spline", 0, "unical");
        const double host_eps = sphere.set_host("air");

        for (const nublar::ExperimentalRow& row : rows) {
            write_spectrum(project_root, row, sphere, host_eps, omega_range);
        }

        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "Error: " << exc.what() << std::endl;
        return 1;
    }
}
