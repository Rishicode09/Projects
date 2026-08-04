"""Financial statements: profit and loss, balance sheet, and the tax bridge.

The tax bridge is the part worth reading. Accounting profit and taxable profit
are different numbers, and the reconciliation between them is where every
adjustment lives -- depreciation added back, entertaining disallowed, capital
allowances claimed, and for a personal residential portfolio, finance costs
denied under Section 24.

Presenting the two figures side by side with the bridge between them answers
the question people actually ask, which is "why is my tax bill bigger than my
profit".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from .ledger import AccountType, Ledger
from .money import Money, total


@dataclass
class ProfitAndLoss:
    entity_id: str
    period_start: date
    period_end: date
    income: Dict[str, Money] = field(default_factory=dict)
    expenses: Dict[str, Money] = field(default_factory=dict)
    account_names: Dict[str, str] = field(default_factory=dict)

    @property
    def total_income(self) -> Money:
        return total(self.income.values())

    @property
    def total_expenses(self) -> Money:
        return total(self.expenses.values())

    @property
    def profit(self) -> Money:
        return self.total_income - self.total_expenses

    def render(self) -> str:
        width = 62
        lines = [
            "PROFIT AND LOSS ACCOUNT",
            f"  {self.entity_id}   {self.period_start} to {self.period_end}",
            "=" * width,
            "Income",
        ]
        for code, amount in sorted(self.income.items()):
            name = self.account_names.get(code, code)
            lines.append(f"  {code} {name[:38]:<38}{str(amount):>16}")
        lines.append(f"  {'':<43}{'-' * 15:>16}")
        lines.append(f"  {'Total income':<43}{str(self.total_income):>16}")
        lines.append("")
        lines.append("Expenses")
        for code, amount in sorted(self.expenses.items()):
            name = self.account_names.get(code, code)
            lines.append(f"  {code} {name[:38]:<38}{str(amount):>16}")
        lines.append(f"  {'':<43}{'-' * 15:>16}")
        lines.append(f"  {'Total expenses':<43}{str(self.total_expenses):>16}")
        lines.append("=" * width)
        label = "PROFIT" if not self.profit.is_negative else "LOSS"
        lines.append(f"  {label:<43}{str(self.profit):>16}")
        return "\n".join(lines)


@dataclass
class BalanceSheet:
    entity_id: str
    as_at: date
    assets: Dict[str, Money] = field(default_factory=dict)
    liabilities: Dict[str, Money] = field(default_factory=dict)
    equity: Dict[str, Money] = field(default_factory=dict)
    retained_profit: Money = field(default_factory=Money.zero)
    profit_for_period: Money = field(default_factory=Money.zero)
    account_names: Dict[str, str] = field(default_factory=dict)

    @property
    def total_assets(self) -> Money:
        return total(self.assets.values())

    @property
    def total_liabilities(self) -> Money:
        return total(self.liabilities.values())

    @property
    def net_assets(self) -> Money:
        return self.total_assets - self.total_liabilities

    @property
    def total_equity(self) -> Money:
        return total(self.equity.values()) + self.retained_profit

    @property
    def balances(self) -> bool:
        return (self.net_assets - self.total_equity).quantize().is_zero

    def render(self) -> str:
        width = 62
        lines = [
            "BALANCE SHEET",
            f"  {self.entity_id}   as at {self.as_at}",
            "=" * width,
            "Assets",
        ]
        for code, amount in sorted(self.assets.items()):
            lines.append(
                f"  {code} {self.account_names.get(code, code)[:38]:<38}{str(amount):>16}"
            )
        lines.append(f"  {'Total assets':<43}{str(self.total_assets):>16}")
        lines.append("")
        lines.append("Liabilities")
        for code, amount in sorted(self.liabilities.items()):
            lines.append(
                f"  {code} {self.account_names.get(code, code)[:38]:<38}{str(amount):>16}"
            )
        lines.append(f"  {'Total liabilities':<43}{str(self.total_liabilities):>16}")
        lines.append("=" * width)
        lines.append(f"  {'NET ASSETS':<43}{str(self.net_assets):>16}")
        lines.append("")
        lines.append("Represented by")
        for code, amount in sorted(self.equity.items()):
            lines.append(
                f"  {code} {self.account_names.get(code, code)[:38]:<38}{str(amount):>16}"
            )
        lines.append(f"  {'Retained earnings':<43}{str(self.retained_profit):>16}")
        lines.append(f"  {'TOTAL EQUITY':<43}{str(self.total_equity):>16}")
        lines.append(f"  {'  of which, profit for the period':<43}{str(self.profit_for_period):>16}")
        if not self.balances:
            lines.append("")
            lines.append(
                f"  ** DOES NOT BALANCE: net assets {self.net_assets} against equity "
                f"{self.total_equity}, difference {(self.net_assets - self.total_equity)}. "
                "Do not issue these figures."
            )
        return "\n".join(lines)


def build_profit_and_loss(
    ledger: Ledger, entity_id: str, start: date, end: date
) -> ProfitAndLoss:
    pl = ProfitAndLoss(entity_id=entity_id, period_start=start, period_end=end)
    pl.income = ledger.totals_by_type(AccountType.INCOME, entity_id, start, end)
    pl.expenses = ledger.totals_by_type(AccountType.EXPENSE, entity_id, start, end)
    pl.account_names = {code: acc.name for code, acc in ledger.accounts.items()}
    return pl


def build_balance_sheet(
    ledger: Ledger, entity_id: str, as_at: date, period_start: Optional[date] = None
) -> BalanceSheet:
    bs = BalanceSheet(entity_id=entity_id, as_at=as_at)
    bs.assets = ledger.totals_by_type(AccountType.ASSET, entity_id, end=as_at)
    bs.liabilities = ledger.totals_by_type(AccountType.LIABILITY, entity_id, end=as_at)
    bs.equity = ledger.totals_by_type(AccountType.EQUITY, entity_id, end=as_at)

    # A balance sheet is cumulative: retained earnings are every profit ever
    # made, not just this period's. Restricting this to the reporting period
    # makes the statement fail to balance whenever the ledger holds anything
    # dated before the period start -- which it almost always does.
    bs.retained_profit = _net_profit(ledger, entity_id, None, as_at)
    bs.profit_for_period = _net_profit(ledger, entity_id, period_start, as_at)
    bs.account_names = {code: acc.name for code, acc in ledger.accounts.items()}
    return bs


def _net_profit(
    ledger: Ledger, entity_id: str, start: Optional[date], end: date
) -> Money:
    income = total(
        ledger.totals_by_type(AccountType.INCOME, entity_id, start, end).values()
    )
    expenses = total(
        ledger.totals_by_type(AccountType.EXPENSE, entity_id, start, end).values()
    )
    return income - expenses


@dataclass
class TaxBridge:
    """Reconciliation from accounting profit to taxable profit."""

    accounting_profit: Money
    adjustments: List[tuple] = field(default_factory=list)  # (label, amount, reason)

    def add(self, label: str, amount: Money, reason: str) -> None:
        self.adjustments.append((label, amount, reason))

    @property
    def taxable_profit(self) -> Money:
        return self.accounting_profit + total(a[1] for a in self.adjustments)

    def render(self) -> str:
        lines = [
            "ACCOUNTING PROFIT TO TAXABLE PROFIT",
            "=" * 68,
            f"  {'Profit per the accounts':<46}{str(self.accounting_profit):>20}",
            "",
        ]
        for label, amount, reason in self.adjustments:
            sign = "add back" if not amount.is_negative else "deduct"
            lines.append(f"  {sign.title()}: {label[:38]:<38}{str(amount):>20}")
            lines.append(f"      {reason}")
        lines.append("=" * 68)
        lines.append(f"  {'TAXABLE PROFIT':<46}{str(self.taxable_profit):>20}")
        gap = self.taxable_profit - self.accounting_profit
        if not gap.is_zero:
            lines.append("")
            lines.append(
                f"  Taxable profit differs from accounting profit by {gap}. Every "
                "line above is a rule, not a choice - but knowing which rules bite "
                "is what makes the next decision a better one."
            )
        return "\n".join(lines)


def build_tax_bridge(
    accounting_profit: Money,
    depreciation: Optional[Money] = None,
    entertaining: Optional[Money] = None,
    capital_allowances: Optional[Money] = None,
    restricted_finance_costs: Optional[Money] = None,
    other_disallowed: Optional[Money] = None,
) -> TaxBridge:
    """Build the standard bridge for a property and trading business."""
    bridge = TaxBridge(accounting_profit=accounting_profit)

    if depreciation and not depreciation.is_zero:
        bridge.add(
            "Depreciation",
            abs(depreciation),
            "Never deductible for tax. Capital allowances replace it where the "
            "asset qualifies - and for a residential dwelling, usually nothing does.",
        )
    if entertaining and not entertaining.is_zero:
        bridge.add(
            "Client entertaining",
            abs(entertaining),
            "Disallowed outright, however commercially necessary it was. Staff "
            "entertaining is treated differently and may be allowable.",
        )
    if restricted_finance_costs and not restricted_finance_costs.is_zero:
        bridge.add(
            "Residential finance costs",
            abs(restricted_finance_costs),
            "Section 24 denies the deduction entirely. Relief returns later as a "
            "basic-rate tax reducer, which is worth less than a deduction to any "
            "higher-rate taxpayer.",
        )
    if other_disallowed and not other_disallowed.is_zero:
        bridge.add(
            "Other disallowable expenditure",
            abs(other_disallowed),
            "Fines, penalties and non-business expenditure.",
        )
    if capital_allowances and not capital_allowances.is_zero:
        bridge.add(
            "Capital allowances",
            -abs(capital_allowances),
            "Statutory relief for qualifying capital expenditure, claimed in place "
            "of depreciation.",
        )
    return bridge
