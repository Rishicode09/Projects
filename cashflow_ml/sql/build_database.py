"""
Load the bank statement CSV into a SQLite database.

SQLite is a database that lives in a single file, and Python can talk to it
without installing anything -- the `sqlite3` module is part of Python itself.
That makes it the easiest way to learn SQL properly. The connection code here
is the same shape you would use against SQL Server, PostgreSQL or MySQL at
work; only the connect() line and the driver change.

The loader ACCUMULATES. Run it again with a new statement and the new rows
are added; run it twice on the same file and nothing is double-counted,
because a unique index treats a transaction with the same date, description,
company, amount and document reference as the one you already have.

Run:
    python build_database.py                        # every CSV in ../data
    python build_database.py march.csv april.csv    # named files
    python build_database.py ~/statements           # a whole folder
    python build_database.py --reset                # start the database again
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# The chart of accounts lives one folder up and is shared with the Excel
# builder and the ML script, so all three agree on the categories.
sys.path.insert(0, str(BASE_DIR.parent))
from chart_of_accounts import categorise  # noqa: E402

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
CREATE TABLE IF NOT EXISTS counterparty (
    counterparty_id INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS category (
    category_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    -- Which side of the profit and loss account this sits on.
    kind        TEXT NOT NULL CHECK (kind IN ('income', 'expense'))
);

CREATE TABLE IF NOT EXISTS transactions (
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
    -- Where this row came from and when, so you can trace any figure in a
    -- report back to the file it was loaded from. Auditors ask this.
    source_file     TEXT    NOT NULL,
    loaded_at       TEXT    NOT NULL,
    CHECK (paid_in >= 0 AND paid_out >= 0),
    CHECK (NOT (paid_in > 0 AND paid_out > 0))   -- a line is one or the other
);

-- The de-duplication key. Two rows describing the same payment on the same
-- day from the same company for the same amount are the same transaction, so
-- loading a file twice cannot double-count it. This is what makes the loader
-- safe to re-run -- "idempotent" is the word for it, and it is the single
-- most important property of a data load in finance.
CREATE UNIQUE INDEX IF NOT EXISTS idx_txn_unique
    ON transactions(txn_date, description, counterparty_id, amount,
                    IFNULL(document_ref, ''));

-- Indexes make the common lookups fast. On 39 rows it makes no difference;
-- on 39 million it is the difference between instant and unusable.
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_txn_counterparty ON transactions(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category_id);
"""

RESET = """
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS counterparty;
DROP TABLE IF EXISTS category;
"""

def to_number(value: str) -> float:
    """Blank cells in a bank CSV mean zero, not missing."""
    return float(value) if value.strip() else 0.0


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def get_or_create(cursor, table: str, columns: str, values: tuple,
                  cache: dict, key: str) -> int:
    """Look an id up, inserting the row the first time we see it."""
    if key in cache:
        return cache[key]

    name_column = columns.split(",")[0].strip()
    cursor.execute(
        f"SELECT rowid FROM {table} WHERE {name_column} = ?", (values[0],)
    )
    found = cursor.fetchone()
    if found:
        cache[key] = found[0]
        return found[0]

    placeholders = ", ".join("?" for _ in values)
    # ? is a placeholder. NEVER build SQL by joining strings with user input
    # -- that is how SQL injection happens. The driver substitutes the value
    # safely. (The table and column names here are our own constants, not
    # user input, which is why they can be formatted in.)
    cursor.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values
    )
    cache[key] = cursor.lastrowid
    return cursor.lastrowid


def load_file(cursor, csv_path: Path) -> tuple[int, int, list[str]]:
    """Load one CSV. Returns (inserted, skipped_as_duplicate, unmatched)."""
    rows = read_rows(csv_path)
    counterparties: dict[str, int] = {}
    categories: dict[str, int] = {}
    loaded_at = datetime.now().isoformat(timespec="seconds")
    inserted = 0
    unmatched: list[str] = []

    for row in rows:
        name = row["counterparty"].strip()
        counterparty_id = get_or_create(
            cursor, "counterparty", "name", (name,), counterparties, name
        )

        paid_in = to_number(row["paid in"])
        paid_out = to_number(row["paid out"])
        txn_date = datetime.strptime(row["date"].strip(), "%d/%m/%Y").date()

        category_name, kind = categorise(row["description"], paid_in - paid_out)
        if category_name.startswith("Uncategorised"):
            unmatched.append(row["description"].strip())
        category_id = get_or_create(
            cursor, "category", "name, kind", (category_name, kind),
            categories, category_name,
        )

        # INSERT OR IGNORE: if this exact transaction is already there, the
        # unique index rejects it and we carry on rather than crashing.
        cursor.execute(
            """
            INSERT OR IGNORE INTO transactions (
                txn_date, description, counterparty_id, category_id,
                property_ref, document_ref, paid_in, paid_out, amount,
                source_file, loaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                txn_date.isoformat(),
                row["description"].strip(),
                counterparty_id,
                category_id,
                row["property"].strip() or None,
                row["document"].strip() or None,
                paid_in,
                paid_out,
                paid_in - paid_out,
                csv_path.name,
                loaded_at,
            ),
        )
        inserted += cursor.rowcount        # 0 when the row was ignored

    return inserted, len(rows) - inserted, unmatched


def build(csv_paths: list[Path], db_path: Path, reset: bool) -> None:
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
        if reset:
            cursor.executescript(RESET)
        cursor.executescript(SCHEMA)

        needs_a_rule: list[str] = []
        for csv_path in csv_paths:
            inserted, skipped, unmatched = load_file(cursor, csv_path)
            note = f", {skipped} already present" if skipped else ""
            print(f"  {csv_path.name}: {inserted} new{note}")
            needs_a_rule.extend(unmatched)

        # Nothing is saved until you commit. If the program crashed halfway
        # through, the database would be left exactly as it started.
        connection.commit()

        totals = cursor.execute(
            """
            SELECT COUNT(*), MIN(txn_date), MAX(txn_date),
                   ROUND(SUM(paid_in), 2), ROUND(SUM(paid_out), 2)
            FROM transactions
            """
        ).fetchone()
        companies = cursor.execute("SELECT COUNT(*) FROM counterparty").fetchone()[0]
    finally:
        # Always close, even if something above raised.
        connection.close()

    if needs_a_rule:
        print("\nThese descriptions matched no category rule. They are still"
              "\nloaded, on the correct side of the P&L, but add a rule to"
              "\nCATEGORY_RULES to code them properly:")
        for description in sorted(set(needs_a_rule)):
            print(f"  {description}")

    count, first, last, cash_in, cash_out = totals
    print(f"\n{db_path} now holds:")
    print(f"  {count} transactions from {first} to {last}")
    print(f"  {companies} counterparties")
    print(f"  cash in £{cash_in or 0:,.2f}, cash out £{cash_out or 0:,.2f}, "
          f"net £{(cash_in or 0) - (cash_out or 0):,.2f}")


def collect_csvs(arguments: list[str]) -> list[Path]:
    """Accept files, folders, or nothing at all (meaning the data folder)."""
    if not arguments:
        folder = DEFAULT_CSV.parent
        return sorted(folder.glob("*.csv")) if folder.is_dir() else []

    paths: list[Path] = []
    for argument in arguments:
        path = Path(argument).expanduser()
        if path.is_dir():
            paths.extend(sorted(path.glob("*.csv")))
        else:
            paths.append(path)
    return paths


def main(argv: list[str]) -> int:
    reset = "--reset" in argv
    arguments = [a for a in argv[1:] if not a.startswith("-")]

    csv_paths = collect_csvs(arguments)
    missing = [p for p in csv_paths if not p.exists()]
    if missing:
        for path in missing:
            print(f"CSV not found: {path}", file=sys.stderr)
        return 1
    if not csv_paths:
        print("No CSV files to load.", file=sys.stderr)
        print(f"Put them in {DEFAULT_CSV.parent} or name them on the command "
              "line.", file=sys.stderr)
        return 1

    print(f"Loading {len(csv_paths)} file(s) into {DB_PATH.name}"
          f"{' (reset first)' if reset else ''}")
    build(csv_paths, DB_PATH, reset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
