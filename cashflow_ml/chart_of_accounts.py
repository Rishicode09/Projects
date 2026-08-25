"""
The chart of accounts, in one place.

The database loader and the Excel workbook both need to know which
descriptions belong to which nominal category. Keeping two copies of that
list is how a reporting pack ends up disagreeing with itself: someone adds a
category in one place and the other quietly carries on with the old list.
That exact bug appeared here -- the workbook filed a service charge receipt
as Uncategorised while the database had it as income -- which is why the
list now lives in one file.

(cashflow_ml.py keeps its own RULES list: those are ML training seeds, which
also record whether an item is revenue or capital, so the two are not quite
the same thing.)

Add a category here and every part of the project picks it up.
"""

from __future__ import annotations

# (keywords, category name, which side of the P&L it sits on).
# Order matters: the first rule whose keyword appears in the description wins.
CATEGORY_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("rent",), "Rental income", "income"),
    (("service charge",), "Service charge income", "income"),
    (("mortgage", "interest"), "Mortgage interest", "expense"),
    (("managing agent", "agent"), "Managing agent fees", "expense"),
    (("insurance",), "Insurance", "expense"),
    (("accountancy", "legal", "audit"), "Professional fees", "expense"),
    (("director", "payroll", "salary"), "Directors remuneration", "expense"),
    (("repair", "maintenance"), "Repairs and maintenance", "expense"),
]

UNCATEGORISED_INCOME = "Uncategorised income"
UNCATEGORISED_EXPENSE = "Uncategorised expense"


def categorise(description: str, amount: float) -> tuple[str, str]:
    """Match a description to a category and the side of the P&L it sits on.

    The amount matters: an unrecognised RECEIPT is not an expense. Defaulting
    everything unmatched to 'expense' would quietly file income under costs
    and understate the profit.
    """
    text = description.lower()
    for keywords, name, kind in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return name, kind
    return ((UNCATEGORISED_INCOME, "income") if amount >= 0
            else (UNCATEGORISED_EXPENSE, "expense"))


def keyword_rows() -> list[tuple[str, str, str]]:
    """Flatten to one row per keyword, for the Excel lookup table.

    Excel's SEARCH works down a single column, so a rule with three keywords
    becomes three rows. Order is preserved, so first match still wins.
    """
    return [
        (keyword.upper(), name, kind.title())
        for keywords, name, kind in CATEGORY_RULES
        for keyword in keywords
    ]
