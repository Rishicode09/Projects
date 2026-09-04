"""
Fit the depreciation model to the Astra and the Golf and compare them.

Both cars go through the identical model, identical cleaning and identical
cross-validation, so the comparison is between two fitted curves rather than
between two analyses.

Run:  python compare_astra_golf.py
"""

import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from car_depreciation_model import (AGE_COL, PRICE_COL, MILEAGE_COL, AstraDepreciationModel,
                                    load_astra_csv, select_transition_age,
                                    _gbp_compact, _style_axis, INK, INK_SOFT, GRID)

DATA_DIR = Path(__file__).resolve().parent / "data"
ASTRA_BLUE, GOLF_ORANGE = "#2a78d6", "#eb6834"      # validated pair, all-pairs light+dark
REF_MILES_PER_YEAR = 10_000

CARS = [
    ("Vauxhall Astra", DATA_DIR / "vauxhall_astra_market_sample.csv", ASTRA_BLUE),
    ("Volkswagen Golf", DATA_DIR / "vw_golf_market_sample.csv", GOLF_ORANGE),
]

# Published UK figures the samples were calibrated on, replotted as a check that
# the fitted curve lands where the research says it should.
PUBLISHED = {
    "Vauxhall Astra": {3: 0.50, 5: 0.42},     # 47-53% at 3yr, ~42% at 5yr
    "Volkswagen Golf": {3: 0.61, 5: 0.45},    # ~61% at 3yr, 42-48% at 5yr
}


def fit_car(name: str, path: Path) -> Dict:
    """Load, choose a transition age, fit, and cross-validate one car."""
    df = load_astra_csv(str(path), verbose=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t0, _ = select_transition_age(df)
        model = AstraDepreciationModel(transition_age=t0).fit(df, warn_on_bounds=False)
        cv_random = model.cross_validate(df, scheme="random", random_state=42)
        cv_age = model.cross_validate(df, scheme="age_blocked")
    return {"name": name, "df": df, "model": model, "t0": t0,
            "cv_random": cv_random, "cv_age": cv_age}


def reference_curve(model: AstraDepreciationModel, ages: np.ndarray) -> np.ndarray:
    """Price of an otherwise-average car doing 10,000 miles a year."""
    ref = pd.DataFrame({AGE_COL: ages,
                        "mileage_10k": ages * (REF_MILES_PER_YEAR / 10_000.0)})
    return model.predict(ref)


def retention_curve(model: AstraDepreciationModel, df: pd.DataFrame,
                    ages: np.ndarray) -> np.ndarray:
    """
    Share of list price retained, measured against the list price of the car's
    OWN registration year.

    Dividing by the fitted V0 instead would understate retention badly, because
    V0 is a 2026-money figure while a ten-year-old car was listed at 2016
    prices. That mistake made the Astra look like it retained 16% at ten years
    when the correct figure is 24%.
    """
    known = df.groupby(AGE_COL)["original_list_gbp"].mean()
    lists = np.interp(ages, known.index.to_numpy(float), known.to_numpy(float))
    return reference_curve(model, ages) / lists


def plot_comparison(fits: List[Dict], save_path: str = None):
    mpl.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                         "axes.labelcolor": INK_SOFT, "figure.facecolor": "#fcfcfb",
                         "axes.facecolor": "#fcfcfb"})
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    grid = np.linspace(0, 10, 120)
    colours = {"Vauxhall Astra": ASTRA_BLUE, "Volkswagen Golf": GOLF_ORANGE}

    # ---- Panel 1: price against age -----------------------------------------
    ax = axes[0, 0]
    _style_axis(ax)
    for f in fits:
        c = colours[f["name"]]
        ax.scatter(f["df"][AGE_COL], f["df"][PRICE_COL], s=20, color=c, alpha=0.35,
                   edgecolors="none", zorder=2)
        ax.plot(grid, reference_curve(f["model"], grid), color=c, linewidth=2.4,
                zorder=4, label=f["name"])
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Asking price")
    ax.set_title("Price against age", fontsize=12, color=INK, pad=8)
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(_gbp_compact))
    ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=6))
    ax.legend(loc="upper right", fontsize=9, framealpha=0.93,
              facecolor="#fcfcfb", edgecolor="none")

    # ---- Panel 2: share of list price retained ------------------------------
    # The headline comparison: it removes the fact that a Golf costs more new.
    ax = axes[0, 1]
    _style_axis(ax)
    for f in fits:
        c = colours[f["name"]]
        ax.plot(grid, retention_curve(f["model"], f["df"], grid) * 100, color=c,
                linewidth=2.4, zorder=4, label=f["name"])
        pub = PUBLISHED[f["name"]]
        ax.scatter(list(pub.keys()), [v * 100 for v in pub.values()], s=64,
                   facecolor="#fcfcfb", edgecolors=c, linewidths=2, zorder=5)
    ax.scatter([], [], s=64, facecolor="#fcfcfb", edgecolors=INK_SOFT, linewidths=2,
               label="Published figure")
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Share of price when new (%)")
    ax.set_title("Value retained — the like-for-like comparison", fontsize=12,
                 color=INK, pad=8)
    ax.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter("{x:.0f}%"))
    ax.legend(loc="upper right", fontsize=9, framealpha=0.93,
              facecolor="#fcfcfb", edgecolor="none")

    # ---- Panel 3: pounds lost from new --------------------------------------
    ax = axes[1, 0]
    _style_axis(ax)
    marks = [3, 5, 7, 10]
    width = 0.36
    xs = np.arange(len(marks))
    for i, f in enumerate(fits):
        c = colours[f["name"]]
        v0 = f["model"].params_["V0"]
        lost = [v0 - reference_curve(f["model"], np.array([float(a)]))[0] for a in marks]
        bars = ax.bar(xs + (i - 0.5) * width, lost, width * 0.92, color=c,
                      zorder=3, label=f["name"])
        ax.bar_label(bars, labels=[_gbp_compact(v) for v in lost], padding=3,
                     fontsize=8, color=INK_SOFT)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{a} yrs" for a in marks])
    ax.set_ylabel("Value lost from new")
    ax.set_title("What depreciation costs the first owner", fontsize=12, color=INK, pad=8)
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(_gbp_compact))
    ax.margins(y=0.16)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.93,
              facecolor="#fcfcfb", edgecolor="none")

    # ---- Panel 4: the numbers ----------------------------------------------
    ax = axes[1, 1]
    ax.axis("off")
    a, g = fits[0], fits[1]

    def pct(model, key):
        return (1 - np.exp(-model.params_[key])) * 100

    lines = ["                        ASTRA      GOLF",
             f"Price when new      {_gbp_compact(a['model'].params_['V0']):>9}"
             f" {_gbp_compact(g['model'].params_['V0']):>9}",
             f"Transition age      {a['t0']:>8.1f}y {g['t0']:>8.1f}y",
             f"Early annual loss   {pct(a['model'], 'k1'):>8.1f}% {pct(g['model'], 'k1'):>8.1f}%",
             f"Later annual loss   {pct(a['model'], 'k2'):>8.1f}% {pct(g['model'], 'k2'):>8.1f}%",
             f"Per 10,000 miles    {pct(a['model'], 'b'):>8.1f}% {pct(g['model'], 'b'):>8.1f}%",
             "",
             "FIT QUALITY",
             f"R²                  {a['model'].metrics_['R2']:>9.3f} {g['model'].metrics_['R2']:>9.3f}",
             f"MAPE, in-sample     {a['model'].metrics_['MAPE']:>8.1f}% {g['model'].metrics_['MAPE']:>8.1f}%",
             f"MAPE, random CV     {a['cv_random']['MAPE_mean']:>8.1f}% {g['cv_random']['MAPE_mean']:>8.1f}%",
             f"MAPE, older-car CV  {a['cv_age']['MAPE_mean']:>8.1f}% {g['cv_age']['MAPE_mean']:>8.1f}%",
             "",
             "RETAINED AT"]
    for age in (3, 5, 10):
        av = retention_curve(a["model"], a["df"], np.array([float(age)]))[0]
        gv = retention_curve(g["model"], g["df"], np.array([float(age)]))[0]
        lines.append(f"  {age:>2} years          {av * 100:>8.1f}% {gv * 100:>8.1f}%")
    lines += ["", "Identical model, cleaning and CV for both.",
              "Only list prices and retention curves differ."]

    w_in, h_in = fig.get_size_inches()
    fs = float(np.clip(min(w_in * 0.66, h_in * 0.95), 6.0, 10.0))
    ax.text(0.0, 1.0, "\n".join(lines), transform=ax.transAxes, va="top", ha="left",
            fontsize=fs, family="DejaVu Sans Mono", color=INK_SOFT, linespacing=1.5)

    fig.suptitle("Vauxhall Astra vs Volkswagen Golf — fitted depreciation",
                 fontsize=15, color=INK, x=0.01, ha="left")
    if save_path:
        fig.savefig(save_path, dpi=120, facecolor="#fcfcfb")
    else:
        plt.show()
    return fig


if __name__ == "__main__":
    fits = [fit_car(name, path) for name, path, _ in CARS]

    print("=" * 74)
    print("ASTRA vs GOLF — same model, same cleaning, same cross-validation")
    print("=" * 74)
    hdr = f"{'':<24}{'Astra':>14}{'Golf':>14}{'Difference':>18}"
    print(hdr)
    print("-" * 74)

    a, g = fits
    def row(label, av, gv, fmt="{:.1f}%", diff=True):
        d = ""
        if diff:
            d = f"{gv - av:+.1f}" + ("%" if fmt.endswith("%}") or "%" in fmt else "")
        print(f"{label:<24}{fmt.format(av):>14}{fmt.format(gv):>14}{d:>18}")

    row("Price when new", a["model"].params_["V0"], g["model"].params_["V0"], "£{:,.0f}", False)
    row("Transition age (years)", a["t0"], g["t0"], "{:.1f}")
    for key, label in (("k1", "Early annual loss"), ("k2", "Later annual loss"),
                       ("b", "Per 10,000 miles")):
        row(label, (1 - np.exp(-a["model"].params_[key])) * 100,
            (1 - np.exp(-g["model"].params_[key])) * 100)
    print("-" * 74)
    for age in (3, 5, 10):
        av = retention_curve(a["model"], a["df"], np.array([float(age)]))[0] * 100
        gv = retention_curve(g["model"], g["df"], np.array([float(age)]))[0] * 100
        row(f"Retained at {age} years", av, gv)
    print("-" * 74)
    print("Fitted retention vs the published figures the samples were built from:")
    for f in fits:
        for age, published in sorted(PUBLISHED[f["name"]].items()):
            fitted = retention_curve(f["model"], f["df"], np.array([float(age)]))[0]
            print(f"  {f['name']:<18} {age} years   fitted {fitted:>5.1%}   "
                  f"published {published:>5.1%}   gap {fitted - published:+.1%}")
    print("-" * 74)
    for f in fits:
        print(f"{f['name']:<20} R² {f['model'].metrics_['R2']:.3f} | "
              f"MAPE in-sample {f['model'].metrics_['MAPE']:.1f}% | "
              f"random CV {f['cv_random']['MAPE_mean']:.1f}% | "
              f"older-car CV {f['cv_age']['MAPE_mean']:.1f}%")
    print("=" * 74)

    print("\nSame car, same age, same mileage — what the badge is worth")
    print(f"  {'Age':>4} {'Mileage':>9} {'Astra':>10} {'Golf':>10} {'Golf premium':>14}")
    for age, miles in ((3, 30_000), (5, 50_000), (7, 70_000), (10, 100_000)):
        row_df = pd.DataFrame({AGE_COL: [float(age)], "mileage_10k": [miles / 10_000.0]})
        av = a["model"].predict(row_df)[0]
        gv = g["model"].predict(row_df)[0]
        print(f"  {age:>4} {miles:>9,} £{av:>9,.0f} £{gv:>9,.0f} "
              f"£{gv - av:>8,.0f} ({gv / av - 1:+.0%})")

    plot_comparison(fits)
