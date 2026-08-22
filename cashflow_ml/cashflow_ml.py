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
    return (
        df.groupby(["direction", "counterparty"])
        .agg(transactions=("amount", "size"), total=("amount", lambda s: s.abs().sum()))
        .reset_index()
        .sort_values(["direction", "total"], ascending=[True, False])
    )


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


def find_csv(argv: list[str]) -> Path | None:
    """Path given on the command line, else the first default that exists."""
    if len(argv) > 1:
        given = Path(argv[1]).expanduser()
        return given if given.exists() else None
    return next((p for p in DEFAULT_CSV_CANDIDATES if p.exists()), None)


def explain_missing_csv(argv: list[str]) -> None:
    """Tell the user exactly where we looked and what we did find."""
    print("Could not find the bank statement CSV.", file=sys.stderr)
    if len(argv) > 1:
        print(f"  You asked for: {Path(argv[1]).expanduser()}", file=sys.stderr)
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
    csv_path = find_csv(argv)
    if csv_path is None:
        explain_missing_csv(argv)
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
    print(f"\nWritten to {OUTPUT_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
