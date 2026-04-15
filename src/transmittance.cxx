#include <cmath>
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

make bin/transmittance

Physics model implemented here:
- coherent top stack: air | effective Ag-island layer | ITO | glass
- incoherent thick substrate: propagation through finite-thickness glass slab
- incoherent back interface: glass | air
- optional incoherent substrate multiple reflections are INCLUDED

So the final transmission is

  T_total = T_front * A * T_back / (1 - R_front_from_glass * R_back * A^2)

where
  T_front            : coherent transmittance air -> (eff | ITO) -> glass
  R_front_from_glass : coherent reflectance of the same top stack, but seen from glass side
  A                  : exp(-alpha_glass * d_glass)
  T_back, R_back     : intensity coefficients of the glass/air back interface

This is the sane first model for a 1.1 mm glass substrate under broadband illumination.
*/

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;
constexpr double kHcEvNm = 1239.8419843320026; // eV * nm

struct Layer {
    std::complex<double> eps;
    double thickness_nm;
};

struct RtCoefficients {
    std::complex<double> r;
    std::complex<double> t;
    double R;
    double T;
};

std::filesystem::path output_path_for_time(const std::string& project_root, int time_s)
{
    return std::filesystem::path(project_root)
           / "data/output/transmittance"
           / ("silver_nanoisland_" + std::to_string(time_s) + "s.dat");
}

double safe_real_or_nan(const std::complex<double>& z)
{
    return std::isfinite(z.real()) ? z.real() : std::numeric_limits<double>::quiet_NaN();
}

double safe_imag_or_nan(const std::complex<double>& z)
{
    return std::isfinite(z.imag()) ? z.imag() : std::numeric_limits<double>::quiet_NaN();
}

std::complex<double> principal_refractive_index(const std::complex<double>& eps)
{
    std::complex<double> n = std::sqrt(eps);

    // Choose the passive branch with non-negative extinction coefficient.
    if (n.imag() < 0.0) {
        n = -n;
    }

    // If imag is numerically zero, prefer positive real part.
    if (std::abs(n.imag()) < 1e-14 && n.real() < 0.0) {
        n = -n;
    }

    return n;
}

RtCoefficients interface_rt(const std::complex<double>& n_left,
                            const std::complex<double>& n_right)
{
    const std::complex<double> denom = n_left + n_right;
    const std::complex<double> r = (n_left - n_right) / denom;
    const std::complex<double> t = (2.0 * n_left) / denom;

    const double R = std::norm(r);
    const double T = (std::real(n_right) / std::real(n_left)) * std::norm(t);

    return {r, t, R, T};
}

RtCoefficients coherent_stack_rt(const std::complex<double>& n_in,
                                 const std::vector<Layer>& layers,
                                 const std::complex<double>& n_out,
                                 double wavelength_nm)
{
    using cd = std::complex<double>;

    cd m11(1.0, 0.0);
    cd m12(0.0, 0.0);
    cd m21(0.0, 0.0);
    cd m22(1.0, 0.0);

    for (const Layer& layer : layers) {
        const cd n_layer = principal_refractive_index(layer.eps);
        const cd delta = (2.0 * kPi / wavelength_nm) * n_layer * layer.thickness_nm;
        const cd c = std::cos(delta);
        const cd s = std::sin(delta);

        const cd a11 = c;
        const cd a12 = cd(0.0, 1.0) * s / n_layer;
        const cd a21 = cd(0.0, 1.0) * n_layer * s;
        const cd a22 = c;

        const cd new_m11 = m11 * a11 + m12 * a21;
        const cd new_m12 = m11 * a12 + m12 * a22;
        const cd new_m21 = m21 * a11 + m22 * a21;
        const cd new_m22 = m21 * a12 + m22 * a22;

        m11 = new_m11;
        m12 = new_m12;
        m21 = new_m21;
        m22 = new_m22;
    }

    const cd denom = n_in * m11 + n_in * n_out * m12 + m21 + n_out * m22;
    const cd r = (n_in * m11 + n_in * n_out * m12 - m21 - n_out * m22) / denom;
    const cd t = (2.0 * n_in) / denom;

    const double R = std::norm(r);
    const double T = (std::real(n_out) / std::real(n_in)) * std::norm(t);

    return {r, t, R, T};
}

std::vector<Layer> reversed_layers(const std::vector<Layer>& layers)
{
    return std::vector<Layer>(layers.rbegin(), layers.rend());
}

double beer_attenuation_factor(const std::complex<double>& n_glass, double wavelength_nm, double thickness_nm)
{
    const double kappa = std::max(0.0, n_glass.imag());
    const double alpha_nm_inv = 4.0 * kPi * kappa / wavelength_nm;
    return std::exp(-alpha_nm_inv * thickness_nm);
}

void write_spectrum(const std::string& project_root,
                    const nublar::ExperimentalRow& row,
                    nanosphere& metal_sphere,
                    nanosphere& dielectric_sphere,
                    double host_eps,
                    const nublar::OmegaRange& omega_range,
                    double ito_thickness_nm,
                    double glass_thickness_nm,
                    bool include_incoherent_multiples)
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
    out << "# effective_thickness_nm " << row.thickness_nm << "\n";
    out << "# ito_thickness_nm " << ito_thickness_nm << "\n";
    out << "# glass_thickness_nm " << glass_thickness_nm << "\n";
    out << "# distribution two_lognormal "
        << row.w1 << " " << row.mu_l1 << " " << row.sig_l1 << " "
        << row.w2 << " " << row.mu_l2 << " " << row.sig_l2 << "\n";
    out << "# omega_range_eV " << omega_range.min_ev << " " << omega_range.max_ev << "\n";
    out << "# model coherent_front_plus_incoherent_glass\n";
    out << "# incoherent_substrate_multiple_reflections "
        << (include_incoherent_multiples ? 1 : 0) << "\n";
    out << "# columns: lambda_nm omega_eV "
        << "T_total T_front T_back A_glass R_front_air R_front_glass R_back "
        << "eps_eff_re eps_eff_im eps_ito_re eps_ito_im eps_glass_re eps_glass_im\n";

    out << std::fixed << std::setprecision(10);

    for (int i = 0; i < row.n_lambda; ++i) {
        const double wavelength_nm = row.lamin_nm + static_cast<double>(i) * row.dlam_nm;
        const double omega_ev = nublar::wavelength_nm_to_omega_ev(wavelength_nm);

        if (omega_ev < omega_range.min_ev || omega_ev > omega_range.max_ev) {
            const double nan = std::numeric_limits<double>::quiet_NaN();
            out << wavelength_nm << " "
                << omega_ev << " "
                << nan << " " << nan << " " << nan << " " << nan << " "
                << nan << " " << nan << " " << nan << " "
                << nan << " " << nan << " " << nan << " "
                << nan << " " << nan << " " << nan << " " << nan << "\n";
            continue;
        }

        const std::complex<double> eps_metal = metal_sphere.metal(omega_ev);
        const std::complex<double> eps_eff = nublar::mmgm_effective_permittivity(
            row.rave_nm, eps_metal, host_eps, wavelength_nm, row.effe, row);

        dielectric_sphere.set_dielectric("ito", "spline", "unical");
        const std::complex<double> eps_ito = dielectric_sphere.dielectric(omega_ev);

        dielectric_sphere.set_dielectric("glass", "spline", "unical");
        const std::complex<double> eps_glass = dielectric_sphere.dielectric(omega_ev);

        const std::complex<double> n_air = principal_refractive_index(std::complex<double>(host_eps, 0.0));
        const std::complex<double> n_glass = principal_refractive_index(eps_glass);

        const std::vector<Layer> front_layers = {
            {eps_eff, row.thickness_nm},
            {eps_ito, ito_thickness_nm}
        };

        const RtCoefficients front_from_air = coherent_stack_rt(
            n_air, front_layers, n_glass, wavelength_nm);

        const RtCoefficients front_from_glass = coherent_stack_rt(
            n_glass, reversed_layers(front_layers), n_air, wavelength_nm);

        const RtCoefficients back_interface = interface_rt(n_glass, n_air);

        const double A_glass = beer_attenuation_factor(n_glass, wavelength_nm, glass_thickness_nm);

        double T_total = front_from_air.T * A_glass * back_interface.T;
        if (include_incoherent_multiples) {
            const double denom = 1.0 - front_from_glass.R * back_interface.R * A_glass * A_glass;
            if (std::abs(denom) < 1e-14) {
                T_total = std::numeric_limits<double>::quiet_NaN();
            } else {
                T_total /= denom;
            }
        }

        out << wavelength_nm << " "
            << omega_ev << " "
            << T_total << " "
            << front_from_air.T << " "
            << back_interface.T << " "
            << A_glass << " "
            << front_from_air.R << " "
            << front_from_glass.R << " "
            << back_interface.R << " "
            << safe_real_or_nan(eps_eff) << " " << safe_imag_or_nan(eps_eff) << " "
            << safe_real_or_nan(eps_ito) << " " << safe_imag_or_nan(eps_ito) << " "
            << safe_real_or_nan(eps_glass) << " " << safe_imag_or_nan(eps_glass) << "\n";
    }

    std::cout << output_path << "\n";
}

} // namespace

int main(int argc, char* argv[])
{
    try {
        const std::string project_root = nublar::resolve_project_root(argv[0]);
        const std::filesystem::path manifest_path = (argc >= 2)
            ? std::filesystem::path(argv[1])
            : std::filesystem::path(project_root) / "data/input/experimental/model_input.dat";

        // Optional CLI overrides
        // argv[2] = ITO thickness in nm          (default 0.0)
        // argv[3] = glass thickness in nm        (default 1.1e6 nm = 1.1 mm)
        // argv[4] = include incoherent multiples (default 1)
        const double ito_thickness_nm = (argc >= 3) ? std::stod(argv[2]) : 0.0;
        const double glass_thickness_nm = (argc >= 4) ? std::stod(argv[3]) : 1.1e6;
        const bool include_incoherent_multiples = (argc >= 5) ? (std::stoi(argv[4]) != 0) : true;

        std::vector<nublar::ExperimentalRow> rows = nublar::read_manifest(manifest_path);

        const nublar::OmegaRange omega_metal = nublar::read_omega_range_from_material_table(
            std::filesystem::path(project_root)
            / "extern/nano_geo_matrix/modules/cup/data/materials/metals/silverUNICALeV.dat");
        const nublar::OmegaRange omega_ito = nublar::read_omega_range_from_material_table(
            std::filesystem::path(project_root)
            / "extern/nano_geo_matrix/modules/cup/data/materials/dielectrics/itoUNICALeV.dat");
        const nublar::OmegaRange omega_glass = nublar::read_omega_range_from_material_table(
            std::filesystem::path(project_root)
            / "extern/nano_geo_matrix/modules/cup/data/materials/dielectrics/glassUNICALeV.dat");

        const nublar::OmegaRange omega_range{
            std::max({omega_metal.min_ev, omega_ito.min_ev, omega_glass.min_ev}),
            std::min({omega_metal.max_ev, omega_ito.max_ev, omega_glass.max_ev})
        };

        if (omega_range.min_ev >= omega_range.max_ev) {
            throw std::runtime_error("No common omega range among silver / ITO / glass tables.");
        }

        nanosphere metal_sphere;
        metal_sphere.init();
        metal_sphere.set_metal("silver", "spline", 0, "unical");
        const double host_eps = metal_sphere.set_host("air");

        nanosphere dielectric_sphere;
        dielectric_sphere.init();

        for (const nublar::ExperimentalRow& row : rows) {
            write_spectrum(project_root,
                           row,
                           metal_sphere,
                           dielectric_sphere,
                           host_eps,
                           omega_range,
                           ito_thickness_nm,
                           glass_thickness_nm,
                           include_incoherent_multiples);
        }

        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "Error: " << exc.what() << std::endl;
        return 1;
    }
}
