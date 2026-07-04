"""
Tests for cleaning.py — run with:  python -m pytest

HOW PYTEST WORKS (60-second version):
- It finds files named test_*.py and runs every function named test_*.
- Inside, `assert <condition>` passes silently or fails loudly.
- Each test should check ONE behaviour and have a name that reads like
  a sentence, so a failure message tells you WHAT broke without
  opening the file.

WHY TESTS AT ALL? Not to prove today's code works — you just ran it,
you know it works. Tests exist so that NEXT MONTH's change can't
silently break TODAY's behaviour. They are a tripwire for future-you.
"""

import numpy as np
import pandas as pd

from energy_insights.cleaning import clean_data, detect_outliers_iqr
from energy_insights.data_generator import generate_energy_data


def make_small_dataset() -> pd.DataFrame:
    """Helper: 30 days of data, seeded so every test run is identical.

    Tests use SMALL data (30 days, not 365) because a test suite you
    have to wait for is a test suite you stop running.
    """
    return generate_energy_data(days=30, seed=123)


def test_detect_outliers_flags_obvious_spike():
    # A hand-built series where WE know the answer: ten 1.0s and one 100.
    # Testing against hand-built cases beats testing against random data —
    # when it fails, you can reason about why.
    series = pd.Series([1.0] * 10 + [100.0])
    mask = detect_outliers_iqr(series)
    assert bool(mask.iloc[-1]) is True      # the spike IS flagged
    assert int(mask.sum()) == 1             # and NOTHING else is


def test_clean_data_removes_all_nans():
    df = make_small_dataset()
    clean_df, _ = clean_data(df)
    # After cleaning there must be zero missing values, full stop.
    assert clean_df["consumption_kwh"].isna().sum() == 0


def test_clean_data_does_not_mutate_input():
    # This enforces the "no side effects" promise from cleaning.py's
    # docstring. If someone later "optimizes" away the .copy(),
    # this test catches them.
    df = make_small_dataset()
    nans_before = df["consumption_kwh"].isna().sum()
    clean_data(df)
    assert df["consumption_kwh"].isna().sum() == nans_before


def test_clean_data_reduces_extreme_values():
    df = make_small_dataset()
    clean_df, report = clean_data(df)
    # Raw data contains 10-30x spikes; clean data must not.
    assert clean_df["consumption_kwh"].max() < df["consumption_kwh"].max()
    assert report["outliers_flagged"] > 0   # and the audit trail says why


def test_report_is_arithmetically_consistent():
    df = make_small_dataset()
    _, report = clean_data(df)
    assert report["rows_out"] == report["rows_in"] - report["rows_dropped"]


# 🔧 EXERCISES FOR YOU:
# 1. EASY   — Break the code on purpose: in cleaning.py, change
#             `out = df.copy()` to `out = df`. Run pytest. Which test
#             fails, and does its NAME alone tell you what went wrong?
#             Revert afterwards.
# 2. MEDIUM — Write test_all_clean_values_positive. Then make it fail:
#             can you construct raw data where interpolation produces a
#             value <= 0? If you genuinely can't, write down WHY not.
# 3. HARD   — Write a test for the exercise-3 function from cleaning.py
#             BEFORE implementing it (the test fails first, then you
#             code until it passes). Congratulations — that's TDD,
#             test-driven development, and it's a phrase worth saying
#             in interviews only if you've actually done it. Now you have.
