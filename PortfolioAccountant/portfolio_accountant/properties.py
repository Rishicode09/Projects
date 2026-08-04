"""Per-property performance analysis -- the management accounting layer.

Portfolio-level numbers hide the property that is losing money. A landlord
looking at a healthy aggregate profit can be cross-subsidising one unit whose
yield after finance costs is negative, and never know until they sell it.

This module produces the per-unit view, and makes the Section 24 gap explicit:
the difference between the cash a property actually generates and the profit it
is taxed on. For a geared personally-held residential portfolio, that gap is
the single most important number on the page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from .model import OwnershipBasis, Portfolio, Property, PropertyUse, Transaction
from .money import Money, total

# Account code prefixes used to interpret the ledger.
INCOME_ACCOUNTS = ("4000", "4010", "4020", "4030", "4040")
FINANCE_ACCOUNTS = ("5100", "5110", "5120")
CAPITAL_ACCOUNTS = ("1700", "1710", "5080")


@dataclass
class PropertyPerformance:
    """One property's results for a period."""

    property_id: str
    address: str
    basis: str
    use: str
    gross_rent: Money = field(default_factory=Money.zero)
    operating_costs: Money = field(default_factory=Money.zero)
    finance_costs: Money = field(default_factory=Money.zero)
    capital_spend: Money = field(default_factory=Money.zero)
    months_in_period: int = 12
    months_let: int = 12
    valuation: Money = field(default_factory=Money.zero)
    mortgage: Money = field(default_factory=Money.zero)
    equity_invested: Money = field(default_factory=Money.zero)
    flags: List[str] = field(default_factory=list)

    # -- profit measures -------------------------------------------------
    @property
    def net_operating_income(self) -> Money:
        """Profit before finance costs. This is the taxable figure under s.24."""
        return self.gross_rent - self.operating_costs

    @property
    def cash_profit(self) -> Money:
        """What the property actually puts in the bank."""
        return self.net_operating_income - self.finance_costs

    @property
    def cost_ratio(self) -> Decimal:
        if self.gross_rent.amount == 0:
            return Decimal("0")
        return self.operating_costs.amount / self.gross_rent.amount * 100

    # -- yields ----------------------------------------------------------
    @property
    def gross_yield(self) -> Decimal:
        if self.valuation.amount == 0:
            return Decimal("0")
        return self.annualised(self.gross_rent).amount / self.valuation.amount * 100

    @property
    def net_yield(self) -> Decimal:
        if self.valuation.amount == 0:
            return Decimal("0")
        return (
            self.annualised(self.net_operating_income).amount
            / self.valuation.amount
            * 100
        )

    @property
    def return_on_equity(self) -> Decimal:
        equity = self.valuation - self.mortgage
        if equity.amount <= 0:
            return Decimal("0")
        return self.annualised(self.cash_profit).amount / equity.amount * 100

    @property
    def occupancy(self) -> Decimal:
        if not self.months_in_period:
            return Decimal("0")
        return Decimal(self.months_let) / Decimal(self.months_in_period) * 100

    def annualised(self, amount: Money) -> Money:
        if self.months_in_period in (0, 12):
            return amount
        return amount.apportion(12, self.months_in_period)

    @property
    def is_s24_affected(self) -> bool:
        """Personally-held geared residential property bears the restriction."""
        return (
            self.basis in (OwnershipBasis.PERSONAL, OwnershipBasis.JOINT)
            and self.use in (PropertyUse.RESIDENTIAL_LET,)
            and self.finance_costs > 0
        )


def months_between(start: date, end: date) -> int:
    """Whole months in a period.

    A UK tax year runs 6 April to 5 April, so naive month-boundary counting
    returns 13 and every property then looks like it has a missing rent month.
    """
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day >= start.day:
        months += 1
    return max(1, months)


def analyse_properties(
    portfolio: Portfolio,
    start: date,
    end: date,
    entity_id: Optional[str] = None,
) -> List[PropertyPerformance]:
    """Build per-property performance from classified transactions."""
    months = months_between(start, end)
    results: List[PropertyPerformance] = []

    for prop in sorted(portfolio.properties.values(), key=lambda p: p.id):
        if entity_id and prop.owner_entity_id != entity_id:
            continue
        if not prop.held_during(start, end):
            continue

        txns = portfolio.transactions_for(
            entity_id=prop.owner_entity_id, start=start, end=end, property_id=prop.id
        )

        perf = PropertyPerformance(
            property_id=prop.id,
            address=prop.address,
            basis=prop.basis,
            use=prop.use,
            months_in_period=months,
            valuation=prop.current_valuation,
            mortgage=prop.mortgage_balance,
            equity_invested=prop.purchase_price
            + prop.acquisition_costs
            - prop.mortgage_balance,
        )

        rent_months = set()
        for txn in txns:
            code = txn.category
            if code.startswith(INCOME_ACCOUNTS):
                perf.gross_rent = perf.gross_rent + txn.amount
                rent_months.add((txn.date.year, txn.date.month))
            elif code.startswith(FINANCE_ACCOUNTS):
                perf.finance_costs = perf.finance_costs + abs(txn.amount)
            elif code.startswith(CAPITAL_ACCOUNTS):
                perf.capital_spend = perf.capital_spend + abs(txn.amount)
            elif code.startswith("9"):
                if "unclassified" not in perf.flags:
                    perf.flags.append("unclassified")
            elif txn.amount < 0:
                perf.operating_costs = perf.operating_costs + abs(txn.amount)

        perf.months_let = len(rent_months)
        _flag_property(perf, prop)
        results.append(perf)

    return results


def _flag_property(perf: PropertyPerformance, prop: Property) -> None:
    """Raise the things a management accountant would query."""
    if perf.months_let < perf.months_in_period and perf.gross_rent > 0:
        missing = perf.months_in_period - perf.months_let
        perf.flags.append(
            f"rent received in only {perf.months_let} of {perf.months_in_period} "
            f"months - {missing} month(s) with no receipt. Void, arrears, or income "
            "banked elsewhere? All three need a different response."
        )
    if perf.gross_rent.is_zero and prop.use != PropertyUse.OWN_HOME:
        perf.flags.append(
            "no rental income recorded at all for a property held as an investment"
        )
    if perf.cash_profit.is_negative:
        perf.flags.append(
            f"cash-negative: costs exceed rent by {abs(perf.cash_profit)} over the period"
        )
    if perf.cost_ratio > 45 and perf.gross_rent > 0:
        perf.flags.append(
            f"operating costs are {perf.cost_ratio:.0f}% of rent, which is high for "
            "a residential let - check for capital items misposted as repairs"
        )
    if perf.capital_spend > 0:
        perf.flags.append(
            f"{perf.capital_spend} of capital spend recorded. Not deductible against "
            "rent, but it increases the CGT base cost - keep the invoices with the "
            "property file permanently, not just for the usual record period."
        )
    if prop.ownership_share != 1:
        perf.flags.append(
            f"held at a {prop.ownership_share * 100:.0f}% share - beneficial "
            "ownership should be evidenced by a declaration of trust, and for "
            "spouses a Form 17 election is needed to depart from a 50/50 split"
        )


@dataclass
class PortfolioSummary:
    """The aggregate view, with the tax gap made explicit."""

    properties: List[PropertyPerformance]
    period_label: str = ""

    @property
    def gross_rent(self) -> Money:
        return total(p.gross_rent for p in self.properties)

    @property
    def operating_costs(self) -> Money:
        return total(p.operating_costs for p in self.properties)

    @property
    def finance_costs(self) -> Money:
        return total(p.finance_costs for p in self.properties)

    @property
    def net_operating_income(self) -> Money:
        return total(p.net_operating_income for p in self.properties)

    @property
    def cash_profit(self) -> Money:
        return total(p.cash_profit for p in self.properties)

    @property
    def s24_properties(self) -> List[PropertyPerformance]:
        return [p for p in self.properties if p.is_s24_affected]

    @property
    def restricted_finance_costs(self) -> Money:
        """Finance costs that s.24 denies as a deduction."""
        return total(p.finance_costs for p in self.s24_properties)

    @property
    def s24_taxable_base(self) -> Money:
        """Profit before finance costs on the affected properties only."""
        return total(p.net_operating_income for p in self.s24_properties)

    @property
    def s24_cash_profit(self) -> Money:
        return total(p.cash_profit for p in self.s24_properties)

    def filtered(self, basis: Optional[List[str]] = None) -> "PortfolioSummary":
        """A sub-summary, e.g. only the personally-held properties.

        The portfolio total mixes entities, and personal and company property
        are taxed under entirely different regimes. Anything feeding a personal
        tax computation must be filtered to what that person actually owns.
        """
        selected = [p for p in self.properties if not basis or p.basis in basis]
        return PortfolioSummary(properties=selected, period_label=self.period_label)

    @property
    def total_value(self) -> Money:
        return total(p.valuation for p in self.properties)

    @property
    def total_debt(self) -> Money:
        return total(p.mortgage for p in self.properties)

    @property
    def loan_to_value(self) -> Decimal:
        if self.total_value.amount == 0:
            return Decimal("0")
        return self.total_debt.amount / self.total_value.amount * 100

    @property
    def interest_cover(self) -> Decimal:
        """Net operating income over finance costs -- the lender's test."""
        if self.finance_costs.amount == 0:
            return Decimal("0")
        return self.net_operating_income.amount / self.finance_costs.amount

    def worst_performers(self, count: int = 3) -> List[PropertyPerformance]:
        return sorted(self.properties, key=lambda p: p.return_on_equity)[:count]

    def render(self) -> str:
        lines = [
            f"Portfolio summary  {self.period_label}",
            "=" * 78,
            f"{'Property':<26}{'Rent':>12}{'Costs':>11}{'Finance':>11}"
            f"{'Cash':>11}{'RoE':>7}",
            "-" * 78,
        ]
        for p in sorted(self.properties, key=lambda x: x.property_id):
            lines.append(
                f"{(p.property_id + ' ' + p.address)[:25]:<26}"
                f"{str(p.gross_rent):>12}"
                f"{str(p.operating_costs):>11}"
                f"{str(p.finance_costs):>11}"
                f"{str(p.cash_profit):>11}"
                f"{p.return_on_equity:>6.1f}%"
            )
        lines.append("-" * 78)
        lines.append(
            f"{'TOTAL':<26}{str(self.gross_rent):>12}{str(self.operating_costs):>11}"
            f"{str(self.finance_costs):>11}{str(self.cash_profit):>11}"
        )
        lines.append("")
        lines.append(f"  Net operating income (taxable base): {self.net_operating_income}")
        lines.append(f"  Cash profit after finance costs:     {self.cash_profit}")

        restricted = self.restricted_finance_costs
        if restricted > 0:
            affected = ", ".join(p.property_id for p in self.s24_properties)
            lines.append("")
            lines.append("  Section 24 gap (personally-held residential only)")
            lines.append(f"    affected: {affected}")
            lines.append(
                f"    {restricted} of finance costs are not deductible. On these "
                f"properties tax is charged on {self.s24_taxable_base}, not on the "
                f"{self.s24_cash_profit} actually earned."
            )
            lines.append(
                "    Relief comes back as a 20% tax reducer, so a higher-rate "
                "taxpayer bears a real cost of 20% of the restricted interest."
            )

        lines.append("")
        lines.append(f"  Portfolio value: {self.total_value}   Debt: {self.total_debt}")
        lines.append(f"  Loan to value:   {self.loan_to_value:.1f}%")
        if self.finance_costs > 0:
            lines.append(
                f"  Interest cover:  {self.interest_cover:.2f}x"
                + ("   (below 1.25x - lenders typically want more)"
                   if self.interest_cover < Decimal("1.25") else "")
            )

        flagged = [p for p in self.properties if p.flags]
        if flagged:
            lines.append("")
            lines.append("  Queries:")
            for p in flagged:
                lines.append(f"    {p.property_id} - {p.address}")
                for flag in p.flags:
                    lines.append(f"      - {flag}")
        return "\n".join(lines)
