"""Single-diode cell parameters, derived from module-level datasheet values.

pvlib's parameter databases are module-level. Because we need *per-cell*
mismatch, we push the module parameters down to one cell using the series
relationships:

    I_L, I_o      identical (cells in series carry the same current)
    R_s(cell)   = R_s(module)  / N_s
    R_sh(cell)  = R_sh(module) / N_s
    a_ref(cell) = a_ref(module) / N_s      (a_ref = n * N_s * k * T / q)

That last one matters: ``a_ref`` in pvlib's De Soto convention already contains
the cell count, so forgetting the division inflates every voltage by ~60x.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from pvlib import pvsystem

logger = logging.getLogger(__name__)

# A representative 60-cell mono-Si module in the CEC/De Soto convention.
# These are reference-condition (STC) values for a ~300 W module; they are
# stand-ins so the repo runs offline. Swap in the real module under test via
# `ModuleSpec.from_cec_name` when you have network access to the SAM database.
DEFAULT_MODULE = {
    "name": "Generic 60-cell mono-Si (~300 W)",
    "cells_in_series": 60,
    "bypass_diode_count": 3,
    "alpha_sc": 0.0045,       # A/K, short-circuit current temperature coeff.
    "a_ref": 1.6,             # V, modified ideality factor at reference
    "I_L_ref": 9.8,           # A, light current at 1000 W/m^2, 25 C
    "I_o_ref": 2.2e-10,       # A, dark saturation current
    "R_sh_ref": 450.0,        # ohm, shunt resistance at reference
    "R_s": 0.32,              # ohm, series resistance
}

# Forward voltage of a conducting bypass diode. Schottky diodes used in
# junction boxes sit around 0.4-0.5 V at operating current.
BYPASS_DIODE_FORWARD_VOLTAGE = 0.5


@dataclass(frozen=True)
class ModuleSpec:
    """Module-level single-diode parameters plus string topology."""

    name: str
    cells_in_series: int
    bypass_diode_count: int
    alpha_sc: float
    a_ref: float
    I_L_ref: float
    I_o_ref: float
    R_sh_ref: float
    R_s: float

    @classmethod
    def default(cls) -> "ModuleSpec":
        return cls(**DEFAULT_MODULE)

    @classmethod
    def from_cec_name(cls, name: str, cells_in_series: int | None = None) -> "ModuleSpec":
        """Look a module up in the SAM CEC database (requires network on first use)."""
        database = pvsystem.retrieve_sam("CECMod")
        if name not in database.columns:
            matches = [c for c in database.columns if name.lower() in c.lower()][:5]
            raise KeyError(f"{name!r} not in CEC database. Close matches: {matches}")

        entry = database[name]
        n_cells = int(cells_in_series or entry.get("N_s", 60))
        return cls(
            name=name,
            cells_in_series=n_cells,
            bypass_diode_count=max(1, n_cells // 20),
            alpha_sc=float(entry["alpha_sc"]),
            a_ref=float(entry["a_ref"]),
            I_L_ref=float(entry["I_L_ref"]),
            I_o_ref=float(entry["I_o_ref"]),
            R_sh_ref=float(entry["R_sh_ref"]),
            R_s=float(entry["R_s"]),
        )

    @property
    def cells_per_substring(self) -> int:
        return max(1, self.cells_in_series // max(1, self.bypass_diode_count))


@dataclass
class CellParameters:
    """Per-cell De Soto parameters at operating conditions.

    Every field is an array of length ``n_cells`` so that a whole module is one
    vectorised object.
    """

    photocurrent: np.ndarray
    saturation_current: np.ndarray
    resistance_series: np.ndarray
    resistance_shunt: np.ndarray
    nNsVth: np.ndarray

    def __len__(self) -> int:
        return len(self.photocurrent)


def cell_parameters_at_conditions(
    module: ModuleSpec,
    effective_irradiance: float,
    cell_temperature: float,
    n_cells: int | None = None,
    photocurrent_scale: np.ndarray | float = 1.0,
    series_resistance_gain: np.ndarray | float = 1.0,
    shunt_resistance_retention: np.ndarray | float = 1.0,
) -> CellParameters:
    """Translate module reference parameters to per-cell operating parameters.

    The degradation multipliers are applied *after* the De Soto translation so
    that they represent physical damage rather than a change in the
    temperature/irradiance response.

    One subtlety in how ``shunt_resistance_retention`` is applied. De Soto
    scales ``R_sh`` inversely with irradiance, so the *healthy* shunt path
    always draws the same fraction of the photocurrent and a plain multiplier
    on ``R_sh`` produces a relative loss that is identical at 100 and at
    1000 W/m^2. That is wrong for damage: a crack-induced shunt is a physical
    resistor that does not know what the sun is doing. So we interpret the
    retention factor as "the shunt resistance you would measure at STC", turn
    it into a *fixed* parallel conductance, and add it to the irradiance-scaled
    healthy conductance. The result is the expected behaviour — shunts cost
    proportionally more at low light, where there is less photocurrent to lose.
    """
    n_cells = int(n_cells or module.cells_in_series)

    # De Soto translation at the module level.
    photocurrent, saturation_current, r_s_module, r_sh_module, nNsVth_module = (
        pvsystem.calcparams_desoto(
            effective_irradiance=max(float(effective_irradiance), 1e-6),
            temp_cell=float(cell_temperature),
            alpha_sc=module.alpha_sc,
            a_ref=module.a_ref,
            I_L_ref=module.I_L_ref,
            I_o_ref=module.I_o_ref,
            R_sh_ref=module.R_sh_ref,
            R_s=module.R_s,
        )
    )

    # Push down to a single cell.
    ones = np.ones(n_cells, dtype=float)
    per_cell_r_s = float(r_s_module) / module.cells_in_series
    per_cell_r_sh = float(r_sh_module) / module.cells_in_series
    per_cell_nNsVth = float(nNsVth_module) / module.cells_in_series

    # Damage shunt as a fixed resistor, calibrated so that the requested
    # retention factor is exactly what you would measure at STC.
    retention = np.clip(np.asarray(shunt_resistance_retention, dtype=float) * ones, 1e-3, 1.0)
    r_sh_cell_stc = module.R_sh_ref / module.cells_in_series
    # G_defect = (1/retention - 1) / R_sh(STC); zero when retention == 1.
    defect_conductance = (1.0 / retention - 1.0) / r_sh_cell_stc
    total_conductance = 1.0 / max(per_cell_r_sh, 1e-9) + defect_conductance

    return CellParameters(
        photocurrent=float(photocurrent) * ones * np.asarray(photocurrent_scale, dtype=float),
        saturation_current=float(saturation_current) * ones,
        resistance_series=per_cell_r_s * ones * np.asarray(series_resistance_gain, dtype=float),
        resistance_shunt=np.maximum(1.0 / total_conductance, 1e-3),
        nNsVth=per_cell_nNsVth * ones,
    )


def cell_voltage_at_current(parameters: CellParameters, current: float) -> np.ndarray:
    """Solve the single-diode equation for V given I, per cell.

    pvlib's Lambert-W inversion is exact for the forward branch. Beyond a
    cell's photocurrent it continues onto the reverse branch, where the ideal
    single-diode model has no avalanche term and voltage plunges. That is
    physically wrong in isolation but harmless here: the bypass diode in
    :mod:`mismatch` clamps the substring long before those voltages matter, and
    modelling avalanche breakdown properly (Bishop's term) would add three more
    uncalibrated parameters for no change in the MPP result.
    """
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        voltage = pvsystem.v_from_i(
            current=float(current),
            photocurrent=parameters.photocurrent,
            saturation_current=parameters.saturation_current,
            resistance_series=parameters.resistance_series,
            resistance_shunt=parameters.resistance_shunt,
            nNsVth=parameters.nNsVth,
            method="lambertw",
        )

    voltage = np.asarray(voltage, dtype=float)
    # A cell driven far past its photocurrent yields NaN from the Lambert-W
    # branch; treat it as deeply reverse biased so the bypass diode takes over.
    return np.nan_to_num(voltage, nan=-50.0, neginf=-50.0, posinf=0.0)


def module_short_circuit_current(parameters: CellParameters) -> float:
    """Largest current the *weakest* cell can supply, i.e. the string ceiling.

    Above this the module can only operate with bypass diodes conducting, so it
    is the natural upper bound for an MPP sweep.
    """
    return float(np.max(parameters.photocurrent))
