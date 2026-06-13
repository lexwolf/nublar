from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPTIMAL_DIR = ROOT / "tools" / "optimal"
if str(OPTIMAL_DIR) not in sys.path:
    sys.path.insert(0, str(OPTIMAL_DIR))

from optimize_global_model_parameters import (  # noqa: E402
    AfmParameterPrior,
    FitWindow,
    HagWindowConstraint,
    ModelBounds,
    OptimizerError,
    feasible_initial_population,
    mmgm_single_global_parameters_from_unit_vector,
    parameter_count_for_model,
    read_afm_prior_config,
    violates_hag_window,
)


def minimal_bounds() -> ModelBounds:
    return ModelBounds(
        effe_min=0.1,
        effe_max=0.5,
        thickness_min_nm=10.0,
        thickness_max_nm=20.0,
        thickness_transform="none",
        fit_window=FitWindow(min_nm=400.0, max_nm=800.0),
        rave_min_nm=1.0,
        rave_max_nm=10.0,
        rave_transform="none",
        sig_l_min=0.1,
        sig_l_max=0.9,
        sig_l_transform="none",
    )


def priors_by_time() -> dict[int, AfmParameterPrior]:
    return {
        10: AfmParameterPrior(
            time_s=10,
            rave_min_nm=2.0,
            rave_max_nm=4.0,
            rave_reference_nm=3.0,
            sig_l_min=0.2,
            sig_l_max=0.4,
            sig_l_reference=0.3,
            thickness_min_nm=1.0,
            thickness_max_nm=4.0,
            thickness_reference_nm=2.0,
        ),
        20: AfmParameterPrior(
            time_s=20,
            rave_min_nm=6.0,
            rave_max_nm=8.0,
            rave_reference_nm=7.0,
            sig_l_min=0.6,
            sig_l_max=0.8,
            sig_l_reference=0.7,
            thickness_min_nm=2.0,
            thickness_max_nm=8.0,
            thickness_reference_nm=4.0,
        ),
    }


def test_bounded_mode_parameter_mapping_uses_time_specific_prior_bounds() -> None:
    parameters = mmgm_single_global_parameters_from_unit_vector(
        [0.25, 0.5, 0.5, 0.5, 0.75, 0.25, 0.5, 0.5],
        minimal_bounds(),
        n_spectra=2,
        afm_priors_by_time_s=priors_by_time(),
        spectrum_times_s=[10, 20],
        afm_priors_mode="bounded",
    )

    assert len(parameters) == 2
    assert parameters[0][2] == pytest.approx(3.0)
    assert parameters[0][3] == pytest.approx(0.3)
    assert parameters[1][2] == pytest.approx(7.0)
    assert parameters[1][3] == pytest.approx(0.7)


def test_bounded_thickness_prior_uses_time_specific_bounds() -> None:
    parameters = mmgm_single_global_parameters_from_unit_vector(
        [0.25, 0.5, 0.5, 0.5, 0.75, 0.25, 0.5, 0.5],
        minimal_bounds(),
        n_spectra=2,
        afm_priors_by_time_s=priors_by_time(),
        spectrum_times_s=[10, 20],
        afm_priors_mode="bounded",
        afm_thickness_prior="bounded",
    )

    assert parameters[0][1] == pytest.approx(2.5)
    assert parameters[1][1] == pytest.approx(3.5)


def test_bounded_mode_can_fix_sigl_to_prior_reference() -> None:
    parameters = mmgm_single_global_parameters_from_unit_vector(
        [0.25, 0.5, 0.5, 0.75, 0.25, 0.5],
        minimal_bounds(),
        n_spectra=2,
        afm_priors_by_time_s=priors_by_time(),
        spectrum_times_s=[10, 20],
        afm_priors_mode="bounded",
        afm_sigl_mode="fixed",
    )

    assert len(parameters) == 2
    assert parameters[0][2] == pytest.approx(3.0)
    assert parameters[0][3] == pytest.approx(0.3)
    assert parameters[1][2] == pytest.approx(7.0)
    assert parameters[1][3] == pytest.approx(0.7)


def test_bounded_thickness_prior_scale_overrides_json_bounds() -> None:
    parameters = mmgm_single_global_parameters_from_unit_vector(
        [0.25, 0.5, 0.5, 0.5, 0.75, 0.25, 0.5, 0.5],
        minimal_bounds(),
        n_spectra=2,
        afm_priors_by_time_s=priors_by_time(),
        spectrum_times_s=[10, 20],
        afm_priors_mode="bounded",
        afm_thickness_prior="bounded",
        afm_thickness_scale_low=0.25,
        afm_thickness_scale_high=4.0,
    )

    assert parameters[0][1] == pytest.approx(4.25)
    assert parameters[1][1] == pytest.approx(4.75)


def test_fixed_mode_parameter_mapping_uses_prior_references() -> None:
    parameters = mmgm_single_global_parameters_from_unit_vector(
        [0.25, 0.5, 0.75, 0.25],
        minimal_bounds(),
        n_spectra=2,
        afm_priors_by_time_s=priors_by_time(),
        spectrum_times_s=[10, 20],
        afm_priors_mode="fixed",
    )

    assert len(parameters) == 2
    assert parameters[0][2] == pytest.approx(3.0)
    assert parameters[0][3] == pytest.approx(0.3)
    assert parameters[1][2] == pytest.approx(7.0)
    assert parameters[1][3] == pytest.approx(0.7)


def test_fixed_mode_rejects_bounded_mode_vector_length() -> None:
    with pytest.raises(OptimizerError, match="must have 4 values"):
        mmgm_single_global_parameters_from_unit_vector(
            [0.25, 0.5, 0.5, 0.5, 0.75, 0.25, 0.5, 0.5],
            minimal_bounds(),
            n_spectra=2,
            afm_priors_by_time_s=priors_by_time(),
            spectrum_times_s=[10, 20],
            afm_priors_mode="fixed",
        )


def test_fixed_mode_requires_afm_priors() -> None:
    with pytest.raises(OptimizerError, match="requires AFM priors"):
        mmgm_single_global_parameters_from_unit_vector(
            [0.25, 0.5, 0.75, 0.25],
            minimal_bounds(),
            n_spectra=2,
            afm_priors_mode="fixed",
        )


def test_parameter_count_depends_on_afm_prior_mode() -> None:
    assert parameter_count_for_model("mmgm_spheres_single", afm_priors_enabled=False) == 4
    assert (
        parameter_count_for_model(
            "mmgm_spheres_single",
            afm_priors_enabled=True,
            afm_priors_mode="bounded",
        )
        == 4
    )
    assert (
        parameter_count_for_model(
            "mmgm_spheres_single",
            afm_priors_enabled=True,
            afm_priors_mode="bounded",
            afm_sigl_mode="fixed",
        )
        == 3
    )
    assert (
        parameter_count_for_model(
            "mmgm_spheres_single",
            afm_priors_enabled=True,
            afm_priors_mode="fixed",
        )
        == 2
    )
    assert parameter_count_for_model("mg", afm_priors_enabled=False) == 2


def test_hag_window_detects_out_of_window_parameters() -> None:
    constraint = HagWindowConstraint(mode="bounded", min_nm=1.0, max_nm=3.0)

    assert not violates_hag_window([(0.2, 6.0), (0.1, 25.0)], constraint)
    assert violates_hag_window([(0.2, 4.0), (0.1, 25.0)], constraint)
    assert violates_hag_window([(0.2, 6.0), (0.2, 20.0)], constraint)


def test_feasible_initial_population_honors_hag_window() -> None:
    constraint = HagWindowConstraint(mode="bounded", min_nm=1.0, max_nm=3.0)

    population = feasible_initial_population(
        model_name="mmgm_spheres_single",
        n_spectra=2,
        bounds=minimal_bounds(),
        population_count=6,
        hag_window_constraint=constraint,
    )

    assert len(population) == 6
    for unit_values in population:
        parameters = mmgm_single_global_parameters_from_unit_vector(
            unit_values,
            minimal_bounds(),
            n_spectra=2,
        )
        assert not violates_hag_window(parameters, constraint)


def afm_prior_json() -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": {
            "model": "mmgm_single",
            "distribution": "single_lognormal",
            "radius_proxy_name": "mean_radius_nm",
        },
        "strategy": {"name": "test"},
        "bounds_by_time_s": {
            "10": {
                "rave_nm": {"min": 2.0, "max": 4.0, "reference": 3.0},
                "sig_l": {"min": 0.2, "max": 0.4, "reference": 0.3},
                "thickness_nm": {"min": 1.0, "max": 4.0, "reference": 2.0},
            },
            "20": {
                "rave_nm": {"min": 6.0, "max": 8.0, "reference": 7.0},
                "sig_l": {"min": 0.6, "max": 0.8, "reference": 0.7},
                "thickness_nm": {"min": 2.0, "max": 8.0, "reference": 4.0},
            },
        },
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_afm_prior_config_loading(tmp_path: Path) -> None:
    path = tmp_path / "afm_priors.json"
    write_json(path, afm_prior_json())

    config = read_afm_prior_config(path)

    assert config.priors_by_time_s[10].rave_reference_nm == pytest.approx(3.0)
    assert config.priors_by_time_s[20].sig_l_reference == pytest.approx(0.7)
    assert config.priors_by_time_s[10].thickness_reference_nm == pytest.approx(2.0)


def test_afm_prior_config_rejects_bad_schema_version(tmp_path: Path) -> None:
    payload = afm_prior_json()
    payload["schema_version"] = 2
    path = tmp_path / "afm_priors_bad_schema.json"
    write_json(path, payload)

    with pytest.raises(OptimizerError, match="schema_version must be 1"):
        read_afm_prior_config(path)


def test_afm_prior_config_rejects_missing_sig_l_reference(tmp_path: Path) -> None:
    payload = afm_prior_json()
    bounds_by_time = payload["bounds_by_time_s"]
    assert isinstance(bounds_by_time, dict)
    time_entry = bounds_by_time["10"]
    assert isinstance(time_entry, dict)
    sig_l = time_entry["sig_l"]
    assert isinstance(sig_l, dict)
    del sig_l["reference"]
    path = tmp_path / "afm_priors_missing_sigl_reference.json"
    write_json(path, payload)

    with pytest.raises(OptimizerError, match="sig_l.reference"):
        read_afm_prior_config(path)
