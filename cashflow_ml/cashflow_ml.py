"""
Cash in / cash out organiser for a company bank statement.

A small, deliberately simple ML pipeline that reads a bank CSV and:

  1. cleans it into a signed cash-flow ledger (cash in positive, cash out negative)
  2. clusters the narratives with TF-IDF + KMeans to discover the recurring
     transaction streams without being told what they are
  3. trains a Naive Bayes text classifier on rule-seeded labels so new,
     unseen narratives can be posted to a nominal category automatically
  4. flags one-off / unusual items with IsolationForest
  5. writes the bookkeeping summaries (monthly cash flow, category totals,
     counterparty totals) to ./output

Usage:
    python cashflow_ml.py [path/to/bank.csv]
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import cross_val_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

# Where to look for the statement when no path is given on the command line.
# Tried in order, so the script works whether the CSV sits in data/ or loose
# next to the script.
DEFAULT_CSV_CANDIDATES = (
    BASE_DIR / "data" / "bank_company.csv",
    BASE_DIR / "bank_company.csv",
)

# Chart of accounts. Each entry is (category, keywords, capital_or_revenue).
# These rules only seed the training labels - the classifier below is what
# actually posts every transaction, including narratives the rules never saw.
RULES: list[tuple[str, tuple[str, ...], str]] = [
    ("Rental income",        ("rent",),                        "revenue"),
    ("Mortgage interest",    ("mortgage", "interest"),          "revenue"),
    ("Managing agent fees",  ("managing agent", "agent"),       "revenue"),
    ("Insurance",            ("insurance",),                    "revenue"),
    ("Professional fees",    ("accountancy", "legal", "audit"), "revenue"),
    ("Directors remuneration", ("director", "payroll", "salary", "wages"), "revenue"),
    ("Repairs & maintenance", ("repair", "maintenance", "works"), "revenue"),
    ("Capital / loan movement", ("loan", "capital", "drawdown", "repayment"), "capital"),
]


# ---------------------------------------------------------------------------
# 1. Load and clean
# ---------------------------------------------------------------------------
def load_ledger(csv_path: Path) -> pd.DataFrame:
    """Read the bank CSV into a tidy, signed ledger."""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    df["date"] = pd.to_datetime(df["date"], dayfirst=True, format="%d/%m/%Y")
    for col in ("paid_in", "paid_out"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ("description", "counterparty", "property", "document"):
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Bookkeeping convention: money in is positive, money out is negative.
    df["amount"] = df["paid_in"] - df["paid_out"]
    df["direction"] = np.where(df["amount"] >= 0, "CASH IN", "CASH OUT")
    df["month"] = df["date"].dt.to_period("M")
    df["property"] = df["property"].replace("", "UNALLOCATED / COMPANY-WIDE")

    # The text the models learn from.
    df["text"] = (df["description"] + " " + df["counterparty"]).str.lower()

    return df.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Rule-based seed labels (the "training data" for the classifier)
# ---------------------------------------------------------------------------
def seed_label(text: str) -> str | None:
    for category, keywords, _ in RULES:
        if any(k in text for k in keywords):
            return category
    return None


def seed_labels(df: pd.DataFrame) -> pd.Series:
    return df["text"].map(seed_label)


# ---------------------------------------------------------------------------
# 3. Unsupervised: discover the recurring transaction streams
# ---------------------------------------------------------------------------
def cluster_streams(df: pd.DataFrame, n_clusters: int | None = None) -> pd.Series:
    """TF-IDF + KMeans over the narratives to find repeating payment streams."""
    if n_clusters is None:
        # One cluster per distinct narrative pattern, capped for small files.
        n_clusters = min(8, df["text"].nunique())

    vectoriser = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    features = vectoriser.fit_transform(df["text"])

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(features)

    # Name each cluster after its most common narrative, so the output is
    # readable to a bookkeeper rather than "cluster 3".
    names = (
        pd.DataFrame({"cluster": labels, "description": df["description"]})
        .groupby("cluster")["description"]
        .agg(lambda s: s.mode().iat[0])
    )
    return pd.Series(labels, index=df.index).map(names).rename("stream")


# ---------------------------------------------------------------------------
# 4. Supervised: learn to post any narrative to a category
# ---------------------------------------------------------------------------
def classify_categories(df: pd.DataFrame) -> tuple[pd.Series, float]:
    """Train a TF-IDF + Naive Bayes classifier and post every line with it."""
    seeds = seed_labels(df)
    train = df.loc[seeds.notna()]
    y = seeds.loc[seeds.notna()]

    pipeline = make_pipeline(
        TfidfVectorizer(stop_words="english", ngram_range=(1, 2)),
        MultinomialNB(alpha=0.1),
    )

    # Honest accuracy check: only score classes with enough examples to split.
    counts = y.value_counts()
    mask = y.isin(counts[counts >= 3].index)
    folds = int(min(5, counts[counts >= 3].min())) if mask.any() else 0
    accuracy = (
        float(cross_val_score(pipeline, train.loc[mask, "text"], y[mask], cv=folds).mean())
        if folds >= 2
        else float("nan")
    )

    pipeline.fit(train["text"], y)
    predicted = pd.Series(pipeline.predict(df["text"]), index=df.index, name="category")
    return predicted, accuracy


# ---------------------------------------------------------------------------
# 5. Anomaly detection: which lines deserve a second look
# ---------------------------------------------------------------------------
def flag_anomalies(df: pd.DataFrame) -> pd.Series:
    """IsolationForest over amount / timing / direction to flag one-offs."""
    features = pd.DataFrame(
        {
            "abs_amount": df["amount"].abs(),
            "is_outflow": (df["amount"] < 0).astype(int),
            "day_of_month": df["date"].dt.day,
            "stream_frequency": df.groupby("text")["text"].transform("size"),
        }
    )
    model = IsolationForest(contamination=0.1, random_state=42)
    return pd.Series(model.fit_predict(features) == -1, index=df.index, name="unusual")


# ---------------------------------------------------------------------------
# 6. Bookkeeping summaries
# ---------------------------------------------------------------------------
def monthly_cashflow(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.groupby("month")
        .agg(cash_in=("paid_in", "sum"), cash_out=("paid_out", "sum"))
        .reset_index()
    )
    out["net_movement"] = out["cash_in"] - out["cash_out"]
    out["closing_balance_movement"] = out["net_movement"].cumsum()
    out["month"] = out["month"].astype(str)
    return out


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.groupby(["direction", "category"])
        .agg(
            transactions=("amount", "size"),
            total=("amount", lambda s: s.abs().sum()),
            average=("amount", lambda s: s.abs().mean()),
        )
        .reset_index()
        .sort_values(["direction", "total"], ascending=[True, False])
    )
    grand = df.groupby("direction")["amount"].apply(lambda s: s.abs().sum())
    out["pct_of_direction"] = (out["total"] / out["direction"].map(grand) * 100).round(1)
    return out


def counterparty_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Accumulated position with each company the business banks with."""
    out = (
        df.groupby(["direction", "counterparty"])
        .agg(
            transactions=("amount", "size"),
            total=("amount", lambda s: s.abs().sum()),
            average=("amount", lambda s: s.abs().mean()),
            first_seen=("date", "min"),
            last_seen=("date", "max"),
            category=("category", lambda s: s.mode().iat[0]),
        )
        .reset_index()
        .sort_values(["direction", "total"], ascending=[True, False])
    )
    grand = df.groupby("direction")["amount"].apply(lambda s: s.abs().sum())
    out["pct_of_direction"] = (out["total"] / out["direction"].map(grand) * 100).round(1)
    return out


def process_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Every recurring cash process: what it is, how often, how much in total."""
    out = (
        df.groupby(["direction", "stream"])
        .agg(
            category=("category", lambda s: s.mode().iat[0]),
            counterparty=("counterparty", lambda s: s.mode().iat[0]),
            transactions=("amount", "size"),
            each=("amount", lambda s: s.abs().median()),
            total=("amount", lambda s: s.abs().sum()),
            first_seen=("date", "min"),
            last_seen=("date", "max"),
        )
        .reset_index()
        .sort_values(["direction", "total"], ascending=[True, False])
    )
    months = df["month"].nunique()
    out["frequency"] = np.where(
        out["transactions"] >= months * 0.9,
        "Monthly",
        np.where(out["transactions"] == 1, "One-off", "Irregular"),
    )
    return out


def profit_and_loss(df: pd.DataFrame) -> pd.DataFrame:
    """Cash-basis income statement: income, then expenses, then the result."""
    rows: list[dict[str, object]] = []

    income = df.loc[df["direction"] == "CASH IN"]
    for category, value in income.groupby("category")["amount"].sum().sort_values(
        ascending=False
    ).items():
        rows.append({"line": category, "amount": value, "kind": "income"})
    total_income = income["amount"].sum()
    rows.append({"line": "Total income", "amount": total_income, "kind": "subtotal"})

    expense = df.loc[df["direction"] == "CASH OUT"]
    for category, value in expense.groupby("category")["amount"].sum().sort_values().items():
        rows.append({"line": category, "amount": value, "kind": "expense"})
    total_expense = expense["amount"].sum()
    rows.append({"line": "Total expenditure", "amount": total_expense, "kind": "subtotal"})

    result = total_income + total_expense
    rows.append(
        {
            "line": "Net profit for the period" if result >= 0 else "Net loss for the period",
            "amount": result,
            "kind": "result",
        }
    )
    return pd.DataFrame(rows)


def money(x: float) -> str:
    return f"-£{abs(x):,.2f}" if x < 0 else f"£{x:,.2f}"


def report(df: pd.DataFrame, accuracy: float) -> None:
    cash_in = df["paid_in"].sum()
    cash_out = df["paid_out"].sum()
    period = f"{df['date'].min():%d/%m/%Y} to {df['date'].max():%d/%m/%Y}"

    print("=" * 78)
    print("CASH IN / CASH OUT ANALYSIS".center(78))
    print(f"Period: {period}   |   {len(df)} transactions".center(78))
    print("=" * 78)

    print("\n1. HEADLINE POSITION")
    print(f"   Total cash in       {money(cash_in):>15}")
    print(f"   Total cash out      {money(-cash_out):>15}")
    print(f"   Net movement        {money(cash_in - cash_out):>15}")
    if cash_in:
        print(f"   Cash retained       {(cash_in - cash_out) / cash_in * 100:>14.1f}%")
        print(f"   Cost ratio          {cash_out / cash_in * 100:>14.1f}%")

    print(f"\n2. CLASSIFIER (TF-IDF + Naive Bayes) cross-validated accuracy: {accuracy:.0%}")
    print("   Recurring streams found by KMeans clustering:")
    streams = (
        df.groupby("stream")
        .agg(n=("amount", "size"), net=("amount", "sum"))
        .sort_values("net", ascending=False)
    )
    for stream, row in streams.iterrows():
        print(f"     {stream[:42]:<44} {int(row['n']):>3} x  {money(row['net']):>14}")

    print("\n3. CASH IN BY CATEGORY")
    print(category_summary(df).query("direction == 'CASH IN'").to_string(index=False))

    print("\n4. CASH OUT BY CATEGORY")
    print(category_summary(df).query("direction == 'CASH OUT'").to_string(index=False))

    print("\n5. MONTHLY CASH FLOW")
    print(monthly_cashflow(df).to_string(index=False))

    print("\n6. ITEMS FLAGGED FOR REVIEW (IsolationForest)")
    flagged = df.loc[df["unusual"], ["date", "description", "amount", "category", "document"]]
    if flagged.empty:
        print("   None.")
    else:
        flagged = flagged.copy()
        flagged["date"] = flagged["date"].dt.strftime("%d/%m/%Y")
        print(flagged.to_string(index=False))

    missing = df.loc[df["document"] == "", ["date", "description", "amount"]]
    print(f"\n7. CONTROLS: {len(missing)} transaction(s) without a document reference.")


# ---------------------------------------------------------------------------
# 7. Final summary table (printed last, after everything is processed)
# ---------------------------------------------------------------------------
SUMMARY_WIDTH = 94

# One layout string used for both the header and the rows, so the columns can
# never drift out of line. Indentation is baked into the first value. Each
# column must be at least as wide as its longest heading and longest value
# ("FREQUENCY" and "Irregular" are both 9), or everything after it shifts.
PROCESS_ROW = "  {process:<34} {company:<29} {freq:<9} {n:>3} {total:>13}"
COMPANY_ROW = "  {company:<32} {direction:<9} {n:>3} {average:>12} {total:>13} {share:>7}"


def trim(text: str, width: int) -> str:
    """Shorten to fit a column, marking that something was cut."""
    return text if len(text) <= width else text[: width - 2] + ".."


def row(layout: str, **cells: object) -> None:
    """Print one table row without the trailing padding spaces."""
    print(layout.format(**cells).rstrip())


def print_summary_table(df: pd.DataFrame) -> None:
    """The single consolidated table: processes, result, and company totals."""
    cash_in = df["paid_in"].sum()
    cash_out = df["paid_out"].sum()
    net = cash_in - cash_out
    processes = process_summary(df)

    print("\n" + "=" * SUMMARY_WIDTH)
    print("SUMMARY TABLE".center(SUMMARY_WIDTH))
    print(
        f"{df['date'].min():%d/%m/%Y} to {df['date'].max():%d/%m/%Y}"
        f"   |   {len(df)} transactions   |   {df['month'].nunique()} months".center(
            SUMMARY_WIDTH
        )
    )
    print("=" * SUMMARY_WIDTH)

    # --- Every cash in / cash out process --------------------------------
    print()
    row(PROCESS_ROW, process="PROCESS", company="COMPANY", freq="FREQUENCY", n="N", total="TOTAL")
    print("-" * SUMMARY_WIDTH)

    for direction, total, count in (
        ("CASH IN", cash_in, int((df["direction"] == "CASH IN").sum())),
        ("CASH OUT", -cash_out, int((df["direction"] == "CASH OUT").sum())),
    ):
        row(PROCESS_ROW, process=direction, company="", freq="", n="", total="")
        for line in processes.loc[processes["direction"] == direction].itertuples():
            signed = line.total if direction == "CASH IN" else -line.total
            row(
                PROCESS_ROW,
                process="  " + trim(line.stream, 32),
                company=trim(line.counterparty, 29),
                freq=line.frequency,
                n=line.transactions,
                total=money(signed),
            )
        row(
            PROCESS_ROW,
            process=f"  Total {direction.lower()}",
            company="",
            freq="",
            n=count,
            total=money(total),
        )

    result = "NET PROFIT FOR THE PERIOD" if net >= 0 else "NET LOSS FOR THE PERIOD"
    margin = net / cash_in * 100 if cash_in else 0.0
    print("-" * SUMMARY_WIDTH)
    row(PROCESS_ROW, process=result, company="", freq="", n=len(df), total=money(net))
    row(
        PROCESS_ROW,
        process=f"  {margin:.1f}% of income retained",
        company="",
        freq="",
        n="",
        total="",
    )
    print("=" * SUMMARY_WIDTH)

    # --- Accumulated position with each company ---------------------------
    print("\nACCUMULATED BY COMPANY")
    print("-" * SUMMARY_WIDTH)
    row(
        COMPANY_ROW,
        company="COMPANY",
        direction="DIRECTION",
        n="N",
        average="AVERAGE",
        total="ACCUMULATED",
        share="SHARE",
    )
    print("-" * SUMMARY_WIDTH)
    for line in counterparty_summary(df).itertuples():
        signed = line.total if line.direction == "CASH IN" else -line.total
        row(
            COMPANY_ROW,
            company=trim(line.counterparty, 32),
            direction=line.direction,
            n=line.transactions,
            average=money(line.average),
            total=money(signed),
            share=f"{line.pct_of_direction:.1f}%",
        )
    print("-" * SUMMARY_WIDTH)


# ---------------------------------------------------------------------------
# 8. One-page HTML summary
# ---------------------------------------------------------------------------
PAGE_CSS = """
:root {
  --ink: #1a1d21; --muted: #6b7280; --line: #e3e6ea; --bg: #ffffff;
  --panel: #f7f8fa; --in: #17694a; --out: #a8341f; --flag: #8a6100;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 40px 24px 64px; background: var(--bg); color: var(--ink);
  font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
.wrap { max-width: 980px; margin: 0 auto; }
h1 { font-size: 25px; letter-spacing: -0.02em; margin: 0 0 4px; }
h2 {
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.09em;
  color: var(--muted); margin: 40px 0 12px; padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
.sub { color: var(--muted); font-size: 14px; margin: 0 0 28px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.kpi { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px 18px; }
.kpi .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); }
.kpi .value { font-size: 23px; font-weight: 600; margin-top: 6px; letter-spacing: -0.02em; }
.kpi .note { font-size: 12px; color: var(--muted); margin-top: 4px; }
.in { color: var(--in); } .out { color: var(--out); } .flag { color: var(--flag); }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--line); white-space: nowrap; }
th {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--ink);
}
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tr.subtotal td { font-weight: 600; background: var(--panel); }
tr.result td { font-weight: 700; border-top: 2px solid var(--ink); border-bottom: 2px solid var(--ink); }
tr.indent td:first-child { padding-left: 28px; }
.tag {
  display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 20px;
  background: var(--panel); border: 1px solid var(--line); color: var(--muted);
}
footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid var(--line);
         font-size: 12.5px; color: var(--muted); }
footer p { margin: 6px 0; }
@media print { body { padding: 0; } h2 { break-after: avoid; } tr { break-inside: avoid; } }
"""


def _cell(value: float) -> str:
    """A money cell, coloured by sign."""
    css = "in" if value >= 0 else "out"
    return f'<td class="num {css}">{money(value)}</td>'


def summary_html(df: pd.DataFrame, accuracy: float, source: Path) -> str:
    cash_in = df["paid_in"].sum()
    cash_out = df["paid_out"].sum()
    net = cash_in - cash_out
    period = f"{df['date'].min():%d %b %Y} – {df['date'].max():%d %b %Y}"
    result_word = "Net profit" if net >= 0 else "Net loss"

    parts: list[str] = [
        "<div class='wrap'>",
        "<h1>Cash In / Cash Out Summary</h1>",
        f"<p class='sub'>{period} &nbsp;·&nbsp; {len(df)} transactions "
        f"&nbsp;·&nbsp; {df['month'].nunique()} months &nbsp;·&nbsp; "
        f"source: {source.name}</p>",
        "<div class='kpis'>",
        f"<div class='kpi'><div class='label'>Cash in</div>"
        f"<div class='value in'>{money(cash_in)}</div>"
        f"<div class='note'>{(df['direction'] == 'CASH IN').sum()} receipts</div></div>",
        f"<div class='kpi'><div class='label'>Cash out</div>"
        f"<div class='value out'>{money(cash_out)}</div>"
        f"<div class='note'>{(df['direction'] == 'CASH OUT').sum()} payments</div></div>",
        f"<div class='kpi'><div class='label'>{result_word}</div>"
        f"<div class='value {'in' if net >= 0 else 'out'}'>{money(net)}</div>"
        f"<div class='note'>{net / cash_in * 100:.1f}% of income retained</div></div>",
        f"<div class='kpi'><div class='label'>Cost ratio</div>"
        f"<div class='value'>{cash_out / cash_in * 100:.1f}%</div>"
        f"<div class='note'>spent per £1 received</div></div>",
        "</div>",
    ]

    # --- Profit and loss --------------------------------------------------
    parts.append("<h2>Profit and loss (cash basis)</h2><div class='scroll'><table>")
    parts.append("<tr><th>Line</th><th class='num'>Amount</th></tr>")
    for row in profit_and_loss(df).itertuples():
        css = {"subtotal": "subtotal", "result": "result"}.get(row.kind, "indent")
        parts.append(f"<tr class='{css}'><td>{row.line}</td>{_cell(row.amount)}</tr>")
    parts.append("</table></div>")

    # --- Processes --------------------------------------------------------
    processes = process_summary(df)
    for direction, heading in (("CASH IN", "Cash in processes"), ("CASH OUT", "Cash out processes")):
        subset = processes.loc[processes["direction"] == direction]
        parts.append(f"<h2>{heading}</h2><div class='scroll'><table>")
        parts.append(
            "<tr><th>Process</th><th>Category</th><th>Counterparty</th><th>Frequency</th>"
            "<th class='num'>Count</th><th class='num'>Each</th><th class='num'>Total</th></tr>"
        )
        for row in subset.itertuples():
            parts.append(
                f"<tr><td>{row.stream}</td><td>{row.category}</td>"
                f"<td>{row.counterparty}</td><td><span class='tag'>{row.frequency}</span></td>"
                f"<td class='num'>{row.transactions}</td>"
                f"<td class='num'>{money(row.each)}</td>"
                f"<td class='num'>{money(row.total)}</td></tr>"
            )
        parts.append("</table></div>")

    # --- Accumulated position per company ---------------------------------
    parts.append("<h2>Accumulated total by company</h2><div class='scroll'><table>")
    parts.append(
        "<tr><th>Company</th><th>Direction</th><th>Category</th>"
        "<th class='num'>Transactions</th><th class='num'>Average</th>"
        "<th class='num'>Accumulated</th><th class='num'>Share</th>"
        "<th>First</th><th>Last</th></tr>"
    )
    for row in counterparty_summary(df).itertuples():
        css = "in" if row.direction == "CASH IN" else "out"
        parts.append(
            f"<tr><td>{row.counterparty}</td>"
            f"<td class='{css}'>{row.direction}</td><td>{row.category}</td>"
            f"<td class='num'>{row.transactions}</td>"
            f"<td class='num'>{money(row.average)}</td>"
            f"<td class='num {css}'>{money(row.total)}</td>"
            f"<td class='num'>{row.pct_of_direction:.1f}%</td>"
            f"<td>{row.first_seen:%d/%m/%Y}</td><td>{row.last_seen:%d/%m/%Y}</td></tr>"
        )
    parts.append("</table></div>")

    # --- Month by month ---------------------------------------------------
    parts.append("<h2>Month by month</h2><div class='scroll'><table>")
    parts.append(
        "<tr><th>Month</th><th class='num'>Cash in</th><th class='num'>Cash out</th>"
        "<th class='num'>Net</th><th class='num'>Running total</th></tr>"
    )
    for row in monthly_cashflow(df).itertuples():
        parts.append(
            f"<tr><td>{row.month}</td>"
            f"<td class='num in'>{money(row.cash_in)}</td>"
            f"<td class='num out'>{money(row.cash_out)}</td>"
            f"{_cell(row.net_movement)}{_cell(row.closing_balance_movement)}</tr>"
        )
    parts.append("</table></div>")

    # --- Review list ------------------------------------------------------
    flagged = df.loc[df["unusual"]]
    parts.append("<h2>Flagged for review</h2>")
    if flagged.empty:
        parts.append("<p class='sub'>Nothing unusual detected.</p>")
    else:
        parts.append("<div class='scroll'><table>")
        parts.append(
            "<tr><th>Date</th><th>Description</th><th>Counterparty</th>"
            "<th>Category</th><th class='num'>Amount</th><th>Document</th></tr>"
        )
        for row in flagged.itertuples():
            parts.append(
                f"<tr><td>{row.date:%d/%m/%Y}</td><td>{row.description}</td>"
                f"<td>{row.counterparty}</td><td>{row.category}</td>"
                f"{_cell(row.amount)}<td>{row.document or '—'}</td></tr>"
            )
        parts.append("</table></div>")

    missing = int((df["document"] == "").sum())
    parts.append(
        "<footer>"
        "<p><strong>Basis.</strong> Prepared on a cash basis from bank transactions only — "
        "receipts and payments as they cleared the account. It is not a statutory profit "
        "figure: no accruals, prepayments, depreciation or tax are included.</p>"
        f"<p><strong>Method.</strong> Categories assigned by a TF-IDF + Naive Bayes classifier "
        f"({accuracy:.0%} cross-validated accuracy); processes grouped by KMeans clustering; "
        f"review flags from IsolationForest.</p>"
        f"<p><strong>Controls.</strong> {missing} transaction(s) without a document reference.</p>"
        "</footer></div>"
    )
    return "\n".join(parts)


def write_summary_page(df: pd.DataFrame, accuracy: float, source: Path, path: Path) -> None:
    """Save the summary as a standalone HTML file that opens in any browser."""
    page = (
        "<!doctype html>\n<html lang='en'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
        "<title>Cash In / Cash Out Summary</title>\n"
        f"<style>{PAGE_CSS}</style>\n</head>\n<body>\n"
        f"{summary_html(df, accuracy, source)}\n</body>\n</html>\n"
    )
    path.write_text(page, encoding="utf-8")


# ---------------------------------------------------------------------------
# 9. Desktop summary window
# ---------------------------------------------------------------------------
WINDOW_TABS: tuple[tuple[str, tuple[str, ...], tuple[int, ...]], ...] = (
    (
        "Processes",
        ("Direction", "Process", "Company", "Frequency", "Count", "Each", "Total"),
        (90, 265, 245, 90, 60, 100, 120),
    ),
    (
        "By company",
        ("Company", "Direction", "Category", "Count", "Average", "Accumulated",
         "Share", "First", "Last"),
        (250, 90, 180, 60, 100, 120, 70, 95, 95),
    ),
    ("Profit and loss", ("Line", "Amount"), (420, 140)),
    (
        "Month by month",
        ("Month", "Cash in", "Cash out", "Net", "Running total"),
        (110, 120, 120, 120, 130),
    ),
    (
        "Flagged for review",
        ("Date", "Description", "Company", "Category", "Amount", "Document"),
        (95, 260, 200, 170, 110, 160),
    ),
)


def _window_rows(df: pd.DataFrame, tab: str) -> list[tuple[list[str], str]]:
    """Rows for one tab, each paired with a colour tag: in, out, or a style."""
    rows: list[tuple[list[str], str]] = []

    if tab == "Processes":
        for line in process_summary(df).itertuples():
            tag = "in" if line.direction == "CASH IN" else "out"
            signed = line.total if line.direction == "CASH IN" else -line.total
            rows.append(
                (
                    [line.direction, line.stream, line.counterparty, line.frequency,
                     str(line.transactions), money(line.each), money(signed)],
                    tag,
                )
            )
    elif tab == "By company":
        for line in counterparty_summary(df).itertuples():
            tag = "in" if line.direction == "CASH IN" else "out"
            signed = line.total if line.direction == "CASH IN" else -line.total
            rows.append(
                (
                    [line.counterparty, line.direction, line.category,
                     str(line.transactions), money(line.average), money(signed),
                     f"{line.pct_of_direction:.1f}%",
                     f"{line.first_seen:%d/%m/%Y}", f"{line.last_seen:%d/%m/%Y}"],
                    tag,
                )
            )
    elif tab == "Profit and loss":
        for line in profit_and_loss(df).itertuples():
            tag = line.kind if line.kind in ("subtotal", "result") else (
                "in" if line.amount >= 0 else "out"
            )
            label = line.line if line.kind in ("subtotal", "result") else f"    {line.line}"
            rows.append(([label, money(line.amount)], tag))
    elif tab == "Month by month":
        for line in monthly_cashflow(df).itertuples():
            rows.append(
                (
                    [line.month, money(line.cash_in), money(-line.cash_out),
                     money(line.net_movement), money(line.closing_balance_movement)],
                    "in" if line.net_movement >= 0 else "out",
                )
            )
    elif tab == "Flagged for review":
        for line in df.loc[df["unusual"]].itertuples():
            rows.append(
                (
                    [f"{line.date:%d/%m/%Y}", line.description, line.counterparty,
                     line.category, money(line.amount), line.document or "—"],
                    "out" if line.amount < 0 else "in",
                )
            )
    return rows


def show_summary_window(
    df: pd.DataFrame, accuracy: float, source: Path, page: Path
) -> None:
    """Open a desktop window summarising the finances. Blocks until closed."""
    try:
        import tkinter as tk
        from tkinter import font as tkfont
        from tkinter import ttk
    except ImportError:
        print(
            "\nCould not open the summary window: this Python has no tkinter."
            "\nThe summary table above and the HTML page still work.",
            file=sys.stderr,
        )
        return

    cash_in = df["paid_in"].sum()
    cash_out = df["paid_out"].sum()
    net = cash_in - cash_out

    root = tk.Tk()
    root.title("Cash In / Cash Out Summary")
    root.geometry("1100x720")
    root.minsize(820, 520)
    root.configure(bg="#ffffff")

    base = tkfont.nametofont("TkDefaultFont").actual()["family"]
    ink, muted, green, red = "#1a1d21", "#6b7280", "#17694a", "#a8341f"

    header = tk.Frame(root, bg="#ffffff", padx=22, pady=18)
    header.pack(fill="x")
    tk.Label(
        header, text="Cash In / Cash Out Summary", bg="#ffffff", fg=ink,
        font=(base, 17, "bold"), anchor="w",
    ).pack(fill="x")
    tk.Label(
        header,
        text=f"{df['date'].min():%d %b %Y} – {df['date'].max():%d %b %Y}"
             f"   ·   {len(df)} transactions   ·   {df['month'].nunique()} months"
             f"   ·   source: {source.name}",
        bg="#ffffff", fg=muted, font=(base, 10), anchor="w",
    ).pack(fill="x", pady=(3, 0))

    kpis = tk.Frame(root, bg="#ffffff", padx=18)
    kpis.pack(fill="x")
    cards = (
        ("CASH IN", money(cash_in), f"{(df['direction'] == 'CASH IN').sum()} receipts", green),
        ("CASH OUT", money(cash_out), f"{(df['direction'] == 'CASH OUT').sum()} payments", red),
        ("NET PROFIT" if net >= 0 else "NET LOSS", money(net),
         f"{net / cash_in * 100:.1f}% of income retained" if cash_in else "",
         green if net >= 0 else red),
        ("COST RATIO", f"{cash_out / cash_in * 100:.1f}%" if cash_in else "n/a",
         "spent per £1 received", ink),
    )
    for column, (label, value, note, colour) in enumerate(cards):
        card = tk.Frame(kpis, bg="#f7f8fa", highlightbackground="#e3e6ea",
                        highlightthickness=1, padx=14, pady=11)
        card.grid(row=0, column=column, sticky="nsew", padx=4)
        kpis.grid_columnconfigure(column, weight=1, uniform="kpi")
        tk.Label(card, text=label, bg="#f7f8fa", fg=muted,
                 font=(base, 8, "bold"), anchor="w").pack(fill="x")
        tk.Label(card, text=value, bg="#f7f8fa", fg=colour,
                 font=(base, 16, "bold"), anchor="w").pack(fill="x", pady=(4, 0))
        tk.Label(card, text=note, bg="#f7f8fa", fg=muted,
                 font=(base, 8), anchor="w").pack(fill="x")

    style = ttk.Style(root)
    style.configure("Treeview", rowheight=25, font=(base, 10),
                    background="#ffffff", fieldbackground="#ffffff")
    style.configure("Treeview.Heading", font=(base, 9, "bold"))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=22, pady=(16, 8))

    for title, columns, widths in WINDOW_TABS:
        frame = tk.Frame(notebook, bg="#ffffff")
        notebook.add(frame, text=f" {title} ")

        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        bar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        for name, width in zip(columns, widths):
            numeric = name in {"Count", "Each", "Total", "Average", "Accumulated",
                               "Share", "Amount", "Cash in", "Cash out", "Net",
                               "Running total"}
            tree.heading(name, text=name.upper())
            tree.column(name, width=width, anchor="e" if numeric else "w", stretch=True)

        tree.tag_configure("in", foreground=green)
        tree.tag_configure("out", foreground=red)
        tree.tag_configure("subtotal", font=(base, 10, "bold"), background="#f7f8fa")
        tree.tag_configure("result", font=(base, 11, "bold"), background="#eef1f4")

        rows = _window_rows(df, title)
        if rows:
            for values, tag in rows:
                tree.insert("", "end", values=values, tags=(tag,))
        else:
            tree.insert("", "end", values=["Nothing to show"] + [""] * (len(columns) - 1))

    footer = tk.Frame(root, bg="#ffffff", padx=22, pady=12)
    footer.pack(fill="x")
    tk.Label(
        footer,
        text="Cash basis: receipts and payments as they cleared the bank. Not a "
             "statutory profit — no accruals, prepayments, depreciation or tax.\n"
             f"Categories by TF-IDF + Naive Bayes ({accuracy:.0%} cross-validated); "
             "processes by KMeans; review flags by IsolationForest.",
        bg="#ffffff", fg=muted, font=(base, 8), justify="left", anchor="w",
    ).pack(side="left")

    buttons = tk.Frame(footer, bg="#ffffff")
    buttons.pack(side="right")
    ttk.Button(
        buttons, text="Open HTML report",
        command=lambda: webbrowser.open(page.resolve().as_uri()),
    ).pack(side="left", padx=4)
    ttk.Button(buttons, text="Close", command=root.destroy).pack(side="left")

    root.mainloop()


def find_csv(positional: list[str]) -> Path | None:
    """Path given on the command line, else the first default that exists."""
    if positional:
        given = Path(positional[0]).expanduser()
        return given if given.exists() else None
    return next((p for p in DEFAULT_CSV_CANDIDATES if p.exists()), None)


def explain_missing_csv(positional: list[str]) -> None:
    """Tell the user exactly where we looked and what we did find."""
    print("Could not find the bank statement CSV.", file=sys.stderr)
    if positional:
        print(f"  You asked for: {Path(positional[0]).expanduser()}", file=sys.stderr)
    else:
        print("  Looked in:", file=sys.stderr)
        for candidate in DEFAULT_CSV_CANDIDATES:
            print(f"    {candidate}", file=sys.stderr)

    nearby = sorted(BASE_DIR.glob("*.csv")) + sorted(BASE_DIR.glob("data/*.csv"))
    if nearby:
        print("\n  CSV files I can see near the script:", file=sys.stderr)
        for path in nearby:
            print(f"    {path}", file=sys.stderr)
        print("\n  Run it again with the one you want, e.g.:", file=sys.stderr)
        print(f'    python "{Path(__file__).name}" "{nearby[0]}"', file=sys.stderr)
    else:
        print(
            f"\n  No CSV files found in {BASE_DIR}. Put the statement next to the"
            "\n  script, or pass its full path as an argument.",
            file=sys.stderr,
        )


def main(argv: list[str]) -> int:
    flags = {arg.lower() for arg in argv[1:] if arg.startswith("-")}
    positional = [arg for arg in argv[1:] if not arg.startswith("-")]

    csv_path = find_csv(positional)
    if csv_path is None:
        explain_missing_csv(positional)
        return 1

    print(f"Reading {csv_path}\n")
    df = load_ledger(csv_path)
    df["stream"] = cluster_streams(df)
    df["category"], accuracy = classify_categories(df)
    df["unusual"] = flag_anomalies(df)

    report(df, accuracy)

    OUTPUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUTPUT_DIR / "categorised_transactions.csv", index=False)
    monthly_cashflow(df).to_csv(OUTPUT_DIR / "monthly_cashflow.csv", index=False)
    category_summary(df).to_csv(OUTPUT_DIR / "category_summary.csv", index=False)
    counterparty_summary(df).to_csv(OUTPUT_DIR / "counterparty_summary.csv", index=False)
    process_summary(df).to_csv(OUTPUT_DIR / "process_summary.csv", index=False)
    profit_and_loss(df).to_csv(OUTPUT_DIR / "profit_and_loss.csv", index=False)

    page = OUTPUT_DIR / "summary.html"
    write_summary_page(df, accuracy, csv_path, page)

    print(f"\nWritten to {OUTPUT_DIR}/")
    print(f"Summary page: {page}")

    # Last thing on screen, once everything else is done.
    print_summary_table(df)

    if "--no-window" not in flags:
        print("\nOpening the summary window. Close it to finish.")
        show_summary_window(df, accuracy, csv_path, page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
