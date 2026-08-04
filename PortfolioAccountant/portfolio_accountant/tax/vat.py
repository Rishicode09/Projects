"""VAT registration monitoring for the trading side of a portfolio.

Residential letting is an exempt supply, so rent does not usually count
towards the registration threshold. Commercial rent (where the option to tax
has been exercised) and serviced accommodation do count -- and a business that
crosses the threshold without noticing owes VAT on supplies it never charged
for, out of its own margin.

The test that catches people is the *forward look*: if taxable turnover in the
next 30 days alone will exceed the threshold, registration is immediate. That
one does not wait for a rolling twelve months to elapse.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from ..config import Jurisdiction
from ..model import Transaction
from ..money import Money, total
from .base import Computation


@dataclass
class TurnoverMonth:
    year: int
    month: int
    taxable_turnover: Money

    @property
    def label(self) -> str:
        return f"{self.year}-{self.month:02d}"


def monthly_taxable_turnover(
    transactions: List[Transaction], taxable_categories: List[str]
) -> List[TurnoverMonth]:
    """Aggregate taxable supplies by month, ignoring exempt income."""
    buckets: Dict[Tuple[int, int], Money] = {}
    for txn in transactions:
        if not txn.is_money_in:
            continue
        if txn.category not in taxable_categories:
            continue
        key = (txn.date.year, txn.date.month)
        buckets[key] = buckets.get(key, Money.zero()) + txn.amount
    return [
        TurnoverMonth(year=y, month=m, taxable_turnover=v)
        for (y, m), v in sorted(buckets.items())
    ]


def check_vat_registration(
    months: List[TurnoverMonth],
    jur: Jurisdiction,
    entity_id: str = "",
    already_registered: bool = False,
) -> Computation:
    """Run the rolling twelve-month test month by month."""
    comp = Computation(
        title="VAT registration threshold review",
        entity_id=entity_id,
        period=jur.tax_year,
    )
    comp.uses("vat.registration_threshold", "vat.standard_rate")
    threshold = jur.money("vat.registration_threshold")
    comp.step("Registration threshold", result=threshold)
    comp.step(
        "Basis",
        note="Rolling 12-month historic test. Only taxable supplies count - "
             "residential rent is exempt and is excluded. Confirm the category "
             "mapping before relying on this.",
    )

    if not months:
        comp.step("No taxable turnover identified in the period")
        comp.totals = {"peak_rolling_turnover": Money.zero(), "total": Money.zero()}
        return comp

    peak = Money.zero()
    breach_month: Optional[str] = None

    for i, month in enumerate(months):
        window = months[max(0, i - 11) : i + 1]
        rolling = total(m.taxable_turnover for m in window)
        if rolling > peak:
            peak = rolling
        if rolling > threshold and breach_month is None:
            breach_month = month.label
            comp.step(
                f"Threshold exceeded in the 12 months to {month.label}",
                result=rolling,
                note="Registration is required by the end of the following month, "
                     "with effect from the first day of the month after that.",
            )
        # Show the last few months for context.
        if i >= len(months) - 3:
            comp.step(f"  Rolling 12 months to {month.label}", result=rolling)

    headroom = threshold - peak
    comp.step("Peak rolling 12-month taxable turnover", result=peak)

    if breach_month and not already_registered:
        comp.warn(
            f"Taxable turnover exceeded the registration threshold in the 12 months "
            f"to {breach_month} and the entity is recorded as not registered. Late "
            "registration means VAT is due on supplies already made, whether or not "
            "it was charged to customers, plus penalties. This needs action now, not "
            "at the year end."
        )
        comp.refer(
            "Late VAT registration. Take advice immediately; an unprompted "
            "disclosure to HMRC generally carries a materially lower penalty than "
            "waiting to be found."
        )
    elif headroom > 0 and headroom < threshold * Decimal("0.15"):
        comp.warn(
            f"Within {headroom} of the registration threshold. Once the forward "
            "30-day test is in play, registration can be triggered immediately "
            "rather than after a rolling year - watch this monthly."
        )

    comp.totals = {
        "peak_rolling_turnover": peak.quantize(),
        "headroom": headroom.quantize(),
        "total": peak.quantize(),
    }
    comp.assume(
        "Taxable supplies have been correctly distinguished from exempt supplies. "
        "Residential rent is exempt; commercial rent is exempt unless the option "
        "to tax has been exercised; serviced accommodation is standard-rated."
    )
    comp.refer(
        "The option to tax, partial exemption and the capital goods scheme all "
        "change this picture materially and are not modelled here."
    )
    return comp
