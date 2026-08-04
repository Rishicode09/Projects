"""UK income tax computation for an individual with property and trading income.

The order of operations matters and is not obvious:

1. Adjusted net income determines whether the personal allowance is tapered.
2. Allowances are set against non-savings income first, then savings, then
   dividends.
3. Income is taxed in that same stacking order, so property profit pushes
   dividends into higher bands -- not the other way round.
4. The savings starting rate, personal savings allowance and dividend
   allowance are *nil-rate bands*, not deductions: they still use up band.
5. Section 24 finance costs are relieved last, as a basic-rate tax reducer,
   capped three ways, with the excess carried forward.

Step 5 is why a geared personal residential portfolio can show a tax bill
larger than its cash profit. The engine makes that visible rather than
burying it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from ..config import Jurisdiction
from ..money import Money, total
from .base import BandSlice, Computation, apply_nil_rate, slice_into_bands


@dataclass
class IncomeSources:
    """Everything that goes into a personal tax computation."""

    employment: Money = field(default_factory=Money.zero)
    pension_income: Money = field(default_factory=Money.zero)
    self_employment_profit: Money = field(default_factory=Money.zero)
    property_profit: Money = field(default_factory=Money.zero)
    other_non_savings: Money = field(default_factory=Money.zero)
    savings_interest: Money = field(default_factory=Money.zero)
    dividends: Money = field(default_factory=Money.zero)

    # Residential finance costs restricted under ITTOIA 2005 s.274A.
    residential_finance_costs: Money = field(default_factory=Money.zero)
    finance_costs_brought_forward: Money = field(default_factory=Money.zero)

    # Reliefs that extend the rate bands and reduce adjusted net income.
    gross_pension_contributions: Money = field(default_factory=Money.zero)
    gift_aid_gross: Money = field(default_factory=Money.zero)

    # Tax already suffered.
    paye_deducted: Money = field(default_factory=Money.zero)
    payments_on_account: Money = field(default_factory=Money.zero)

    @property
    def non_savings(self) -> Money:
        return (
            self.employment
            + self.pension_income
            + self.self_employment_profit
            + self.property_profit
            + self.other_non_savings
        )

    @property
    def total_income(self) -> Money:
        return self.non_savings + self.savings_interest + self.dividends


def compute_income_tax(
    sources: IncomeSources,
    jur: Jurisdiction,
    entity_id: str = "",
    country: str = "England",
) -> Computation:
    """Compute an individual's income tax liability with full workings."""
    comp = Computation(
        title="Income tax computation",
        entity_id=entity_id,
        period=jur.tax_year,
    )

    if country.strip().lower() in ("scotland", "wales"):
        jur.assert_supported("scottish_income_tax")

    comp.uses(
        "income_tax.personal_allowance",
        "income_tax.pa_taper_threshold",
        "income_tax.bands",
        "income_tax.dividend_allowance",
        "income_tax.dividend_rates.ordinary",
        "income_tax.savings_allowance.basic",
        "income_tax.starting_rate_for_savings.limit",
        "income_tax.finance_cost_relief_rate",
    )

    # -- 1. Adjusted net income and the personal allowance taper ---------
    band_extension = sources.gross_pension_contributions + sources.gift_aid_gross
    adjusted_net_income = sources.total_income - band_extension

    comp.step("Total income", result=sources.total_income)
    if band_extension > 0:
        comp.step(
            "Less gross pension contributions and Gift Aid",
            amount=band_extension,
            result=adjusted_net_income,
            note="Reduces adjusted net income and extends the basic and higher rate bands.",
        )

    full_pa = jur.money("income_tax.personal_allowance")
    taper_threshold = jur.money("income_tax.pa_taper_threshold")
    divisor = jur.decimal("income_tax.pa_taper_divisor")

    if adjusted_net_income > taper_threshold:
        excess = adjusted_net_income - taper_threshold
        reduction = excess / divisor
        personal_allowance = full_pa - reduction
        if personal_allowance < 0:
            personal_allowance = Money.zero()
        comp.step(
            "Personal allowance tapered",
            amount=full_pa,
            result=personal_allowance,
            note=(
                f"Adjusted net income {adjusted_net_income} exceeds {taper_threshold} "
                f"by {excess}; allowance reduced by £1 per £{divisor}. The effective "
                "marginal rate in this band is 60%, which is the single strongest "
                "argument for a pension contribution or Gift Aid payment here."
            ),
        )
        if personal_allowance.is_zero:
            comp.warn("Personal allowance fully abated.")
    else:
        personal_allowance = full_pa
        comp.step("Personal allowance", result=personal_allowance)

    # -- 2. Allowance allocation: non-savings, then savings, then dividends
    pa_remaining = personal_allowance

    def absorb(income: Money) -> tuple:
        nonlocal pa_remaining
        used = pa_remaining if pa_remaining < income else income
        pa_remaining = pa_remaining - used
        return income - used, used

    taxable_non_savings, pa_ns = absorb(sources.non_savings)
    taxable_savings, pa_sv = absorb(sources.savings_interest)
    taxable_dividends, pa_dv = absorb(sources.dividends)

    comp.step(
        "Taxable non-savings income",
        amount=sources.non_savings,
        result=taxable_non_savings,
        note=f"after {pa_ns} of personal allowance"
        + (
            f" (includes property profit {sources.property_profit})"
            if sources.property_profit > 0
            else ""
        ),
    )
    if sources.savings_interest > 0:
        comp.step(
            "Taxable savings income",
            amount=sources.savings_interest,
            result=taxable_savings,
            note=f"after {pa_sv} of personal allowance",
        )
    if sources.dividends > 0:
        comp.step(
            "Taxable dividend income",
            amount=sources.dividends,
            result=taxable_dividends,
            note=f"after {pa_dv} of personal allowance",
        )

    taxable_total = taxable_non_savings + taxable_savings + taxable_dividends

    # -- 3. Non-savings income across the bands --------------------------
    bands = jur.bands("income_tax.bands")
    ns_slices = slice_into_bands(
        taxable_non_savings, bands, Money.zero(), extension=band_extension
    )
    used = taxable_non_savings

    # -- 4. Savings income: starting rate, then PSA, then normal bands ----
    sv_slices: List[BandSlice] = []
    if taxable_savings > 0:
        starting_limit = jur.money("income_tax.starting_rate_for_savings.limit")
        starting_available = starting_limit - taxable_non_savings
        if starting_available < 0:
            starting_available = Money.zero()

        psa = _personal_savings_allowance(taxable_total, jur, comp)
        nil_band = starting_available + psa

        sv_slices = slice_into_bands(
            taxable_savings, bands, used, extension=band_extension
        )
        sv_slices = apply_nil_rate(sv_slices, nil_band)
        used = used + taxable_savings

        if starting_available > 0:
            comp.step(
                "Starting rate for savings available",
                result=starting_available,
                note="Reduced £1 for £1 by non-savings income above the personal allowance.",
            )
        comp.step("Personal savings allowance", result=psa)

    # -- 5. Dividends: allowance as a nil-rate band ----------------------
    dv_slices: List[BandSlice] = []
    if taxable_dividends > 0:
        dividend_bands = [
            {"name": "basic", "upper": bands[0]["upper"],
             "rate": jur.decimal("income_tax.dividend_rates.ordinary")},
            {"name": "higher", "upper": bands[1]["upper"],
             "rate": jur.decimal("income_tax.dividend_rates.upper")},
            {"name": "additional", "upper": None,
             "rate": jur.decimal("income_tax.dividend_rates.additional")},
        ]
        dv_slices = slice_into_bands(
            taxable_dividends, dividend_bands, used, extension=band_extension
        )
        allowance = jur.money("income_tax.dividend_allowance")
        dv_slices = apply_nil_rate(dv_slices, allowance)
        comp.step(
            "Dividend allowance",
            result=allowance,
            note="A nil-rate band: it still uses up basic rate band, so it does not "
                 "shelter other income.",
        )

    # -- 6. Tax on each slice --------------------------------------------
    def charge(label: str, slices: List[BandSlice]) -> Money:
        subtotal = Money.zero()
        for sl in slices:
            if sl.amount.is_zero:
                continue
            tax = sl.tax
            comp.step(f"  {label} - {sl.band}", amount=sl.amount, rate=sl.rate, result=tax)
            subtotal = subtotal + tax
        return subtotal

    comp.step("Tax charged:")
    tax_ns = charge("non-savings", ns_slices)
    tax_sv = charge("savings", sv_slices)
    tax_dv = charge("dividends", dv_slices)
    tax_before_reducers = tax_ns + tax_sv + tax_dv
    comp.step("Income tax before reducers", result=tax_before_reducers)

    # -- 7. Section 24 finance cost tax reducer ---------------------------
    finance_costs = sources.residential_finance_costs + sources.finance_costs_brought_forward
    reducer = Money.zero()
    excess_carried = Money.zero()

    if finance_costs > 0:
        relief_rate = jur.decimal("income_tax.finance_cost_relief_rate")
        # Capped at the lowest of: finance costs, property profits, and
        # adjusted total income above the personal allowance.
        adjusted_total_income = sources.non_savings - personal_allowance
        if adjusted_total_income < 0:
            adjusted_total_income = Money.zero()

        cap_basis = min(
            [finance_costs, sources.property_profit, adjusted_total_income],
            key=lambda m: m.amount,
        )
        reducer = cap_basis * relief_rate

        comp.step(
            "Section 24 finance costs",
            amount=finance_costs,
            note=(
                f"restricted to the lowest of: finance costs {finance_costs}, "
                f"property profits {sources.property_profit}, adjusted total income "
                f"above the allowance {adjusted_total_income}"
            ),
        )
        comp.step(
            "  Basic rate tax reducer",
            amount=cap_basis,
            rate=relief_rate,
            result=reducer,
        )

        if cap_basis < finance_costs:
            excess_carried = finance_costs - cap_basis
            comp.step(
                "  Unrelieved finance costs carried forward",
                result=excess_carried,
                note="Carried forward indefinitely against future property profits "
                     "of the same property business.",
            )
            comp.carried_forward["unrelieved_finance_costs"] = excess_carried

        # Cannot create a repayment.
        if reducer > tax_before_reducers:
            comp.warn(
                f"Tax reducer {reducer} exceeds the liability {tax_before_reducers}; "
                "restricted to nil. The unused element is not repayable."
            )
            reducer = tax_before_reducers

        comp.assume(
            "All finance costs entered relate to residential property held "
            "personally. Commercial property and company-held property are not "
            "restricted and should be deducted as an expense instead."
        )

    liability = tax_before_reducers - reducer
    if liability < 0:
        liability = Money.zero()

    # -- 8. Class 4 NIC on trading profit ---------------------------------
    class4 = _class4_nic(sources.self_employment_profit, jur, comp)

    total_due = liability + class4
    already_paid = sources.paye_deducted + sources.payments_on_account
    balance = total_due - already_paid

    comp.totals = {
        "income_tax": liability.quantize(),
        "class_4_nic": class4.quantize(),
        "total": total_due.quantize(),
        "already_paid": already_paid.quantize(),
        "balance_due": balance.quantize(),
    }

    # -- 9. Standing caveats ---------------------------------------------
    if sources.property_profit > 0 and sources.residential_finance_costs > 0:
        effective = (
            (liability.amount / sources.property_profit.amount * 100)
            if sources.property_profit.amount
            else Decimal(0)
        )
        comp.step(
            "Memo: tax as a share of property profit",
            note=f"{effective:.1f}% - note that property profit here is stated "
                 "BEFORE finance costs, because s.24 disallows them as a deduction.",
        )

    comp.assume(
        "Rates and thresholds are those in the loaded jurisdiction file; confirm "
        "each against HMRC before relying on the figure."
    )
    comp.assume(
        "Allowances are allocated in the standard order (non-savings, savings, "
        "dividends). HMRC's calculator applies a beneficial allocation in some "
        "cases, which can produce a slightly lower liability."
    )
    comp.refer(
        "This is a computation, not a tax return. It must be reviewed by a person "
        "who can see the underlying records before anything is filed."
    )

    for warning in _completeness_checks(sources):
        comp.warn(warning)

    return comp


def _personal_savings_allowance(
    taxable_total: Money, jur: Jurisdiction, comp: Computation
) -> Money:
    """PSA depends on the taxpayer's highest rate band."""
    basic_limit = jur.money("income_tax.basic_rate_limit")
    higher_limit = jur.money("income_tax.higher_rate_limit")
    if taxable_total <= basic_limit:
        return jur.money("income_tax.savings_allowance.basic")
    if taxable_total <= higher_limit:
        return jur.money("income_tax.savings_allowance.higher")
    return jur.money("income_tax.savings_allowance.additional")


def _class4_nic(profit: Money, jur: Jurisdiction, comp: Computation) -> Money:
    """Class 4 NIC on self-employment profit only.

    Property income does not attract Class 4 NIC unless the activity amounts to
    a trade. That question is fact-specific and the engine will not decide it.
    """
    if profit <= 0:
        return Money.zero()

    comp.uses(
        "national_insurance.class4_lower_profits_limit",
        "national_insurance.class4_upper_profits_limit",
        "national_insurance.class4_main_rate",
        "national_insurance.class4_additional_rate",
    )
    lower = jur.money("national_insurance.class4_lower_profits_limit")
    upper = jur.money("national_insurance.class4_upper_profits_limit")
    main_rate = jur.decimal("national_insurance.class4_main_rate")
    add_rate = jur.decimal("national_insurance.class4_additional_rate")

    if profit <= lower:
        return Money.zero()

    main_band = (profit if profit < upper else upper) - lower
    main_nic = main_band * main_rate
    comp.step("Class 4 NIC - main rate", amount=main_band, rate=main_rate, result=main_nic)

    additional_nic = Money.zero()
    if profit > upper:
        additional_band = profit - upper
        additional_nic = additional_band * add_rate
        comp.step(
            "Class 4 NIC - additional rate",
            amount=additional_band,
            rate=add_rate,
            result=additional_nic,
        )

    return main_nic + additional_nic


def _completeness_checks(sources: IncomeSources) -> List[str]:
    """Things a preparer would query before signing anything."""
    issues = []
    if sources.property_profit > 0 and sources.residential_finance_costs.is_zero:
        issues.append(
            "Property profit is present but no residential finance costs were "
            "entered. If any property is mortgaged, the s.24 reducer is being "
            "missed and the liability is overstated."
        )
    if sources.dividends > 0 and sources.self_employment_profit > 0:
        issues.append(
            "Both dividends and self-employment profit present. Confirm the "
            "dividends were properly declared out of distributable reserves; an "
            "unlawful distribution is repayable and can be recharacterised as "
            "salary or a loan."
        )
    if sources.gross_pension_contributions > 0:
        issues.append(
            "Pension contributions entered gross. Confirm they are within the "
            "annual allowance and relevant UK earnings; property income alone is "
            "not relevant earnings for pension relief purposes."
        )
    return issues
