# energy-insights ⚡

Household electricity analysis and next-hour forecasting — built as a
*learning* project with the structure of a *professional* one: a proper
Python package, a CLI, tests, and honest model evaluation against a
baseline.

> **Why synthetic data?** The generator injects *known* faults (missing
> readings, sensor spikes), so the cleaning pipeline can be validated
> against ground truth — something you can't do with a downloaded CSV.

## Quick start

```bash
pip install -e ".[dev]"            # install package + pytest (editable mode)

python -m energy_insights generate # 1. create data/energy_raw.csv (1 year, hourly)
python -m energy_insights clean    # 2. fix outliers + gaps -> data/energy_clean.csv
python -m energy_insights analyze  # 3. stats + data/overview.png
python -m energy_insights train    # 4. baseline vs LinearRegression vs RandomForest

python -m pytest                   # run the test suite
```

## What's inside

| File | Role | Key ideas |
|---|---|---|
| `energy_insights/data_generator.py` | create realistic dirty data | seeded randomness, sine-wave seasonality, injected faults |
| `energy_insights/cleaning.py` | make data trustworthy | IQR outlier detection, interpolation with limits, audit report |
| `energy_insights/analysis.py` | answer human questions | groupby profiles, the correlation-≈-0 trap, plotting |
| `energy_insights/model.py` | forecast next hour | feature engineering, **time-based split**, baseline comparison |
| `energy_insights/__main__.py` | command-line interface | argparse subcommands (git-style) |
| `tests/` | tripwires for future changes | property-based assertions, not exact-number assertions |

## Results (seed 42, 1 year of data)

The scoreboard from `train` — the point is not the numbers, it's that
every model is judged against the "same hour yesterday" baseline:

| model | MAE (kWh) | R² |
|---|---|---|
| baseline_yesterday | 0.209 | 0.803 |
| linear_regression | 0.197 | 0.825 |
| random_forest | 0.136 | 0.914 |

Note how *good* the dumb baseline already is (R² 0.80) — daily routine
is highly repetitive. Linear regression barely beats it; the forest
earns its keep. This is the honest shape of most real ML projects.

## Design decisions (a.k.a. interview answers)

- **Time-based split, not random** — shuffling time series leaks the
  future into training and inflates scores.
- **Outliers fixed *before* gap interpolation** — otherwise spikes
  smear into the filled values.
- **IQR rule, not mean±3σ** — outliers corrupt the mean and σ used to
  detect them; quartiles are robust.
- **Functions return new DataFrames** — no hidden mutation of caller
  data; this is enforced by a test.
- **Report dict from cleaning** — a pipeline that silently changes 500
  values is a liability; leave an audit trail.

## Learning path

This repo is meant to be *modified*, not admired. Every module ends
with 🔧 exercises (easy → hard). Start with `EXERCISES.md`.
