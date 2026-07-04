"""
STEP 1 — data_generator.py: create realistic, *dirty* energy data.

WHY GENERATE DATA INSTEAD OF DOWNLOADING IT?
--------------------------------------------
1. The project runs anywhere with zero downloads.
2. You control the "ground truth", so you can check whether your
   cleaning and modelling actually recover the patterns you put in.
3. Interview gold: "I injected known faults into synthetic data to
   validate my cleaning pipeline" is a strong answer.

THE PHYSICS WE FAKE (this is your EE knowledge showing up in code):
- A daily cycle: people use more power in the morning and evening.
- A yearly cycle: heating in winter, cooling in summer.
- Weekends look different from weekdays.
- Random noise, because real sensors are noisy.
- Faults: missing readings (sensor offline) and absurd spikes
  (sensor glitches). We add these ON PURPOSE so cleaning.py has
  a real job to do.
"""

import numpy as np
import pandas as pd

# A "seed" makes randomness repeatable: same seed -> same "random" data.
# Without it, every run produces different numbers and your results
# (and your tests!) would be impossible to reproduce.
# 🔧 TRY THIS: change 42 to any other number, rerun `generate`, and
#    watch the summary statistics shift slightly. Then remove the seed
#    entirely and see results change on EVERY run.
DEFAULT_SEED = 42


def generate_energy_data(
    days: int = 365,
    seed: int = DEFAULT_SEED,
    missing_fraction: float = 0.02,
    spike_fraction: float = 0.005,
) -> pd.DataFrame:
    """Return one row per HOUR: timestamp, temperature_c, consumption_kwh.

    Parameters are the knobs of this function — the caller decides how
    much data and how dirty it is, without editing this file.

    🔧 TRY THIS: call this with missing_fraction=0.30 (30% missing!)
       and see how far downstream the damage travels — does the model
       in model.py get worse? By how much?
    """
    rng = np.random.default_rng(seed)  # our source of randomness

    # One timestamp per hour. periods = days * 24 because 24 hours/day.
    timestamps = pd.date_range("2025-01-01", periods=days * 24, freq="h")

    # --- Temperature (°C): a yearly sine wave + daily wiggle + noise ---
    # np.sin works in radians; 2*pi = one full cycle. We stretch one
    # cycle over 365 days for seasons, and one over 24 h for day/night.
    hour_of_year = np.arange(len(timestamps))
    yearly = -10 * np.cos(2 * np.pi * hour_of_year / (365 * 24))  # cold Jan, warm Jul
    daily = 4 * np.sin(2 * np.pi * (hour_of_year % 24 - 6) / 24)  # warmest mid-afternoon
    temperature = 12 + yearly + daily + rng.normal(0, 1.5, len(timestamps))

    # --- Consumption (kWh) built from interpretable pieces ---
    base = 0.4  # fridge, router, standby — always on

    # Morning (7-9) and evening (18-22) peaks, as boolean masks.
    # A boolean array (True/False) multiplied by a number becomes 0/1 * number.
    hours = timestamps.hour.to_numpy()
    morning_peak = ((hours >= 7) & (hours <= 9)) * 0.8
    evening_peak = ((hours >= 18) & (hours <= 22)) * 1.2

    # Weekends: people are home, usage up 15%.
    # dayofweek: Monday=0 ... Sunday=6, so >=5 means Sat/Sun.
    weekend = (timestamps.dayofweek.to_numpy() >= 5) * 0.15

    # Heating/cooling: the further temperature is from a comfy 18°C,
    # the more energy we burn. abs() makes both directions cost energy.
    hvac = 0.05 * np.abs(temperature - 18)

    noise = rng.normal(0, 0.15, len(timestamps))  # sensor + behaviour noise
    consumption = base + morning_peak + evening_peak + weekend + hvac + noise
    consumption = np.clip(consumption, 0.05, None)  # power can't be negative

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "temperature_c": np.round(temperature, 2),
            "consumption_kwh": np.round(consumption, 3),
        }
    )

    # --- Now BREAK the data on purpose ---
    # rng.choice picks random row positions without repeats.
    n = len(df)

    missing_idx = rng.choice(n, size=int(n * missing_fraction), replace=False)
    df.loc[missing_idx, "consumption_kwh"] = np.nan  # NaN = "no reading"

    spike_idx = rng.choice(n, size=int(n * spike_fraction), replace=False)
    # A glitching sensor reports 10-30x the true value.
    df.loc[spike_idx, "consumption_kwh"] *= rng.uniform(10, 30, size=len(spike_idx))

    return df


def save_data(df: pd.DataFrame, path: str = "data/energy_raw.csv") -> None:
    """Write the DataFrame to CSV. index=False stops pandas from adding
    a useless unnamed first column (a classic beginner gotcha)."""
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)  # create data/ if absent
    df.to_csv(path, index=False)


# 🔧 EXERCISES FOR YOU (do them in order, rerun the pipeline after each):
# 1. EASY   — Make evening_peak 2.0 instead of 1.2. Which plot/statistic
#             downstream changes the most?
# 2. MEDIUM — Add a `solar_panels: bool` parameter. If True, SUBTRACT
#             generation during daylight hours (roughly 9-17). Careful:
#             consumption still must not go below 0.05.
# 3. HARD   — Add a second fault type: "stuck sensor" that repeats the
#             same value for 24 h straight. Then check: does cleaning.py
#             catch it? (Spoiler: it won't. That's exercise 3 in
#             cleaning.py.)
