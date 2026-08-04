"""Audit and internal control review.

This module implements the reviewer's side of the work, and it is deliberately
separate from the preparation code. The reason is professional rather than
technical: a review performed by whoever prepared the figures is not a review.
It is called the self-review threat, and it is the reason auditors are required
to be independent of the accounts they examine.

An AI agent makes that threat sharper, not softer. The same system that
classified a transaction will happily "verify" its own classification, and it
will be wrong with exactly the same confidence in both directions. So the
checks here test the *records against external evidence* -- bank statements,
counts, documents -- rather than testing the records against the reasoning that
produced them.

What this module cannot do: give an audit opinion. A statutory audit is a
regulated activity performed by a registered auditor. This produces a review
file, which is a different and lesser thing, and it is labelled as such
everywhere it appears.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from .classify import AWAITING_EVIDENCE, SUSPENSE_ACCOUNT
from .config import Jurisdiction
from .ledger import Ledger
from .model import Transaction
from .money import Money, total


@dataclass
class ControlCheck:
    """One internal control test and its outcome."""

    name: str
    passed: bool
    detail: str
    risk_if_failed: str = ""
    severity: str = "medium"

    def render(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        line = f"  [{mark}] {self.name}\n        {self.detail}"
        if not self.passed and self.risk_if_failed:
            line += f"\n        risk: {self.risk_if_failed}"
        return line


@dataclass
class ReviewFile:
    """The output of a review -- explicitly not an audit opinion."""

    entity_id: str
    period: str
    checks: List[ControlCheck] = field(default_factory=list)
    materiality: Money = field(default_factory=Money.zero)
    trivial_threshold: Money = field(default_factory=Money.zero)
    sample: List[Transaction] = field(default_factory=list)
    unadjusted_differences: List[str] = field(default_factory=list)
    prepared_by: str = ""
    reviewed_by: str = ""
    ledger_hash: str = ""

    @property
    def failures(self) -> List[ControlCheck]:
        return [c for c in self.checks if not c.passed]

    @property
    def is_clean(self) -> bool:
        return not self.failures

    def render(self) -> str:
        lines = [
            "REVIEW FILE  (not a statutory audit)",
            f"  entity:      {self.entity_id}",
            f"  period:      {self.period}",
            f"  materiality: {self.materiality}  (trivial below {self.trivial_threshold})",
            f"  prepared by: {self.prepared_by or 'unrecorded'}",
            f"  reviewed by: {self.reviewed_by or 'NOT YET REVIEWED BY A PERSON'}",
            f"  ledger hash: {self.ledger_hash}",
            "=" * 74,
            "Control checks",
        ]
        for check in self.checks:
            lines.append(check.render())

        if self.sample:
            lines.append("")
            lines.append(f"Sample selected for vouching ({len(self.sample)} items)")
            lines.append(
                "  Trace each to its invoice or contract and confirm the amount, "
                "the date, the payee and the business purpose."
            )
            for txn in self.sample:
                lines.append(
                    f"    {txn.date}  {txn.description[:36]:<36} "
                    f"{str(txn.amount):>12}  [{txn.source_ref}]"
                )

        lines.append("")
        lines.append("-" * 74)
        if self.is_clean:
            lines.append(
                "No control failures identified by the tests applied. This is a "
                "limited review, not assurance: these tests examine the records "
                "that exist and cannot detect income that was never recorded."
            )
        else:
            lines.append(
                f"{len(self.failures)} control failure(s) require resolution before "
                "these figures are used for any filing or given to a lender."
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Materiality
# ---------------------------------------------------------------------------


def calculate_materiality(
    revenue: Money, jur: Jurisdiction, risk_factor: Decimal = Decimal("1")
) -> tuple:
    """Materiality benchmark, reduced where risk is elevated.

    Materiality is a judgement, not arithmetic. The percentage below is a
    starting benchmark; lower it where there is a bank covenant nearby, a
    disposal in prospect, or any fraud indicator, because in those situations a
    smaller error changes a decision.
    """
    percent = jur.decimal("materiality.default_percent_of_revenue") * risk_factor
    materiality = revenue * percent
    trivial = materiality * jur.decimal("materiality.trivial_percent_of_materiality")
    return materiality.quantize(), trivial.quantize()


# ---------------------------------------------------------------------------
# Control checks
# ---------------------------------------------------------------------------


def check_trial_balance(ledger: Ledger, entity_id: str = "") -> ControlCheck:
    difference = ledger.trial_balance_check(entity_id or None)
    return ControlCheck(
        name="Trial balance agrees",
        passed=difference.quantize().is_zero,
        detail=f"debits less credits = {difference.quantize()}",
        risk_if_failed="The ledger does not balance. Every figure derived from it "
                       "is unreliable until this is resolved.",
        severity="high",
    )


def check_bank_reconciliation(
    ledger_balance: Money, statement_balance: Money, account: str = "bank"
) -> ControlCheck:
    """The single most valuable control there is.

    It ties the books to a document produced by an independent third party.
    Almost no other check has that property.
    """
    difference = (ledger_balance - statement_balance).quantize()
    return ControlCheck(
        name=f"Bank reconciliation - {account}",
        passed=difference.is_zero,
        detail=(
            f"ledger {ledger_balance.quantize()} vs statement "
            f"{statement_balance.quantize()}, difference {difference}"
        ),
        risk_if_failed=(
            "An unreconciled difference means either a missing transaction or a "
            "duplicated one. Missing receipts understate income; missing payments "
            "overstate profit. Resolve to nil, not to 'close enough'."
        ),
        severity="high",
    )


def check_suspense_cleared(
    transactions: Sequence[Transaction], materiality: Money
) -> ControlCheck:
    stuck = [
        t for t in transactions if t.category in (SUSPENSE_ACCOUNT, AWAITING_EVIDENCE)
    ]
    value = total(abs(t.amount) for t in stuck)
    return ControlCheck(
        name="Suspense accounts cleared",
        passed=value <= materiality,
        detail=f"{len(stuck)} item(s) totalling {value} remain unclassified "
               f"(materiality {materiality})",
        risk_if_failed=(
            "Unclassified items above materiality mean the profit figure is not "
            "yet determined. Each one is either an expense, a capital item or "
            "drawings, and the three have entirely different tax outcomes."
        ),
        severity="high",
    )


def check_no_deleted_entries(ledger: Ledger) -> ControlCheck:
    """Corrections should appear as reversals, never as vanished entries."""
    reversals = [j for j in ledger.journals if j.reverses]
    orphaned = [
        j for j in reversals
        if not any(other.id == j.reverses for other in ledger.journals)
    ]
    return ControlCheck(
        name="Audit trail intact",
        passed=not orphaned,
        detail=(
            f"{len(ledger.journals)} journals, {len(reversals)} corrections, "
            f"{len(orphaned)} reversal(s) referencing a missing original"
        ),
        risk_if_failed=(
            "A reversal whose original cannot be found suggests entries have been "
            "removed rather than corrected. This is the pattern regulators look "
            "for first."
        ),
        severity="high",
    )


def check_segregation_of_duties(prepared_by: str, reviewed_by: str) -> ControlCheck:
    """Preparer and reviewer must be different people."""
    prepared = (prepared_by or "").strip().lower()
    reviewed = (reviewed_by or "").strip().lower()
    passed = bool(prepared) and bool(reviewed) and prepared != reviewed
    if not reviewed:
        detail = "no reviewer recorded"
    elif prepared == reviewed:
        detail = f"'{prepared_by}' both prepared and reviewed these figures"
    else:
        detail = f"prepared by {prepared_by}, reviewed by {reviewed_by}"
    return ControlCheck(
        name="Segregation of duties",
        passed=passed,
        detail=detail,
        risk_if_failed=(
            "Preparation and review by the same party is a self-review threat. "
            "Where an AI agent both prepares and checks the figures, the review "
            "adds no assurance at all: the same reasoning produces the same "
            "error twice. A named person must review before anything is filed."
        ),
        severity="high",
    )


def check_income_completeness(
    transactions: Sequence[Transaction],
    expected_monthly_rent: Money,
    months: int,
) -> ControlCheck:
    """Compare rent received against rent contractually due.

    Completeness of income is the hardest assertion to test, because the
    evidence for income that was never banked does not exist in the records.
    Comparing to the tenancy agreements is one of the few ways in.
    """
    received = total(
        t.amount for t in transactions if t.is_money_in and t.category.startswith("40")
    )
    expected = expected_monthly_rent * months
    shortfall = expected - received
    tolerance = expected * Decimal("0.02")
    return ControlCheck(
        name="Rental income completeness",
        passed=abs(shortfall) <= tolerance,
        detail=(
            f"expected {expected} over {months} months per the tenancy terms, "
            f"received {received}, difference {shortfall}"
        ),
        risk_if_failed=(
            "A shortfall is arrears, a void, a rent reduction, or income that did "
            "not reach the recorded account. Only the last is a problem, but it is "
            "the one that has to be ruled out explicitly."
        ),
        severity="high",
    )


def check_period_locked(ledger: Ledger, period_end: date) -> ControlCheck:
    locked = any(start <= period_end <= end for start, end, _ in ledger.closed_periods)
    return ControlCheck(
        name="Prior period locked",
        passed=locked,
        detail="period is closed to further posting" if locked
        else "period remains open to posting",
        risk_if_failed=(
            "An open prior period means filed figures can still change. Close it "
            "once reported, and post corrections in the current period instead."
        ),
        severity="medium",
    )


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def select_sample(
    transactions: Sequence[Transaction],
    materiality: Money,
    sample_size: int = 25,
    seed: str = "",
) -> List[Transaction]:
    """Select items for vouching: everything material, plus a reproducible sample.

    Every item above materiality is tested, because a single error there
    matters on its own. Below that, a deterministic pseudo-random selection
    gives coverage. The selection is seeded and reproducible so that a third
    party can verify the same sample was tested -- an unreproducible sample is
    not evidence of anything.
    """
    above = [t for t in transactions if abs(t.amount) >= materiality]
    below = [t for t in transactions if abs(t.amount) < materiality]

    remaining = max(0, sample_size - len(above))
    if remaining and below:
        scored = sorted(
            below,
            key=lambda t: hashlib.sha256(
                (seed + t.fingerprint()).encode("utf-8")
            ).hexdigest(),
        )
        below_sample = scored[:remaining]
    else:
        below_sample = []

    return sorted(above + below_sample, key=lambda t: t.date)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_review(
    ledger: Ledger,
    transactions: Sequence[Transaction],
    jur: Jurisdiction,
    entity_id: str,
    period: str,
    revenue: Money,
    statement_balances: Optional[Dict[str, Money]] = None,
    expected_monthly_rent: Optional[Money] = None,
    months: int = 12,
    prepared_by: str = "",
    reviewed_by: str = "",
    risk_factor: Decimal = Decimal("1"),
) -> ReviewFile:
    """Run the standard review programme over a period."""
    materiality, trivial = calculate_materiality(revenue, jur, risk_factor)

    review = ReviewFile(
        entity_id=entity_id,
        period=period,
        materiality=materiality,
        trivial_threshold=trivial,
        prepared_by=prepared_by,
        reviewed_by=reviewed_by,
        ledger_hash=ledger.integrity_hash(),
    )

    review.checks.append(check_trial_balance(ledger, entity_id))
    review.checks.append(check_suspense_cleared(transactions, materiality))
    review.checks.append(check_no_deleted_entries(ledger))
    review.checks.append(check_segregation_of_duties(prepared_by, reviewed_by))

    for account, statement_balance in (statement_balances or {}).items():
        ledger_balance = ledger.balance(account, entity_id or None)
        review.checks.append(
            check_bank_reconciliation(ledger_balance, statement_balance, account)
        )

    if expected_monthly_rent is not None:
        review.checks.append(
            check_income_completeness(transactions, expected_monthly_rent, months)
        )

    review.sample = select_sample(
        [t for t in transactions if not t.is_money_in],
        materiality,
        seed=review.ledger_hash,
    )
    return review
