"""
Vauxhall Astra depreciation model.

Tailored to vauxhall_astra_market_sample.csv: a cross-section of 100 cars where
many different cars share the same age, and where age and mileage vary
independently of each other.

Model:

    price = V0 * exp(-rate(age)) * exp(-b * mileage_10k) * PRODUCT(multipliers)

    rate(age) = k1 * age                                  for age <= t0
              = k1 * t0 + k2 * (age - t0)                 for age >  t0

V0 is what the car was worth new, k1 the fast early depreciation rate, k2 the
slower rate after the transition age t0, and b the penalty per 10,000 miles.
The multipliers are one number per level of each categorical column, so a GS
trim or a full service history shifts the whole curve up or down by a
percentage rather than changing its shape.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap, Normalize
from scipy.optimize import curve_fit
from sklearn.model_selection import KFold, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from typing import Dict, Iterable, List, Optional, Tuple

# Resolved next to this file, not relative to wherever you happen to run it
# from. Editors and notebooks each pick their own working directory, so a bare
# filename here is the usual cause of "FileNotFoundError" on someone else's machine.
DATA_PATH = str(Path(__file__).resolve().parent / "vauxhall_astra_market_sample.csv")

# Columns the model needs. Everything else in the CSV is carried along but unused.
AGE_COL = "age_years"
MILEAGE_COL = "mileage"
PRICE_COL = "asking_price_gbp"
CATEGORICAL_COLS = ["trim", "fuel", "transmission",
                    "service_history", "seller_type", "condition"]

# ---- palette (validated categorical slots 1-3 + blue sequential ramp) -------
BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
INK, INK_SOFT, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#104281"]
MILEAGE_CMAP = LinearSegmentedColormap.from_list("mileage", BLUE_RAMP)


# ============================================================================
# 1. LOADING
# ============================================================================
def load_astra_csv(path: str = DATA_PATH, verbose: bool = True) -> pd.DataFrame:
    """
    Read the sample CSV and keep only rows the model can actually use.

    Real listing exports contain rows that will silently poison a fit: a price
    of £1 for an advert placeholder, a six-digit mileage typo, a blank age. The
    same guards are applied here so that swapping in real data does not require
    rewriting this function.
    """
    # keep_default_na=False matters here: pandas treats the literal string
    # "None" as missing by default, which would silently turn every
    # "None" service history into a NaN and invent a phantom category.
    df = pd.read_csv(path, keep_default_na=False,
                     na_values=["", "NA", "N/A", "NaN", "null", "NULL"])

    required = [AGE_COL, MILEAGE_COL, PRICE_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required column(s): {missing}")

    n_start = len(df)
    reasons: Dict[str, int] = {}

    def drop(mask: pd.Series, why: str) -> None:
        nonlocal df
        n = int(mask.sum())
        if n:
            reasons[why] = n
            df = df.loc[~mask].copy()

    drop(df[required].isna().any(axis=1), "missing age, mileage or price")
    drop(df[PRICE_COL] <= 0, "price not positive")
    drop(df[PRICE_COL] < 300, "price below £300 (placeholder advert)")
    drop(df[MILEAGE_COL] < 0, "negative mileage")
    drop(df[MILEAGE_COL] > 300_000, "mileage above 300,000 (likely typo)")
    drop(df[AGE_COL] < 0, "negative age")

    # Model works in units of 10,000 miles so that b lands on a readable scale.
    df["mileage_10k"] = df[MILEAGE_COL] / 10_000.0

    for col in CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)

    if verbose:
        print(f"Loaded {path}: {len(df)} of {n_start} rows usable")
        for why, n in reasons.items():
            print(f"  dropped {n}: {why}")
        print(f"  age {df[AGE_COL].min():.0f}-{df[AGE_COL].max():.0f} yrs | "
              f"mileage {df[MILEAGE_COL].min():,.0f}-{df[MILEAGE_COL].max():,.0f} | "
              f"price £{df[PRICE_COL].min():,.0f}-£{df[PRICE_COL].max():,.0f}")
        corr = df[AGE_COL].corr(df[MILEAGE_COL])
        print(f"  corr(age, mileage) = {corr:.3f}", end="")
        print("  <- age and mileage are separable" if abs(corr) < 0.95
              else "  <- WARNING: too collinear to separate age from mileage")
    return df


# ============================================================================
# 2. MODEL
# ============================================================================
class AstraDepreciationModel:
    """Two-phase exponential depreciation with a mileage penalty and categorical multipliers."""

    CORE_PARAMS = ["V0", "k1", "k2", "b"]
    DEFAULT_BOUNDS = ([8_000, 0.02, 0.001, 0.001], [45_000, 0.60, 0.40, 0.30])

    def __init__(self, transition_age: float = 3.0,
                 categorical_cols: Optional[Iterable[str]] = None,
                 shrinkage: float = 3.0):
        """
        Args:
            transition_age: Age (years) at which the depreciation rate changes.
            categorical_cols: Columns to fit price multipliers for. None uses
                the module default; an empty list fits the curve alone.
            shrinkage: Pulls multipliers for thinly-populated levels back
                toward 1.0. A level seen n times keeps n/(n+shrinkage) of its
                estimated effect, so a trim appearing twice cannot swing the
                model on the strength of two cars.
        """
        self.transition_age = float(transition_age)
        self.categorical_cols = (list(CATEGORICAL_COLS) if categorical_cols is None
                                 else list(categorical_cols))
        self.shrinkage = float(shrinkage)

        self.params_: Optional[Dict[str, float]] = None
        self.multipliers_: Dict[str, Dict[str, float]] = {}
        self.bounds_: Optional[Tuple] = None
        self.metrics_: Dict = {}
        self.train_: Optional[pd.DataFrame] = None

    # ---- core curve --------------------------------------------------------
    def _curve(self, x, V0, k1, k2, b):
        age, miles = x
        rate = np.where(age <= self.transition_age,
                        k1 * age,
                        k1 * self.transition_age + k2 * (age - self.transition_age))
        return V0 * np.exp(-rate) * np.exp(-b * miles)

    def _adjustment(self, df: pd.DataFrame) -> np.ndarray:
        """Combined categorical multiplier for each row (1.0 where unknown)."""
        adj = np.ones(len(df))
        for col, levels in self.multipliers_.items():
            if col in df.columns:
                adj *= df[col].map(levels).fillna(1.0).to_numpy(dtype=float)
        return adj

    def _fit_core(self, age, miles, price, p0=None):
        lower, upper = (np.asarray(b, dtype=float) for b in self.bounds_)
        if p0 is None:
            p0 = np.array([float(np.max(price)) * 1.1, 0.20, 0.12, 0.05])
        margin = 1e-6 * (upper - lower)
        p0 = np.clip(np.asarray(p0, dtype=float), lower + margin, upper - margin)
        popt, _ = curve_fit(self._curve, (age, miles), price,
                            p0=p0, bounds=self.bounds_, maxfev=20_000)
        return popt

    def fit(self, df: pd.DataFrame, bounds: Optional[Tuple] = None,
            n_iter: int = 6, warn_on_bounds: bool = True) -> "AstraDepreciationModel":
        """
        Fit the curve and the categorical multipliers by backfitting.

        The two cannot be fitted in one pass without adding a parameter per
        level, which 100 rows will not support. Instead the curve is fitted to
        prices divided by the current multipliers, the multipliers are
        re-estimated from what the curve leaves behind, and the two steps
        alternate until they stop moving.
        """
        self.bounds_ = bounds if bounds is not None else self.DEFAULT_BOUNDS
        if len(df) < len(self.CORE_PARAMS):
            raise ValueError(f"Need at least {len(self.CORE_PARAMS)} rows, got {len(df)}.")

        age = df[AGE_COL].to_numpy(dtype=float)
        miles = df["mileage_10k"].to_numpy(dtype=float)
        price = df[PRICE_COL].to_numpy(dtype=float)

        cols = [c for c in self.categorical_cols if c in df.columns]
        self.multipliers_ = {c: {} for c in cols}
        popt = None

        for _ in range(n_iter):
            adj = self._adjustment(df)
            popt = self._fit_core(age, miles, price / adj, p0=popt)
            base = self._curve((age, miles), *popt)

            for col in cols:
                # Ratio left over once the curve and every OTHER column are accounted for.
                others = self._adjustment(df) / np.where(
                    df[col].map(self.multipliers_[col]).fillna(1.0).to_numpy(dtype=float) == 0,
                    1.0,
                    df[col].map(self.multipliers_[col]).fillna(1.0).to_numpy(dtype=float))
                ratio = price / np.maximum(base * others, 1e-9)
                log_ratio = np.log(np.maximum(ratio, 1e-9))

                est = {}
                for level, idx in df.groupby(col).groups.items():
                    rows = df.index.get_indexer(idx)
                    n = len(rows)
                    raw = float(np.mean(log_ratio[rows]))
                    est[str(level)] = float(np.exp(raw * n / (n + self.shrinkage)))

                # Normalise so the multipliers describe deviations around the
                # curve rather than quietly rescaling V0.
                mapped = df[col].map(est).astype(float).to_numpy()
                est = {k: v / float(np.exp(np.mean(np.log(mapped)))) for k, v in est.items()}
                self.multipliers_[col] = est

        self.params_ = dict(zip(self.CORE_PARAMS, popt))
        if warn_on_bounds:
            self._warn_if_pinned(popt)

        self.train_ = df.copy()
        pred = self.predict(df)
        resid = price - pred
        self.metrics_ = {
            "R2": 1 - np.sum(resid ** 2) / np.sum((price - price.mean()) ** 2),
            "MAE": mean_absolute_error(price, pred),
            "MAPE": mean_absolute_percentage_error(price, pred) * 100,
            "RMSE": float(np.sqrt(np.mean(resid ** 2))),
            "n": len(df),
        }
        return self

    def _warn_if_pinned(self, popt) -> None:
        """A parameter sitting on a bound was constrained, not estimated."""
        lower, upper = (np.asarray(b, dtype=float) for b in self.bounds_)
        tol = 1e-6 * (upper - lower)
        pinned = [n for n, v, lo, hi, t in zip(self.CORE_PARAMS, popt, lower, upper, tol)
                  if v <= lo + t or v >= hi - t]
        if pinned:
            warnings.warn(
                f"Parameter(s) {', '.join(pinned)} converged onto a fitting bound. "
                f"They are constrained, not estimated, and must not be read as rates.",
                RuntimeWarning, stacklevel=3)

    # ---- prediction --------------------------------------------------------
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if self.params_ is None:
            raise RuntimeError("Call fit() before predict().")
        age = df[AGE_COL].to_numpy(dtype=float)
        miles = (df["mileage_10k"] if "mileage_10k" in df.columns
                 else df[MILEAGE_COL] / 10_000.0).to_numpy(dtype=float)
        return self._curve((age, miles), *[self.params_[p] for p in self.CORE_PARAMS]) \
            * self._adjustment(df)

    def predict_car(self, age: float, mileage: float, **features) -> float:
        """Price one specific car. Unknown or omitted features get a multiplier of 1.0."""
        row = {AGE_COL: age, MILEAGE_COL: mileage, "mileage_10k": mileage / 10_000.0}
        row.update(features)
        return float(self.predict(pd.DataFrame([row]))[0])

    def effective_n_params(self) -> int:
        """Curve parameters plus one free multiplier per level beyond the first."""
        return len(self.CORE_PARAMS) + sum(max(len(v) - 1, 0)
                                           for v in self.multipliers_.values())

    def predict_with_uncertainty(self, df: pd.DataFrame, n_bootstrap: int = 400,
                                 confidence: float = 0.90,
                                 random_state: Optional[int] = None) -> Dict[str, np.ndarray]:
        """
        Prediction intervals by resampling proportional residuals.

        Proportional rather than absolute, because a £25k car misses by
        hundreds where a £3k car misses by tens; pooling absolute residuals
        would make the interval far too narrow at the top of the range and far
        too wide at the bottom.
        """
        if self.train_ is None:
            raise RuntimeError("Call fit() before predict_with_uncertainty().")
        rng = np.random.default_rng(random_state)

        train = self.train_
        price = train[PRICE_COL].to_numpy(dtype=float)
        fitted = self.predict(train)
        dof = len(train) - self.effective_n_params()
        if dof <= 0:
            raise ValueError(
                f"{len(train)} rows cannot support {self.effective_n_params()} effective "
                f"parameters. Reduce categorical_cols or raise shrinkage.")
        # In-sample residuals understate real error because the fit bends toward
        # the noise; sqrt(n/(n-p)) restores the spread.
        rel = (price / np.maximum(fitted, 1e-9) - 1.0) * np.sqrt(len(train) / dof)

        age = train[AGE_COL].to_numpy(dtype=float)
        miles = train["mileage_10k"].to_numpy(dtype=float)
        adj_train = self._adjustment(train)
        base_pred = self.predict(df)
        p0 = [self.params_[p] for p in self.CORE_PARAMS]

        draws: List[np.ndarray] = []
        for _ in range(n_bootstrap):
            boot = fitted * (1.0 + rng.choice(rel, size=len(train), replace=True))
            try:
                popt = self._fit_core(age, miles, np.maximum(boot, 1.0) / adj_train, p0=p0)
            except (RuntimeError, ValueError):
                continue
            curve = self._curve(
                (df[AGE_COL].to_numpy(dtype=float),
                 (df["mileage_10k"] if "mileage_10k" in df.columns
                  else df[MILEAGE_COL] / 10_000.0).to_numpy(dtype=float)), *popt)
            # Add an independent noise draw: this is an interval for one car,
            # not for the average car.
            draws.append(curve * self._adjustment(df)
                         * (1.0 + rng.choice(rel, size=len(df), replace=True)))

        if not draws:
            warnings.warn("Every bootstrap refit failed; returning point predictions.",
                          RuntimeWarning, stacklevel=2)
            return {"mean": base_pred, "lower": base_pred, "upper": base_pred,
                    "confidence": confidence}

        arr = np.asarray(draws)
        return {
            "mean": base_pred,
            "lower": np.percentile(arr, (1 - confidence) / 2 * 100, axis=0),
            "upper": np.percentile(arr, (1 + confidence) / 2 * 100, axis=0),
            "confidence": confidence,
        }

    # ---- validation --------------------------------------------------------
    def cross_validate(self, df: pd.DataFrame, n_splits: int = 5,
                       scheme: str = "random", random_state: int = 0) -> Dict[str, float]:
        """
        Estimate out-of-sample error.

        scheme="random"      hold out random cars. Answers: how well do we price
                             a car similar to ones already seen?
        scheme="age_blocked" train on younger cars, test on older ones. Answers:
                             how well do we extrapolate down the curve? This is
                             the harder and more honest test, and the one that
                             matches forecasting a car's future value.
        """
        if scheme == "random":
            splitter = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
            order = df.index
        elif scheme == "age_blocked":
            splitter = TimeSeriesSplit(n_splits=n_splits)
            order = df.sort_values(AGE_COL).index
        else:
            raise ValueError("scheme must be 'random' or 'age_blocked'")

        ordered = df.loc[order].reset_index(drop=True)
        mapes, maes, skipped = [], [], 0

        for train_idx, test_idx in splitter.split(ordered):
            train, test = ordered.iloc[train_idx], ordered.iloc[test_idx]
            if len(train) < len(self.CORE_PARAMS) + 2:
                skipped += 1
                continue
            fold = AstraDepreciationModel(self.transition_age,
                                          self.categorical_cols, self.shrinkage)
            # Bound warnings from folds are noise; the full-data fit reports them.
            fold.fit(train, bounds=self.bounds_, warn_on_bounds=False)
            pred = fold.predict(test)
            actual = test[PRICE_COL].to_numpy(dtype=float)
            mapes.append(mean_absolute_percentage_error(actual, pred) * 100)
            maes.append(mean_absolute_error(actual, pred))

        if not mapes:
            raise ValueError(f"No usable CV folds for scheme={scheme!r}.")
        return {"scheme": scheme, "folds": len(mapes), "skipped": skipped,
                "MAPE_mean": float(np.mean(mapes)), "MAPE_std": float(np.std(mapes)),
                "MAE_mean": float(np.mean(maes)), "MAE_std": float(np.std(maes))}


def select_transition_age(df: pd.DataFrame, candidates=np.arange(1.5, 6.5, 0.5),
                          **kwargs) -> Tuple[float, pd.DataFrame]:
    """
    Choose t0 by fit quality instead of assuming 3 years.

    t0 adds no parameters, so comparing in-sample RMSE across candidates is a
    fair comparison rather than a complexity contest.
    """
    rows = []
    for t0 in candidates:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = AstraDepreciationModel(transition_age=float(t0), **kwargs).fit(
                df, warn_on_bounds=False)
        rows.append({"transition_age": float(t0), "RMSE": m.metrics_["RMSE"],
                     "MAPE": m.metrics_["MAPE"], "R2": m.metrics_["R2"]})
    table = pd.DataFrame(rows)
    return float(table.loc[table["RMSE"].idxmin(), "transition_age"]), table


# ============================================================================
# 3. VISUALISATION
# ============================================================================
def _gbp_compact(x, _pos=None) -> str:
    """£12,500 -> '£13k'. Long money labels are what crowds a resized x-axis."""
    return f"£{x / 1000:,.0f}k" if abs(x) >= 1000 else f"£{x:,.0f}"


def _style_axis(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def plot_analysis(model: AstraDepreciationModel, df: pd.DataFrame,
                  cv_random: Dict, cv_age: Dict,
                  random_state: Optional[int] = None, save_path: Optional[str] = None):
    """Four panels: the fitted curve, residuals, categorical effects, and the numbers."""
    mpl.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                         "axes.labelcolor": INK_SOFT, "figure.facecolor": "#fcfcfb",
                         "axes.facecolor": "#fcfcfb"})
    # constrained_layout, not tight_layout: it reserves room for the colorbar and
    # the long categorical tick labels as the window is resized, instead of
    # solving the layout once for one particular figure size.
    fig, axes = plt.subplots(2, 2, figsize=(15, 10.5), constrained_layout=True)

    # ---- Panel 1: price vs age, shaded by mileage --------------------------
    ax = axes[0, 0]
    _style_axis(ax)
    ages = df[AGE_COL].to_numpy(dtype=float)
    prices = df[PRICE_COL].to_numpy(dtype=float)
    miles = df[MILEAGE_COL].to_numpy(dtype=float)

    norm = Normalize(vmin=miles.min(), vmax=miles.max())
    ax.scatter(ages, prices, c=miles, cmap=MILEAGE_CMAP, norm=norm,
               s=52, edgecolors="#fcfcfb", linewidths=1.2, zorder=3, label="Cars in sample")

    # Reference curve: a car doing 10,000 miles a year on average settings.
    grid = np.linspace(0, ages.max() + 2, 160)
    ref = pd.DataFrame({AGE_COL: grid, "mileage_10k": grid * 1.0})
    band = model.predict_with_uncertainty(ref, confidence=0.90, random_state=random_state)
    ax.fill_between(grid, band["lower"], band["upper"], color=ORANGE, alpha=0.16,
                    linewidth=0, zorder=1, label="90% prediction interval")
    ax.plot(grid, band["mean"], color=ORANGE, linewidth=2, zorder=4,
            label="Fitted curve (10k miles/yr)")
    ax.axvline(model.transition_age, color=INK_SOFT, linestyle=":", linewidth=1.2,
               alpha=0.8, zorder=2, label=f"Transition age ({model.transition_age:g} yrs)")

    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Asking price (£)")
    ax.set_title("Astra depreciation: price against age", fontsize=12, color=INK, pad=10)
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(_gbp_compact))
    ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=6))
    # Framed in the surface colour: on a small window the legend sits over the
    # curve, and unframed text on top of marks is unreadable.
    ax.legend(loc="upper right", fontsize=8, framealpha=0.93,
              facecolor="#fcfcfb", edgecolor="none", borderpad=0.6)
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=MILEAGE_CMAP), ax=ax, pad=0.02)
    cb.set_label("Mileage", color=INK_SOFT, fontsize=9)
    cb.ax.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter("{x:,.0f}"))
    cb.ax.tick_params(colors=INK_SOFT, labelsize=8)
    cb.outline.set_visible(False)

    # ---- Panel 2: residuals ------------------------------------------------
    ax = axes[0, 1]
    _style_axis(ax)
    fitted = model.predict(df)
    resid_pct = (prices - fitted) / fitted * 100
    ax.scatter(fitted, resid_pct, s=46, color=BLUE, alpha=0.75,
               edgecolors="#fcfcfb", linewidths=1.1, zorder=3)
    ax.axhline(0, color=RED, linestyle="--", linewidth=1.4, zorder=2)
    ax.set_xlabel("Fitted price (£)")
    ax.set_ylabel("Residual (% of fitted price)")
    # Short enough to survive a narrow window; the y-axis label carries the detail.
    ax.set_title("Residuals vs fitted price", fontsize=12, color=INK, pad=10)
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(_gbp_compact))
    ax.xaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=6, prune="both"))

    # ---- Panel 3: categorical effects --------------------------------------
    ax = axes[1, 0]
    _style_axis(ax)
    effects = [(f"{col.replace('_', ' ')}: {lvl}", (mult - 1) * 100)
               for col, levels in model.multipliers_.items()
               for lvl, mult in levels.items()]
    effects.sort(key=lambda t: t[1])
    top = effects[:6] + effects[-6:] if len(effects) > 12 else effects
    labels = [t[0] for t in top]
    values = [t[1] for t in top]
    bars = ax.barh(range(len(top)), values, height=0.66,
                   color=[BLUE if v >= 0 else ORANGE for v in values], zorder=3)
    ax.axvline(0, color=INK_SOFT, linewidth=1.1, zorder=4)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(labels, fontsize=max(6.5, min(8.5, fig.get_size_inches()[0] * 0.6)))
    ax.set_xlabel("Effect on price (%)")
    ax.set_title("What moves the price, age and mileage held fixed",
                 fontsize=11, color=INK, pad=10)
    # bar_label offsets in points, not data units, so the gap between bar and
    # label stays constant as the window resizes. Placing these by hand in data
    # coordinates put the longest negative label on top of its own tick label
    # on a small window, because data units per point grow as the axes shrink.
    span = max(max(values) - min(values), 1e-6)
    ax.set_xlim(min(min(values), 0) - 0.42 * span, max(max(values), 0) + 0.42 * span)
    ax.bar_label(bars, labels=[f"{v:+.1f}%" for v in values], padding=3,
                 fontsize=max(6.0, min(8.0, fig.get_size_inches()[0] * 0.55)),
                 color=INK_SOFT)
    ax.grid(axis="y", visible=False)

    # ---- Panel 4: the numbers ----------------------------------------------
    # Drawn as ONE multi-line string rather than a text call per line. Line
    # spacing is then a property of the font, so the block can never overlap
    # itself no matter how small the window gets — separate calls at fixed
    # offsets collide as soon as the figure is smaller than it was designed for.
    ax = axes[1, 1]
    ax.axis("off")
    p = model.params_
    # Every line kept under ~42 characters so the block does not run past the
    # panel edge on a small window.
    block = "\n".join([
        "FITTED CURVE",
        f"  V0 (when new)       £{p['V0']:,.0f}",
        f"  Early annual loss   {(1 - np.exp(-p['k1'])) * 100:4.1f}%  (to age {model.transition_age:g})",
        f"  Later annual loss   {(1 - np.exp(-p['k2'])) * 100:4.1f}%",
        f"  Per 10,000 miles    {(1 - np.exp(-p['b'])) * 100:4.1f}%",
        "",
        "IN-SAMPLE FIT",
        f"  R²    {model.metrics_['R2']:.3f}     MAE   £{model.metrics_['MAE']:,.0f}",
        f"  MAPE  {model.metrics_['MAPE']:.1f}%      RMSE  £{model.metrics_['RMSE']:,.0f}",
        "",
        "CROSS-VALIDATED",
        f"  Random holdout     {cv_random['MAPE_mean']:.1f}% ± {cv_random['MAPE_std']:.1f}"
        f"  (£{cv_random['MAE_mean']:,.0f})",
        f"  Older-car holdout  {cv_age['MAPE_mean']:.1f}% ± {cv_age['MAPE_std']:.1f}"
        f"  (£{cv_age['MAE_mean']:,.0f})",
        "",
        "HOW TO READ THIS",
        f"  {model.metrics_['n']} cars, {model.effective_n_params()} effective parameters.",
        "  Random holdout is the easier test;",
        "  the older-car holdout extrapolates,",
        "  and is the one to quote for forecasts.",
    ])
    # Scale on width as well as height: it is the width that clips this block.
    w_in, h_in = fig.get_size_inches()
    fs = float(np.clip(min(w_in * 0.62, h_in * 0.92), 6.0, 10.0))
    ax.text(0.0, 1.0, block, transform=ax.transAxes, va="top", ha="left",
            fontsize=fs, family="DejaVu Sans Mono", color=INK_SOFT,
            linespacing=1.5)

    fig.suptitle("Vauxhall Astra depreciation model", fontsize=15, color=INK,
                 x=0.01, ha="left")
    if save_path:
        fig.savefig(save_path, dpi=120, facecolor="#fcfcfb")
    else:
        plt.show()
    return fig


# ============================================================================
# 4. MAIN
# ============================================================================
if __name__ == "__main__":
    SEED = 42
    df = load_astra_csv(DATA_PATH)

    print("\nChoosing the transition age")
    best_t0, t0_table = select_transition_age(df)
    print(t0_table.to_string(index=False, float_format=lambda v: f"{v:.4g}"))
    print(f"  best transition age: {best_t0:g} years")

    print("\nFitting")
    model = AstraDepreciationModel(transition_age=best_t0).fit(df)
    p = model.params_
    print(f"  V0 = £{p['V0']:,.0f} | early {(1 - np.exp(-p['k1'])) * 100:.1f}%/yr"
          f" | later {(1 - np.exp(-p['k2'])) * 100:.1f}%/yr"
          f" | {(1 - np.exp(-p['b'])) * 100:.1f}% per 10k miles")
    print(f"  R² {model.metrics_['R2']:.3f} | MAPE {model.metrics_['MAPE']:.1f}%"
          f" | MAE £{model.metrics_['MAE']:,.0f}")

    print("\nWhat moves the price, holding age and mileage fixed")
    for col, levels in model.multipliers_.items():
        parts = ", ".join(f"{lvl} {(m - 1) * 100:+.1f}%"
                          for lvl, m in sorted(levels.items(), key=lambda kv: -kv[1]))
        print(f"  {col:<16} {parts}")

    print("\nCross-validation")
    cv_random = model.cross_validate(df, scheme="random", random_state=SEED)
    cv_age = model.cross_validate(df, scheme="age_blocked")
    for cv in (cv_random, cv_age):
        print(f"  {cv['scheme']:<12} {cv['folds']} folds | "
              f"MAPE {cv['MAPE_mean']:.1f}% ± {cv['MAPE_std']:.1f} | "
              f"MAE £{cv['MAE_mean']:,.0f}")

    print("\nExample valuations (90% prediction interval)")
    examples = [
        dict(age=3, mileage=30_000, trim="GS", fuel="Petrol", transmission="Manual",
             service_history="Full", seller_type="Franchise dealer", condition="Good"),
        dict(age=3, mileage=75_000, trim="Design", fuel="Diesel", transmission="Manual",
             service_history="Partial", seller_type="Private", condition="Fair"),
        dict(age=7, mileage=60_000, trim="SRi", fuel="Petrol", transmission="Manual",
             service_history="Full", seller_type="Independent dealer", condition="Good"),
    ]
    rows = []
    for e in examples:
        rows.append({AGE_COL: e["age"], MILEAGE_COL: e["mileage"],
                     "mileage_10k": e["mileage"] / 10_000.0,
                     **{k: v for k, v in e.items() if k not in ("age", "mileage")}})
    ex_df = pd.DataFrame(rows)
    band = model.predict_with_uncertainty(ex_df, confidence=0.90, random_state=SEED)
    header = f"  {'Age':>3} {'Mileage':>8} {'Spec':<46} {'Estimate':>10} {'90% range':>19}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for i, e in enumerate(examples):
        spec = f"{e['trim']}, {e['fuel']}, {e['service_history']} history, {e['seller_type']}"
        spec = spec if len(spec) <= 46 else spec[:43] + "..."
        rng_txt = f"£{band['lower'][i]:,.0f} - £{band['upper'][i]:,.0f}"
        print(f"  {e['age']:>3} {e['mileage']:>8,} {spec:<46} "
              f"£{band['mean'][i]:>9,.0f} {rng_txt:>19}")

    plot_analysis(model, df, cv_random, cv_age, random_state=SEED)
