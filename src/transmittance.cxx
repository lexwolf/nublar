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

#include "effective_medium.hpp"
#include "nano_island_permittivity.hpp"
#include "project_paths.hpp"
#include "transmittance_workflow.hpp"

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

double forward_power_flux(const std::complex<double>& n_medium,
                          const std::complex<double>& e_forward);

struct ToyCase {
    std::string label;
    double wavelength_nm;
    std::complex<double> n_in;
    std::complex<double> n_slab;
    double d_slab_nm;
    std::complex<double> n_out;
};

struct SingleSlabTmmDebug {
    std::complex<double> beta;
    std::complex<double> exp_i_beta;
    std::complex<double> exp_2i_beta;
    std::complex<double> m11;
    std::complex<double> m12;
    std::complex<double> m21;
    std::complex<double> m22;
    RtCoefficients rt;
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
    constexpr double kImagEpsTolerance = 1e-8;

    // Spline/interpolation noise can produce tiny negative Im(eps) values for
    // weakly absorbing dielectrics. Clamp those to the lossless limit before
    // taking the square root so the passive branch remains physically stable.
    std::complex<double> eps_sanitized = eps;
    if (eps_sanitized.imag() < 0.0 && std::abs(eps_sanitized.imag()) <= kImagEpsTolerance) {
        eps_sanitized = {eps_sanitized.real(), 0.0};
    }

    std::complex<double> n = std::sqrt(eps_sanitized);

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
    const double incident_flux = forward_power_flux(n_left, std::complex<double>(1.0, 0.0));
    const double transmitted_flux = forward_power_flux(n_right, t);
    const double T = (incident_flux > 0.0)
        ? (transmitted_flux / incident_flux)
        : std::numeric_limits<double>::quiet_NaN();

    return {r, t, R, T};
}

double forward_power_flux(const std::complex<double>& n_medium,
                          const std::complex<double>& e_forward)
{
    const std::complex<double> h_forward = n_medium * e_forward;
    return std::real(e_forward * std::conj(h_forward));
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
        const cd a12 = -cd(0.0, 1.0) * s / n_layer;
        const cd a21 = -cd(0.0, 1.0) * n_layer * s;
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
    const double incident_flux = forward_power_flux(n_in, cd(1.0, 0.0));
    const double transmitted_flux = forward_power_flux(n_out, t);
    const double T = (incident_flux > 0.0)
        ? (transmitted_flux / incident_flux)
        : std::numeric_limits<double>::quiet_NaN();

    return {r, t, R, T};
}

std::vector<Layer> reversed_layers(const std::vector<Layer>& layers)
{
    return std::vector<Layer>(layers.rbegin(), layers.rend());
}

std::filesystem::path toy_output_path(const std::string& project_root)
{
    return std::filesystem::path(project_root)
           / "data/output/transmittance"
           / "toy_front_stack_diagnostic.dat";
}

double beer_attenuation_factor(const std::complex<double>& n_glass, double wavelength_nm, double thickness_nm)
{
    const double kappa = std::max(0.0, n_glass.imag());
    const double alpha_nm_inv = 4.0 * kPi * kappa / wavelength_nm;
    return std::exp(-alpha_nm_inv * thickness_nm);
}

bool violates_passivity(double R, double T, double A)
{
    constexpr double kTol = 1e-9;
    return R < -kTol || T < -kTol || T > 1.0 + kTol || A < -kTol;
}

RtCoefficients single_slab_rt_analytic(const std::complex<double>& n_in,
                                       const std::complex<double>& n_slab,
                                       double slab_thickness_nm,
                                       const std::complex<double>& n_out,
                                       double wavelength_nm)
{
    using cd = std::complex<double>;

    const cd r01 = (n_in - n_slab) / (n_in + n_slab);
    const cd r12 = (n_slab - n_out) / (n_slab + n_out);
    const cd t01 = (2.0 * n_in) / (n_in + n_slab);
    const cd t12 = (2.0 * n_slab) / (n_slab + n_out);
    const cd beta = (2.0 * kPi / wavelength_nm) * n_slab * slab_thickness_nm;
    const cd exp_i_beta = std::exp(cd(0.0, 1.0) * beta);
    const cd exp_2i_beta = std::exp(cd(0.0, 2.0) * beta);
    const cd denom = cd(1.0, 0.0) + r01 * r12 * exp_2i_beta;

    const cd r = (r01 + r12 * exp_2i_beta) / denom;
    const cd t = (t01 * t12 * exp_i_beta) / denom;

    const double R = std::norm(r);
    const double incident_flux = forward_power_flux(n_in, cd(1.0, 0.0));
    const double transmitted_flux = forward_power_flux(n_out, t);
    const double T = (incident_flux > 0.0)
        ? (transmitted_flux / incident_flux)
        : std::numeric_limits<double>::quiet_NaN();

    return {r, t, R, T};
}

SingleSlabTmmDebug single_slab_rt_tmm_debug(const std::complex<double>& n_in,
                                            const std::complex<double>& n_slab,
                                            double slab_thickness_nm,
                                            const std::complex<double>& n_out,
                                            double wavelength_nm)
{
    using cd = std::complex<double>;

    const cd beta = (2.0 * kPi / wavelength_nm) * n_slab * slab_thickness_nm;
    const cd exp_i_beta = std::exp(cd(0.0, 1.0) * beta);
    const cd exp_2i_beta = std::exp(cd(0.0, 2.0) * beta);
    const cd c = std::cos(beta);
    const cd s = std::sin(beta);

    const cd m11 = c;
    const cd m12 = -cd(0.0, 1.0) * s / n_slab;
    const cd m21 = -cd(0.0, 1.0) * n_slab * s;
    const cd m22 = c;

    const cd denom = n_in * m11 + n_in * n_out * m12 + m21 + n_out * m22;
    const cd r = (n_in * m11 + n_in * n_out * m12 - m21 - n_out * m22) / denom;
    const cd t = (2.0 * n_in) / denom;

    const double R = std::norm(r);
    const double incident_flux = forward_power_flux(n_in, cd(1.0, 0.0));
    const double transmitted_flux = forward_power_flux(n_out, t);
    const double T = (incident_flux > 0.0)
        ? (transmitted_flux / incident_flux)
        : std::numeric_limits<double>::quiet_NaN();

    return {
        beta,
        exp_i_beta,
        exp_2i_beta,
        m11,
        m12,
        m21,
        m22,
        {r, t, R, T},
    };
}

int run_toy_front_stack_diagnostic(const std::string& project_root)
{
    const std::vector<ToyCase> toy_cases = {
        {
            "ToyCaseA_weak_absorbing_dielectric",
            500.0,
            {1.0, 0.0},
            {1.5, 0.01},
            50.0,
            {1.5, 0.0},
        },
        {
            "ToyCaseB_absorbing_metal_like",
            500.0,
            {1.0, 0.0},
            {0.3, 2.0},
            20.0,
            {1.5, 0.0},
        },
    };

    const std::filesystem::path output_path = toy_output_path(project_root);
    std::filesystem::create_directories(output_path.parent_path());

    std::ofstream out(output_path);
    if (!out.is_open()) {
        throw std::runtime_error("Could not open toy diagnostic file: " + output_path.string());
    }

    out << "# Toy front-stack diagnostic using coherent_stack_rt()\n";
    out << "# columns: case_label lambda_nm "
        << "n_in_re n_in_im n_slab_re n_slab_im d_slab_nm n_out_re n_out_im "
        << "beta_re beta_im exp_i_beta_re exp_i_beta_im exp_2i_beta_re exp_2i_beta_im "
        << "M11_re M11_im M12_re M12_im M21_re M21_im M22_re M22_im "
        << "R_tmm T_tmm A_tmm "
        << "R_analytic T_analytic A_analytic "
        << "dR dT dA "
        << "r_tmm_re r_tmm_im t_tmm_re t_tmm_im "
        << "r_analytic_re r_analytic_im t_analytic_re t_analytic_im\n";
    out << std::fixed << std::setprecision(10);

    bool any_failure = false;
    for (const ToyCase& toy_case : toy_cases) {
        const std::vector<Layer> layers = {
            {toy_case.n_slab * toy_case.n_slab, toy_case.d_slab_nm},
        };

        const RtCoefficients rt_tmm = coherent_stack_rt(
            toy_case.n_in, layers, toy_case.n_out, toy_case.wavelength_nm);
        const SingleSlabTmmDebug tmm_debug = single_slab_rt_tmm_debug(
            toy_case.n_in, toy_case.n_slab, toy_case.d_slab_nm, toy_case.n_out, toy_case.wavelength_nm);
        const RtCoefficients rt_analytic = single_slab_rt_analytic(
            toy_case.n_in, toy_case.n_slab, toy_case.d_slab_nm, toy_case.n_out, toy_case.wavelength_nm);

        const double A_tmm = 1.0 - rt_tmm.R - rt_tmm.T;
        const double A_analytic = 1.0 - rt_analytic.R - rt_analytic.T;
        const double dR = rt_tmm.R - rt_analytic.R;
        const double dT = rt_tmm.T - rt_analytic.T;
        const double dA = A_tmm - A_analytic;

        const bool tmm_failed = violates_passivity(rt_tmm.R, rt_tmm.T, A_tmm);
        const bool analytic_failed = violates_passivity(rt_analytic.R, rt_analytic.T, A_analytic);

        out << toy_case.label << " "
            << toy_case.wavelength_nm << " "
            << toy_case.n_in.real() << " " << toy_case.n_in.imag() << " "
            << toy_case.n_slab.real() << " " << toy_case.n_slab.imag() << " "
            << toy_case.d_slab_nm << " "
            << toy_case.n_out.real() << " " << toy_case.n_out.imag() << " "
            << safe_real_or_nan(tmm_debug.beta) << " " << safe_imag_or_nan(tmm_debug.beta) << " "
            << safe_real_or_nan(tmm_debug.exp_i_beta) << " " << safe_imag_or_nan(tmm_debug.exp_i_beta) << " "
            << safe_real_or_nan(tmm_debug.exp_2i_beta) << " " << safe_imag_or_nan(tmm_debug.exp_2i_beta) << " "
            << safe_real_or_nan(tmm_debug.m11) << " " << safe_imag_or_nan(tmm_debug.m11) << " "
            << safe_real_or_nan(tmm_debug.m12) << " " << safe_imag_or_nan(tmm_debug.m12) << " "
            << safe_real_or_nan(tmm_debug.m21) << " " << safe_imag_or_nan(tmm_debug.m21) << " "
            << safe_real_or_nan(tmm_debug.m22) << " " << safe_imag_or_nan(tmm_debug.m22) << " "
            << rt_tmm.R << " " << rt_tmm.T << " " << A_tmm << " "
            << rt_analytic.R << " " << rt_analytic.T << " " << A_analytic << " "
            << dR << " " << dT << " " << dA << " "
            << safe_real_or_nan(rt_tmm.r) << " " << safe_imag_or_nan(rt_tmm.r) << " "
            << safe_real_or_nan(rt_tmm.t) << " " << safe_imag_or_nan(rt_tmm.t) << " "
            << safe_real_or_nan(rt_analytic.r) << " " << safe_imag_or_nan(rt_analytic.r) << " "
            << safe_real_or_nan(rt_analytic.t) << " " << safe_imag_or_nan(rt_analytic.t) << "\n";

        if (tmm_failed || analytic_failed) {
            any_failure = true;
            std::cerr << "[WARN] " << toy_case.label << ": "
                      << (tmm_failed ? "TMM failed" : "TMM passed") << ", "
                      << (analytic_failed ? "analytic failed" : "analytic passed")
                      << " | TMM(R=" << rt_tmm.R << ", T=" << rt_tmm.T << ", A=" << A_tmm << ")"
                      << " | analytic(R=" << rt_analytic.R << ", T=" << rt_analytic.T << ", A=" << A_analytic << ")"
                      << std::endl;
        } else {
            std::cerr << "[INFO] " << toy_case.label << ": TMM passed, analytic passed"
                      << " | TMM(R=" << rt_tmm.R << ", T=" << rt_tmm.T << ", A=" << A_tmm << ")"
                      << " | analytic(R=" << rt_analytic.R << ", T=" << rt_analytic.T << ", A=" << A_analytic << ")"
                      << std::endl;
        }
    }

    std::cout << output_path << "\n";
    return any_failure ? 2 : 0;
}

void write_spectrum(const std::string& project_root,
                    const nublar::ExperimentalRow& row,
                    nanosphere& metal_sphere,
                    nanosphere& dielectric_sphere,
                    double host_eps,
                    const nublar::OmegaRange& omega_range,
                    double ito_thickness_nm,
                    double glass_thickness_nm,
                    bool include_incoherent_multiples,
                    double eta,
                    double xi)
{
    const std::filesystem::path output_path = output_path_for_time(project_root, row.time_s);
    std::filesystem::create_directories(output_path.parent_path());

    std::ofstream out(output_path);
    if (!out.is_open()) {
        throw std::runtime_error("Could not open output file: " + output_path.string());
    }

    out << "# time_s " << row.time_s << "\n";
    out << "# effe " << std::setprecision(16) << row.effe << "\n";
    out << "# effe_scaled " << (xi * row.effe) << "\n";
    out << "# Rave_nm " << row.rave_nm << "\n";
    out << "# effective_thickness_nm " << row.thickness_nm << "\n";
    out << "# eta " << eta << "\n";
    out << "# xi " << xi << "\n";
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
        << "eps_eff_re eps_eff_im eps_ito_re eps_ito_im eps_glass_re eps_glass_im A_front\n";

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

        const std::complex<double> eps_metal =
            nublar::workflow_silver_permittivity(metal_sphere, omega_ev);
        const double effe_scaled = xi * row.effe;
        const std::complex<double> eps_eff = nublar::mmgm_effective_permittivity(
            row.rave_nm, eps_metal, host_eps, wavelength_nm, effe_scaled, row);

        const std::complex<double> eps_ito =
            nublar::workflow_dielectric_permittivity(dielectric_sphere, "ito", omega_ev);
        const std::complex<double> eps_glass =
            nublar::workflow_dielectric_permittivity(dielectric_sphere, "glass", omega_ev);

        const std::complex<double> n_air = principal_refractive_index(
            nublar::workflow_air_permittivity(host_eps));
        const std::complex<double> n_glass = principal_refractive_index(eps_glass);
        const double d_eff_nm = eta * row.thickness_nm;

        const std::vector<Layer> front_layers = {
            {eps_eff, d_eff_nm},
            {eps_ito, ito_thickness_nm}
        };

        const RtCoefficients front_from_air = coherent_stack_rt(
            n_air, front_layers, n_glass, wavelength_nm);

        const RtCoefficients front_from_glass = coherent_stack_rt(
            n_glass, reversed_layers(front_layers), n_air, wavelength_nm);

        const RtCoefficients back_interface = interface_rt(n_glass, n_air);

        const double A_glass = beer_attenuation_factor(n_glass, wavelength_nm, glass_thickness_nm);
        const double A_front = 1.0 - front_from_air.R - front_from_air.T;

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
            << safe_real_or_nan(eps_glass) << " " << safe_imag_or_nan(eps_glass) << " "
            << A_front << "\n";
    }

    std::cout << output_path << "\n";
}

} // namespace

int main(int argc, char* argv[])
{
    try {
        const std::string project_root = nublar::resolve_project_root(argv[0]);
        if (argc >= 2 && std::string(argv[1]) == "--toy") {
            return run_toy_front_stack_diagnostic(project_root);
        }
        const std::filesystem::path manifest_path = (argc >= 2)
            ? std::filesystem::path(argv[1])
            : std::filesystem::path(project_root) / "data/input/experimental/model_input.dat";

        // Optional CLI overrides
        // argv[2] = ITO thickness in nm          (default 0.0)
        // argv[3] = glass thickness in nm        (default 1.1e6 nm = 1.1 mm)
        // argv[4] = include incoherent multiples (default 1)
        // argv[5] = nanoisland effective thickness scaling eta (default 1.0)
        // argv[6] = effective filling fraction scaling xi (default 1.0)
        const double ito_thickness_nm = (argc >= 3) ? std::stod(argv[2]) : 0.0;
        const double glass_thickness_nm = (argc >= 4) ? std::stod(argv[3]) : 1.1e6;
        const bool include_incoherent_multiples = (argc >= 5) ? (std::stoi(argv[4]) != 0) : true;
        double eta = 1.0;
        if (argc > 5) {
            eta = std::stod(argv[5]);
        }
        double xi = 1.0;
        if (argc > 6) {
            xi = std::stod(argv[6]);
        }

        std::cerr << "[INFO] Using thickness scaling eta = " << eta << std::endl;
        std::cerr << "[INFO] Using filling-fraction scaling xi = " << xi << std::endl;

        std::vector<nublar::ExperimentalRow> rows = nublar::read_manifest(manifest_path);

        const nublar::OmegaRange omega_range =
            nublar::read_transmittance_workflow_omega_range(project_root);

        nublar::WorkflowDielectricModels models =
            nublar::make_transmittance_workflow_dielectric_models();

        for (const nublar::ExperimentalRow& row : rows) {
            write_spectrum(project_root,
                           row,
                           models.metal_sphere,
                           models.dielectric_sphere,
                           models.host_eps,
                           omega_range,
                           ito_thickness_nm,
                           glass_thickness_nm,
                           include_incoherent_multiples,
                           eta,
                           xi);
        }

        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "Error: " << exc.what() << std::endl;
        return 1;
    }
}
