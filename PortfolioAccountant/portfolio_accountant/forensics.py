"""Forensic review: anomaly indicators across the transaction record.

A caution that belongs at the top of the file, because it governs everything
below it. **None of these tests proves anything.** Every one of them produces
false positives, and an innocent explanation exists for almost any single
finding. A round-sum payment is usually a standing order. A weekend posting is
usually a batch job. Benford deviation on a small sample is usually noise.

What these tests do is *direct attention*. They turn ten thousand rows into a
short list worth asking about. The output is therefore always phrased as an
indicator requiring explanation, with the evidence attached, so that the person
being asked can answer it -- which is both fairer and far more effective than
an accusation.

If a finding is not resolved by an explanation, the correct next step is a
qualified forensic accountant and, where relevant, a lawyer. Not this tool.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from .model import Transaction
from .money import Money, total


class Severity:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2, INFO: 3}


@dataclass
class Finding:
    """An indicator requiring explanation -- never a conclusion."""

    test: str
    severity: str
    summary: str
    explanation_sought: str
    evidence: List[str] = field(default_factory=list)
    value_at_risk: Money = field(default_factory=Money.zero)
    innocent_explanations: List[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"[{self.severity.upper()}] {self.test}: {self.summary}"]
        if not self.value_at_risk.is_zero:
            lines.append(f"    value involved: {self.value_at_risk}")
        lines.append(f"    question to ask: {self.explanation_sought}")
        if self.innocent_explanations:
            lines.append(
                "    commonly innocent because: "
                + "; ".join(self.innocent_explanations)
            )
        for item in self.evidence[:6]:
            lines.append(f"      - {item}")
        if len(self.evidence) > 6:
            lines.append(f"      ... and {len(self.evidence) - 6} more")
        return "\n".join(lines)


@dataclass
class ForensicReport:
    findings: List[Finding] = field(default_factory=list)
    transactions_reviewed: int = 0
    period: str = ""
    evidence_hash: str = ""

    def add(self, finding: Optional[Finding]) -> None:
        if finding is not None:
            self.findings.append(finding)

    def sorted_findings(self) -> List[Finding]:
        return sorted(
            self.findings, key=lambda f: (Severity.ORDER.get(f.severity, 9), f.test)
        )

    def render(self) -> str:
        lines = [
            "Forensic review",
            f"  transactions reviewed: {self.transactions_reviewed}",
            f"  period: {self.period}",
            f"  evidence hash: {self.evidence_hash}",
            "=" * 74,
        ]
        if not self.findings:
            lines.append("  No indicators raised by the tests applied.")
            lines.append(
                "  This is not assurance that the records are complete or honest. "
                "These tests only see what was recorded; they cannot see income "
                "that never entered the books."
            )
            return "\n".join(lines)

        for finding in self.sorted_findings():
            lines.append(finding.render())
            lines.append("")

        lines.append("-" * 74)
        lines.append(
            "Every item above is an indicator, not a conclusion. Seek the "
            "explanation before drawing any inference, and document the answer "
            "next to the finding."
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Individual tests
# ---------------------------------------------------------------------------

BENFORD_EXPECTED = {
    d: Decimal(str(math.log10(1 + 1 / d))) for d in range(1, 10)
}


def benford_first_digit(
    transactions: Sequence[Transaction], minimum_sample: int = 200
) -> Optional[Finding]:
    """Compare the first-digit distribution against Benford's law.

    Genuine accounting populations that span several orders of magnitude tend
    to follow it. Fabricated figures often do not, because people invent
    numbers that feel random and over-use middle digits.

    The sample size gate matters. Below a few hundred items the test says
    nothing, and running it anyway produces confident nonsense.
    """
    digits = []
    for txn in transactions:
        magnitude = abs(txn.amount).amount
        if magnitude < 10:
            continue
        first = str(magnitude).lstrip("0.")
        first = next((c for c in first if c.isdigit() and c != "0"), None)
        if first:
            digits.append(int(first))

    if len(digits) < minimum_sample:
        return Finding(
            test="Benford first-digit",
            severity=Severity.INFO,
            summary=f"not run - only {len(digits)} usable amounts, below the "
                    f"{minimum_sample} minimum",
            explanation_sought="None. The test is unreliable on small samples and "
                               "has been skipped rather than reported.",
        )

    counts = Counter(digits)
    n = len(digits)
    chi_square = Decimal("0")
    deviations = []
    for digit in range(1, 10):
        expected = BENFORD_EXPECTED[digit] * n
        observed = Decimal(counts.get(digit, 0))
        if expected > 0:
            chi_square += (observed - expected) ** 2 / expected
        deviation = (observed - expected) / expected * 100 if expected else Decimal(0)
        deviations.append((digit, int(observed), float(expected), float(deviation)))

    # 8 degrees of freedom, ~15.51 at 95%, ~20.09 at 99%.
    if chi_square < Decimal("15.51"):
        return None

    severity = Severity.MEDIUM if chi_square < Decimal("20.09") else Severity.HIGH
    worst = sorted(deviations, key=lambda d: -abs(d[3]))[:3]
    return Finding(
        test="Benford first-digit",
        severity=severity,
        summary=f"first-digit distribution deviates from Benford's law "
                f"(chi-square {float(chi_square):.1f} on {n} amounts)",
        explanation_sought=(
            "Is there a structural reason for the distribution - for example, "
            "many transactions at a fixed price point, regulated fees, or rent at "
            "round amounts? A portfolio with 40 identical rents will fail this "
            "test honestly."
        ),
        innocent_explanations=[
            "repeated fixed-price or fixed-rent transactions",
            "a population spanning too narrow a range of magnitudes",
            "amounts set by a schedule rather than arising naturally",
        ],
        evidence=[
            f"digit {d}: observed {o}, expected {e:.0f} ({dev:+.0f}%)"
            for d, o, e, dev in worst
        ],
    )


def _is_recurring_series(items: List[Transaction]) -> bool:
    """Is this a standing order or subscription rather than a duplicate?

    Without this, every monthly agent fee and mortgage payment is reported as a
    duplicate, and a test that fires on hundreds of ordinary transactions is
    one the reader learns to ignore. A regular monthly cadence is the signature
    of a recurring arrangement, not a double payment.
    """
    if len(items) < 3:
        return False
    gaps = [(b.date - a.date).days for a, b in zip(items, items[1:])]
    monthly = [g for g in gaps if 25 <= g <= 35]
    return len(monthly) >= len(gaps) * 0.7


def duplicate_payments(
    transactions: Sequence[Transaction], window_days: int = 14
) -> Optional[Finding]:
    """Same payee, same amount, close together -- the classic double payment."""
    buckets: Dict[tuple, List[Transaction]] = defaultdict(list)
    for txn in transactions:
        if txn.is_money_in:
            continue
        key = (
            (txn.counterparty or txn.description).strip().upper()[:24],
            abs(txn.amount).quantize().amount,
        )
        buckets[key].append(txn)

    evidence = []
    at_risk = Money.zero()
    excluded_series = 0

    for (payee, amount), items in buckets.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda t: t.date)
        if _is_recurring_series(items):
            excluded_series += 1
            continue
        for earlier, later in zip(items, items[1:]):
            gap = (later.date - earlier.date).days
            if gap > window_days:
                continue
            # Different invoice numbers mean two separate liabilities. Three
            # identical safety certificates for three flats on the same day is
            # not a duplicate, and reporting it as one wastes the reader's
            # attention on the findings that matter.
            if (
                earlier.document_ref
                and later.document_ref
                and earlier.document_ref != later.document_ref
            ):
                continue
            same_document = bool(
                earlier.document_ref and earlier.document_ref == later.document_ref
            )
            evidence.append(
                f"{payee} {amount} on {earlier.date} and again on {later.date} "
                f"({gap} day gap)"
                + (
                    f" - BOTH quote document {earlier.document_ref}, which makes "
                    "this the strongest indicator in the set"
                    if same_document
                    else ""
                )
                + f" [{earlier.source_ref} / {later.source_ref}]"
            )
            at_risk = at_risk + abs(later.amount)

    if not evidence:
        return None

    return Finding(
        test="Duplicate payment",
        severity=Severity.MEDIUM if len(evidence) < 5 else Severity.HIGH,
        summary=f"{len(evidence)} pair(s) of identical payments to the same payee "
                f"within {window_days} days"
                + (
                    f" ({excluded_series} recurring monthly series excluded)"
                    if excluded_series
                    else ""
                ),
        explanation_sought=(
            "Was each pair a genuine separate liability, or has an invoice been "
            "paid twice? Duplicate payments are usually error rather than fraud, "
            "and the money is often recoverable if identified quickly."
        ),
        innocent_explanations=[
            "genuine recurring charges at a fixed amount",
            "deposits and first month's rent of the same value",
            "instalments on a payment plan",
        ],
        evidence=evidence,
        value_at_risk=at_risk,
    )


def round_sum_payments(
    transactions: Sequence[Transaction], threshold: Money = None, minimum_count: int = 5
) -> Optional[Finding]:
    """Unusually many large, perfectly round payments."""
    threshold = threshold or Money(1000)
    hits = [
        t
        for t in transactions
        if not t.is_money_in
        and abs(t.amount) >= threshold
        and abs(t.amount).amount % 100 == 0
    ]
    if len(hits) < minimum_count:
        return None

    large_payments = [t for t in transactions if not t.is_money_in and abs(t.amount) >= threshold]
    ratio = Decimal(len(hits)) / Decimal(len(large_payments)) * 100 if large_payments else Decimal(0)
    if ratio < 25:
        return None

    return Finding(
        test="Round-sum payments",
        severity=Severity.LOW if ratio < 50 else Severity.MEDIUM,
        summary=f"{len(hits)} of {len(large_payments)} payments over {threshold} "
                f"are exact multiples of £100 ({ratio:.0f}%)",
        explanation_sought=(
            "Are these against priced invoices, or are they estimates and "
            "on-account payments? Round sums to contractors without a matching "
            "priced invoice are worth tracing to the underlying work."
        ),
        innocent_explanations=[
            "standing orders and regular transfers",
            "loan repayments and drawings, which are naturally round",
            "deposits and retainers",
        ],
        evidence=[
            f"{t.date} {t.counterparty or t.description[:30]} {abs(t.amount)} "
            f"[{t.source_ref}]"
            for t in sorted(hits, key=lambda t: -abs(t.amount).amount)[:8]
        ],
        value_at_risk=total(abs(t.amount) for t in hits),
    )


def threshold_structuring(
    transactions: Sequence[Transaction],
    thresholds: Sequence[Money],
    band: Decimal = Decimal("0.05"),
) -> Optional[Finding]:
    """Payments clustering just below an approval or reporting threshold."""
    # Approval limits govern spending, so only payments are relevant. Including
    # receipts turns a rent roll of identical amounts into a false positive.
    payments = [t for t in transactions if not t.is_money_in]
    evidence = []
    for threshold in thresholds:
        floor = threshold * (1 - band)
        near = [t for t in payments if floor <= abs(t.amount) < threshold]
        just_over = [
            t for t in payments if threshold <= abs(t.amount) <= threshold * (1 + band)
        ]
        if len(near) >= 3 and len(near) > len(just_over) * 2:
            evidence.append(
                f"{len(near)} payments between {floor} and {threshold}, "
                f"against only {len(just_over)} just above it"
            )
            evidence.extend(
                f"    {t.date} {t.counterparty or t.description[:28]} "
                f"{abs(t.amount)} [{t.source_ref}]"
                for t in sorted(near, key=lambda t: -abs(t.amount).amount)[:4]
            )

    if not evidence:
        return None

    return Finding(
        test="Threshold clustering",
        severity=Severity.MEDIUM,
        summary="payments cluster just below a control or reporting threshold",
        explanation_sought=(
            "Is there a commercial reason the amounts sit just under the "
            "threshold, or has work been split to stay below an approval limit? "
            "Ask who set the amounts and whether the underlying job was priced "
            "as a whole."
        ),
        innocent_explanations=[
            "a supplier pricing to a known budget",
            "genuine phased work invoiced in stages",
            "coincidence, which is common with few data points",
        ],
        evidence=evidence,
    )


def weekend_and_backdated(
    transactions: Sequence[Transaction], period_end: Optional[date] = None
) -> Optional[Finding]:
    """Entries dated at unusual times, and bunching right before a period end."""
    weekend = [t for t in transactions if t.date.weekday() >= 5]
    evidence = []
    severity = Severity.LOW

    if weekend and len(weekend) > len(transactions) * 0.15:
        evidence.append(
            f"{len(weekend)} of {len(transactions)} entries are dated on a weekend "
            f"({len(weekend) / len(transactions) * 100:.0f}%)"
        )

    if period_end:
        window_start = period_end - timedelta(days=7)
        late = [
            t
            for t in transactions
            if window_start <= t.date <= period_end and not t.is_money_in
        ]
        expected_weekly = len(transactions) / 52 if transactions else 0
        if expected_weekly and len(late) > expected_weekly * 3:
            severity = Severity.MEDIUM
            evidence.append(
                f"{len(late)} payments in the final week before {period_end}, "
                f"against a weekly average of {expected_weekly:.1f}"
            )
            evidence.extend(
                f"    {t.date} {t.counterparty or t.description[:28]} "
                f"{abs(t.amount)} [{t.source_ref}]"
                for t in sorted(late, key=lambda t: -abs(t.amount).amount)[:5]
            )

    if not evidence:
        return None

    return Finding(
        test="Timing anomalies",
        severity=severity,
        summary="entries cluster at unusual dates",
        explanation_sought=(
            "For period-end bunching: was the expenditure genuinely incurred "
            "before the year end, or has the date been chosen to move a deduction "
            "into this period? The invoice date and the delivery of the goods or "
            "services are what matter, not the payment date."
        ),
        innocent_explanations=[
            "batch processing that posts on a fixed day",
            "genuine year-end purchasing and stock-up",
            "quarterly bills that happen to fall near the period end",
        ],
        evidence=evidence,
    )


def related_party_flows(
    transactions: Sequence[Transaction], related_names: Sequence[str]
) -> Optional[Finding]:
    """Payments to or from connected people and entities."""
    if not related_names:
        return None
    patterns = [
        (name, re.compile(re.escape(name), re.IGNORECASE)) for name in related_names if name
    ]
    hits = []
    for txn in transactions:
        haystack = f"{txn.counterparty} {txn.description}"
        for name, pattern in patterns:
            if pattern.search(haystack):
                hits.append((name, txn))
                break

    if not hits:
        return None

    return Finding(
        test="Related party transactions",
        severity=Severity.MEDIUM,
        summary=f"{len(hits)} transaction(s) involve a declared related party",
        explanation_sought=(
            "Were these on arm's length terms, and are they disclosed? Related "
            "party transactions are entirely legitimate and extremely common in a "
            "family property business. The risk is not the transaction, it is the "
            "non-disclosure: they require disclosure in company accounts, they can "
            "be recharacterised for tax if not at market value, and a director's "
            "loan account that goes overdrawn triggers a s.455 charge."
        ),
        innocent_explanations=[
            "normal funding of an SPV by its owner",
            "a spouse genuinely employed in the business at a commercial wage",
            "rent paid between entities under a written lease",
        ],
        evidence=[
            f"{t.date} {name}: {t.description[:34]} {t.amount} [{t.source_ref}]"
            for name, t in sorted(hits, key=lambda h: h[1].date)[:10]
        ],
        value_at_risk=total(abs(t.amount) for _, t in hits),
    )


def missing_evidence(transactions: Sequence[Transaction]) -> Optional[Finding]:
    """Deductions claimed without a document reference."""
    hits = [
        t
        for t in transactions
        if not t.is_money_in and not t.document_ref and abs(t.amount) >= Money(100)
    ]
    if not hits:
        return None
    at_risk = total(abs(t.amount) for t in hits)
    return Finding(
        test="Missing evidence",
        severity=Severity.HIGH if len(hits) > 20 else Severity.MEDIUM,
        summary=f"{len(hits)} payment(s) over £100 with no document reference, "
                f"totalling {at_risk}",
        explanation_sought=(
            "Where is the invoice or receipt for each? On an enquiry, an expense "
            "without supporting evidence is generally disallowed regardless of "
            "whether it was genuinely incurred. Retrieving the documents now is "
            "far easier than reconstructing them in three years."
        ),
        innocent_explanations=[
            "documents held but not yet referenced in the import",
            "direct debits where the statement is the evidence",
        ],
        evidence=[
            f"{t.date} {t.counterparty or t.description[:32]} {abs(t.amount)} "
            f"[{t.source_ref}]"
            for t in sorted(hits, key=lambda t: -abs(t.amount).amount)[:8]
        ],
        value_at_risk=at_risk,
    )


def unexplained_cash(transactions: Sequence[Transaction]) -> Optional[Finding]:
    """Cash movements, which carry both tax and anti-money-laundering weight."""
    pattern = re.compile(r"\b(cash|atm|withdrawal|counter credit)\b", re.IGNORECASE)
    hits = [t for t in transactions if pattern.search(t.description)]
    if not hits:
        return None
    deposits = [t for t in hits if t.is_money_in]
    return Finding(
        test="Cash movements",
        severity=Severity.MEDIUM if deposits else Severity.LOW,
        summary=f"{len(hits)} cash-related entries ({len(deposits)} deposits)",
        explanation_sought=(
            "What is the source of each cash deposit, and is it recorded as "
            "income where it is income? Cash rent that reaches a personal account "
            "without entering the rental records is unrecorded taxable income. If "
            "any of it is, the correct route is a voluntary disclosure to HMRC, "
            "which carries substantially lower penalties than discovery."
        ),
        innocent_explanations=[
            "personal cash withdrawals that are simply drawings",
            "petty cash float movements",
            "a tenant who genuinely pays in cash and gets a receipt",
        ],
        evidence=[
            f"{t.date} {t.description[:38]} {t.amount} [{t.source_ref}]"
            for t in sorted(hits, key=lambda t: -abs(t.amount).amount)[:8]
        ],
        value_at_risk=total(abs(t.amount) for t in deposits),
    )


def ghost_supplier(
    transactions: Sequence[Transaction], minimum_payments: int = 3
) -> Optional[Finding]:
    """Suppliers paid regularly whose narrative carries no identifying detail."""
    by_payee: Dict[str, List[Transaction]] = defaultdict(list)
    for txn in transactions:
        if txn.is_money_in:
            continue
        name = (txn.counterparty or "").strip()
        if not name:
            continue
        by_payee[name.upper()].append(txn)

    suspicious = []
    for name, items in by_payee.items():
        if len(items) < minimum_payments:
            continue
        if any(t.document_ref for t in items):
            continue
        # Generic-looking names with no invoice references at all.
        if re.fullmatch(r"[A-Z][A-Z ]{2,20}", name) and len(set(
            abs(t.amount).quantize().amount for t in items
        )) <= 2:
            suspicious.append((name, items))

    if not suspicious:
        return None

    evidence = []
    at_risk = Money.zero()
    for name, items in suspicious[:5]:
        paid = total(abs(t.amount) for t in items)
        at_risk = at_risk + paid
        evidence.append(
            f"{name}: {len(items)} payments totalling {paid}, no invoice "
            f"reference on any of them, near-identical amounts"
        )

    return Finding(
        test="Unverified supplier",
        severity=Severity.MEDIUM,
        summary=f"{len(suspicious)} supplier(s) paid repeatedly with no invoice "
                "reference and near-identical amounts",
        explanation_sought=(
            "Who are these suppliers, what did they provide, and can an invoice "
            "and a company or VAT number be produced for each? This pattern is "
            "consistent with a retainer, and equally consistent with a fictitious "
            "supplier - the invoice settles which."
        ),
        innocent_explanations=[
            "a genuine monthly retainer or fixed-fee contract",
            "a cleaner or gardener paid a standing amount",
            "invoice references simply not captured in the import",
        ],
        evidence=evidence,
        value_at_risk=at_risk,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_forensic_review(
    transactions: Sequence[Transaction],
    related_names: Sequence[str] = (),
    period_end: Optional[date] = None,
    approval_thresholds: Sequence[Money] = (),
    period_label: str = "",
) -> ForensicReport:
    """Run every test and collect the indicators."""
    report = ForensicReport(
        transactions_reviewed=len(transactions),
        period=period_label,
        evidence_hash=evidence_hash(transactions),
    )
    if not transactions:
        return report

    thresholds = list(approval_thresholds) or [Money(500), Money(1000), Money(5000)]

    report.add(benford_first_digit(transactions))
    report.add(duplicate_payments(transactions))
    report.add(round_sum_payments(transactions))
    report.add(threshold_structuring(transactions, thresholds))
    report.add(weekend_and_backdated(transactions, period_end))
    report.add(related_party_flows(transactions, related_names))
    report.add(missing_evidence(transactions))
    report.add(unexplained_cash(transactions))
    report.add(ghost_supplier(transactions))
    return report


def evidence_hash(transactions: Sequence[Transaction]) -> str:
    """Hash the reviewed population so the report is tied to exact data.

    If a finding is ever disputed, this establishes which version of the
    records the review was performed on. Record it in the working papers.
    """
    digest = hashlib.sha256()
    for fingerprint in sorted(t.fingerprint() for t in transactions):
        digest.update(fingerprint.encode("utf-8"))
    return digest.hexdigest()[:24]
