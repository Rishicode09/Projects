# Car Depreciation Model

Estimates what a used **Vauxhall Astra** or **VW Golf** is worth from its age and
mileage, puts an honest uncertainty range around the answer, and compares how the
two cars hold value.

```
price = V0 × exp(−rate(age)) × exp(−b × mileage) × (trim, fuel, history, … multipliers)
```

Value falls by a **percentage** each year rather than a fixed amount, which is
what `exp(−rate × age)` encodes. The rate is steeper early and flatter later,
switching at a transition age that is **chosen from the data** rather than
assumed.

## Results on the bundled sample

| | |
|---|---|
| Price when new (V0) | £28,321 |
| Early annual loss | 17.0% (to age 4.5) |
| Later annual loss | 9.9% |
| Per 10,000 miles | 3.9% |
| In-sample | R² 0.991 · MAPE 4.4% · MAE £462 |
| Cross-validated, random holdout | MAPE 5.9% ± 0.9 |
| Cross-validated, older-car holdout | MAPE 8.7% ± 2.0 |

The **older-car holdout** trains on younger cars and predicts older ones. It is
the harder test and the one to quote when talking about forecasting.

Holding age and mileage fixed, the largest price effects are a private sale
(−10.3%), Fair condition (−7.4%), no service history (−7.2%), and Ultimate trim
(+6.5%).

## Astra vs Golf

`python compare_astra_golf.py` fits both cars through the identical model,
cleaning and cross-validation, so the comparison is between two curves rather
than two analyses.

| | Astra | Golf |
|---|---|---|
| Price when new | £28,321 | £30,289 |
| Transition age | 4.5 yrs | 6.0 yrs |
| Early annual loss | 17.0% | 13.6% |
| Later annual loss | 9.9% | 9.3% |
| Retained at 3 years | 52.2% | **61.4%** |
| Retained at 5 years | 41.3% | **47.2%** |
| Retained at 10 years | 24.4% | 26.0% |

The fitted curves land within ~2 points of the published UK figures the samples
were calibrated on (Golf at 3 years: fitted 61.4% against a published ~61%).

Two findings worth stating carefully:

- **The Golf's advantage is front-loaded.** It is 9 points ahead at three years,
  6 at five, and under 2 by ten. Badge premium is an early-life effect that
  washes out as both cars become old cars.
- **Better retention is not the same as losing less money.** Because the Golf
  costs about £2,000 more new, by year seven it has lost *more in pounds* than
  the Astra (£22k vs £21k) despite retaining a higher percentage throughout.
  Which number matters depends on whether you are pricing a trade-in or
  budgeting a purchase.

## About the data

`data/vauxhall_astra_market_sample.csv` and `data/vw_golf_market_sample.csv` —
100 cars each, ages 0–10, plus a combined CSV and a comparison workbook.

**These are not real listings.** No row is a real car or a real advert. The
prices were generated from a documented model calibrated against published
depreciation figures (2026 list prices, ~50% of value retained at three years,
~42% at five, flattening after year seven). Every anchor, source and generating
parameter is recorded on the **Calibration** tab of the `.xlsx`.

It exists to give age and mileage that vary *independently* (correlation 0.73).
An earlier synthetic set had mileage ≈ 1.1 × age (correlation 0.999), which made
the age and mileage effects impossible to tell apart — the mileage coefficient
pinned to its bound in 85% of runs. The model warns when that happens.

Both cars share **identical** mileage, trim, fuel, history, seller and condition
multipliers. Only the list prices and retention curves differ, so any fitted
difference other than the age curve is noise rather than something rigged in.

**Replace this with real data before showing the project to anyone.** Kaggle's
"100,000 UK Used Car Data set" contains real scraped `vauxhall.csv` *and*
`vw.csv` — the same comparison, done for real. The loader already validates for
the mess real exports contain.

## Running it

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python car_depreciation_model.py
```

Prints the fitted parameters, the price effects, cross-validation and three
example valuations, then opens a four-panel chart. **The script waits at the
chart until you close the window.**

In VS Code: open this folder, then `Ctrl+Shift+P` → *Python: Select Interpreter*
→ pick the `.venv` one. Skipping that step causes `ModuleNotFoundError` even
though the packages are installed.

## Files

| File | What it is |
|---|---|
| `car_depreciation_model.py` | The model, validation and charts. Run this first. |
| `compare_astra_golf.py` | Fits both cars and compares them. |
| `build_samples.py` | Regenerates both datasets. Seeded, so they reproduce exactly. |
| `data/vauxhall_astra_market_sample.csv` | Astra sample, 100 cars. |
| `data/vw_golf_market_sample.csv` | Golf sample, 100 cars. |
| `data/combined_market_sample.csv` | Both, with a `model` column. |
| `data/astra_vs_golf_market_sample.xlsx` | Both, plus Read Me / Comparison / Calibration tabs. |

## Using it in your own code

```python
from car_depreciation_model import load_astra_csv, AstraDepreciationModel

df = load_astra_csv()
model = AstraDepreciationModel(transition_age=4.5).fit(df)

model.predict_car(age=3, mileage=30_000, trim="GS", fuel="Petrol",
                  service_history="Full", seller_type="Franchise dealer")
# -> 15362.0
```

## Known limitations

- The bundled data is synthetic. Nothing here describes the real market.
- Held-out coverage of the nominal 90% interval measures **86.2%**, so the
  intervals are slightly too narrow on unseen cars. Nesting the bootstrap
  inside the cross-validation loop would fix it.
- No baseline comparison yet. Fitting a linear regression on log(price) and a
  gradient-boosting model alongside this one would show whether the parametric
  curve earns its place, and is the most valuable next addition.
