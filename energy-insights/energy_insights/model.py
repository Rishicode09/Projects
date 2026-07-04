"""
STEP 4 — model.py: forecast the next hour's consumption (the AI hat).

WHAT WE PREDICT: consumption for hour t, using things known BEFORE t.

THE THREE IDEAS THAT MATTER HERE (all common interview questions):

1. FEATURE ENGINEERING beats fancy models. A linear model with good
   features usually beats a deep net with raw ones. We hand the model
   the patterns we know exist: hour of day, weekday, distance of
   temperature from 18°C, and what happened 1h/24h ago.

2. TIME-BASED SPLIT, never random split. If you shuffle time series
   data, the model trains on Tuesday 3pm and is "tested" on Tuesday
   2pm — it has effectively seen the future. Scores look amazing and
   are lies. We train on the first 80% of the year, test on the last 20%.

3. ALWAYS COMPARE AGAINST A DUMB BASELINE. Ours: "predict that this
   hour equals the same hour yesterday." If your ML can't beat that,
   you have built nothing. Most real projects die at this step —
   knowing to check is what makes you senior.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

TARGET = "consumption_kwh"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Turn raw columns into things a model can learn from."""
    out = df.copy()
    ts = out["timestamp"]

    out["hour"] = ts.dt.hour              # 0-23: captures the daily cycle
    out["dayofweek"] = ts.dt.dayofweek    # 0-6: captures weekends
    out["month"] = ts.dt.month            # 1-12: captures seasons

    # The V-shape fix from analysis.py: distance from comfy 18°C.
    # This one engineered column is why LinearRegression works at all here.
    out["temp_deviation"] = (out["temperature_c"] - 18).abs()

    # LAG features: what happened 1 hour ago and 24 hours ago.
    # .shift(1) moves the column down one row, so row t sees value t-1.
    # For forecasting, lags are usually the strongest features you have.
    out["lag_1h"] = out[TARGET].shift(1)
    out["lag_24h"] = out[TARGET].shift(24)

    # The first 24 rows now contain NaN lags (no "yesterday" exists yet).
    # Models crash on NaN, so we drop those rows.
    return out.dropna().reset_index(drop=True)


FEATURES = ["hour", "dayofweek", "month", "temp_deviation", "lag_1h", "lag_24h"]


def time_split(df: pd.DataFrame, train_fraction: float = 0.8):
    """First 80% of rows -> train, last 20% -> test. NO SHUFFLING.

    🔧 TRY THIS: replace this function's body with sklearn's
       train_test_split(df, test_size=0.2, shuffle=True) and rerun.
       R² will jump suspiciously close to 1.0. Now you have SEEN data
       leakage instead of just reading about it — describe in one
       sentence why the shuffled score is a lie.
    """
    cut = int(len(df) * train_fraction)
    return df.iloc[:cut], df.iloc[cut:]  # iloc = select rows by position


def evaluate(y_true, y_pred, name: str) -> dict:
    """Two metrics, chosen on purpose:

    MAE  = mean absolute error, in kWh. "On average we're off by X kWh."
           Your manager understands this one.
    R²   = fraction of the variation we explain (1.0 = perfect,
           0.0 = no better than always guessing the mean,
           negative = actively worse than guessing the mean!).
    """
    return {
        "model": name,
        "mae_kwh": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def train_and_compare(df: pd.DataFrame) -> pd.DataFrame:
    """Train baseline + 2 models on identical splits; return a scoreboard."""
    data = build_features(df)
    train, test = time_split(data)

    X_train, y_train = train[FEATURES], train[TARGET]
    X_test, y_test = test[FEATURES], test[TARGET]

    results = []

    # --- Baseline: "same hour yesterday" (no learning at all) ---
    results.append(evaluate(y_test, test["lag_24h"], "baseline_yesterday"))

    # --- Model 1: LinearRegression = weighted sum of features + intercept.
    # Interpretable: you can read the learned coefficients like a recipe.
    lin = LinearRegression()
    lin.fit(X_train, y_train)              # .fit() = learn from examples
    results.append(evaluate(y_test, lin.predict(X_test), "linear_regression"))

    # --- Model 2: RandomForest = many decision trees, each trained on a
    # random sample of rows/features, predictions averaged. Handles
    # non-linear patterns without us engineering them, but is slower
    # and harder to explain. That trade-off IS the interview answer.
    # 🔧 TRY THIS: n_estimators is the number of trees. Try 5, 50, 300.
    #    Watch accuracy AND runtime. Where do returns diminish?
    forest = RandomForestRegressor(n_estimators=50, random_state=0, n_jobs=-1)
    forest.fit(X_train, y_train)
    results.append(evaluate(y_test, forest.predict(X_test), "random_forest"))

    # Bonus interview ammo: which features did the forest rely on?
    importances = pd.Series(forest.feature_importances_, index=FEATURES)
    print("\nRandomForest feature importances (sum to 1):")
    print(importances.sort_values(ascending=False).round(3).to_string())

    return pd.DataFrame(results)


# 🔧 EXERCISES FOR YOU:
# 1. EASY   — Remove "lag_1h" from FEATURES and rerun. How much does MAE
#             worsen? That delta is the "value" of one feature.
# 2. MEDIUM — Add a lag_168h (one week ago) feature. Does it help more
#             on weekends than weekdays? Design a check that answers this
#             (hint: compute MAE separately on weekend test rows).
# 3. HARD   — Our lag features assume rows are exactly 1 hour apart, but
#             cleaning.py DROPS rows (gaps > 6h). So shift(1) sometimes
#             grabs a value from >1 hour ago — a subtle bug shipped in
#             this very file. Quantify how often it happens
#             (hint: df["timestamp"].diff() != "1h"), then fix it
#             (hint: set_index("timestamp").asfreq("h") or merge on
#             timestamp-1h). This is a REAL production-grade bug hunt.
