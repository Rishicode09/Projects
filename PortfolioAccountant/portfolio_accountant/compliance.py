"""The compliance calendar: what is due, when, and what happens if it is missed.

Most penalties a portfolio owner actually pays are not for getting a number
wrong. They are for missing a date -- the 60-day CGT return after a sale, the
14-day SDLT return after a purchase, the confirmation statement nobody
remembers. These are avoidable in a way that arguing about deductibility is
not.

This module turns the entity and property facts into dated obligations, so the
work is scheduling rather than remembering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional

from .config import Jurisdiction
from .model import Entity, EntityType, Portfolio, Property
from .money import Money


@dataclass
class Obligation:
    """One dated filing or payment obligation."""

    due: date
    title: str
    entity_id: str
    authority: str = "HMRC"
    consequence: str = ""
    detail: str = ""
    is_payment: bool = False

    def days_until(self, as_at: Optional[date] = None) -> int:
        return (self.due - (as_at or date.today())).days

    def status(self, as_at: Optional[date] = None) -> str:
        days = self.days_until(as_at)
        if days < 0:
            return "OVERDUE"
        if days <= 14:
            return "URGENT"
        if days <= 60:
            return "DUE SOON"
        return "scheduled"

    def render(self, as_at: Optional[date] = None) -> str:
        days = self.days_until(as_at)
        when = f"{abs(days)} days {'ago' if days < 0 else 'away'}"
        lines = [
            f"  {self.due}  [{self.status(as_at):<9}] {self.title}  ({when})",
            f"      {self.entity_id} - {self.authority}",
        ]
        if self.detail:
            lines.append(f"      {self.detail}")
        if self.consequence and days <= 60:
            lines.append(f"      if missed: {self.consequence}")
        return "\n".join(lines)


@dataclass
class ComplianceCalendar:
    obligations: List[Obligation] = field(default_factory=list)
    as_at: date = field(default_factory=date.today)

    def add(self, obligation: Obligation) -> None:
        self.obligations.append(obligation)

    def upcoming(self, within_days: int = 365) -> List[Obligation]:
        horizon = self.as_at + timedelta(days=within_days)
        return sorted(
            [o for o in self.obligations if o.due <= horizon],
            key=lambda o: o.due,
        )

    @property
    def overdue(self) -> List[Obligation]:
        return [o for o in self.obligations if o.due < self.as_at]

    def render(self, within_days: int = 365) -> str:
        lines = [
            "COMPLIANCE CALENDAR",
            f"  as at {self.as_at}",
            "=" * 74,
        ]
        overdue = self.overdue
        if overdue:
            lines.append("OVERDUE - deal with these first")
            for obligation in sorted(overdue, key=lambda o: o.due):
                lines.append(obligation.render(self.as_at))
            lines.append("")
            lines.append(
                "  Late filing penalties generally accrue automatically and are "
                "not negotiable on the basis of being busy. Where a deadline has "
                "genuinely been missed, filing now stops the penalty growing - a "
                "late return is better than a later one."
            )
            lines.append("")

        lines.append("Upcoming")
        for obligation in self.upcoming(within_days):
            if obligation.due >= self.as_at:
                lines.append(obligation.render(self.as_at))
        if not self.obligations:
            lines.append("  No obligations derived. Check the entity data is loaded.")
        return "\n".join(lines)


def _tax_year_bounds(jur: Jurisdiction, reference: date) -> tuple:
    """The UK tax year containing a date."""
    start_month, start_day = jur.year_start.month, jur.year_start.day
    boundary = date(reference.year, start_month, start_day)
    if reference < boundary:
        return date(reference.year - 1, start_month, start_day), boundary - timedelta(days=1)
    next_boundary = date(reference.year + 1, start_month, start_day)
    return boundary, next_boundary - timedelta(days=1)


def build_calendar(
    portfolio: Portfolio,
    jur: Jurisdiction,
    as_at: Optional[date] = None,
    recent_acquisitions: Optional[List[tuple]] = None,
) -> ComplianceCalendar:
    """Derive the obligation calendar from the portfolio's facts."""
    as_at = as_at or date.today()
    calendar = ComplianceCalendar(as_at=as_at)

    for entity in portfolio.entities.values():
        if entity.entity_type == EntityType.COMPANY:
            _add_company_obligations(calendar, entity, jur, as_at)
        else:
            _add_individual_obligations(calendar, entity, jur, as_at)

        if entity.vat_registered:
            calendar.add(
                Obligation(
                    due=_next_quarter_end(as_at) + timedelta(days=37),
                    title="VAT return and payment",
                    entity_id=entity.id,
                    detail="One month and seven days after the quarter end.",
                    consequence="Points-based late submission penalties, plus late "
                                "payment penalties escalating after 15 and 30 days.",
                    is_payment=True,
                )
            )

    # Property-driven obligations.
    for prop in portfolio.properties.values():
        if prop.disposal_date and prop.disposal_date <= as_at + timedelta(days=90):
            days = int(jur.value("capital_gains_tax.residential_reporting_days"))
            calendar.add(
                Obligation(
                    due=prop.disposal_date + timedelta(days=days),
                    title=f"CGT return and payment on account - {prop.id}",
                    entity_id=prop.owner_entity_id,
                    detail=(
                        f"UK residential disposal completed {prop.disposal_date}. A "
                        f"standalone return is due within {days} days, entirely "
                        "separate from the self-assessment return."
                    ),
                    consequence="Automatic late filing penalty, then further "
                                "penalties at 6 and 12 months, plus interest on "
                                "the unpaid tax.",
                    is_payment=True,
                )
            )

    for acquisition_date, entity_id, description in recent_acquisitions or []:
        days = int(jur.value("sdlt.filing_days"))
        calendar.add(
            Obligation(
                due=acquisition_date + timedelta(days=days),
                title=f"SDLT return and payment - {description}",
                entity_id=entity_id,
                detail=f"Due within {days} days of the effective date.",
                consequence="Automatic penalty plus interest; the window is short "
                            "and it is normally the solicitor who files, so confirm "
                            "it was actually done.",
                is_payment=True,
            )
        )

    return calendar


def _add_individual_obligations(
    calendar: ComplianceCalendar, entity: Entity, jur: Jurisdiction, as_at: date
) -> None:
    year_start, year_end = _tax_year_bounds(jur, as_at)
    filing_deadline = date(year_end.year + 1, 1, 31)

    calendar.add(
        Obligation(
            due=filing_deadline,
            title=f"Self assessment return for the year to {year_end}",
            entity_id=entity.id,
            detail="Online filing deadline. Paper returns were due by 31 October.",
            consequence="£100 immediate penalty even if no tax is due, then daily "
                        "penalties from three months, then tax-geared penalties.",
        )
    )
    calendar.add(
        Obligation(
            due=filing_deadline,
            title="Balancing payment and first payment on account",
            entity_id=entity.id,
            consequence="Interest from the due date, plus a 5% surcharge at 30 days, "
                        "6 months and 12 months.",
            is_payment=True,
        )
    )
    calendar.add(
        Obligation(
            due=date(year_end.year + 1, 7, 31),
            title="Second payment on account",
            entity_id=entity.id,
            is_payment=True,
            consequence="Interest accrues from the due date.",
        )
    )


def _add_company_obligations(
    calendar: ComplianceCalendar, entity: Entity, jur: Jurisdiction, as_at: date
) -> None:
    period_end = _company_period_end(entity, as_at)
    if period_end is None:
        return

    calendar.add(
        Obligation(
            due=_add_months(period_end, 9) + timedelta(days=1),
            title="Corporation tax payment",
            entity_id=entity.id,
            detail="Nine months and one day after the period end - three months "
                   "BEFORE the return itself is due, which surprises people.",
            consequence="Interest from the due date, non-deductible.",
            is_payment=True,
        )
    )
    calendar.add(
        Obligation(
            due=_add_months(period_end, 12),
            title="Corporation tax return (CT600)",
            entity_id=entity.id,
            consequence="£100 penalty, rising, and a further tax-geared penalty at "
                        "18 and 24 months.",
        )
    )
    calendar.add(
        Obligation(
            due=_add_months(period_end, 9),
            title="Annual accounts to Companies House",
            entity_id=entity.id,
            authority="Companies House",
            consequence="Automatic penalty from £150 to £1,500 depending on "
                        "lateness, doubled if late two years running. Persistent "
                        "default can lead to strike-off and to director "
                        "disqualification proceedings.",
        )
    )


def _company_period_end(entity: Entity, as_at: date) -> Optional[date]:
    """Next accounting period end from a 'DD-MM' setting."""
    if not entity.accounting_period_end:
        return None
    try:
        day, month = (int(part) for part in entity.accounting_period_end.split("-"))
    except ValueError:
        return None
    candidate = date(as_at.year, month, day)
    if candidate < as_at:
        candidate = date(as_at.year - 1, month, day)
    return candidate


def _add_months(when: date, months: int) -> date:
    month = when.month - 1 + months
    year = when.year + month // 12
    month = month % 12 + 1
    day = min(when.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                         else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def _next_quarter_end(as_at: date) -> date:
    month = ((as_at.month - 1) // 3 + 1) * 3
    year = as_at.year
    if month > 12:
        month, year = month - 12, year + 1
    day = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        day = 29
    return date(year, month, day)


def record_retention_note(jur: Jurisdiction) -> str:
    """What to keep and for how long."""
    return (
        "RECORD RETENTION\n"
        f"  Individuals with business or property income: "
        f"{jur.value('record_keeping.individual_years')} years from the 31 January "
        "filing deadline (TMA 1970 s.12B).\n"
        f"  Companies: {jur.value('record_keeping.company_years')} years from the "
        "end of the accounting period (Companies Act 2006 s.388).\n"
        f"  VAT: {jur.value('record_keeping.vat_years')} years.\n"
        "  Property purchase files, improvement invoices and legal documents: keep "
        "for as long as the property is owned PLUS the retention period after "
        "disposal. A 1998 extension invoice is what proves the CGT base cost in "
        "2035, and the usual retention period is no help at all there.\n"
        "  Keep records in a form that can be produced on request. Digital copies "
        "are acceptable to HMRC provided they are complete and legible."
    )
