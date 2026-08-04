"""Turn classified transactions into balanced double-entry journals.

Every bank transaction becomes two postings: one to the bank account, one to
the category the classifier assigned. Because the ledger rejects an unbalanced
journal, a classification error can misstate *where* a figure sits but can
never make the books stop balancing -- which is exactly the property that makes
the trial balance a meaningful check rather than a formality.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .ledger import Journal, Ledger, Posting
from .model import Transaction
from .money import Money

DEFAULT_BANK_ACCOUNT = "1000"


def post_transactions(
    ledger: Ledger,
    transactions: Sequence[Transaction],
    bank_account: str = DEFAULT_BANK_ACCOUNT,
    prepared_by: str = "portfolio-accountant",
    account_overrides: Optional[Dict[str, str]] = None,
) -> List[Journal]:
    """Post classified transactions to the ledger.

    Returns the journals created. Anything that cannot be posted raises, rather
    than being skipped quietly -- a silently dropped transaction is how a set of
    books ends up complete-looking and wrong.
    """
    overrides = account_overrides or {}
    created: List[Journal] = []

    for txn in transactions:
        if not txn.category:
            raise ValueError(
                f"transaction {txn.source_ref} has no category; classify before posting"
            )

        bank = overrides.get(txn.account, bank_account)
        amount = abs(txn.amount)

        if txn.is_money_in:
            # Money in: debit the bank, credit income (or reduce an expense).
            postings = [
                Posting(account=bank, debit=amount, memo=txn.description[:60]),
                Posting(
                    account=txn.category,
                    credit=amount,
                    property_id=txn.property_id,
                    memo=txn.description[:60],
                ),
            ]
        else:
            postings = [
                Posting(
                    account=txn.category,
                    debit=amount,
                    property_id=txn.property_id,
                    memo=txn.description[:60],
                ),
                Posting(account=bank, credit=amount, memo=txn.description[:60]),
            ]

        journal = Journal(
            date=txn.date,
            narrative=txn.description[:120],
            postings=postings,
            entity_id=txn.entity_id,
            source_ref=txn.source_ref,
            prepared_by=prepared_by,
        )
        created.append(ledger.post(journal))

    return created


def post_accrual(
    ledger: Ledger,
    when,
    narrative: str,
    debit_account: str,
    credit_account: str,
    amount: Money,
    entity_id: str = "",
    property_id: Optional[str] = None,
    prepared_by: str = "",
    source_ref: str = "",
) -> Journal:
    """Post a year-end adjustment: accrual, prepayment, depreciation, accrued rent.

    Adjustments are where judgement enters the accounts, so each one carries a
    narrative explaining the basis. "Accrual" on its own is not a narrative;
    "accrued gas safety certificate invoiced 12 April for March work" is.
    """
    if not narrative or len(narrative) < 12:
        raise ValueError(
            "an adjusting journal needs a narrative that explains its basis - "
            "this is the entry a reviewer will question first"
        )
    return ledger.post(
        Journal(
            date=when,
            narrative=narrative,
            postings=[
                Posting(account=debit_account, debit=amount, property_id=property_id),
                Posting(account=credit_account, credit=amount, property_id=property_id),
            ],
            entity_id=entity_id,
            source_ref=source_ref,
            prepared_by=prepared_by,
        )
    )
