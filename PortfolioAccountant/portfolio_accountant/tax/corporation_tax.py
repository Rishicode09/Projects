"""UK corporation tax, including marginal relief and associated companies.

The associated-companies rule is the part people get wrong in a property
portfolio. If a person controls several SPVs, the £50,000 and £250,000 limits
are divided between all of them. Setting up "one company per property" without
accounting for this can push every company into the marginal band, where the
effective rate is about 26.5% -- higher than the headline main rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Optional

from ..config import Jurisdiction
from ..money import Money
from .base import Computation


@dataclass
class CompanyProfits:
    trading_profit: Money = field(default_factory=Money.zero)
    property_profit: Money = field(default_factory=Money.zero)
    other_income: Money = field(default_factory=Money.zero)
    chargeable_gains: Money = field(default_factory=Money.zero)
    losses_brought_forward: Money = field(default_factory=Money.zero)
    # Dividends received from non-group companies count towards the limits
    # even though they are usually not themselves taxable.
    exempt_distributions_received: Money = field(default_factory=Money.zero)
    associated_companies: int = 0
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    # Adjustments from accounting profit to taxable profit.
    depreciation_addback: Money = field(default_factory=Money.zero)
    disallowed_expenses: Money = field(default_factory=Money.zero)
    capital_allowances: Money = field(default_factory=Money.zero)

    @property
    def total_profits(self) -> Money:
        return (
            self.trading_profit
            + self.property_profit
            + self.other_income
            + self.chargeable_gains
        )


def _marginal_rate(
    small_rate: Decimal, main_rate: Decimal, lower: Money, upper: Money
) -> Decimal:
    """Effective rate on the next pound of profit inside the marginal band.

    Tax at the top of the band is ``upper x main_rate``; at the bottom it is
    ``lower x small_rate``. The slope between those two points is the rate that
    actually matters for any timing decision.
    """
    span = upper.amount - lower.amount
    if span == 0:  # pragma: no cover - defensive
        return main_rate
    return (upper.amount * main_rate - lower.amount * small_rate) / span


def compute_corporation_tax(
    profits: CompanyProfits,
    jur: Jurisdiction,
    entity_id: str = "",
) -> Computation:
    """Compute corporation tax with marginal relief and full workings."""
    comp = Computation(
        title="Corporation tax computation",
        entity_id=entity_id,
        period=(
            f"{profits.period_start} to {profits.period_end}"
            if profits.period_start
            else jur.tax_year
        ),
    )
    comp.uses(
        "corporation_tax.small_profits_rate",
        "corporation_tax.main_rate",
        "corporation_tax.lower_limit",
        "corporation_tax.upper_limit",
        "corporation_tax.marginal_relief_fraction",
    )

    # -- 1. Accounting profit to taxable profit --------------------------
    comp.step("Trading profit per accounts", result=profits.trading_profit)
    if not profits.property_profit.is_zero:
        comp.step("Property business profit", result=profits.property_profit)
    if not profits.other_income.is_zero:
        comp.step("Other income", result=profits.other_income)
    if not profits.chargeable_gains.is_zero:
        comp.step(
            "Chargeable gains",
            result=profits.chargeable_gains,
            note="Companies pay corporation tax on gains, not CGT, and have no "
                 "annual exempt amount.",
        )

    adjustments = profits.depreciation_addback + profits.disallowed_expenses
    if not adjustments.is_zero:
        comp.step(
            "Add back depreciation and disallowed expenses",
            result=adjustments,
            note="Depreciation is never deductible; capital allowances replace it.",
        )
    if not profits.capital_allowances.is_zero:
        comp.step("Less capital allowances", result=-profits.capital_allowances)

    total_profits = profits.total_profits + adjustments - profits.capital_allowances

    losses_used = Money.zero()
    if profits.losses_brought_forward > 0:
        losses_used = min(
            [profits.losses_brought_forward, total_profits], key=lambda m: m.amount
        )
        if losses_used < 0:
            losses_used = Money.zero()
        comp.step(
            "Less losses brought forward",
            result=-losses_used,
            note="Post-April-2017 losses are broadly flexible but subject to the "
                 "£5m deductions allowance and 50% restriction above it.",
        )
        remaining_losses = profits.losses_brought_forward - losses_used
        if remaining_losses > 0:
            comp.carried_forward["losses"] = remaining_losses

    taxable = total_profits - losses_used
    if taxable < 0:
        comp.carried_forward["losses"] = comp.carried_forward.get(
            "losses", Money.zero()
        ) + abs(taxable)
        taxable = Money.zero()

    comp.step("Taxable total profits", result=taxable)

    if taxable.is_zero:
        comp.totals = {"corporation_tax": Money.zero(), "total": Money.zero()}
        comp.step("No taxable profits - nil liability")
        comp.warn(
            "A nil return is still a required return. The CT600 is due 12 months "
            "after the period end even where no tax is payable."
        )
        return comp

    # -- 2. Limits, divided by associated companies ----------------------
    divisor = profits.associated_companies + 1
    lower_limit = jur.money("corporation_tax.lower_limit") / divisor
    upper_limit = jur.money("corporation_tax.upper_limit") / divisor

    if profits.associated_companies:
        comp.step(
            f"Limits divided by {divisor} associated companies",
            note=f"Lower limit {lower_limit}, upper limit {upper_limit}. "
                 "Associated companies are those under common control - including "
                 "companies controlled by associates such as a spouse. Getting the "
                 "count wrong changes the rate.",
        )
        comp.refer(
            "Confirm the associated company count. Control is tested under "
            "CTA 2010 s.450-451 and catches more relationships than people expect."
        )

    # Augmented profits include exempt distributions for the limit test only.
    augmented = taxable + profits.exempt_distributions_received
    if not profits.exempt_distributions_received.is_zero:
        comp.step(
            "Augmented profits (for the limit test only)",
            result=augmented,
            note="Exempt dividends received raise augmented profits and can push "
                 "the company into a higher rate, without themselves being taxed.",
        )

    small_rate = jur.decimal("corporation_tax.small_profits_rate")
    main_rate = jur.decimal("corporation_tax.main_rate")

    # -- 3. Rate and marginal relief -------------------------------------
    if augmented <= lower_limit:
        tax = taxable * small_rate
        comp.step("Small profits rate", amount=taxable, rate=small_rate, result=tax)
        effective = small_rate
    elif augmented >= upper_limit:
        tax = taxable * main_rate
        comp.step("Main rate", amount=taxable, rate=main_rate, result=tax)
        effective = main_rate
    else:
        gross_tax = taxable * main_rate
        comp.step("Main rate on all profits", amount=taxable, rate=main_rate, result=gross_tax)

        fraction = jur.decimal("corporation_tax.marginal_relief_fraction")
        # MR = F x (U - A) x (N / A)
        relief = (
            (upper_limit - augmented)
            * fraction
            * (taxable.amount / augmented.amount)
        )
        comp.step(
            "Less marginal relief",
            result=-relief,
            note=(
                f"F x (upper limit - augmented profits) x (taxable / augmented) "
                f"= {fraction} x {upper_limit - augmented} x "
                f"{(taxable.amount / augmented.amount):.4f}"
            ),
        )
        tax = gross_tax - relief
        effective = (
            Decimal(tax.amount / taxable.amount) if taxable.amount else Decimal(0)
        )
        marginal_rate = _marginal_rate(small_rate, main_rate, lower_limit, upper_limit)
        comp.warn(
            f"Profits fall in the marginal relief band. The effective rate on the "
            f"next pound of profit is {marginal_rate * 100:.2f}%, higher than the "
            "headline main rate. Timing income or deductible expenditure across the "
            "period end has a real effect while profits sit in this band."
        )

    tax = tax.quantize()
    comp.step(
        "Corporation tax payable",
        result=tax,
        note=f"Effective rate {effective * 100:.2f}% of taxable profits.",
    )

    comp.totals = {"corporation_tax": tax, "total": tax}

    # -- 4. Deadlines -----------------------------------------------------
    if profits.period_end:
        comp.uses("corporation_tax.payment_due_months", "corporation_tax.return_due_months")
        comp.step(
            "Payment due",
            note=f"9 months and 1 day after {profits.period_end}. The CT600 itself "
                 "is not due until 12 months after the period end, so the money is "
                 "due three months before the return.",
        )

    comp.assume(
        "The company is not a close investment holding company. A CIHC pays the "
        "main rate on all profits with no small profits rate - a property "
        "investment company can fall into this if it is not genuinely letting to "
        "unconnected parties."
    )
    comp.refer(
        "Quarterly instalment payments apply above £1.5m augmented profits "
        "(divided by associated companies). Not modelled here."
    )
    return comp
