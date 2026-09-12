"""Tests for the plain-English presentation layer.

These check the properties that make the report trustworthy to a beginner:
it never contradicts itself, it never states a number the reader cannot
reconcile, and it always ends with a clear instruction.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from pvdefect.report import (
    bar,
    cell_verdict,
    days_switched_off,
    glossary,
    overall_verdict,
    plain_model_report,
    plain_module_report,
)


@dataclass
class FakeResult:
    """Stand-in for EnergyResult, so these tests need no physics solve."""

    annual_energy_healthy_kwh: float
    annual_energy_defective_kwh: float

    @property
    def annual_energy_loss_kwh(self) -> float:
        return self.annual_energy_healthy_kwh - self.annual_energy_defective_kwh

    @property
    def annual_energy_loss_fraction(self) -> float:
        if self.annual_energy_healthy_kwh <= 0:
            return 0.0
        return self.annual_energy_loss_kwh / self.annual_energy_healthy_kwh


def names_for(n: int) -> list[str]:
    return [f"r{i // 10}c{i % 10}" for i in range(n)]


# ------------------------------------------------------------- small pieces

def test_cell_verdict_escalates_with_probability():
    words = [cell_verdict(p) for p in (0.05, 0.35, 0.65, 0.95)]
    assert words == [
        "looks fine",
        "maybe cracked",
        "probably cracked",
        "almost certainly cracked",
    ]


def test_bar_is_fixed_width_and_proportional():
    assert len(bar(0.0)) == len(bar(0.5)) == len(bar(1.0)) == 10
    assert bar(0.0).count("#") == 0
    assert bar(1.0).count("#") == 10
    assert bar(0.5).count("#") == 5


def test_bar_clamps_out_of_range_input():
    assert bar(-1.0).count("#") == 0
    assert bar(5.0).count("#") == 10


def test_days_switched_off_matches_the_percentage():
    """The anchor must be the same fact, not a new estimate."""
    assert days_switched_off(0.0) == 0
    assert days_switched_off(1.0) == 365
    assert days_switched_off(0.20) == 73


@pytest.mark.parametrize(
    "loss, cracked, expected",
    [
        (0.0, 0, "HEALTHY"),
        (0.01, 2, "MOSTLY FINE"),
        (0.05, 3, "WORTH WATCHING"),
        (0.30, 5, "NEEDS ATTENTION"),
    ],
)
def test_verdict_bands(loss, cracked, expected):
    headline, advice = overall_verdict(loss, cracked)
    assert headline == expected
    assert advice.strip(), "every verdict must come with an instruction"


# ----------------------------------------------------------- module report

def test_healthy_panel_does_not_print_a_table_of_zeros():
    """A cost breakdown full of zeros reads as a broken program, not good news."""
    result = FakeResult(550.0, 549.9)
    text = plain_module_report(result, np.zeros(60), names_for(60))

    assert "HEALTHY" in text
    assert "Essentially nothing." in text
    assert "0% less electricity" not in text
    assert "So you lose" not in text


def test_damaged_panel_numbers_reconcile():
    """healthy - actual = lost, as printed. A reader will check this."""
    result = FakeResult(550.0, 440.0)
    text = plain_module_report(result, np.full(60, 0.9), names_for(60))

    assert "550 kWh" in text
    assert "440 kWh" in text
    assert "110 kWh" in text
    assert "20% less electricity" in text
    assert "73 days" in text          # 20% of 365


def test_money_for_one_panel_and_many_do_not_look_contradictory():
    """One panel at "0" beside 200 panels at "7" reads as a bug."""
    result = FakeResult(550.0, 545.0)      # ~0.9% loss, small money
    text = plain_module_report(
        result, np.full(60, 0.9), names_for(60), modules_affected=200, tariff=0.12
    )

    money_lines = [ln for ln in text.splitlines() if "per year" in ln]
    assert money_lines
    # The single-panel figure must not render as a bare zero while the fleet
    # figure is non-zero.
    single = [ln for ln in money_lines if "This one panel" in ln]
    assert single and " 0 per year" not in single[0]


def test_currency_symbol_is_used_when_given():
    result = FakeResult(550.0, 440.0)
    text = plain_module_report(result, np.full(60, 0.9), names_for(60), currency="$")
    assert "$" in text


def test_untrained_model_is_flagged_to_the_reader():
    result = FakeResult(550.0, 549.0)
    text = plain_module_report(result, np.zeros(60), names_for(60), used_model=False)
    assert "no trained model" in text.lower()


def test_synthetic_weather_is_flagged_differently_from_real():
    result = FakeResult(550.0, 440.0)
    fake = plain_module_report(result, np.full(60, 0.9), names_for(60),
                               synthetic_weather=True)
    real = plain_module_report(result, np.full(60, 0.9), names_for(60),
                               synthetic_weather=False)
    assert "made-up" in fake
    assert "made-up" not in real


def test_worst_cells_are_listed_worst_first():
    result = FakeResult(550.0, 440.0)
    probabilities = np.zeros(60)
    probabilities[5] = 0.99
    probabilities[9] = 0.80
    probabilities[1] = 0.60

    text = plain_module_report(result, probabilities, names_for(60))
    section = text.split("THE WORST CELLS")[1]
    assert section.index("r0c5") < section.index("r0c9") < section.index("r0c1")


def test_report_always_carries_an_uncertainty_warning():
    for actual in (549.9, 500.0, 100.0):
        text = plain_module_report(FakeResult(550.0, actual), np.zeros(60), names_for(60))
        assert "not as an exact measurement" in text


def test_report_avoids_unexplained_jargon():
    """The whole point is that a beginner can read it without a glossary."""
    text = plain_module_report(FakeResult(550.0, 440.0), np.full(60, 0.9), names_for(60))
    for term in ("STC", "single-diode", "bypass diode", "photocurrent", "irradiance"):
        assert term not in text, f"{term!r} leaked into the plain report"


# ------------------------------------------------------------ model report

def test_model_report_converts_rates_to_counts():
    text = plain_model_report({"recall": 0.87, "precision": 0.74, "accuracy": 0.91})
    assert "87" in text and "74" in text
    assert "misses about 13" in text
    assert "About 26 in every 100" in text


def test_model_report_warns_when_accuracy_hides_poor_recall():
    """The classic imbalanced-data trap, stated plainly."""
    text = plain_model_report({"recall": 0.20, "precision": 0.80, "accuracy": 0.93})
    assert "WARNING" in text
    assert "says 'fine' to" in text


def test_model_report_has_no_warning_on_a_balanced_result():
    text = plain_model_report({"recall": 0.85, "precision": 0.80, "accuracy": 0.92})
    assert "WARNING" not in text


def test_model_report_handles_missing_metrics():
    """A split with no positives yields a partial metric dict; must not crash."""
    text = plain_model_report({})
    assert "HOW GOOD IS THE MODEL?" in text


def test_glossary_explains_the_unavoidable_terms():
    text = glossary()
    for term in ("cell", "kWh", "cracked"):
        assert term in text
