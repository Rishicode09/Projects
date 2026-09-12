"""Plain-English presentation of results.

Everything else in this project speaks in the units a PV engineer uses — STC
power loss, kWh per module per year, precision and recall. Those are the right
units for the physics and for a paper, and they are close to useless for
someone seeing the output for the first time: "0.06% STC loss" does not tell
you whether to care.

This module is a *presentation layer only*. It computes nothing new and changes
no result. It takes the same numbers and says them in sentences, with three
things a beginner needs and the raw figures do not give:

1. **A verdict.** Is this panel fine or not? Stated first, in one word.
2. **An anchor.** "You lose 112 kWh a year" means nothing without a reference.
   "Like the panel being switched off for 74 days a year" is the same fact in
   a form you can picture.
3. **What to do.** A number with no recommended action is trivia.

The technical output is still available (``--technical``); this is the default
because the first question is almost always "is it bad?", not "what is the
fill factor?".
"""

from __future__ import annotations

import numpy as np

# Verdict bands, by fraction of annual energy lost. Chosen to match how a
# maintenance decision actually gets made rather than to be round numbers:
# below 2% is inside the noise of the uncalibrated damage model, so calling
# that a problem would be overclaiming.
_NEGLIGIBLE = 0.005   # rounds to "0%"; a cost table of zeros reads as a bug
_MINOR = 0.02         # real but not worth anyone's time
_WATCH = 0.10         # re-photograph in 6-12 months
                      # above _WATCH: go and look at it

WIDTH = 64


def _rule(char: str = "=") -> str:
    return char * WIDTH


def _heading(text: str) -> str:
    return f"\n{_rule('-')}\n  {text.upper()}\n{_rule('-')}"


def _row(label: str, value: str, indent: int = 4, width: int = 34) -> str:
    """A dotted leader line whose values line up regardless of label length."""
    dots = "." * max(3, width - len(label))
    return f"{' ' * indent}{label} {dots} {value}"


def cell_verdict(probability: float) -> str:
    """One plain phrase for a single cell's crack probability."""
    if probability < 0.20:
        return "looks fine"
    if probability < 0.50:
        return "maybe cracked"
    if probability < 0.80:
        return "probably cracked"
    return "almost certainly cracked"


def bar(fraction: float, width: int = 10) -> str:
    """A tiny text bar, so the reader sees the shape without reading digits."""
    filled = int(round(np.clip(fraction, 0.0, 1.0) * width))
    return "#" * filled + "." * (width - filled)


def days_switched_off(loss_fraction: float) -> int:
    """Annual loss expressed as days of total shutdown.

    Losing 20% of a year's output is arithmetically the same as producing
    nothing for 73 days. That is not more precise than the percentage — it is
    the same number — but it is far easier to picture, which is the whole job
    of this module.
    """
    return int(round(np.clip(loss_fraction, 0.0, 1.0) * 365))


def overall_verdict(loss_fraction: float, cracked_cells: int) -> tuple[str, str]:
    """``(headline, what_to_do)`` for the whole panel."""
    if cracked_cells == 0 and loss_fraction < _MINOR:
        return ("HEALTHY", "Nothing to do. This panel looks normal.")
    if loss_fraction < _MINOR:
        return (
            "MOSTLY FINE",
            "Some marks were found, but they are costing you almost nothing.\n"
            "  Leave it alone and check again at your next inspection.",
        )
    if loss_fraction < _WATCH:
        return (
            "WORTH WATCHING",
            "Real damage, but not urgent.\n"
            "  Photograph this panel again in 6-12 months and compare.\n"
            "  Cracks that spread are the ones that end up costing money.",
        )
    return (
        "NEEDS ATTENTION",
        "This panel is losing a serious amount of power.\n"
        "  Worth inspecting in person, and worth pricing up a replacement.",
    )


def plain_module_report(
    result,
    probabilities: np.ndarray,
    names: list[str],
    threshold: float = 0.5,
    modules_affected: int = 1,
    tariff: float = 0.12,
    currency: str = "",
    detected_areas: np.ndarray | None = None,
    used_model: bool = True,
    synthetic_weather: bool = True,
    top_n: int = 5,
) -> str:
    """The beginner-facing report for one panel.

    ``result`` is an :class:`physics.energy.EnergyResult`; everything else is
    context needed to phrase the output, not to compute it.
    """
    probabilities = np.asarray(probabilities, dtype=float)
    cracked = int((probabilities >= threshold).sum())
    loss_fraction = result.annual_energy_loss_fraction
    headline, advice = overall_verdict(loss_fraction, cracked)

    healthy_kwh = result.annual_energy_healthy_kwh
    actual_kwh = result.annual_energy_defective_kwh
    lost_kwh = result.annual_energy_loss_kwh

    money_year = lost_kwh * tariff
    money_fleet = money_year * modules_affected

    def money(value: float) -> str:
        # Small values need decimals or the arithmetic looks broken to the
        # reader: one panel rounding to "0" beside 200 panels at "7" reads as
        # a bug, even though both are correct to their own rounding.
        digits = 2 if abs(value) < 10 else 0
        return f"{currency}{value:,.{digits}f}" if currency else f"{value:,.{digits}f}"

    lines: list[str] = [
        "",
        _rule(),
        "  SOLAR PANEL HEALTH REPORT",
        _rule(),
        "",
        f"  VERDICT:   {headline}",
        "",
        f"  {advice}",
    ]

    # ---------------------------------------------------------- what we saw
    lines += [_heading("what we looked at"), ""]
    lines += [
        _row("Cells checked in this panel", str(len(probabilities)), indent=2),
        _row("Cells that look cracked", str(cracked), indent=2),
    ]
    if not used_model:
        lines += [
            "",
            "  NOTE: no trained model was used, so these are rough guesses",
            "        from image brightness alone. Train a model for real answers.",
        ]

    # ------------------------------------------------------ what it costs
    lines += [_heading("what the damage costs you"), ""]
    if loss_fraction < _NEGLIGIBLE:
        lines += [
            "  Essentially nothing.",
            "",
            f"  This panel still makes about {actual_kwh:,.0f} kWh a year,",
            "  which is what a healthy panel of this size should make.",
        ]
    else:
        lines += [
            f"  This panel makes {loss_fraction:.0%} less electricity than a healthy one.",
            "",
            "  Over a year:",
            _row("A healthy panel would make", f"{healthy_kwh:,.0f} kWh"),
            _row("This panel makes", f"{actual_kwh:,.0f} kWh"),
            _row("So you lose", f"{lost_kwh:,.0f} kWh"),
            "",
            f"  That is the same as this panel being switched off",
            f"  for {days_switched_off(loss_fraction)} days out of every year.",
            "",
            f"  Money, at {tariff} per kWh:",
            _row("This one panel", f"{money(money_year)} per year"),
        ]
        if modules_affected > 1:
            lines += [
                _row(f"All {modules_affected} panels",
                     f"{money(money_fleet)} per year"),
                _row("Over 10 years", money(money_fleet * 10)),
            ]

    # -------------------------------------------------------- worst cells
    if cracked or probabilities.max() > 0.2:
        lines += [_heading("the worst cells"), ""]
        order = np.argsort(probabilities)[::-1][: max(1, top_n)]
        for rank, index in enumerate(order, start=1):
            area = ""
            if detected_areas is not None and detected_areas[index] > 0.005:
                area = f"  ({detected_areas[index]:.0%} of the cell is dead)"
            lines.append(
                f"  {rank}. {names[index]:<14s} "
                f"[{bar(probabilities[index])}] "
                f"{cell_verdict(probabilities[index])}{area}"
            )

    # ------------------------------------------------------- health warning
    lines += [_heading("how much to trust this"), ""]
    lines += [
        "  Treat these numbers as a guide for deciding which panels to",
        "  look at first - not as an exact measurement.",
        "",
        "  Two reasons:",
        "    1. Turning a photo of a crack into a power figure relies on",
        "       assumptions that have not been checked against real",
        "       electrical tests yet.",
    ]
    if synthetic_weather:
        lines += [
            "    2. The weather used here is a made-up perfectly sunny year,",
            "       because real weather data could not be downloaded. Real",
            "       yields will be lower. The percentages are still fair.",
        ]
    else:
        lines += [
            "    2. Weather comes from a typical-year dataset for your",
            "       location, so an unusual year will differ.",
        ]

    lines += ["", _rule(), ""]
    return "\n".join(lines)


def plain_model_report(metrics: dict, threshold: float = 0.5) -> str:
    """Plain-English version of the classifier's test metrics.

    Precision and recall are the two numbers that matter operationally, and
    both are far clearer stated as counts out of a hundred than as decimals —
    "misses 13 cracked cells in every 100" is a sentence someone can act on,
    where "recall 0.87" is one they have to translate first.
    """
    recall = metrics.get("recall", 0.0)
    precision = metrics.get("precision", 0.0)
    accuracy = metrics.get("accuracy", 0.0)

    missed = int(round((1 - recall) * 100))
    false_alarms = int(round((1 - precision) * 100))

    lines = [
        "",
        _rule(),
        "  HOW GOOD IS THE MODEL?",
        _rule(),
        "",
        _row("Out of every 100 cracked cells, it finds",
             f"{recall * 100:.0f}", indent=2, width=46),
        _row("When it says 'cracked', it is right",
             f"{precision * 100:.0f} times in 100", indent=2, width=46),
        _row("Overall it gets",
             f"{accuracy * 100:.0f} out of 100 right", indent=2, width=46),
        "",
        "  In practice that means:",
        f"    It misses about {missed} cracked cells in every 100.",
        f"    About {false_alarms} in every 100 alarms are false.",
        "",
        f"  (Measured at a cut-off of {threshold:.2f}. Lowering the cut-off",
        "   catches more cracks but raises more false alarms.)",
    ]

    if accuracy > 0.9 and recall < 0.5:
        lines += [
            "",
            "  WARNING: high overall score but low crack-finding rate.",
            "  Most cells are healthy, so a model that says 'fine' to",
            "  everything still scores well. Judge it on the first line.",
        ]

    lines += ["", _rule(), ""]
    return "\n".join(lines)


def format_duration(seconds: float) -> str:
    """A duration at the precision the reader can actually use.

    Nobody plans around "6847 seconds". The thresholds are deliberately low --
    90 seconds reads as minutes, 90 minutes as hours -- because the decision
    this figure informs is "do I wait, or come back later?".
    """
    if seconds < 90:
        return f"{seconds:.0f} seconds"
    minutes = seconds / 60.0
    if minutes < 90:
        return f"{minutes:.0f} minutes"
    return f"{minutes / 60.0:.1f} hours"


def training_plan(
    backbone: str,
    device: str,
    epochs: int,
    seconds_per_epoch: float,
    patience: int | None = None,
    slow_threshold: float = 45 * 60,
) -> str:
    """What this training run is about to cost, said before it starts.

    A run that turns out to take three hours is a far worse experience than one
    that says so up front, and the fix is the same either way: print the
    estimate while the reader can still change their mind.
    """
    total = seconds_per_epoch * epochs
    lines = [
        "",
        _rule("-"),
        f"  Training {backbone} on {device}.",
        f"  About {format_duration(seconds_per_epoch)} per epoch, "
        f"up to {epochs} epochs.",
        f"  Worst case: roughly {format_duration(total)}.",
    ]
    if patience:
        lines.append(
            f"  It usually stops earlier -- training ends after {patience} epochs"
        )
        lines.append("  with no improvement, which normally comes first.")
    if total > slow_threshold and device == "cpu":
        lines += [
            "",
            "  That is a long time on a processor. Two ways to cut it:",
            "    - a shorter run for checking the pipeline works:",
            "        python -m pvdefect.train --config configs/fast.yaml",
            "    - a machine with a CUDA graphics card, which is 10-50x faster",
            "      and needs no config change (device: auto finds it).",
        ]
    lines += [_rule("-"), ""]
    return "\n".join(lines)


def glossary() -> str:
    """The handful of terms the reports cannot avoid."""
    return "\n".join(
        [
            "",
            _rule(),
            "  WHAT THE WORDS MEAN",
            _rule(),
            "",
            "  cell        One small square in a solar panel. A typical panel",
            "              is 60 of them wired in a line.",
            "",
            "  kWh         Kilowatt-hour: a unit of electricity. Roughly what",
            "              a fridge uses in a day.",
            "",
            "  cracked     The silicon has a fracture. Small cracks often cost",
            "              nothing; it only matters when a crack cuts part of",
            "              the cell off from the wiring.",
            "",
            "  why one     The cells are wired in a line, like old Christmas",
            "  bad cell    lights. Current has to pass through every one, so",
            "  matters     the weakest cell holds back the whole panel. One",
            "              badly damaged cell can cost far more than its share.",
            "",
            _rule(),
            "",
        ]
    )
