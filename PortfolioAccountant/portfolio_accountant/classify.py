"""Rule-based transaction classification.

Classification is deterministic and rule-driven on purpose. A language model
guessing that "PAYMENT TO J SMITH" is a repair rather than drawings produces a
number nobody can defend two years later when HMRC asks. Here, every
classified transaction records the ID of the rule that classified it, and
anything no rule matches goes to suspense for a human to decide.

That means the suspense account is the point of the exercise, not a failure of
it. The list of unclassified items is the work queue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from .model import Transaction
from .money import Money

SUSPENSE_ACCOUNT = "9000"
AWAITING_EVIDENCE = "9010"


@dataclass
class Rule:
    """One classification rule.

    All specified conditions must match. Rules are evaluated in order and the
    first match wins, so put specific rules above general ones.
    """

    id: str
    account: str
    description_pattern: str = ""
    counterparty_pattern: str = ""
    direction: str = "any"            # in | out | any
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    property_id: Optional[str] = None
    entity_id: Optional[str] = None
    requires_evidence: bool = False
    note: str = ""
    _description_re: Optional[re.Pattern] = field(default=None, repr=False, compare=False)
    _counterparty_re: Optional[re.Pattern] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.description_pattern:
            self._description_re = re.compile(self.description_pattern, re.IGNORECASE)
        if self.counterparty_pattern:
            self._counterparty_re = re.compile(self.counterparty_pattern, re.IGNORECASE)

    def matches(self, txn: Transaction) -> bool:
        if self.entity_id and txn.entity_id != self.entity_id:
            return False
        if self.direction == "in" and not txn.is_money_in:
            return False
        if self.direction == "out" and txn.is_money_in:
            return False
        if self._description_re and not self._description_re.search(txn.description):
            return False
        if self._counterparty_re and not self._counterparty_re.search(txn.counterparty):
            return False
        magnitude = abs(txn.amount).amount
        if self.amount_min is not None and magnitude < self.amount_min:
            return False
        if self.amount_max is not None and magnitude > self.amount_max:
            return False
        return True

    @classmethod
    def from_dict(cls, data: Dict) -> "Rule":
        return cls(
            id=data["id"],
            account=data["account"],
            description_pattern=data.get("description_pattern", ""),
            counterparty_pattern=data.get("counterparty_pattern", ""),
            direction=data.get("direction", "any"),
            amount_min=Decimal(str(data["amount_min"])) if "amount_min" in data else None,
            amount_max=Decimal(str(data["amount_max"])) if "amount_max" in data else None,
            property_id=data.get("property_id"),
            entity_id=data.get("entity_id"),
            requires_evidence=bool(data.get("requires_evidence", False)),
            note=data.get("note", ""),
        )


@dataclass
class ClassificationReport:
    classified: int = 0
    unclassified: List[Transaction] = field(default_factory=list)
    awaiting_evidence: List[Transaction] = field(default_factory=list)
    by_rule: Dict[str, int] = field(default_factory=dict)
    unmatched_descriptions: Dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.classified + len(self.unclassified)

    @property
    def coverage(self) -> Decimal:
        if not self.total:
            return Decimal("0")
        return Decimal(self.classified) / Decimal(self.total) * 100

    def summary(self) -> str:
        lines = [
            "Classification",
            f"  classified:   {self.classified} of {self.total} ({self.coverage:.1f}%)",
            f"  unclassified: {len(self.unclassified)}",
            f"  no evidence:  {len(self.awaiting_evidence)}",
        ]
        if self.unclassified:
            lines.append("")
            lines.append("  Work queue - most frequent unmatched descriptions:")
            top = sorted(
                self.unmatched_descriptions.items(), key=lambda kv: -kv[1]
            )[:12]
            for description, count in top:
                lines.append(f"    {count:>4}x  {description}")
            lines.append("")
            lines.append(
                "  Each needs either a new rule or a manual posting. Nothing here "
                "should be guessed: an expense without a determinable purpose is "
                "not a deductible expense."
            )
        if self.awaiting_evidence:
            lines.append("")
            lines.append(
                f"  {len(self.awaiting_evidence)} transaction(s) matched a rule that "
                "requires a document reference, but none was supplied. These sit in "
                "9010 until the receipt or invoice is attached. No receipt, no "
                "deduction - that is the rule HMRC applies on enquiry."
            )
        return "\n".join(lines)


def classify(
    transactions: List[Transaction], rules: List[Rule]
) -> ClassificationReport:
    """Apply rules in order; first match wins. Mutates transactions in place."""
    report = ClassificationReport()

    for txn in transactions:
        matched = None
        for rule in rules:
            if rule.matches(txn):
                matched = rule
                break

        if matched is None:
            txn.category = SUSPENSE_ACCOUNT
            txn.confidence = "unclassified"
            txn.classification_rule = ""
            txn.flags.append("unclassified")
            report.unclassified.append(txn)
            key = _description_key(txn.description)
            report.unmatched_descriptions[key] = (
                report.unmatched_descriptions.get(key, 0) + 1
            )
            continue

        if matched.requires_evidence and not txn.document_ref:
            txn.category = AWAITING_EVIDENCE
            txn.confidence = "rule"
            txn.classification_rule = matched.id
            txn.flags.append("no_evidence")
            report.awaiting_evidence.append(txn)
            report.classified += 1
            report.by_rule[matched.id] = report.by_rule.get(matched.id, 0) + 1
            continue

        txn.category = matched.account
        txn.confidence = "rule"
        txn.classification_rule = matched.id
        if matched.property_id and not txn.property_id:
            txn.property_id = matched.property_id
        if matched.note:
            txn.notes = matched.note
        report.classified += 1
        report.by_rule[matched.id] = report.by_rule.get(matched.id, 0) + 1

    return report


def _description_key(description: str) -> str:
    """Normalise a bank narrative so similar entries group together.

    Card references, dates and long digit strings are stripped so that twelve
    variations of the same merchant collapse into one work-queue line.
    """
    text = description.upper()
    text = re.sub(r"\b\d{2}[/-]\d{2}([/-]\d{2,4})?\b", " ", text)
    text = re.sub(r"\b\d{4,}\b", " ", text)
    text = re.sub(r"\bREF\s*\S+", " ", text)
    text = re.sub(r"[^A-Z& ]", " ", text)
    return " ".join(text.split())[:48] or description[:48]


def load_rules(data: List[Dict]) -> List[Rule]:
    """Build rules from config, checking for duplicate IDs."""
    rules = [Rule.from_dict(row) for row in data]
    seen = set()
    for rule in rules:
        if rule.id in seen:
            raise ValueError(
                f"duplicate rule id '{rule.id}' - rule IDs appear in the audit "
                "trail and must be unique"
            )
        seen.add(rule.id)
    return rules


def unclassified_value(transactions: List[Transaction]) -> Money:
    """Total absolute value sitting in suspense.

    Used as a materiality gate: no statutory report should be issued while a
    material amount is unclassified.
    """
    result = Money.zero()
    for txn in transactions:
        if txn.category in (SUSPENSE_ACCOUNT, AWAITING_EVIDENCE):
            result = result + abs(txn.amount)
    return result
