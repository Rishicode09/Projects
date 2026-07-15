"""Data drift detection via the Population Stability Index (PSI).

A model trained on last year's fleet quietly degrades when the fleet
changes — new vehicle models, different duty cycles, a sensor firmware
update. PSI compares the distribution of each feature at serving time
against its training distribution:

* PSI < 0.10 — stable
* 0.10–0.25  — moderate shift, worth investigating
* > 0.25     — significant shift, retraining likely needed

These conventional cut-offs come from credit-risk model monitoring and are
encoded in :func:`drift_report` so alerting stays consistent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fleetpulse.config import SENSOR_COLUMNS

_EPS = 1e-6


def population_stability_index(
    expected: np.ndarray, actual: np.ndarray, n_bins: int = 10
) -> float:
    """PSI between a reference sample and a new sample of one feature.

    Bin edges are quantiles of the *expected* (training) distribution, so
    each reference bin holds ~1/n_bins of the data and the statistic is not
    dominated by outliers.
    """
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.unique(np.quantile(expected, quantiles))
    edges[0], edges[-1] = -np.inf, np.inf

    expected_frac = np.histogram(expected, bins=edges)[0] / max(len(expected), 1)
    actual_frac = np.histogram(actual, bins=edges)[0] / max(len(actual), 1)

    expected_frac = np.clip(expected_frac, _EPS, None)
    actual_frac = np.clip(actual_frac, _EPS, None)
    return float(np.sum((actual_frac - expected_frac) * np.log(actual_frac / expected_frac)))


def _severity(psi: float) -> str:
    if psi < 0.10:
        return "stable"
    if psi < 0.25:
        return "moderate_shift"
    return "significant_shift"


def drift_report(reference: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """Per-sensor PSI between a reference window and the current window."""
    rows = []
    for col in SENSOR_COLUMNS:
        psi = population_stability_index(
            reference[col].to_numpy(), current[col].to_numpy()
        )
        rows.append({"feature": col, "psi": round(psi, 4), "severity": _severity(psi)})
    return pd.DataFrame(rows).sort_values("psi", ascending=False).reset_index(drop=True)
