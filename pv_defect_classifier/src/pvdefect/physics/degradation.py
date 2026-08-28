"""Mapping from visual defect severity to single-diode parameter degradation.

This is the weakest link in the whole pipeline and the most interesting part of
the research, so it is isolated in one file with every assumption named.

**The honest framing.** EL imagery shows where charge carriers recombine; it
does not measure power. The literature is emphatic that the relationship is
loose in one specific direction: many cracked cells lose no measurable power
until the crack electrically isolates a region (Köntges et al., IEA-PVPS
T13-01:2014). So a model that maps "crack visible" straight to "power lost"
will systematically over-predict losses. We encode three separate mechanisms
instead, and let the mild classes act mostly through area loss that is near
zero.

**The three mechanisms visible in EL:**

1. *Inactive area* — a region cut off from the busbars contributes no
   photocurrent. Scales the cell's ``I_L`` (photocurrent) directly. This is the
   dominant mechanism for severe defects.
2. *Series resistance increase* — broken fingers force current through longer
   paths in the emitter. Raises ``R_s``, which costs fill factor and gets worse
   at high irradiance (loss goes as I^2 R).
3. *Shunting* — process-induced or crack-induced local shorts. Lowers
   ``R_sh``, which costs the most at *low* irradiance, where the shunt current
   is a larger fraction of the total.

Mechanisms 2 and 3 have opposite irradiance dependence, which is why the annual
energy loss is not a simple scaling of the STC power loss, and why this
pipeline runs an hourly simulation rather than multiplying a single number.

**Calibration status: uncalibrated.** The coefficients below are plausible
values drawn from the ranges in the cited literature, not fitted to paired
EL/flash-test data. Fit them with :func:`fit_from_measurements` before quoting
absolute watt figures. Until then, treat outputs as *relative* rankings.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

# Severity levels of the ELPV annotation, in [0, 1].
_LEVELS = np.array([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0])


@dataclass(frozen=True)
class DegradationModel:
    """Severity -> parameter multipliers.

    Each mechanism is a monotone function of severity, anchored at the four
    annotation levels and interpolated in between (the classifier emits a
    continuous expected severity, not a hard level).

    Attributes
    ----------
    inactive_area_by_level:
        Fraction of cell area electrically disconnected, at each of the four
        severity levels. Note the near-zero value at "mild": a hairline crack
        that has not yet isolated anything costs no current.
    series_resistance_gain_by_level:
        Multiplier on cell ``R_s``. 1.0 = undamaged.
    shunt_resistance_retention_by_level:
        Multiplier on cell ``R_sh``. 1.0 = undamaged; smaller = more shunted.
    area_prior_weight:
        How much to trust the *image-derived* dark-area estimate from
        ``preprocess.cell_prep.estimate_inactive_area_fraction`` relative to
        the level-table value. 0 = ignore the image, 1 = trust it fully.
    """

    inactive_area_by_level: tuple[float, ...] = (0.0, 0.01, 0.10, 0.30)
    series_resistance_gain_by_level: tuple[float, ...] = (1.0, 1.10, 1.60, 3.00)
    shunt_resistance_retention_by_level: tuple[float, ...] = (1.0, 0.90, 0.55, 0.25)
    area_prior_weight: float = 0.35

    def _interpolate(self, table: tuple[float, ...], severity: np.ndarray) -> np.ndarray:
        return np.interp(np.clip(severity, 0.0, 1.0), _LEVELS, np.asarray(table, dtype=float))

    def inactive_area(
        self,
        severity: np.ndarray | float,
        image_area_estimate: np.ndarray | float | None = None,
    ) -> np.ndarray:
        """Fraction of the cell contributing no photocurrent.

        When an image-derived estimate is supplied we blend the two: the
        classifier knows *whether* a defect is serious, the dark-area measure
        knows *how much* of the cell it covers, and neither alone is reliable.
        """
        severity = np.asarray(severity, dtype=float)
        base = self._interpolate(self.inactive_area_by_level, severity)

        if image_area_estimate is None:
            return base

        measured = np.clip(np.asarray(image_area_estimate, dtype=float), 0.0, 1.0)
        # The image estimate only earns weight where the classifier already
        # suspects a defect; otherwise dark busbars in a healthy cell would
        # invent losses that are not there.
        weight = self.area_prior_weight * np.clip(severity / max(_LEVELS[1], 1e-6), 0.0, 1.0)
        return np.clip((1.0 - weight) * base + weight * measured, 0.0, 0.95)

    def series_resistance_gain(self, severity: np.ndarray | float) -> np.ndarray:
        return self._interpolate(self.series_resistance_gain_by_level, np.asarray(severity, float))

    def shunt_resistance_retention(self, severity: np.ndarray | float) -> np.ndarray:
        return self._interpolate(
            self.shunt_resistance_retention_by_level, np.asarray(severity, float)
        )

    def perturb(
        self,
        severity: np.ndarray | float,
        image_area_estimate: np.ndarray | float | None = None,
    ) -> dict[str, np.ndarray]:
        """All three multipliers at once, as arrays broadcast over cells."""
        severity = np.atleast_1d(np.asarray(severity, dtype=float))
        area = self.inactive_area(severity, image_area_estimate)
        return {
            "photocurrent_scale": 1.0 - area,
            "series_resistance_gain": self.series_resistance_gain(severity),
            "shunt_resistance_retention": self.shunt_resistance_retention(severity),
            "inactive_area": area,
        }

    def with_uncertainty(self, factor: float) -> "DegradationModel":
        """A pessimistic (``factor > 1``) or optimistic (``< 1``) variant.

        Use this to bracket results: run the whole energy simulation at 0.5 and
        1.5 and report the span. Given the calibration status above, that span
        is a more honest deliverable than any single number.
        """
        factor = float(max(factor, 0.0))
        return replace(
            self,
            inactive_area_by_level=tuple(
                float(np.clip(v * factor, 0.0, 0.95)) for v in self.inactive_area_by_level
            ),
            series_resistance_gain_by_level=tuple(
                float(max(1.0, 1.0 + (v - 1.0) * factor))
                for v in self.series_resistance_gain_by_level
            ),
            shunt_resistance_retention_by_level=tuple(
                float(np.clip(1.0 - (1.0 - v) * factor, 0.02, 1.0))
                for v in self.shunt_resistance_retention_by_level
            ),
        )


def fit_from_measurements(
    severities: np.ndarray,
    measured_power_ratio: np.ndarray,
    base_model: DegradationModel | None = None,
) -> DegradationModel:
    """Fit the inactive-area table to paired EL / flash-test data.

    Parameters
    ----------
    severities:
        Predicted (or annotated) severity per *module*, aggregated as the mean
        over its cells.
    measured_power_ratio:
        Measured ``P_mp,defective / P_mp,nominal`` for the same modules, from a
        flash test or IV curve tracer.

    This is the function that turns the pipeline from a ranking tool into a
    measurement tool. It needs perhaps 30-50 paired modules to be meaningful,
    which is the natural next experiment for this project.
    """
    from scipy.optimize import least_squares

    base = base_model or DegradationModel()
    severities = np.asarray(severities, dtype=float)
    measured_power_ratio = np.asarray(measured_power_ratio, dtype=float)

    if severities.shape != measured_power_ratio.shape:
        raise ValueError("severities and measured_power_ratio must have the same shape")
    if severities.size < 4:
        raise ValueError("need at least 4 paired observations to fit 3 free parameters")

    def residuals(params: np.ndarray) -> np.ndarray:
        # Fit the three non-trivial anchor points; level 0 stays pinned at 0.
        table = (0.0, *np.clip(np.sort(params), 0.0, 0.95))
        candidate = replace(base, inactive_area_by_level=table)
        # First-order approximation: power ratio tracks active area. Adequate
        # as a fitting target because the R_s/R_sh terms are second-order at
        # STC, which is where flash tests are performed.
        predicted = 1.0 - candidate.inactive_area(severities)
        return predicted - measured_power_ratio

    initial = np.array(base.inactive_area_by_level[1:], dtype=float)
    result = least_squares(residuals, initial, bounds=(0.0, 0.95))
    fitted = (0.0, *np.clip(np.sort(result.x), 0.0, 0.95))
    return replace(base, inactive_area_by_level=fitted)
