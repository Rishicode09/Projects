"""Physics tests.

These assert *physical* properties rather than golden numbers, so they keep
their meaning if the degradation coefficients are recalibrated.
"""

from __future__ import annotations

import numpy as np
import pytest

from pvdefect.physics.cell_model import ModuleSpec, cell_parameters_at_conditions
from pvdefect.physics.degradation import DegradationModel, fit_from_measurements
from pvdefect.physics.energy import simulate_annual_energy
from pvdefect.physics.mismatch import iv_curve, solve_maximum_power_point
from pvdefect.physics.weather import SiteSpec, clear_sky_year, plane_of_array


@pytest.fixture(scope="module")
def module() -> ModuleSpec:
    return ModuleSpec.default()


@pytest.fixture(scope="module")
def poa():
    site = SiteSpec()
    weather = clear_sky_year(site)
    weather.attrs["source"] = "test clear-sky"
    return plane_of_array(site, weather)


def test_healthy_module_is_near_nameplate(module):
    """A 60-cell module with these parameters should land near 300 W at STC."""
    operating_point = solve_maximum_power_point(
        cell_parameters_at_conditions(module, 1000.0, 25.0), module
    )
    assert 250.0 < operating_point.p_mp < 340.0
    assert 25.0 < operating_point.v_mp < 40.0
    assert operating_point.bypassed_substrings == 0


def test_power_decreases_monotonically_with_damage(module):
    """More damage must never produce more power."""
    powers = []
    for inactive_fraction in [0.0, 0.1, 0.2, 0.3, 0.4]:
        scale = np.ones(module.cells_in_series)
        scale[0] = 1.0 - inactive_fraction
        parameters = cell_parameters_at_conditions(
            module, 1000.0, 25.0, photocurrent_scale=scale
        )
        powers.append(solve_maximum_power_point(parameters, module).p_mp)

    assert all(later <= earlier + 1e-6 for earlier, later in zip(powers, powers[1:]))


def test_single_bad_cell_costs_far_more_than_its_area(module):
    """Mismatch amplification: this is the reason for per-cell classification.

    One cell losing 30% of its area is 0.5% of the module's area, but series
    connection forces a much larger power loss.
    """
    healthy = solve_maximum_power_point(
        cell_parameters_at_conditions(module, 1000.0, 25.0), module
    ).p_mp

    scale = np.ones(module.cells_in_series)
    scale[7] = 0.7
    damaged = solve_maximum_power_point(
        cell_parameters_at_conditions(module, 1000.0, 25.0, photocurrent_scale=scale), module
    ).p_mp

    area_fraction_lost = 0.3 / module.cells_in_series   # 0.5%
    power_fraction_lost = 1.0 - damaged / healthy
    assert power_fraction_lost > 10 * area_fraction_lost


def test_bypass_diode_bounds_the_loss(module):
    """A fully dead cell must cost one substring, not the whole module."""
    scale = np.ones(module.cells_in_series)
    scale[0] = 0.01

    operating_point = solve_maximum_power_point(
        cell_parameters_at_conditions(module, 1000.0, 25.0, photocurrent_scale=scale), module
    )
    healthy = solve_maximum_power_point(
        cell_parameters_at_conditions(module, 1000.0, 25.0), module
    ).p_mp

    assert operating_point.bypassed_substrings >= 1
    # Roughly 1/3 lost for a 3-diode module, with headroom for the diode drop.
    assert 0.25 < 1.0 - operating_point.p_mp / healthy < 0.45


def test_series_and_shunt_have_opposite_irradiance_dependence(module):
    """The reason the pipeline simulates hourly instead of scaling one number.

    Series-resistance loss goes as I^2 R, so it hurts most in bright sun.
    Shunt loss is a fixed leakage path, so it hurts most in dim light.
    """
    def loss_at(irradiance: float, **damage) -> float:
        healthy = solve_maximum_power_point(
            cell_parameters_at_conditions(module, irradiance, 25.0), module
        ).p_mp
        damaged = solve_maximum_power_point(
            cell_parameters_at_conditions(module, irradiance, 25.0, **damage), module
        ).p_mp
        return 1.0 - damaged / healthy

    series_bright = loss_at(1000.0, series_resistance_gain=3.0)
    series_dim = loss_at(150.0, series_resistance_gain=3.0)
    assert series_bright > series_dim

    shunt_bright = loss_at(1000.0, shunt_resistance_retention=0.25)
    shunt_dim = loss_at(150.0, shunt_resistance_retention=0.25)
    assert shunt_dim > shunt_bright


def test_iv_curve_is_physically_shaped(module):
    parameters = cell_parameters_at_conditions(module, 1000.0, 25.0)
    current, voltage, power = iv_curve(parameters, module)

    assert np.all(voltage >= 0.0)
    assert np.all(np.diff(voltage) <= 1e-6)          # V falls as I rises
    assert power.max() > 200.0
    # Peak power sits inside the sweep, not at an endpoint.
    assert 0 < int(np.argmax(power)) < len(power) - 1


def test_mild_defects_cost_almost_nothing():
    """Encodes the literature finding that hairline cracks need not lose power.

    If this test starts failing, the degradation model has been recalibrated to
    something more pessimistic — check that against measurement before shipping.
    """
    model = DegradationModel()
    assert model.inactive_area(1 / 3) < 0.03
    assert model.inactive_area(1.0) > 5 * model.inactive_area(1 / 3)


def test_degradation_is_monotone_in_severity():
    model = DegradationModel()
    severities = np.linspace(0.0, 1.0, 25)
    perturbation = model.perturb(severities)

    assert np.all(np.diff(perturbation["photocurrent_scale"]) <= 1e-9)
    assert np.all(np.diff(perturbation["series_resistance_gain"]) >= -1e-9)
    assert np.all(np.diff(perturbation["shunt_resistance_retention"]) <= 1e-9)


def test_uncertainty_scaling_brackets_the_default():
    optimistic = DegradationModel().with_uncertainty(0.5)
    pessimistic = DegradationModel().with_uncertainty(1.5)
    assert optimistic.inactive_area(1.0) < DegradationModel().inactive_area(1.0)
    assert pessimistic.inactive_area(1.0) > DegradationModel().inactive_area(1.0)


def test_annual_energy_is_plausible_and_ordered(poa, module):
    healthy = simulate_annual_energy(np.zeros(60), poa, module)
    assert healthy.annual_energy_loss_fraction == pytest.approx(0.0, abs=1e-6)
    # A 300 W module under a clear-sky German year: hundreds of kWh, not thousands.
    assert 200.0 < healthy.annual_energy_healthy_kwh < 900.0

    severities = np.zeros(60)
    severities[5] = 1.0
    damaged = simulate_annual_energy(severities, poa, module)
    assert damaged.annual_energy_loss_fraction > 0.01
    assert damaged.annual_energy_defective_kwh < damaged.annual_energy_healthy_kwh


def test_more_defective_cells_lose_more_energy(poa, module):
    losses = []
    for count in [0, 1, 3, 8]:
        severities = np.zeros(60)
        severities[:count] = 1.0
        losses.append(simulate_annual_energy(severities, poa, module).annual_energy_loss_kwh)

    assert all(later >= earlier - 1e-6 for earlier, later in zip(losses, losses[1:]))


def test_severity_resampling_handles_wrong_cell_count(poa, module):
    """A partially inspected module should still simulate, with a warning."""
    result = simulate_annual_energy(np.zeros(36), poa, module)
    assert result.annual_energy_healthy_kwh > 0


def test_fit_from_measurements_recovers_a_known_mapping():
    truth = DegradationModel(inactive_area_by_level=(0.0, 0.05, 0.15, 0.40))
    severities = np.array([0.0, 1 / 3, 2 / 3, 1.0, 1 / 3, 1.0, 2 / 3, 0.0])
    measured = 1.0 - truth.inactive_area(severities)

    fitted = fit_from_measurements(severities, measured)
    assert fitted.inactive_area_by_level == pytest.approx(
        truth.inactive_area_by_level, abs=0.02
    )
