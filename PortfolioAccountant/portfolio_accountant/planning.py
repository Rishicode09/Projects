"""Tax planning: statutory reliefs used as Parliament intended.

The line this module is built around
------------------------------------

**Tax evasion** is illegal. It means misrepresenting reality to HMRC:
concealing income, inventing expenses, backdating documents, hiding ownership,
understating a disposal. It is a criminal offence and there is no version of it
this package will assist with.

**Tax avoidance schemes** are legal in the narrow sense that they are not
crimes, but they are contrived arrangements whose purpose is to produce a tax
result Parliament did not intend. They are attacked by the General Anti-Abuse
Rule (FA 2013 Part 5), unwound by the courts under the Ramsay principle,
notifiable under DOTAS, and they leave the user with interest, penalties, and
frequently an accelerated payment notice years later. This package does not
design them either -- not because they are illegal, but because they are bad
advice.

**Tax planning** is choosing between genuinely available alternatives, taking
the reliefs Parliament legislated for on the terms it set. Contributing to a
pension. Owning an asset jointly with a spouse who actually owns half of it.
Timing a disposal across a tax year end. Claiming an allowance you qualify for.
That is what this module does, and every suggestion below states the statutory
basis, the conditions that must genuinely be met, and what goes wrong if they
are not.

The test applied throughout: **would this still make sense if HMRC read the
whole file?** If a step only works when nobody looks at it, it is not planning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Optional

from .config import Jurisdiction
from .money import Money
from .properties import PortfolioSummary

# Requests this package will not assist with, at any level of insistence.
# These are not stylistic preferences; each describes conduct that is either a
# criminal offence or professional misconduct.
REFUSED = [
    "concealing or under-declaring income of any kind",
    "creating, backdating or altering an invoice, contract or receipt",
    "recording personal expenditure as a business expense",
    "hiding beneficial ownership of an asset or an income stream",
    "disguising employment as self-employment to reduce NIC",
    "moving money to obscure its source or defeat a creditor",
    "designing a contrived scheme whose main purpose is a tax advantage",
    "advising on how to avoid detection by HMRC or an auditor",
    "signing, submitting or approving a return as though a person had reviewed it",
    "presenting an estimate as a filed or agreed figure",
]

# Where a discovered problem should go, rather than being quietly fixed.
DISCLOSURE_ROUTES = {
    "past_underdeclaration": (
        "HMRC's Digital Disclosure Service, or the Let Property Campaign for "
        "undeclared rental income. An unprompted disclosure carries a materially "
        "lower penalty than one made after HMRC opens an enquiry, and in serious "
        "cases the Contractual Disclosure Facility (Code of Practice 9) offers "
        "protection from criminal prosecution. Take specialist advice before "
        "making any disclosure - the route chosen matters."
    ),
    "vat_error": (
        "Errors below the reporting threshold can be corrected on the next "
        "return; above it, form VAT652 is required. Deliberately spreading a "
        "large error across returns to stay below the threshold is itself an "
        "offence."
    ),
    "companies_house": (
        "Accounts already filed can be amended, and a voluntary amendment before "
        "anyone asks is treated far better than one extracted later."
    ),
}


@dataclass
class Opportunity:
    """A legitimate planning point, with its conditions and its risks."""

    title: str
    statutory_basis: str
    summary: str
    conditions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    indicative_benefit: Optional[Money] = None
    priority: str = "medium"
    requires_adviser: bool = True

    def render(self) -> str:
        lines = [f"[{self.priority.upper()}] {self.title}"]
        lines.append(f"    basis: {self.statutory_basis}")
        lines.append(f"    {self.summary}")
        if self.indicative_benefit is not None:
            lines.append(
                f"    indicative benefit: {self.indicative_benefit} "
                "(illustrative only - not a computation)"
            )
        if self.conditions:
            lines.append("    conditions that must genuinely be met:")
            lines.extend(f"      - {c}" for c in self.conditions)
        if self.risks:
            lines.append("    risks:")
            lines.extend(f"      ! {r}" for r in self.risks)
        if self.requires_adviser:
            lines.append(
                "    Confirm with a qualified adviser before acting. The facts that "
                "decide this are ones the engine cannot see."
            )
        return "\n".join(lines)


@dataclass
class PlanningReview:
    entity_id: str
    period: str
    opportunities: List[Opportunity] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def add(self, opportunity: Optional[Opportunity]) -> None:
        if opportunity is not None:
            self.opportunities.append(opportunity)

    def render(self) -> str:
        order = {"high": 0, "medium": 1, "low": 2}
        lines = [
            "TAX PLANNING REVIEW",
            f"  {self.entity_id}   {self.period}",
            "=" * 74,
            "Every item below is the use of a statutory relief on its own terms.",
            "None of it depends on HMRC not noticing.",
            "",
        ]
        for opp in sorted(self.opportunities, key=lambda o: order.get(o.priority, 9)):
            lines.append(opp.render())
            lines.append("")
        if self.notes:
            lines.append("-" * 74)
            lines.extend(f"  {n}" for n in self.notes)
        lines.append("-" * 74)
        lines.append(
            "This is a list of questions to put to your adviser, not advice. "
            "Tax advice is a regulated activity and depends on facts including "
            "residence, domicile, existing structures, family circumstances and "
            "intentions that are not in these records."
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_personal_allowance_taper(
    adjusted_net_income: Money, jur: Jurisdiction
) -> Optional[Opportunity]:
    """The 60% band between £100,000 and £125,140."""
    threshold = jur.money("income_tax.pa_taper_threshold")
    upper = jur.money("income_tax.higher_rate_limit")
    if not (threshold < adjusted_net_income <= upper):
        return None

    excess = adjusted_net_income - threshold
    # Every £1 contributed restores 50p of allowance, so relief is 40% on the
    # contribution plus 40% on the restored allowance.
    benefit = excess * Decimal("0.60")
    return Opportunity(
        title="Income falls in the 60% effective marginal rate band",
        statutory_basis="ITA 2007 s.35 (allowance taper); FA 2004 Part 4 (pension relief)",
        summary=(
            f"Adjusted net income of {adjusted_net_income} sits {excess} above the "
            f"taper threshold. In this band each extra pound costs 40p of tax plus "
            "the loss of 50p of personal allowance, an effective 60%. A gross "
            "pension contribution or Gift Aid payment reduces adjusted net income "
            "pound for pound and reverses the taper."
        ),
        conditions=[
            "Pension contributions must be within the annual allowance, including "
            "any tapered allowance and unused relief brought forward",
            "Relief is limited to relevant UK earnings - property income does NOT "
            "count as relevant earnings, so a pure landlord may be capped at the "
            "£3,600 gross basic amount",
            "Gift Aid requires a genuine donation to a qualifying charity; the "
            "money is actually gone",
        ],
        risks=[
            "A contribution beyond the annual allowance triggers a charge that can "
            "wipe out the saving",
            "Pension money is locked until the minimum pension age",
        ],
        indicative_benefit=benefit,
        priority="high",
    )


def check_spousal_allowances(
    portfolio_summary: PortfolioSummary, jur: Jurisdiction
) -> Optional[Opportunity]:
    """Ownership split between spouses -- a genuine transfer, not a paper one."""
    if portfolio_summary.net_operating_income <= 0:
        return None
    return Opportunity(
        title="Review ownership shares between spouses or civil partners",
        statutory_basis=(
            "TCGA 1992 s.58 (no gain/no loss transfers); ITA 2007 s.836 and "
            "Form 17 (unequal beneficial shares)"
        ),
        summary=(
            "Where one spouse pays tax at a higher rate than the other, holding "
            "property in shares that reflect who actually bears the economic "
            "interest can use both personal allowances and both basic rate bands. "
            "Transfers between spouses are on a no gain/no loss basis for CGT."
        ),
        conditions=[
            "The transfer must be a genuine, outright and unconditional gift of "
            "beneficial ownership - the recipient really does own that share, "
            "including on divorce or death",
            "Jointly held property is taxed 50/50 by default; a different split "
            "needs a declaration of trust AND a Form 17 election filed within 60 "
            "days of signing",
            "The declaration of trust must precede the income it is meant to affect",
            "SDLT can arise if the transferee takes on a share of the mortgage debt",
        ],
        risks=[
            "A transfer that is not genuine - where the transferor keeps control "
            "and the income in substance - is caught by the settlements "
            "legislation (ITTOIA 2005 Part 5 Ch.5) and the income is taxed back "
            "on the transferor",
            "Form 17 applies only to spouses and only to property held as tenants "
            "in common, and it cannot be backdated",
        ],
        priority="high",
    )


def check_section_24_structure(
    summary: PortfolioSummary, jur: Jurisdiction
) -> Optional[Opportunity]:
    """Incorporation is the obvious answer to s.24 and usually the wrong one."""
    restricted = summary.restricted_finance_costs
    if restricted <= 0:
        return None

    relief_rate = jur.decimal("income_tax.finance_cost_relief_rate")
    higher_rate = Decimal("0.40")
    cost = restricted * (higher_rate - relief_rate)

    return Opportunity(
        title="Section 24 restriction is costing real money - consider the options carefully",
        statutory_basis="ITTOIA 2005 s.274A; TCGA 1992 s.162 (incorporation relief)",
        summary=(
            f"{restricted} of residential finance costs are non-deductible. For a "
            f"higher-rate taxpayer the annual cost of the restriction is around "
            f"{cost}. Incorporation removes the restriction, because companies "
            "deduct interest in full - but incorporating an existing portfolio is "
            "a disposal at market value and is expensive to get wrong."
        ),
        conditions=[
            "Transferring property to a company is a disposal at market value for "
            "CGT, even though no money changes hands",
            "SDLT is charged on the market value, at higher rates, and often at "
            "the 17% flat rate for a company - this alone can exceed the annual "
            "saving many times over",
            "Section 162 incorporation relief can defer the CGT, but only where "
            "the whole of a genuine *business* is transferred as a going concern. "
            "Passive letting is often not a business for this purpose; the level "
            "of activity is a question of fact and HMRC contests it",
            "Existing mortgages usually have to be redeemed and replaced with "
            "company lending at higher rates, with early repayment charges",
            "Extracting profit from the company is taxed again as dividends, so "
            "the comparison must be made on money in hand, not on company profit",
        ],
        risks=[
            "The arithmetic frequently does not work for a small portfolio held a "
            "long time with large latent gains",
            "A company holding a dwelling above the ATED threshold has an annual "
            "charge and an annual return even when relief applies",
            "Promoters market incorporation aggressively, including via schemes "
            "using partnerships to sidestep SDLT. Some of these are notifiable "
            "arrangements. Be sceptical of anyone selling a structure rather than "
            "advising on one",
        ],
        indicative_benefit=cost,
        priority="high",
    )


def check_capital_vs_revenue(summary: PortfolioSummary) -> Optional[Opportunity]:
    """Repairs are deductible now; improvements only reduce a future gain."""
    if summary.gross_rent <= 0:
        return None
    return Opportunity(
        title="Classify property work correctly between repairs and improvements",
        statutory_basis="ITTOIA 2005 s.272; ITTOIA 2005 s.311A (domestic items)",
        summary=(
            "A repair restores an asset to its previous condition and is deducted "
            "against rent now. An improvement makes it better than it was and is "
            "capital, relieved only against a future capital gain. Replacing a "
            "kitchen with a comparable one is generally a repair; upgrading it "
            "substantially is not. Getting this right in both directions is worth "
            "money - claiming improvements as repairs is an error HMRC finds "
            "easily, and treating genuine repairs as capital gives away relief."
        ),
        conditions=[
            "Keep the invoice detail, not just the total - 'refurbishment £14,000' "
            "cannot be analysed later, but a specification can",
            "Where a job mixes both, apportion it on the invoice at the time",
            "Replacement of domestic items relief applies to like-for-like "
            "replacement of furnishings in a let dwelling, not to the initial "
            "provision of them",
        ],
        risks=[
            "Work done before a property is first let may be capital regardless of "
            "its nature, if the property was not in a lettable state when bought",
        ],
        priority="medium",
    )


def check_cgt_timing(
    unused_annual_exemption: Money, planned_disposal: bool = False
) -> Optional[Opportunity]:
    if unused_annual_exemption <= 0:
        return None
    return Opportunity(
        title="Annual exempt amount is partly unused",
        statutory_basis="TCGA 1992 s.1K",
        summary=(
            f"{unused_annual_exemption} of the capital gains annual exempt amount "
            "will be lost at the end of the tax year. It cannot be carried forward "
            "or transferred. Where a disposal is already intended, which side of "
            "5 April it completes on can use one exemption or two."
        ),
        conditions=[
            "The disposal date for CGT is normally the date of the unconditional "
            "contract (exchange), not completion - this catches people out in both "
            "directions",
            "The transaction must be genuine and commercially motivated; timing an "
            "intended sale is planning, manufacturing a disposal is not",
        ],
        risks=[
            "Deferring a sale for tax reasons exposes you to market movement that "
            "can dwarf the tax saved",
        ],
        indicative_benefit=None,
        priority="medium",
    )


def check_corporation_tax_band(
    taxable_profits: Money, jur: Jurisdiction, associated_companies: int = 0
) -> Optional[Opportunity]:
    divisor = associated_companies + 1
    lower = jur.money("corporation_tax.lower_limit") / divisor
    upper = jur.money("corporation_tax.upper_limit") / divisor
    if not (lower < taxable_profits < upper):
        return None
    return Opportunity(
        title="Company profits sit in the marginal relief band",
        statutory_basis="CTA 2010 s.18A-19",
        summary=(
            f"Taxable profits of {taxable_profits} fall between {lower} and "
            f"{upper}, where the effective marginal rate is about 26.5% - above "
            "the headline main rate. Deductible expenditure genuinely incurred "
            "before the period end, or employer pension contributions actually "
            "paid, relieve at that higher marginal rate."
        ),
        conditions=[
            "Expenditure must be genuinely incurred, wholly and exclusively for "
            "the trade, and for a pension contribution actually PAID before the "
            "period end - an accrual does not work",
            "Count associated companies correctly; each additional one divides "
            "both limits and can change the rate for every company in the group",
        ],
        risks=[
            "Buying something you do not need to save tax loses you the difference. "
            "Accelerating spending you were going to make anyway is the whole point",
        ],
        priority="medium",
    )


def check_mtd_readiness(
    gross_property_income: Money, gross_trading_income: Money, jur: Jurisdiction
) -> Optional[Opportunity]:
    qualifying = gross_property_income + gross_trading_income
    threshold = jur.money("mtd.itsa_threshold_2026")
    if qualifying < threshold * Decimal("0.8"):
        return None
    return Opportunity(
        title="Making Tax Digital for Income Tax will apply",
        statutory_basis="Income Tax (Digital Requirements) Regulations 2021",
        summary=(
            f"Qualifying income of {qualifying} is at or approaching the {threshold} "
            "threshold. MTD for Income Tax requires digital record keeping and "
            "quarterly updates rather than one annual return. The threshold is "
            "tested on GROSS income before expenses, so a geared portfolio with "
            "thin profits is still caught."
        ),
        conditions=[
            "Records must be kept in compatible software with digital links - a "
            "manually re-keyed spreadsheet total does not satisfy the requirement",
            "Property and self-employment income are reported as separate businesses",
        ],
        risks=[
            "Leaving the transition to the quarter it starts means the first "
            "submission is late. The bookkeeping discipline has to be in place "
            "beforehand",
        ],
        priority="high",
        requires_adviser=False,
    )


def check_payments_on_account(liability: Money, prior_liability: Money) -> Optional[Opportunity]:
    if prior_liability <= 0 or liability >= prior_liability:
        return None
    reduction = prior_liability - liability
    return Opportunity(
        title="Payments on account may be reducible",
        statutory_basis="TMA 1970 s.59A",
        summary=(
            f"The liability of {liability} is {reduction} below the prior year's "
            f"{prior_liability}, on which payments on account are based. A claim "
            "to reduce them frees up cash flow."
        ),
        conditions=[
            "The reduction must be a genuine expectation based on real "
            "circumstances, not optimism",
        ],
        risks=[
            "Reducing payments on account below the eventual liability attracts "
            "interest from the original due dates, and a careless or deliberate "
            "over-reduction can attract a penalty. Under-claiming is cheap; "
            "over-claiming is not",
        ],
        priority="low",
        requires_adviser=False,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_planning_review(
    summary: PortfolioSummary,
    jur: Jurisdiction,
    entity_id: str = "",
    adjusted_net_income: Optional[Money] = None,
    company_profits: Optional[Money] = None,
    associated_companies: int = 0,
    unused_annual_exemption: Optional[Money] = None,
    trading_income: Optional[Money] = None,
) -> PlanningReview:
    """Surface the statutory reliefs the portfolio's facts actually engage."""
    review = PlanningReview(entity_id=entity_id, period=jur.tax_year)

    if adjusted_net_income is not None:
        review.add(check_personal_allowance_taper(adjusted_net_income, jur))
    review.add(check_spousal_allowances(summary, jur))
    review.add(check_section_24_structure(summary, jur))
    review.add(check_capital_vs_revenue(summary))
    if unused_annual_exemption is not None:
        review.add(check_cgt_timing(unused_annual_exemption))
    if company_profits is not None:
        review.add(
            check_corporation_tax_band(company_profits, jur, associated_companies)
        )
    review.add(
        check_mtd_readiness(summary.gross_rent, trading_income or Money.zero(), jur)
    )

    review.notes.append(
        "Nothing here relies on non-disclosure. If a step would only work "
        "because HMRC did not see the whole picture, it is not in this list."
    )
    review.notes.append(
        "If any of these are pursued, document the commercial reasoning at the "
        "time. Contemporaneous evidence of purpose is what distinguishes ordinary "
        "planning from an arrangement, and it cannot be created afterwards."
    )
    return review
