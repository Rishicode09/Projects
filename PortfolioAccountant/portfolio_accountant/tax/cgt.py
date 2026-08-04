"""Capital gains tax on property and other asset disposals.

The two things that most often go wrong on a property disposal:

* the 60-day reporting deadline is missed, because people assume it follows
  the self-assessment cycle; and
* the base cost is understated, because improvement spending from years ago
  was never captured in the books.

The second is a bookkeeping problem that only shows up as a tax problem a
decade later, which is exactly why the ledger tracks improvements separately
from repairs from day one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from ..config import Jurisdiction
from ..model import Property
from ..money import Money, total
from .base import Computation


@dataclass
class Disposal:
    """A single chargeable disposal."""

    description: str
    disposal_date: date
    proceeds: Money
    acquisition_cost: Money
    incidental_acquisition_costs: Money = field(default_factory=Money.zero)
    improvement_costs: Money = field(default_factory=Money.zero)
    incidental_disposal_costs: Money = field(default_factory=Money.zero)
    is_residential: bool = True
    ownership_share: Decimal = Decimal("1")
    # Private residence relief inputs.
    total_months_owned: int = 0
    months_as_main_residence: int = 0
    qualifies_for_badr: bool = False

    @property
    def allowable_cost(self) -> Money:
        return (
            self.acquisition_cost
            + self.incidental_acquisition_costs
            + self.improvement_costs
            + self.incidental_disposal_costs
        )

    @property
    def raw_gain(self) -> Money:
        return (self.proceeds - self.allowable_cost) * self.ownership_share

    @classmethod
    def from_property(cls, prop: Property) -> "Disposal":
        if not prop.is_disposed:
            raise ValueError(f"property '{prop.id}' has no disposal date")
        months = 0
        if prop.purchase_date:
            months = max(
                1,
                (prop.disposal_date.year - prop.purchase_date.year) * 12
                + (prop.disposal_date.month - prop.purchase_date.month),
            )
        return cls(
            description=prop.address or prop.id,
            disposal_date=prop.disposal_date,
            proceeds=prop.disposal_proceeds,
            acquisition_cost=prop.purchase_price,
            incidental_acquisition_costs=prop.acquisition_costs,
            improvement_costs=prop.capital_improvements,
            incidental_disposal_costs=prop.disposal_costs,
            is_residential=prop.use
            in ("residential_let", "own_home", "furnished_holiday_let"),
            ownership_share=prop.ownership_share,
            total_months_owned=months,
            months_as_main_residence=prop.months_as_main_residence,
        )


def compute_cgt(
    disposals: List[Disposal],
    jur: Jurisdiction,
    taxable_income: Money,
    entity_id: str = "",
    losses_brought_forward: Optional[Money] = None,
) -> Computation:
    """Compute CGT for a tax year across all disposals."""
    comp = Computation(
        title="Capital gains tax computation",
        entity_id=entity_id,
        period=jur.tax_year,
    )
    comp.uses(
        "capital_gains_tax.annual_exempt_amount",
        "capital_gains_tax.rates.residential_basic",
        "capital_gains_tax.rates.residential_higher",
        "capital_gains_tax.residential_reporting_days",
    )
    losses_brought_forward = losses_brought_forward or Money.zero()

    residential_gains = Money.zero()
    other_gains = Money.zero()
    losses_in_year = Money.zero()

    for d in disposals:
        comp.step(f"Disposal: {d.description} ({d.disposal_date})")
        comp.step("  Proceeds", result=d.proceeds * d.ownership_share)
        comp.step(
            "  Less allowable cost",
            result=-(d.allowable_cost * d.ownership_share),
            note=(
                f"purchase {d.acquisition_cost} + acquisition costs "
                f"{d.incidental_acquisition_costs} + improvements "
                f"{d.improvement_costs} + disposal costs "
                f"{d.incidental_disposal_costs}"
            ),
        )
        if d.ownership_share != 1:
            comp.step(
                "  Ownership share",
                rate=d.ownership_share,
                note="Share must match the beneficial ownership, evidenced by a "
                     "declaration of trust where it differs from the legal title.",
            )

        gain = d.raw_gain
        comp.step("  Gain before reliefs", result=gain)

        # Private residence relief.
        if d.months_as_main_residence > 0 and d.total_months_owned > 0:
            comp.assume(
                f"{d.description}: PRR calculated on a simple time basis. Periods "
                "of absence, job-related accommodation and the final-period "
                "exemption all have their own rules and are not modelled."
            )
            relief_months = min(d.months_as_main_residence, d.total_months_owned)
            prr = gain.apportion(relief_months, d.total_months_owned)
            comp.step(
                "  Private residence relief",
                result=-prr,
                note=f"{relief_months} of {d.total_months_owned} months "
                     "(indicative time apportionment only)",
            )
            gain = gain - prr
            comp.refer(
                f"{d.description}: private residence relief and any lettings relief "
                "must be confirmed by an adviser against the actual occupation "
                "history. The time-apportioned figure here is a starting point, not "
                "a conclusion."
            )

        if gain < 0:
            losses_in_year = losses_in_year + abs(gain)
            comp.step("  Allowable loss", result=gain)
        elif d.is_residential:
            residential_gains = residential_gains + gain
        else:
            other_gains = other_gains + gain

        # The 60-day trap.
        if d.is_residential and gain > 0:
            deadline = d.disposal_date + timedelta(
                days=int(jur.value("capital_gains_tax.residential_reporting_days"))
            )
            comp.warn(
                f"{d.description}: UK residential disposal. A standalone CGT return "
                f"and a payment on account were due by {deadline} "
                f"({jur.value('capital_gains_tax.residential_reporting_days')} days "
                "after completion) - separately from, and much earlier than, the "
                "self-assessment return."
            )

        if d.qualifies_for_badr:
            comp.refer(
                f"{d.description}: Business Asset Disposal Relief claimed. The "
                "qualifying conditions (two-year ownership, personal company, "
                "officer or employee status) must be evidenced before claiming."
            )

    gross_gains = residential_gains + other_gains
    comp.step("Total chargeable gains", result=gross_gains)

    # Losses: current year first, then brought forward, but only down to the AEA.
    net_gains = gross_gains - losses_in_year
    if net_gains < 0:
        net_gains = Money.zero()
    if not losses_in_year.is_zero:
        comp.step("Less losses of the year", result=-losses_in_year)

    aea = jur.money("capital_gains_tax.annual_exempt_amount")

    if losses_brought_forward > 0:
        # Brought-forward losses are restricted so as not to waste the AEA.
        usable = net_gains - aea
        if usable < 0:
            usable = Money.zero()
        applied = min([losses_brought_forward, usable], key=lambda m: m.amount)
        if applied > 0:
            comp.step(
                "Less losses brought forward",
                result=-applied,
                note="Restricted so the annual exempt amount is not wasted - "
                     "unused brought-forward losses stay available indefinitely.",
            )
            net_gains = net_gains - applied
        remaining = losses_brought_forward - applied
        if remaining > 0:
            comp.carried_forward["capital_losses"] = remaining

    comp.step("Less annual exempt amount", result=-aea)
    taxable_gains = net_gains - aea
    if taxable_gains < 0:
        unused_aea = abs(taxable_gains)
        taxable_gains = Money.zero()
        comp.step(
            "Taxable gains",
            result=taxable_gains,
            note=f"{unused_aea} of the annual exempt amount is unused. It cannot be "
                 "carried forward or transferred - if a further disposal is planned, "
                 "the timing of it across 5 April is worth considering.",
        )
    else:
        comp.step("Taxable gains", result=taxable_gains)

    if taxable_gains.is_zero:
        comp.totals = {"capital_gains_tax": Money.zero(), "total": Money.zero()}
        comp.warn(
            "No CGT payable, but a residential disposal may still require a "
            "60-day return. A nil liability does not always mean nil reporting."
        )
        return comp

    # -- Rates depend on the basic rate band left after income ------------
    basic_limit = jur.money("income_tax.basic_rate_limit")
    headroom = basic_limit - taxable_income
    if headroom < 0:
        headroom = Money.zero()

    comp.step(
        "Basic rate band remaining after income",
        result=headroom,
        note=f"Taxable income {taxable_income} against a basic rate limit of "
             f"{basic_limit}. Gains stack on top of income, so income in the same "
             "year directly raises the CGT rate.",
    )

    # Residential gains use the band first (they carry the same rates now, but
    # keeping them separate preserves the working if rates diverge again).
    tax = Money.zero()
    remaining_headroom = headroom

    for label, amount, basic_key, higher_key in (
        (
            "Residential",
            min([residential_gains, taxable_gains], key=lambda m: m.amount),
            "capital_gains_tax.rates.residential_basic",
            "capital_gains_tax.rates.residential_higher",
        ),
        (
            "Other assets",
            taxable_gains - min([residential_gains, taxable_gains], key=lambda m: m.amount),
            "capital_gains_tax.rates.other_basic",
            "capital_gains_tax.rates.other_higher",
        ),
    ):
        if amount <= 0:
            continue
        at_basic = min([amount, remaining_headroom], key=lambda m: m.amount)
        if at_basic < 0:
            at_basic = Money.zero()
        at_higher = amount - at_basic
        remaining_headroom = remaining_headroom - at_basic
        if remaining_headroom < 0:
            remaining_headroom = Money.zero()

        if at_basic > 0:
            rate = jur.decimal(basic_key)
            charge = at_basic * rate
            comp.step(f"  {label} at basic rate", amount=at_basic, rate=rate, result=charge)
            tax = tax + charge
        if at_higher > 0:
            rate = jur.decimal(higher_key)
            charge = at_higher * rate
            comp.step(f"  {label} at higher rate", amount=at_higher, rate=rate, result=charge)
            tax = tax + charge

    tax = tax.quantize()
    comp.totals = {"capital_gains_tax": tax, "total": tax}
    comp.assume(
        "No connected-party disposal. A transfer to a connected person is treated "
        "as taking place at market value regardless of what actually changed hands."
    )
    comp.refer(
        "Spousal transfers before a sale take place at no gain/no loss and can use "
        "a second annual exempt amount and basic rate band. This is an ordinary, "
        "long-standing statutory feature, but it must be a genuine outright "
        "transfer of beneficial ownership made before exchange - not a paper "
        "arrangement after the fact."
    )
    return comp
