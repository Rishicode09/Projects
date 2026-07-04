"""
STEP 2 — cleaning.py: turn dirty sensor data into trustworthy data.

THE MOST IMPORTANT FILE IN THE PROJECT.
Interviewers care more about this than about your model, because in
real jobs ~70% of the work is exactly this. The two faults we planted
in data_generator.py are the two most common real-world ones:

  1. MISSING VALUES (NaN)  -> we fill them by interpolation
  2. OUTLIERS (spikes)     -> we detect them with the IQR rule, then
                              treat them as missing and fill them too

DESIGN RULE used throughout: functions take a DataFrame and RETURN A
NEW ONE instead of modifying the input ("no side effects"). This makes
code predictable and testable — ask me why in an interview and say:
"so the caller's data is never mutated behind their back."
"""

import numpy as np
import pandas as pd


def load_data(path: str) -> pd.DataFrame:
    """Read the CSV and parse timestamps.

    parse_dates matters: without it, 'timestamp' is just text (strings),
    and time-based operations (.dt.hour, resampling) won't work.
    🔧 TRY THIS: remove parse_dates, run the pipeline, and read the
       error you get. Learning to read tracebacks IS the skill.
    """
    return pd.read_csv(path, parse_dates=["timestamp"])


def missing_report(df: pd.DataFrame) -> pd.Series:
    """How many NaNs per column? Always LOOK before you fix.

    .isna() gives a True/False table; .sum() counts the Trues
    (True behaves as 1 in arithmetic — a Python fact worth knowing).
    """
    return df.isna().sum()


def detect_outliers_iqr(series: pd.Series, k: float = 3.0) -> pd.Series:
    """Return a True/False mask marking outliers, using the IQR rule.

    IQR = Interquartile Range = Q3 - Q1 = the spread of the middle 50%
    of the data. Anything further than k*IQR outside that middle band
    is suspicious. This is the same logic as the whiskers on a box plot.

    WHY NOT just use mean ± 3 standard deviations? Because outliers
    inflate the mean and std themselves — the fault would hide its own
    evidence. Quartiles barely move when a few values explode. This
    exact question comes up in data interviews.

    🔧 TRY THIS: change k from 3.0 to 1.0 and rerun. You'll see FAR more
       "outliers" flagged — including real evening peaks. That's a
       FALSE POSITIVE problem. Now try k=10 — spikes survive. That's a
       FALSE NEGATIVE problem. Picking k is a judgement call; defend it.
    """
    q1 = series.quantile(0.25)  # 25% of values are below this
    q3 = series.quantile(0.75)  # 75% of values are below this
    iqr = q3 - q1
    lower = q1 - k * iqr
    upper = q3 + k * iqr
    return (series < lower) | (series > upper)


def clean_data(df: pd.DataFrame, iqr_k: float = 3.0) -> tuple[pd.DataFrame, dict]:
    """Full cleaning pipeline. Returns (clean_df, report).

    Returning a report dict alongside the data is deliberate: a pipeline
    that silently changes 500 values is a liability. Always leave an
    audit trail.
    """
    out = df.copy()  # never mutate the caller's data (see file docstring)
    report: dict = {}

    report["rows_in"] = len(out)
    report["missing_before"] = int(out["consumption_kwh"].isna().sum())

    # --- Fix outliers FIRST, then fill gaps. ---
    # Order matters! If we interpolated first, a 20x spike next to a gap
    # would leak its madness into the filled values.
    # 🔧 TRY THIS: swap the two blocks below and compare report values —
    #    you will see interpolation "smearing" spikes into the gaps.
    spikes = detect_outliers_iqr(out["consumption_kwh"], k=iqr_k)
    report["outliers_flagged"] = int(spikes.sum())
    out.loc[spikes, "consumption_kwh"] = np.nan  # demote spikes to "unknown"

    # Interpolation draws a straight line between the known neighbours
    # of a gap. Good for smooth signals like hourly energy; terrible for
    # e.g. categorical data. limit=6 means: never bridge a gap longer
    # than 6 hours — beyond that we'd be inventing data.
    out["consumption_kwh"] = out["consumption_kwh"].interpolate(
        method="linear", limit=6
    )

    # Any NaNs that survived (gaps > 6h, or at the very edges) — drop.
    remaining = int(out["consumption_kwh"].isna().sum())
    report["rows_dropped"] = remaining
    out = out.dropna(subset=["consumption_kwh"]).reset_index(drop=True)

    report["rows_out"] = len(out)
    return out, report


# 🔧 EXERCISES FOR YOU:
# 1. EASY   — In clean_data, print the report with print(report) and run
#             the pipeline. Do the numbers match the fractions you set
#             in data_generator.py? (0.02 missing of 8760 rows ≈ 175.)
# 2. MEDIUM — interpolate(method="linear") vs .ffill() (copy last known
#             value forward). Implement both, compare which one recovers
#             the true signal better. How would you MEASURE "better"?
#             Hint: generate data with seed 42, keep a copy BEFORE
#             adding faults, and compare fills against that truth.
# 3. HARD   — Write detect_stuck_sensor(series, window=24): flag runs
#             where the value doesn't change for `window` consecutive
#             hours. Hint: series.diff() == 0, then .rolling(window).
#             Add it to clean_data and to the report.
