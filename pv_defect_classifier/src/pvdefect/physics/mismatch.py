"""Series-string mismatch and maximum power point solving.

The single most important fact this module encodes: **a module's power is not
the average of its cells, it is limited by its worst cell.** Sixty cells in
series all carry the same current, so one cell with 30% of its area
disconnected drags the entire string toward its own reduced photocurrent. This
is why a per-cell classifier is worth building at all — a module-level "percent
of cells defective" score cannot express it.

Bypass diodes are what stop this from being catastrophic. Each substring
(typically 20 cells) has a diode across it; when the substring's voltage goes
negative enough, the diode conducts and the substring is shorted out of the
circuit. The module then loses that substring's contribution but keeps the rest
— so the loss curve against severity has a distinct knee where bypassing kicks
in, which the simulation reproduces rather than assumes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize_scalar

from .cell_model import (
    BYPASS_DIODE_FORWARD_VOLTAGE,
    CellParameters,
    ModuleSpec,
    cell_voltage_at_current,
    module_short_circuit_current,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OperatingPoint:
    """A solved maximum power point for one module."""

    p_mp: float
    v_mp: float
    i_mp: float
    bypassed_substrings: int
    substring_voltages: np.ndarray


def module_voltage_at_current(
    parameters: CellParameters,
    current: float,
    cells_per_substring: int,
    bypass_voltage: float = BYPASS_DIODE_FORWARD_VOLTAGE,
) -> tuple[float, np.ndarray]:
    """Module terminal voltage at a given string current.

    Returns ``(total_voltage, substring_voltages)``. Each substring is the sum
    of its cell voltages, clamped from below at ``-bypass_voltage`` because the
    diode conducts before the substring can go more negative than that.
    """
    cell_voltages = cell_voltage_at_current(parameters, current)

    n_cells = len(cell_voltages)
    n_substrings = max(1, int(np.ceil(n_cells / cells_per_substring)))
    # array_split handles a module whose cell count is not an exact multiple.
    groups = np.array_split(cell_voltages, n_substrings)

    substring_voltages = np.array(
        [max(float(np.sum(group)), -bypass_voltage) for group in groups],
        dtype=float,
    )
    return float(np.sum(substring_voltages)), substring_voltages


def solve_maximum_power_point(
    parameters: CellParameters,
    module: ModuleSpec,
    coarse_points: int = 60,
) -> OperatingPoint:
    """Find the MPP of a module with per-cell heterogeneous parameters.

    There is no closed form once cells differ, so this is a two-stage numeric
    solve: a coarse sweep over string current to bracket the peak, then Brent
    refinement inside that bracket.

    The coarse sweep is not optional. Mismatched strings with bypass diodes have
    a genuinely **multi-modal** P-V curve — one local peak per bypass
    configuration — and a bare optimiser started from a single guess will
    happily return the wrong one. The sweep picks the right basin; Brent only
    polishes it.
    """
    i_max = module_short_circuit_current(parameters)
    if not np.isfinite(i_max) or i_max <= 1e-9:
        zeros = np.zeros(module.bypass_diode_count)
        return OperatingPoint(0.0, 0.0, 0.0, 0, zeros)

    cells_per_substring = module.cells_per_substring

    def negative_power(current: float) -> float:
        voltage, _ = module_voltage_at_current(parameters, current, cells_per_substring)
        return -max(voltage, 0.0) * current

    # Slightly past i_max so we capture the case where bypassing lets the
    # module run above its weakest cell's photocurrent.
    currents = np.linspace(1e-6, i_max * 1.05, coarse_points)
    powers = np.array([-negative_power(i) for i in currents])

    best = int(np.argmax(powers))
    lower = currents[max(best - 1, 0)]
    upper = currents[min(best + 1, len(currents) - 1)]

    if upper > lower:
        result = minimize_scalar(
            negative_power, bounds=(lower, upper), method="bounded",
            options={"xatol": 1e-5},
        )
        i_mp = float(result.x) if result.success else float(currents[best])
    else:
        i_mp = float(currents[best])

    v_mp, substring_voltages = module_voltage_at_current(parameters, i_mp, cells_per_substring)
    v_mp = max(v_mp, 0.0)

    # A substring sitting at the diode clamp is being bypassed.
    bypassed = int(np.sum(substring_voltages <= -BYPASS_DIODE_FORWARD_VOLTAGE + 1e-6))

    return OperatingPoint(
        p_mp=v_mp * i_mp,
        v_mp=v_mp,
        i_mp=i_mp,
        bypassed_substrings=bypassed,
        substring_voltages=substring_voltages,
    )


def iv_curve(
    parameters: CellParameters,
    module: ModuleSpec,
    points: int = 120,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Full I-V and P-V curves, for plotting in the Streamlit app.

    Returns ``(current, voltage, power)``. Worth looking at directly: the
    staircase kinks in a mismatched curve are the bypass diodes switching, and
    seeing them is how you sanity-check that the topology is right.
    """
    i_max = module_short_circuit_current(parameters)
    currents = np.linspace(1e-6, max(i_max * 1.05, 1e-6), points)

    voltages = np.array(
        [module_voltage_at_current(parameters, i, module.cells_per_substring)[0] for i in currents]
    )
    voltages = np.maximum(voltages, 0.0)
    return currents, voltages, voltages * currents
