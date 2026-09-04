"""
Run the Astra vs Golf comparison on REAL listings you collected yourself.

Fill in data/real_listings.csv from the template, then:

    python analyse_real_listings.py
    python analyse_real_listings.py --data data/my_other_file.csv

One file, one row per car, with a `model` column naming which car it is. Only
four columns are actually required: model, reg_year (or age_years), mileage,
asking_price_gbp. Everything else is optional and improves the fit if present.

This script deliberately reports the things that tell you whether the data is
real: within-age price spread, R², and how far the fit is from the published
figures. Real listings are messier than any generated sample, and the numbers
below are where that shows up.
"""

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from car_depreciation_model import (AGE_COL, MILEAGE_COL, PRICE_COL,
                                    AstraDepreciationModel, load_astra_csv,
                                    select_transition_age)

HERE = Path(__file__).resolve().parent
DEFAULT = HERE / "data" / "real_listings.csv"
MIN_PER_MODEL = 12          # below this a four-parameter curve is not worth fitting


def summarise_reality(df: pd.DataFrame, label: str) -> None:
    """Print the diagnostics that separate real listings from a smooth sample."""
    print(f"\n{label} — {len(df)} cars")
    print(f"  age {df[AGE_COL].min():.0f}-{df[AGE_COL].max():.0f} yrs | "
          f"mileage {df[MILEAGE_COL].min():,.0f}-{df[MILEAGE_COL].max():,.0f} | "
          f"price £{df[PRICE_COL].min():,.0f}-£{df[PRICE_COL].max():,.0f}")
    corr = df[AGE_COL].corr(df[MILEAGE_COL])
    print(f"  corr(age, mileage) = {corr:.3f}"
          + ("" if abs(corr) < 0.95 else "   <- too collinear to separate the two effects"))

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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(DEFAULT),
                    help="CSV of real listings (default: data/real_listings.csv)")
    args = ap.parse_args(argv)

    path = Path(args.data)
    if not path.exists():
        print(f"No file at {path}.\n"
              f"Copy data/real_listings_template.csv to {path.name}, delete the two\n"
              f"example rows, and paste in your own listings.", file=sys.stderr)
        return 1

    df = load_astra_csv(str(path), verbose=False)
    if "model" not in df.columns:
        print("The file needs a 'model' column naming which car each row is.", file=sys.stderr)
        return 1

    # Drop the template's example rows if they were left in by accident.
    if "notes" in df.columns:
        keep = ~df["notes"].astype(str).str.contains("DELETE THIS ROW", case=False, na=False)
        if (~keep).any():
            print(f"Ignoring {int((~keep).sum())} template example row(s).")
            df = df[keep].copy()

    print("=" * 76)
    print(f"REAL LISTINGS — {path.name}")
    print("=" * 76)

    fits = []
    for name, sub in df.groupby("model"):
        summarise_reality(sub, str(name))
        if len(sub) < MIN_PER_MODEL:
            print(f"  SKIPPED: {len(sub)} cars is too few to fit four parameters "
                  f"(need at least {MIN_PER_MODEL}).")
            continue
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            t0, _ = select_transition_age(sub)
            model = AstraDepreciationModel(transition_age=t0).fit(sub)
            pinned = [str(x.message) for x in w if "bound" in str(x.message)]
            cv_random = model.cross_validate(sub, scheme="random", random_state=42)
        p = model.params_
        print(f"  fitted: V0 £{p['V0']:,.0f} | transition {t0:g}y | "
              f"early {(1 - np.exp(-p['k1'])) * 100:.1f}%/yr | "
              f"later {(1 - np.exp(-p['k2'])) * 100:.1f}%/yr | "
              f"{(1 - np.exp(-p['b'])) * 100:.1f}% per 10k miles")
        print(f"  R² {model.metrics_['R2']:.3f} | MAPE in-sample {model.metrics_['MAPE']:.1f}% "
              f"| random CV {cv_random['MAPE_mean']:.1f}%")
        if model.metrics_["R2"] > 0.95:
            print("  NOTE: R² above 0.95 on real listings is unusual. Check the sample is not")
            print("        all one trim, or the prices are not from a valuation tool.")
        if pinned:
            print(f"  WARNING: {pinned[0]}")
        fits.append((str(name), model, sub))

    if len(fits) == 2:
        (n1, m1, d1), (n2, m2, d2) = fits
        print("\n" + "=" * 76)
        print(f"LIKE-FOR-LIKE: {n1} vs {n2}")
        print("=" * 76)
        print(f"  {'Age':>4} {'Mileage':>9} {n1[:16]:>17} {n2[:16]:>17} {'Difference':>14}")
        for age, miles in ((3, 30_000), (5, 50_000), (7, 70_000), (10, 100_000)):
            row = pd.DataFrame({AGE_COL: [float(age)], "mileage_10k": [miles / 10_000.0]})
            a, b = m1.predict(row)[0], m2.predict(row)[0]
            print(f"  {age:>4} {miles:>9,} £{a:>16,.0f} £{b:>16,.0f} "
                  f"{b / a - 1:>13.0%}")
        print("\n  Ages outside the range you collected are extrapolation, not measurement.")
    elif len(fits) < 2:
        print("\nFit at least two models to get a comparison.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
