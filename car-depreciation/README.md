# Car Depreciation Model

Estimates what a used Vauxhall Astra is worth from its age and mileage, and puts
an honest uncertainty range around the answer.

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

## About the data

`data/vauxhall_astra_market_sample.csv` — 100 cars, ages 0–10.

**These are not real listings.** No row is a real car or a real advert. The
prices were generated from a documented model calibrated against published
depreciation figures (2026 list prices, ~50% of value retained at three years,
~42% at five, flattening after year seven). Every anchor, source and generating
parameter is recorded on the **Calibration** tab of the `.xlsx`.

It exists to give age and mileage that vary *independently* (correlation 0.73).
An earlier synthetic set had mileage ≈ 1.1 × age (correlation 0.999), which made
the age and mileage effects impossible to tell apart — the mileage coefficient
pinned to its bound in 85% of runs. The model warns when that happens.

**Replace this with real data before showing the project to anyone.** Kaggle's
"100,000 UK Used Car Data set" contains a real scraped `vauxhall.csv`. The
loader already validates for the mess real exports contain.

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
| `car_depreciation_model.py` | The model, validation and charts. Run this. |
| `build_astra_sample.py` | Regenerates the sample dataset. Seeded, so it reproduces exactly. |
| `data/*.csv` | The dataset the model reads. |
| `data/*.xlsx` | Same data, plus Read Me / Market Summary / Calibration tabs. |

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
