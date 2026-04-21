#include <array>
#include <complex>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>

#include "effective_medium.hpp"
#include "project_paths.hpp"
#include "transmittance_workflow.hpp"

namespace {

constexpr std::array<double, 6> kFractions{0.0, 0.2, 0.4, 0.6, 0.8, 1.0};

std::filesystem::path data_output_path(const std::string& project_root)
{
    return std::filesystem::path(project_root) / "data/output/test_bruggeman.dat";
}

std::filesystem::path gnuplot_output_path(const std::string& project_root)
{
    return std::filesystem::path(project_root) / "scripts/gnuiplot/tests/test_bruggeman.gp";
}

std::filesystem::path png_output_path(const std::string& project_root)
{
    return std::filesystem::path(project_root) / "img/tests/test_bruggeman.png";
}

void write_gnuplot_script(const std::filesystem::path& script_path,
                          const std::filesystem::path& data_path,
                          const std::filesystem::path& png_path)
{
    std::ofstream gp(script_path);
    if (!gp.is_open()) {
        throw std::runtime_error("Could not open gnuplot script: " + script_path.string());
    }

    gp << "set terminal pngcairo size 1600,1000 noenhanced\n";
    gp << "set output '" << png_path.string() << "'\n";
    gp << "set datafile commentschars '#'\n";
    gp << "set grid\n";
    gp << "set key outside right\n";
    gp << "set xlabel 'Wavelength (nm)'\n";
    gp << "set multiplot layout 2,1 title 'Bruggeman effective permittivity vs air and silver'\n";
    gp << "set ylabel 'Re(epsilon)'\n";
    gp << "plot \\\n";
    gp << "  '" << data_path.string() << "' using 1:2 with lines lw 3 lc rgb '#404040' title 'air', \\\n";
    gp << "  '" << data_path.string() << "' using 1:4 with lines lw 3 lc rgb '#c00000' title 'silver', \\\n";
    gp << "  '" << data_path.string() << "' using 1:6  with lines lw 1.5 dt 2 title 'Bruggeman f=0.0', \\\n";
    gp << "  '" << data_path.string() << "' using 1:8  with lines lw 1.5 dt 2 title 'Bruggeman f=0.2', \\\n";
    gp << "  '" << data_path.string() << "' using 1:10 with lines lw 1.5 dt 2 title 'Bruggeman f=0.4', \\\n";
    gp << "  '" << data_path.string() << "' using 1:12 with lines lw 1.5 dt 2 title 'Bruggeman f=0.6', \\\n";
    gp << "  '" << data_path.string() << "' using 1:14 with lines lw 1.5 dt 2 title 'Bruggeman f=0.8', \\\n";
    gp << "  '" << data_path.string() << "' using 1:16 with lines lw 1.5 dt 2 title 'Bruggeman f=1.0'\n";
    gp << "set ylabel 'Im(epsilon)'\n";
    gp << "set yrange [-0.1:*]\n";
    gp << "plot \\\n";
    gp << "  '" << data_path.string() << "' using 1:3 with lines lw 3 lc rgb '#404040' title 'air', \\\n";
    gp << "  '" << data_path.string() << "' using 1:5 with lines lw 3 lc rgb '#c00000' title 'silver', \\\n";
    gp << "  '" << data_path.string() << "' using 1:7  with lines lw 1.5 dt 2 title 'Bruggeman f=0.0', \\\n";
    gp << "  '" << data_path.string() << "' using 1:9  with lines lw 1.5 dt 2 title 'Bruggeman f=0.2', \\\n";
    gp << "  '" << data_path.string() << "' using 1:11 with lines lw 1.5 dt 2 title 'Bruggeman f=0.4', \\\n";
    gp << "  '" << data_path.string() << "' using 1:13 with lines lw 1.5 dt 2 title 'Bruggeman f=0.6', \\\n";
    gp << "  '" << data_path.string() << "' using 1:15 with lines lw 1.5 dt 2 title 'Bruggeman f=0.8', \\\n";
    gp << "  '" << data_path.string() << "' using 1:17 with lines lw 1.5 dt 2 title 'Bruggeman f=1.0'\n";
    gp << "unset multiplot\n";
}

}  // namespace

int main(int argc, char* argv[])
{
    try {
        const std::string project_root = nublar::resolve_project_root(argv[0]);
        const std::filesystem::path manifest_path = (argc >= 2)
            ? std::filesystem::path(argv[1])
            : std::filesystem::path(project_root) / "data/input/experimental/model_input.dat";

        const nublar::CommonWavelengthGrid grid =
            nublar::read_common_transmittance_wavelength_grid(manifest_path);
        nublar::WorkflowDielectricModels models =
            nublar::make_transmittance_workflow_dielectric_models();
        const nublar::OmegaRange omega_range =
            nublar::read_omega_range_from_material_table(
                std::filesystem::path(project_root)
                / "extern/nano_geo_matrix/modules/cup/data/materials/metals/silverUNICALeV.dat");

        const std::filesystem::path data_path = data_output_path(project_root);
        const std::filesystem::path script_path = gnuplot_output_path(project_root);
        const std::filesystem::path png_path = png_output_path(project_root);
        std::filesystem::create_directories(data_path.parent_path());
        std::filesystem::create_directories(script_path.parent_path());
        std::filesystem::create_directories(png_path.parent_path());

        std::ofstream out(data_path);
        if (!out.is_open()) {
            throw std::runtime_error("Could not open output data file: " + data_path.string());
        }

        out << "# columns: wavelength_nm air_re air_im silver_re silver_im "
            << "bruggeman_f0.0_re bruggeman_f0.0_im "
            << "bruggeman_f0.2_re bruggeman_f0.2_im "
            << "bruggeman_f0.4_re bruggeman_f0.4_im "
            << "bruggeman_f0.6_re bruggeman_f0.6_im "
            << "bruggeman_f0.8_re bruggeman_f0.8_im "
            << "bruggeman_f1.0_re bruggeman_f1.0_im\n";
        out << std::fixed << std::setprecision(10);

        double max_f0_error = 0.0;
        double max_f1_error = 0.0;
        std::array<std::optional<std::complex<double>>, kFractions.size()> previous_eps_eff{};

        for (int i = 0; i < grid.n_lambda; ++i) {
            const double wavelength_nm = grid.lamin_nm + static_cast<double>(i) * grid.dlam_nm;
            const double omega_ev = nublar::wavelength_nm_to_omega_ev(wavelength_nm);
            const std::complex<double> eps_air =
                nublar::workflow_air_permittivity(models.host_eps);

            out << wavelength_nm;

            if (omega_ev < omega_range.min_ev || omega_ev > omega_range.max_ev) {
                const double nan = std::numeric_limits<double>::quiet_NaN();
                for (int col = 0; col < 16; ++col) {
                    out << " " << nan;
                }
                out << "\n";
                continue;
            }

            const std::complex<double> eps_silver =
                nublar::workflow_silver_permittivity(models, omega_ev);

            out << " " << eps_air.real() << " " << eps_air.imag()
                << " " << eps_silver.real() << " " << eps_silver.imag();

            for (std::size_t fraction_index = 0; fraction_index < kFractions.size(); ++fraction_index) {
                const double fraction = kFractions[fraction_index];
                const auto roots = nublar::BruggemanRoots(fraction, eps_silver, eps_air);
                const std::complex<double> eps_eff = previous_eps_eff[fraction_index].has_value()
                    ? nublar::BruggemanSelectContinuationRoot(
                        roots, *previous_eps_eff[fraction_index])
                    : nublar::BruggemanSelectInitialRoot(
                        fraction, roots, eps_silver, eps_air);

                previous_eps_eff[fraction_index] = eps_eff;
                if (nublar::BruggemanSelectedRootViolatesPassivity(
                        eps_eff, eps_silver, eps_air)) {
                    std::cerr << "WARNING: selected Bruggeman root has Im(eps_eff) = "
                              << eps_eff.imag()
                              << " at wavelength_nm = " << wavelength_nm
                              << " for f = " << fraction
                              << " while both constituents are passive"
                              << std::endl;
                }

                out << " " << eps_eff.real() << " " << eps_eff.imag();

                if (fraction == 0.0) {
                    max_f0_error = std::max(max_f0_error, std::abs(eps_eff - eps_air));
                }
                if (fraction == 1.0) {
                    max_f1_error = std::max(max_f1_error, std::abs(eps_eff - eps_silver));
                }
            }

            out << "\n";
        }

        write_gnuplot_script(script_path, data_path, png_path);

        constexpr double kTolerance = 1e-10;
        std::cout << "Sanity check f=0 vs air: max |delta| = " << std::setprecision(16)
                  << max_f0_error
                  << ((max_f0_error <= kTolerance) ? " [ok]\n" : " [warning]\n");
        std::cout << "Sanity check f=1 vs silver: max |delta| = " << std::setprecision(16)
                  << max_f1_error
                  << ((max_f1_error <= kTolerance) ? " [ok]\n" : " [warning]\n");
        std::cout << "Wrote data: " << data_path << "\n";
        std::cout << "Wrote gnuplot script: " << script_path << "\n";

        return (max_f0_error <= kTolerance && max_f1_error <= kTolerance) ? 0 : 2;
    } catch (const std::exception& exc) {
        std::cerr << "Error: " << exc.what() << std::endl;
        return 1;
    }
}
