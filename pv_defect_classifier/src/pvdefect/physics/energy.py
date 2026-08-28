"""Annual energy loss from per-cell defect severity.

Naively this is 8,760 hourly MPP solves, each of which is a 60-cell Lambert-W
evaluation inside a bounded optimisation — a few minutes per module, which is
far too slow for an interactive app and unusable for a plant with thousands of
modules.

The fix relies on a property of the electrical model: module power depends on
the weather *only* through two scalars, effective irradiance and cell
temperature. So we solve the module on a modest 2-D grid over those two
variables, build an interpolator over the resulting loss surface, and evaluate
that at each of the 8,760 hours. Two hundred-odd exact solves replace 17,520,
and because the loss surface is smooth in both arguments the interpolation
error is far below the uncertainty in the degradation model itself.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from .cell_model import ModuleSpec, cell_parameters_at_conditions
from .degradation import DegradationModel
from .mismatch import solve_maximum_power_point

logger = logging.getLogger(__name__)

# Grid bounds. The irradiance axis is denser at the bottom because that is
# where the loss surface bends most sharply (shunt-dominated regime) and where
# a temperate-climate TMY spends most of its daylight hours.
DEFAULT_IRRADIANCE_GRID = np.array(
    [20.0, 50.0, 100.0, 150.0, 200.0, 300.0, 400.0, 550.0, 700.0, 850.0, 1000.0, 1200.0]
)
DEFAULT_TEMPERATURE_GRID = np.array([-10.0, 5.0, 15.0, 25.0, 40.0, 55.0, 70.0])

# Below this irradiance the inverter is off; including these hours would put
# 0/0 into the loss ratio and add nothing to annual energy.
MINIMUM_OPERATING_IRRADIANCE = 20.0


@dataclass
class EnergyResult:
    """Annual energy comparison between a healthy and a defective module."""

    annual_energy_healthy_kwh: float
    annual_energy_defective_kwh: float
    stc_power_healthy_w: float
    stc_power_defective_w: float
    hourly: pd.DataFrame
    weather_source: str

    @property
    def annual_energy_loss_kwh(self) -> float:
        return self.annual_energy_healthy_kwh - self.annual_energy_defective_kwh

    @property
    def annual_energy_loss_fraction(self) -> float:
        if self.annual_energy_healthy_kwh <= 0:
            return 0.0
        return self.annual_energy_loss_kwh / self.annual_energy_healthy_kwh

    @property
    def stc_power_loss_fraction(self) -> float:
        if self.stc_power_healthy_w <= 0:
            return 0.0
        return 1.0 - self.stc_power_defective_w / self.stc_power_healthy_w

    def summary(self) -> str:
        return (
            f"STC power loss:      {self.stc_power_loss_fraction:6.2%}\n"
            f"Annual energy loss:  {self.annual_energy_loss_fraction:6.2%} "
            f"({self.annual_energy_loss_kwh:.1f} kWh/module/year)\n"
            f"Healthy yield:       {self.annual_energy_healthy_kwh:.1f} kWh/module/year\n"
            f"Weather source:      {self.weather_source}"
        )


def build_power_surface(
    module: ModuleSpec,
    photocurrent_scale: np.ndarray,
    series_resistance_gain: np.ndarray,
    shunt_resistance_retention: np.ndarray,
    irradiance_grid: np.ndarray = DEFAULT_IRRADIANCE_GRID,
    temperature_grid: np.ndarray = DEFAULT_TEMPERATURE_GRID,
) -> RegularGridInterpolator:
    """Exact MPP solve on a (irradiance, temperature) grid -> interpolator.

    Linear interpolation is used rather than cubic on purpose: the surface has
    a genuine kink where a bypass diode starts conducting, and a cubic spline
    would overshoot around it and can produce a non-monotone loss curve.
    """
    power = np.empty((len(irradiance_grid), len(temperature_grid)), dtype=float)

    for i, irradiance in enumerate(irradiance_grid):
        for j, temperature in enumerate(temperature_grid):
            parameters = cell_parameters_at_conditions(
                module,
                effective_irradiance=float(irradiance),
                cell_temperature=float(temperature),
                photocurrent_scale=photocurrent_scale,
                series_resistance_gain=series_resistance_gain,
                shunt_resistance_retention=shunt_resistance_retention,
            )
            power[i, j] = solve_maximum_power_point(parameters, module).p_mp

    return RegularGridInterpolator(
        (irradiance_grid, temperature_grid),
        power,
        method="linear",
        bounds_error=False,
        fill_value=None,  # linear extrapolation beyond the grid edges
    )


def simulate_annual_energy(
    cell_severities: np.ndarray,
    poa: pd.DataFrame,
    module: ModuleSpec | None = None,
    degradation: DegradationModel | None = None,
    image_area_estimates: np.ndarray | None = None,
) -> EnergyResult:
    """Full chain: per-cell severity -> annual kWh lost.

    Parameters
    ----------
    cell_severities:
        One value in [0, 1] per cell, normally the classifier's expected
        severity. Length should match ``module.cells_in_series``; shorter or
        longer arrays are resampled with a warning so that a 60-cell model can
        still be driven by a partially inspected module.
    poa:
        Output of :func:`weather.plane_of_array`.
    image_area_estimates:
        Optional per-cell dark-area fractions from
        ``preprocess.cell_prep.estimate_inactive_area_fraction``.
    """
    module = module or ModuleSpec.default()
    degradation = degradation or DegradationModel()

    severities = np.asarray(cell_severities, dtype=float).ravel()
    n_expected = module.cells_in_series
    if len(severities) != n_expected:
        logger.warning(
            "Got %d severities for a %d-cell module; resampling.", len(severities), n_expected
        )
        if len(severities) == 0:
            severities = np.zeros(n_expected)
        else:
            positions = np.linspace(0, len(severities) - 1, n_expected)
            severities = np.interp(positions, np.arange(len(severities)), severities)
            if image_area_estimates is not None:
                areas = np.asarray(image_area_estimates, dtype=float).ravel()
                image_area_estimates = np.interp(
                    np.linspace(0, len(areas) - 1, n_expected), np.arange(len(areas)), areas
                )

    perturbation = degradation.perturb(severities, image_area_estimates)
    healthy_ones = np.ones(n_expected)

    healthy_surface = build_power_surface(module, healthy_ones, healthy_ones, healthy_ones)
    defective_surface = build_power_surface(
        module,
        perturbation["photocurrent_scale"],
        perturbation["series_resistance_gain"],
        perturbation["shunt_resistance_retention"],
    )

    operating = poa[poa["effective_irradiance"] >= MINIMUM_OPERATING_IRRADIANCE]
    if operating.empty:
        raise ValueError("No operating hours in the supplied weather; check the site definition.")

    query = np.column_stack(
        [
            operating["effective_irradiance"].to_numpy(),
            operating["cell_temperature"].to_numpy(),
        ]
    )
    power_healthy = np.clip(healthy_surface(query), 0.0, None)
    power_defective = np.clip(defective_surface(query), 0.0, None)
    # Damage cannot create power; guard against interpolation crossing over.
    power_defective = np.minimum(power_defective, power_healthy)

    # Hourly data at 1 h resolution: watts and watt-hours are numerically equal.
    hours = _mean_interval_hours(operating.index)
    energy_healthy_kwh = float(power_healthy.sum() * hours / 1000.0)
    energy_defective_kwh = float(power_defective.sum() * hours / 1000.0)

    hourly = pd.DataFrame(
        {
            "effective_irradiance": operating["effective_irradiance"],
            "cell_temperature": operating["cell_temperature"],
            "power_healthy_w": power_healthy,
            "power_defective_w": power_defective,
            "power_loss_w": power_healthy - power_defective,
        },
        index=operating.index,
    )

    stc_healthy = float(healthy_surface([[1000.0, 25.0]])[0])
    stc_defective = float(defective_surface([[1000.0, 25.0]])[0])

    return EnergyResult(
        annual_energy_healthy_kwh=energy_healthy_kwh,
        annual_energy_defective_kwh=energy_defective_kwh,
        stc_power_healthy_w=stc_healthy,
        stc_power_defective_w=min(stc_defective, stc_healthy),
        hourly=hourly,
        weather_source=str(poa.attrs.get("source", "unknown")),
    )


def _mean_interval_hours(index: pd.DatetimeIndex) -> float:
    """Hours per sample, so sub-hourly weather integrates correctly.

    Uses ``total_seconds`` rather than viewing the index as int64: pandas
    datetime indexes carry a unit (ns, us, s) that varies with how they were
    constructed, and a hard-coded nanosecond divisor silently scales the whole
    annual energy figure by a factor of 1000 when the index happens to be
    microsecond-resolution.
    """
    if len(index) < 2:
        return 1.0
    deltas = pd.Series(index).diff().dropna().dt.total_seconds() / 3600.0
    median = float(deltas.median())
    return median if np.isfinite(median) and median > 0 else 1.0


def revenue_impact(
    result: EnergyResult,
    modules_affected: int = 1,
    tariff_per_kwh: float = 0.12,
    years: int = 10,
) -> dict[str, float]:
    """Translate energy loss into money, for maintenance prioritisation.

    Deliberately simple: no discounting, no degradation trend, no downtime
    cost. The purpose is to rank which strings to send a technician to, and for
    that a first-order figure is enough. Do not put this in a financial model.
    """
    annual_loss_kwh = result.annual_energy_loss_kwh * modules_affected
    return {
        "annual_energy_loss_kwh": annual_loss_kwh,
        "annual_revenue_loss": annual_loss_kwh * tariff_per_kwh,
        "cumulative_revenue_loss": annual_loss_kwh * tariff_per_kwh * years,
        "modules_affected": float(modules_affected),
    }
