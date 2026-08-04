"""Portfolio Accountant -- an agent toolkit for a mixed property and business portfolio.

The package is built on one principle: **the computer does the arithmetic, a
person takes the decisions, and the trail between them is always visible.**

Nothing here files a return, signs off accounts, or gives tax advice. Those are
regulated acts that require a qualified, accountable human. What this does is
prepare the work to the point where that human's time is spent on judgement
rather than on data entry -- and make every figure traceable back to the
document it came from.

Modules
-------
``money``       exact decimal arithmetic, never floats
``config``      tax parameters with provenance and verification dates
``model``       entities, properties, transactions
``ingest``      CSV import with duplicate protection
``classify``    deterministic rule-based categorisation
``ledger``      double-entry with an immutable audit trail
``posting``     transactions into balanced journals
``statements``  profit and loss, balance sheet, tax bridge
``properties``  per-property performance and the Section 24 gap
``tax``         income tax, corporation tax, CGT, SDLT, VAT
``audit``       controls, materiality, sampling, independence
``forensics``   anomaly indicators requiring explanation
``planning``    statutory reliefs, with the evasion line drawn explicitly
``compliance``  the deadline calendar
"""

__version__ = "0.1.0"

from .config import load_jurisdiction
from .model import Entity, Portfolio, Property, Transaction
from .money import Money

__all__ = [
    "Money",
    "Portfolio",
    "Entity",
    "Property",
    "Transaction",
    "load_jurisdiction",
    "__version__",
]
