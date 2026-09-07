"""
Compare the Astra and the Golf, on real listings if you have them.

    python analyse_real_listings.py

Runs immediately with no setup. If you have not collected real listings yet it
analyses the bundled sample and says so, loudly, at the top and bottom of the
output. Once data/real_listings.csv has your own cars in it, it uses those
instead automatically — no flag to remember.

    python analyse_real_listings.py --data path/to/other.csv
    python analyse_real_listings.py --strict     # refuse to fall back to the sample

One row per car, with a `model` column naming which car it is. Only four
columns are required: model, reg_year (or age_years), mileage,
asking_price_gbp. Everything else is optional and sharpens the fit.
"""

import argparse
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from car_depreciation_model import (AGE_COL, MILEAGE_COL, PRICE_COL,
                                    AstraDepreciationModel, load_astra_csv,
                                    select_transition_age)

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / "data" / "real_listings.csv"
TEMPLATE = HERE / "data" / "real_listings_template.csv"
SAMPLE = HERE / "data" / "combined_market_sample.csv"
MIN_PER_MODEL = 12          # below this a four-parameter curve is not worth fitting

SAMPLE_WARNING = [
    "!" * 76,
    "  THIS IS THE BUNDLED SAMPLE, NOT REAL LISTINGS.",
    "",
    "  Every price below was generated from a documented curve calibrated to",
    "  published UK depreciation figures. No row is a real car or a real advert.",
    "  These numbers describe the curve they were built from, not the market.",
    "  Do not quote any of them as evidence of what the market did.",
    "!" * 76,
]


def start_a_file(path: Path) -> bool:
    """Create the file to fill in. Never overwrites an existing one."""
    if path.exists() or not TEMPLATE.exists():
        return False
    path.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def drop_template_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Remove the template's example rows if they were left in."""
    if "notes" not in df.columns:
        return df, 0
    keep = ~df["notes"].astype(str).str.contains("DELETE THIS ROW", case=False, na=False)
    return df[keep].copy(), int((~keep).sum())


def load_user_data(path: Path) -> Optional[pd.DataFrame]:
    """Return the user's listings, or None if there are none worth using yet."""
    if not path.exists():
        return None
    try:
        df = load_astra_csv(str(path), verbose=False)
    except (ValueError, pd.errors.ParserError) as exc:
        print(f"Could not read {path}: {exc}\n", file=sys.stderr)
        return None
    if "model" not in df.columns:
        print(f"{path.name} has no 'model' column, so it cannot be used.\n"
              f"Columns found: {list(df.columns)}\n", file=sys.stderr)
        return None
    df, _ = drop_template_rows(df)
    return df if not df.empty else None


def how_to_use_real_data(path: Path) -> None:
    print("\n" + "-" * 76)
    print("To run this on REAL cars instead:")
    print(f"\n  Edit  {path}")
    print("\n  One row per car. Only four columns are required:")
    print("      model,reg_year,mileage,asking_price_gbp")
    print("      Vauxhall Astra,2019,58000,7995")
    print("      Volkswagen Golf,2020,42000,13250")
    print(f"\n  Needs at least {MIN_PER_MODEL} cars per model. Aim for a spread of ages")
    print("  1-10, and deliberately mix low-mileage old cars with high-mileage young")
    print("  ones, or age and mileage cannot be told apart.")
    print("\n  Then run this script again — it picks the file up automatically.")
    print("-" * 76)


def summarise_reality(df: pd.DataFrame, label: str) -> None:
    """Print the diagnostics that separate real listings from a smooth sample."""
    print(f"\n{label} — {len(df)} cars")
    print(f"  age {df[AGE_COL].min():.0f}-{df[AGE_COL].max():.0f} yrs | "
          f"mileage {df[MILEAGE_COL].min():,.0f}-{df[MILEAGE_COL].max():,.0f} | "
          f"price £{df[PRICE_COL].min():,.0f}-£{df[PRICE_COL].max():,.0f}")

    # A correlation needs a few points to mean anything, and numpy warns loudly
    # on a one-row group. Say nothing rather than print a nan.
    if len(df) >= 5:
        with np.errstate(invalid="ignore", divide="ignore"):
            corr = df[AGE_COL].corr(df[MILEAGE_COL])
        if pd.notna(corr):
            print(f"  corr(age, mileage) = {corr:.3f}"
                  + ("" if abs(corr) < 0.95
                     else "   <- too collinear to separate the two effects"))

    bands = df.groupby(AGE_COL)[PRICE_COL].agg(["count", "mean", "std"])
    bands = bands[bands["count"] >= 3]
    if len(bands):
        cv = float((bands["std"] / bands["mean"]).mean())
        print(f"  within-age price spread (CV) = {cv:.2f}", end="")
        if cv < 0.20:
            print("   <- suspiciously tidy for real listings (expect 0.25-0.40)")
        elif cv > 0.55:
            print("   <- very wide; check for mixed trims or data-entry errors")
        else:
            print("   <- in the range real listings usually show")


def fit_one(name: str, sub: pd.DataFrame, is_sample: bool) -> Optional[Dict]:
    """Fit one car, reporting anything that makes the fit untrustworthy."""
    summarise_reality(sub, name)
    if len(sub) < MIN_PER_MODEL:
        print(f"  SKIPPED: {len(sub)} cars is too few to fit four parameters "
              f"(need at least {MIN_PER_MODEL}).")
        return None

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        t0, _ = select_transition_age(sub)
        model = AstraDepreciationModel(transition_age=t0).fit(sub)
        pinned = [str(w.message) for w in caught if "bound" in str(w.message)]
        cv = model.cross_validate(sub, scheme="random", random_state=42)

    p = model.params_
    print(f"  fitted: V0 £{p['V0']:,.0f} | transition {t0:g}y | "
          f"early {(1 - np.exp(-p['k1'])) * 100:.1f}%/yr | "
          f"later {(1 - np.exp(-p['k2'])) * 100:.1f}%/yr | "
          f"{(1 - np.exp(-p['b'])) * 100:.1f}% per 10k miles")
    print(f"  R² {model.metrics_['R2']:.3f} | MAPE in-sample {model.metrics_['MAPE']:.1f}% "
          f"| random CV {cv['MAPE_mean']:.1f}%")
    if model.metrics_["R2"] > 0.95 and not is_sample:
        print("  NOTE: R² above 0.95 on real listings is unusual. Check the sample is not")
        print("        all one trim, or the prices are not from a valuation tool.")
    if pinned:
        print(f"  WARNING: {pinned[0]}")
    return {"name": name, "model": model, "df": sub}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compare car depreciation on real listings, or on the bundled sample.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(DEFAULT),
                    help="CSV of listings (default: data/real_listings.csv)")
    ap.add_argument("--strict", action="store_true",
                    help="fail rather than fall back to the bundled sample")
    args = ap.parse_args(argv)

    path = Path(args.data).resolve()
    df = load_user_data(path)
    is_sample = df is None

    if is_sample:
        if args.strict:
            print(f"No usable listings in {path}, and --strict forbids the sample.",
                  file=sys.stderr)
            return 1
        if not SAMPLE.exists():
            print(f"No usable listings in {path}, and no sample at {SAMPLE}.",
                  file=sys.stderr)
            return 1
        # Leave a file ready to fill in, but do not stop for it.
        start_a_file(path)
        df = load_astra_csv(str(SAMPLE), verbose=False)
        df, _ = drop_template_rows(df)

    print("=" * 76)
    if is_sample:
        for line in SAMPLE_WARNING:
            print(line)
    else:
        print(f"REAL LISTINGS — {path}")
    print("=" * 76)

    fits: List[Dict] = []
    for name, sub in df.groupby("model"):
        fit = fit_one(str(name), sub, is_sample)
        if fit:
            fits.append(fit)

    if len(fits) == 2:
        a, b = fits
        print("\n" + "=" * 76)
        print(f"LIKE-FOR-LIKE: {a['name']} vs {b['name']}")
        print("=" * 76)
        print(f"  {'Age':>4} {'Mileage':>9} {a['name'][:16]:>17} {b['name'][:16]:>17} "
              f"{'Difference':>12}")
        for age, miles in ((3, 30_000), (5, 50_000), (7, 70_000), (10, 100_000)):
            row = pd.DataFrame({AGE_COL: [float(age)], "mileage_10k": [miles / 10_000.0]})
            av, bv = a["model"].predict(row)[0], b["model"].predict(row)[0]
            print(f"  {age:>4} {miles:>9,} £{av:>16,.0f} £{bv:>16,.0f} {bv / av - 1:>11.0%}")
        print("\n  Ages outside the range collected are extrapolation, not measurement.")
    elif len(fits) == 1:
        print(f"\nOnly one model had enough cars to fit. Add at least {MIN_PER_MODEL} "
              f"of the other one to get a comparison.")
    else:
        print(f"\nNo model had the {MIN_PER_MODEL} cars needed to fit a curve.")

    if is_sample:
        print()
        for line in SAMPLE_WARNING:
            print(line)
        how_to_use_real_data(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
