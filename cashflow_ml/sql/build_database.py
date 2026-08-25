"""
Load the bank statement CSV into a SQLite database.

SQLite is a database that lives in a single file, and Python can talk to it
without installing anything -- the `sqlite3` module is part of Python itself.
That makes it the easiest way to learn SQL properly. The connection code here
is the same shape you would use against SQL Server, PostgreSQL or MySQL at
work; only the connect() line and the driver change.

Run:
    python build_database.py            # builds cashflow.db next to this file
    python build_database.py ../data/bank_company.csv
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cashflow.db"
DEFAULT_CSV = BASE_DIR.parent / "data" / "bank_company.csv"

# ---------------------------------------------------------------------------
# The schema
# ---------------------------------------------------------------------------
# Three tables instead of one flat sheet. Each company is stored once in
# `counterparty` and referenced by an id, so a company can be renamed in one
# place and every transaction follows. That is what "normalised" means, and
# it is the main thing a database gives you over a spreadsheet.
SCHEMA = """
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS counterparty;
DROP TABLE IF EXISTS category;

CREATE TABLE counterparty (
    counterparty_id INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE
);

CREATE TABLE category (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    -- Which side of the profit and loss account this sits on.
    kind        TEXT NOT NULL CHECK (kind IN ('income', 'expense'))
);

CREATE TABLE transactions (
    transaction_id  INTEGER PRIMARY KEY,
    txn_date        TEXT    NOT NULL,          -- ISO yyyy-mm-dd, so it sorts
    description     TEXT    NOT NULL,
    counterparty_id INTEGER NOT NULL REFERENCES counterparty(counterparty_id),
    category_id     INTEGER NOT NULL REFERENCES category(category_id),
    property_ref    TEXT,
    document_ref    TEXT,
    paid_in         REAL    NOT NULL DEFAULT 0,
    paid_out        REAL    NOT NULL DEFAULT 0,
    -- Money in positive, money out negative. Stored once so every query
    -- agrees on the sign convention.
    amount          REAL    NOT NULL,
    CHECK (paid_in >= 0 AND paid_out >= 0),
    CHECK (NOT (paid_in > 0 AND paid_out > 0))   -- a line is one or the other
);

-- Indexes make the common lookups fast. On 39 rows it makes no difference;
-- on 39 million it is the difference between instant and unusable.
CREATE INDEX idx_txn_date ON transactions(txn_date);
CREATE INDEX idx_txn_counterparty ON transactions(counterparty_id);
CREATE INDEX idx_txn_category ON transactions(category_id);
"""

# Keyword -> (category, income or expense). Same chart of accounts the Python
# classifier is trained on, kept here as plain data.
CATEGORY_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("rent",), "Rental income", "income"),
    (("mortgage", "interest"), "Mortgage interest", "expense"),
    (("managing agent", "agent"), "Managing agent fees", "expense"),
    (("insurance",), "Insurance", "expense"),
    (("accountancy", "legal", "audit"), "Professional fees", "expense"),
    (("director", "payroll", "salary"), "Directors remuneration", "expense"),
    (("repair", "maintenance"), "Repairs and maintenance", "expense"),
]


def categorise(description: str) -> tuple[str, str]:
    text = description.lower()
    for keywords, name, kind in CATEGORY_RULES:
        if any(k in text for k in keywords):
            return name, kind
    return "Uncategorised", "expense"


def to_number(value: str) -> float:
    """Blank cells in a bank CSV mean zero, not missing."""
    return float(value) if value.strip() else 0.0


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build(csv_path: Path, db_path: Path) -> None:
    rows = read_rows(csv_path)

    # connect() creates the file if it does not exist. Against a real server
    # this line becomes e.g.
    #     pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=...")
    #     psycopg2.connect(host=..., dbname=..., user=..., password=...)
    # Everything after it is identical.
    connection = sqlite3.connect(db_path)
    try:
        # A cursor is the thing you send statements through and read results from.
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.executescript(SCHEMA)

        counterparties: dict[str, int] = {}
        categories: dict[str, int] = {}

        for row in rows:
            name = row["counterparty"].strip()
            if name not in counterparties:
                # ? is a placeholder. NEVER build SQL by joining strings with
                # user input -- that is how SQL injection happens. The driver
                # substitutes the value safely.
                cursor.execute(
                    "INSERT INTO counterparty (name) VALUES (?)", (name,)
                )
                counterparties[name] = cursor.lastrowid

            category_name, kind = categorise(row["description"])
            if category_name not in categories:
                cursor.execute(
                    "INSERT INTO category (name, kind) VALUES (?, ?)",
                    (category_name, kind),
                )
                categories[category_name] = cursor.lastrowid

            paid_in = to_number(row["paid in"])
            paid_out = to_number(row["paid out"])
            txn_date = datetime.strptime(row["date"].strip(), "%d/%m/%Y").date()

            cursor.execute(
                """
                INSERT INTO transactions (
                    txn_date, description, counterparty_id, category_id,
                    property_ref, document_ref, paid_in, paid_out, amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    txn_date.isoformat(),
                    row["description"].strip(),
                    counterparties[name],
                    categories[category_name],
                    row["property"].strip() or None,
                    row["document"].strip() or None,
                    paid_in,
                    paid_out,
                    paid_in - paid_out,
                ),
            )

        # Nothing is saved until you commit. If the program crashed halfway
        # through, the database would be left exactly as it started.
        connection.commit()
    finally:
        # Always close, even if something above raised.
        connection.close()

    print(f"Built {db_path}")
    print(f"  {len(rows)} transactions")
    print(f"  {len(counterparties)} counterparties")
    print(f"  {len(categories)} categories")


def main(argv: list[str]) -> int:
    csv_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1
    build(csv_path, DB_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
