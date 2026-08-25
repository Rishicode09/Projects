"""
Connect to the database and run the queries in queries.sql.

Shows the two ways you will connect to a database in a finance job:

  1. plain sqlite3  -- the standard library way, no extra packages
  2. pandas.read_sql -- hands the result straight back as a table you can
     pivot, chart or write to Excel

Run:
    python build_database.py     # first, to create cashflow.db
    python run_queries.py
    python run_queries.py monthly_cashflow      # just one
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cashflow.db"
SQL_PATH = BASE_DIR / "queries.sql"


def load_queries(path: Path) -> dict[str, str]:
    """Split queries.sql into named blocks on the '-- @name x' markers."""
    queries: dict[str, str] = {}
    name: str | None = None
    body: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- @name "):
            if name:
                queries[name] = "\n".join(body).strip()
            name = line.removeprefix("-- @name ").strip()
            body = []
        elif name:
            body.append(line)

    if name:
        queries[name] = "\n".join(body).strip()
    return queries


def run_with_sqlite3(query: str) -> tuple[list[str], list[tuple]]:
    """The standard library way: connect, cursor, execute, fetch, close."""
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        # cursor.description holds the column names of the last result.
        columns = [column[0] for column in cursor.description]
        return columns, cursor.fetchall()
    finally:
        connection.close()


def run_with_pandas(query: str):
    """The analyst's way: the result comes back as a DataFrame."""
    import pandas as pd

    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(query, connection)


def print_table(title: str, columns: list[str], rows: list[tuple]) -> None:
    print(f"\n=== {title} " + "=" * max(0, 74 - len(title)))
    if not rows:
        print("  (no rows)")
        return

    cells = [[("" if v is None else str(v)) for v in row] for row in rows]
    widths = [
        max(len(columns[i]), *(len(row[i]) for row in cells))
        for i in range(len(columns))
    ]
    print("  " + "  ".join(c.upper().ljust(w) for c, w in zip(columns, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for row in cells:
        print("  " + "  ".join(v.ljust(w) for v, w in zip(row, widths)))


def main(argv: list[str]) -> int:
    if not DB_PATH.exists():
        print(f"No database at {DB_PATH}", file=sys.stderr)
        print("Run:  python build_database.py", file=sys.stderr)
        return 1

    queries = load_queries(SQL_PATH)
    wanted = argv[1:] or list(queries)

    for name in wanted:
        if name not in queries:
            print(f"No query called {name!r}. Available: {', '.join(queries)}",
                  file=sys.stderr)
            return 1
        columns, rows = run_with_sqlite3(queries[name])
        print_table(name, columns, rows)

    # The same query through pandas, to show the handover point between SQL
    # and the analysis tools -- this is how a real report gets built.
    print("\n\nSame query via pandas.read_sql_query -- ready for Excel or a chart:")
    frame = run_with_pandas(queries["monthly_cashflow"])
    print(frame.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
