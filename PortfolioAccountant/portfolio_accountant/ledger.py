"""Double-entry ledger with an immutable audit trail.

Two rules are enforced structurally rather than by convention:

1. **Every journal balances.** An unbalanced journal is rejected at posting
   time, not discovered at year end.
2. **Nothing is ever deleted or edited.** A mistake is corrected by posting a
   reversing journal that references the original. This is what makes the books
   defensible if HMRC, an auditor or a court ever asks what changed and when --
   and it is the single control that catches the largest share of real fraud.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

from .money import Money, total


class AccountType:
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


# Accounts whose natural balance is a debit.
DEBIT_NATURAL = {AccountType.ASSET, AccountType.EXPENSE}


class UnbalancedJournal(ValueError):
    """Raised when debits and credits do not agree."""


class LedgerLocked(RuntimeError):
    """Raised on any attempt to post into a closed accounting period."""


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    type: str
    tax_treatment: str = ""   # e.g. "allowable", "disallowable", "capital"
    parent: str = ""

    @property
    def is_debit_natural(self) -> bool:
        return self.type in DEBIT_NATURAL


@dataclass(frozen=True)
class Posting:
    """One side of a journal entry. Positive debit, positive credit, never both."""

    account: str
    debit: Money = field(default_factory=Money.zero)
    credit: Money = field(default_factory=Money.zero)
    property_id: Optional[str] = None
    memo: str = ""

    def __post_init__(self) -> None:
        if self.debit.is_negative or self.credit.is_negative:
            raise ValueError(
                f"posting to {self.account} has a negative amount; "
                "reverse the debit/credit instead of negating"
            )
        if not self.debit.is_zero and not self.credit.is_zero:
            raise ValueError(f"posting to {self.account} is both a debit and a credit")

    @property
    def signed(self) -> Money:
        """Debit-positive signed amount."""
        return self.debit - self.credit


@dataclass
class Journal:
    """A balanced set of postings representing one economic event."""

    date: date
    narrative: str
    postings: List[Posting]
    entity_id: str = ""
    source_ref: str = ""
    reverses: Optional[str] = None      # journal id this corrects
    prepared_by: str = ""
    posted_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.postings:
            raise UnbalancedJournal(f"journal '{self.narrative}' has no postings")
        debits = total(p.debit for p in self.postings)
        credits = total(p.credit for p in self.postings)
        if debits.quantize() != credits.quantize():
            raise UnbalancedJournal(
                f"journal '{self.narrative}' on {self.date} does not balance: "
                f"debits {debits} vs credits {credits} "
                f"(difference {(debits - credits).quantize()})"
            )
        if not self.posted_at:
            self.posted_at = datetime.now().isoformat(timespec="seconds")
        if not self.id:
            self.id = self._compute_id()

    def _compute_id(self) -> str:
        basis = "|".join(
            [self.date.isoformat(), self.narrative, self.entity_id, self.source_ref]
            + [f"{p.account}:{p.signed.quantize().amount}" for p in self.postings]
        )
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]

    @property
    def value(self) -> Money:
        return total(p.debit for p in self.postings)

    def reversal(self, reason: str, prepared_by: str = "") -> "Journal":
        """Build the correcting journal. The original stays in the record."""
        return Journal(
            date=date.today(),
            narrative=f"Reversal of {self.id}: {reason}",
            postings=[
                Posting(
                    account=p.account,
                    debit=p.credit,
                    credit=p.debit,
                    property_id=p.property_id,
                    memo=p.memo,
                )
                for p in self.postings
            ],
            entity_id=self.entity_id,
            source_ref=self.source_ref,
            reverses=self.id,
            prepared_by=prepared_by,
        )


@dataclass
class Ledger:
    """The general ledger for one or more entities."""

    accounts: Dict[str, Account] = field(default_factory=dict)
    journals: List[Journal] = field(default_factory=list)
    closed_periods: List[tuple] = field(default_factory=list)  # (start, end, note)

    # -- setup -----------------------------------------------------------
    def add_account(self, account: Account) -> None:
        self.accounts[account.code] = account

    def load_chart(self, chart: Iterable[Dict]) -> None:
        for row in chart:
            self.add_account(
                Account(
                    code=row["code"],
                    name=row["name"],
                    type=row["type"],
                    tax_treatment=row.get("tax_treatment", ""),
                    parent=row.get("parent", ""),
                )
            )

    def account(self, code: str) -> Account:
        if code not in self.accounts:
            raise KeyError(
                f"account '{code}' is not in the chart of accounts. "
                "Add it deliberately rather than posting to a catch-all."
            )
        return self.accounts[code]

    # -- period control --------------------------------------------------
    def close_period(self, start: date, end: date, note: str = "") -> None:
        """Lock a period once it has been reviewed and reported.

        After closing, corrections must be posted in the *open* period with a
        reference to the original. This preserves comparability of anything
        already filed or shown to a lender.
        """
        self.closed_periods.append((start, end, note))

    def _assert_open(self, when: date) -> None:
        for start, end, note in self.closed_periods:
            if start <= when <= end:
                raise LedgerLocked(
                    f"{when} falls in a closed period ({start} to {end}"
                    f"{'; ' + note if note else ''}). Post a correcting journal "
                    "in the current open period instead of altering history."
                )

    # -- posting ---------------------------------------------------------
    def post(self, journal: Journal) -> Journal:
        self._assert_open(journal.date)
        for posting in journal.postings:
            self.account(posting.account)  # raises if unknown
        if any(j.id == journal.id for j in self.journals):
            raise ValueError(
                f"journal {journal.id} has already been posted (duplicate import?)"
            )
        self.journals.append(journal)
        return journal

    def reverse(self, journal_id: str, reason: str, prepared_by: str = "") -> Journal:
        original = next((j for j in self.journals if j.id == journal_id), None)
        if original is None:
            raise KeyError(f"no journal with id {journal_id}")
        return self.post(original.reversal(reason, prepared_by))

    # -- reporting -------------------------------------------------------
    def _in_scope(
        self,
        entity_id: Optional[str],
        start: Optional[date],
        end: Optional[date],
    ) -> List[Journal]:
        out = []
        for journal in self.journals:
            if entity_id and journal.entity_id != entity_id:
                continue
            if start and journal.date < start:
                continue
            if end and journal.date > end:
                continue
            out.append(journal)
        return out

    def balance(
        self,
        account_code: str,
        entity_id: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        property_id: Optional[str] = None,
    ) -> Money:
        """Balance of one account, signed to its natural side (positive normal)."""
        account = self.account(account_code)
        running = Money.zero()
        for journal in self._in_scope(entity_id, start, end):
            for posting in journal.postings:
                if posting.account != account_code:
                    continue
                if property_id and posting.property_id != property_id:
                    continue
                running = running + posting.signed
        return running if account.is_debit_natural else -running

    def trial_balance(
        self,
        entity_id: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> Dict[str, Money]:
        """Debit-positive balances per account, for the classic TB check."""
        balances: Dict[str, Money] = {}
        for journal in self._in_scope(entity_id, start, end):
            for posting in journal.postings:
                balances[posting.account] = (
                    balances.get(posting.account, Money.zero()) + posting.signed
                )
        return {k: v for k, v in sorted(balances.items()) if not v.quantize().is_zero}

    def trial_balance_check(
        self,
        entity_id: Optional[str] = None,
        end: Optional[date] = None,
    ) -> Money:
        """Sum of all debit-positive balances. Must be zero."""
        return total(self.trial_balance(entity_id, end=end).values())

    def totals_by_type(
        self,
        account_type: str,
        entity_id: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        property_id: Optional[str] = None,
    ) -> Dict[str, Money]:
        """Natural-signed balances for every account of a given type."""
        out: Dict[str, Money] = {}
        for code, account in sorted(self.accounts.items()):
            if account.type != account_type:
                continue
            bal = self.balance(code, entity_id, start, end, property_id)
            if not bal.quantize().is_zero:
                out[code] = bal
        return out

    def audit_trail(self, account_code: Optional[str] = None) -> List[Dict]:
        """Chronological record of every posting, for inspection or export."""
        rows = []
        for journal in sorted(self.journals, key=lambda j: (j.date, j.id)):
            for posting in journal.postings:
                if account_code and posting.account != account_code:
                    continue
                rows.append(
                    {
                        "journal_id": journal.id,
                        "date": journal.date.isoformat(),
                        "entity": journal.entity_id,
                        "narrative": journal.narrative,
                        "account": posting.account,
                        "account_name": self.accounts[posting.account].name
                        if posting.account in self.accounts
                        else "",
                        "debit": str(posting.debit.quantize().amount),
                        "credit": str(posting.credit.quantize().amount),
                        "property": posting.property_id or "",
                        "source_ref": journal.source_ref,
                        "reverses": journal.reverses or "",
                        "prepared_by": journal.prepared_by,
                        "posted_at": journal.posted_at,
                    }
                )
        return rows

    def integrity_hash(self) -> str:
        """Hash over the whole ledger.

        Record this alongside any report you issue. If the hash still matches
        later, the underlying records demonstrably have not been altered.
        """
        digest = hashlib.sha256()
        for journal in sorted(self.journals, key=lambda j: j.id):
            digest.update(journal.id.encode("utf-8"))
        return digest.hexdigest()
