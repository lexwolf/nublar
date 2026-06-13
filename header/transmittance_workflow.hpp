#pragma once

#include <algorithm>
#include <cmath>
#include <complex>
#include <filesystem>
#include <stdexcept>

#include <nano_geo_matrix/quasi_static/geometry/single.hpp>
#define CUP_BACKEND_QUASI_STATIC
#include <cup.hpp>

#include "nano_island_permittivity.hpp"

namespace nublar {

struct WorkflowDielectricModels {
    nanosphere metal_sphere;
    nanosphere dielectric_sphere;
    double host_eps = 0.0;
};

struct CommonWavelengthGrid {
    int n_lambda = 0;
    double lamin_nm = 0.0;
    double lamax_nm = 0.0;
    double dlam_nm = 0.0;
};

inline WorkflowDielectricModels make_transmittance_workflow_dielectric_models()
{
    WorkflowDielectricModels models;
    models.metal_sphere.init();
    models.metal_sphere.set_metal("silver", "spline", 0, "unical");
    models.host_eps = models.metal_sphere.set_host("air");

    models.dielectric_sphere.init();
    return models;
}

inline std::complex<double> workflow_air_permittivity(double host_eps)
{
    return {host_eps, 0.0};
}

inline std::complex<double> workflow_silver_permittivity(WorkflowDielectricModels& models,
                                                         double omega_ev)
{
    return models.metal_sphere.metal(omega_ev);
}

inline std::complex<double> workflow_silver_permittivity(nanosphere& metal_sphere,
                                                         double omega_ev)
{
    return metal_sphere.metal(omega_ev);
}

inline std::complex<double> workflow_dielectric_permittivity(WorkflowDielectricModels& models,
                                                             const char* material,
                                                             double omega_ev)
{
    models.dielectric_sphere.set_dielectric(material, "spline", "unical");
    return models.dielectric_sphere.dielectric(omega_ev);
}

inline std::complex<double> workflow_dielectric_permittivity(nanosphere& dielectric_sphere,
                                                             const char* material,
                                                             double omega_ev)
{
    dielectric_sphere.set_dielectric(material, "spline", "unical");
    return dielectric_sphere.dielectric(omega_ev);
}

inline long long checked_grid_index(double origin_nm, double value_nm, double step_nm)
{
    if (step_nm <= 0.0) {
        throw std::runtime_error("Wavelength grid step must be positive");
    }

    const double index = (value_nm - origin_nm) / step_nm;
    const long long rounded = std::llround(index);
    constexpr double kTolerance = 1e-9;
    if (std::abs(index - static_cast<double>(rounded)) > kTolerance) {
        throw std::runtime_error("Common wavelength range is not aligned to the manifest grid");
    }
    return rounded;
}

inline CommonWavelengthGrid read_common_transmittance_wavelength_grid(
    const std::filesystem::path& manifest_path)
{
    const std::vector<ExperimentalRow> rows = read_manifest(manifest_path);

    CommonWavelengthGrid grid;
    grid.lamin_nm = rows.front().lamin_nm;
    grid.lamax_nm = rows.front().lamax_nm;
    grid.dlam_nm = rows.front().dlam_nm;

    constexpr double kTolerance = 1e-9;
    for (const ExperimentalRow& row : rows) {
        if (std::abs(row.dlam_nm - grid.dlam_nm) > kTolerance) {
            throw std::runtime_error("Transmittance manifest rows do not share one wavelength step");
        }

        grid.lamin_nm = std::max(grid.lamin_nm, row.lamin_nm);
        grid.lamax_nm = std::min(grid.lamax_nm, row.lamax_nm);
    }

    if (grid.lamin_nm > grid.lamax_nm) {
        throw std::runtime_error("No common wavelength range exists in the transmittance manifest");
    }

    grid.n_lambda = static_cast<int>(checked_grid_index(
        grid.lamin_nm, grid.lamax_nm, grid.dlam_nm) + 1);

    if (grid.n_lambda <= 0) {
        throw std::runtime_error("Computed common wavelength grid is empty");
    }

    return grid;
}

inline OmegaRange read_transmittance_workflow_omega_range(const std::string& project_root)
{
    const OmegaRange omega_metal = read_omega_range_from_material_table(
        std::filesystem::path(project_root)
        / "extern/nano_geo_matrix/modules/cup/data/materials/metals/silverUNICALeV.dat");
    const OmegaRange omega_ito = read_omega_range_from_material_table(
        std::filesystem::path(project_root)
        / "extern/nano_geo_matrix/modules/cup/data/materials/dielectrics/itoUNICALeV.dat");
    const OmegaRange omega_glass = read_omega_range_from_material_table(
        std::filesystem::path(project_root)
        / "extern/nano_geo_matrix/modules/cup/data/materials/dielectrics/glassUNICALeV.dat");

    const OmegaRange omega_range{
        std::max({omega_metal.min_ev, omega_ito.min_ev, omega_glass.min_ev}),
        std::min({omega_metal.max_ev, omega_ito.max_ev, omega_glass.max_ev})
    };

    if (omega_range.min_ev >= omega_range.max_ev) {
        throw std::runtime_error("No common omega range among silver / ITO / glass tables.");
    }

    return omega_range;
}

}  // namespace nublar
