"""
STEP 3 — analysis.py: ask the data questions (the Data Analyst hat).

A model tells you WHAT will happen; analysis tells you WHY. In a job
you'll present these numbers to non-technical people, so every function
here answers a question a human would actually ask:

  - "What does a typical day look like?"        -> hourly_profile
  - "Are weekends really different?"            -> weekday_weekend_comparison
  - "Does weather drive our usage?"             -> temperature_correlation
  - "Which months cost us the most?"            -> monthly_totals
"""

import pandas as pd


def summary_stats(df: pd.DataFrame) -> pd.Series:
    """The 30-second health check: mean, std, min, max, quartiles.

    ALWAYS run this first. If max is 40 kWh in a household dataset,
    your cleaning failed and everything downstream is garbage.
    """
    return df["consumption_kwh"].describe()


def hourly_profile(df: pd.DataFrame) -> pd.Series:
    """Average consumption for each hour of the day (24 numbers).

    groupby is THE core data-analysis operation. Read it aloud:
    "group the rows by hour, then take the mean of each group."
    SQL equivalent: SELECT hour, AVG(kwh) ... GROUP BY hour —
    interviewers love asking you to translate between the two.

    🔧 TRY THIS: swap .mean() for .max(). The evening peak gets more
       extreme — why? (Because mean averages calm and busy days
       together; max only remembers the busiest one.)
    """
    return df.groupby(df["timestamp"].dt.hour)["consumption_kwh"].mean()


def weekday_weekend_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Mean and std of usage, weekdays vs weekends.

    We report std TOO because two means can be equal while one group
    swings wildly — a mean without a spread is half a story.
    """
    is_weekend = df["timestamp"].dt.dayofweek >= 5  # Sat=5, Sun=6
    grouped = df.groupby(is_weekend)["consumption_kwh"].agg(["mean", "std"])
    grouped.index = ["weekday", "weekend"]  # rename False/True to words
    return grouped


def temperature_correlation(df: pd.DataFrame) -> float:
    """Pearson correlation between temperature and consumption, -1..+1.

    EXPECT ROUGHLY -0.46, and here is the trap hiding inside it:
    we built consumption from abs(temp - 18) — a V shape, not a line.
    Pearson only measures STRAIGHT-LINE relationships, so it reports
    "colder -> more energy" (negative) because winters here are more
    extreme than summers, and it completely misses that HOT days also
    increase usage. One number, half the story.

    🔧 TRY THIS: compute df["temperature_c"].sub(18).abs().corr(
       df["consumption_kwh"]) — correlating the DISTANCE from 18°C
       instead. The sign flips to about +0.49 because now summer
       cooling counts too. You just did feature engineering, the same
       trick model.py uses. Then ask: why is it still only ~0.5 and
       not ~0.9? (Hint: what besides weather drives the daily peaks?)
    """
    return float(df["temperature_c"].corr(df["consumption_kwh"]))


def monthly_totals(df: pd.DataFrame) -> pd.Series:
    """Total kWh per month — what the electricity bill actually shows."""
    return df.groupby(df["timestamp"].dt.month)["consumption_kwh"].sum().round(1)


def plot_overview(df: pd.DataFrame, path: str = "data/overview.png") -> str:
    """Save a 2-panel figure: daily profile + monthly totals.

    matplotlib is imported INSIDE the function so the rest of the
    package works even on machines without matplotlib installed.
    """
    import matplotlib

    matplotlib.use("Agg")  # "Agg" = draw to file, no screen needed (servers/CI)
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    hourly_profile(df).plot(ax=ax1, marker="o", color="#1f77b4")
    ax1.set_title("Average consumption by hour of day")
    ax1.set_xlabel("Hour")
    ax1.set_ylabel("kWh")
    ax1.grid(True, alpha=0.3)  # alpha = transparency, keeps grid subtle

    monthly_totals(df).plot(kind="bar", ax=ax2, color="#ff7f0e")
    ax2.set_title("Total consumption by month")
    ax2.set_xlabel("Month")
    ax2.set_ylabel("kWh")

    fig.tight_layout()  # stops labels overlapping
    fig.savefig(path, dpi=120)
    plt.close(fig)  # free memory — matters when generating many plots
    return path


# 🔧 EXERCISES FOR YOU:
# 1. EASY   — Add day_of_week_profile(df): mean consumption per weekday
#             (Mon..Sun). One groupby line + nice index names.
# 2. MEDIUM — Add find_peak_hours(df, top_n=5) returning the 5 timestamps
#             with highest consumption. Hint: .nlargest(). Then answer:
#             are they all in winter evenings? Why would a utility
#             company pay you to know this?
# 3. HARD   — Add a third panel to plot_overview: a SCATTER plot of
#             temperature vs consumption. You should literally SEE the
#             V shape that fooled the Pearson correlation.
