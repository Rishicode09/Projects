# PV Defect Classifier → Power Loss

Grades physical defects in silicon solar cells from electroluminescence (EL)
images, then simulates what those defects cost in electrical power and annual
energy yield.

The point of the project is the coupling. A defect classifier on its own
answers "is this cell cracked?", which is not a question anyone can act on. The
question a plant operator has is "which modules should I replace this year?",
and answering that means turning a visual grade into kilowatt-hours. That
conversion is where the physics lives, and it is not a proportionality
constant — a single badly damaged cell in a 60-cell series string costs far
more power than its share of the module's area, and how much more depends on
irradiance, temperature and where the bypass diodes sit.

```
EL image ──► OpenCV preprocessing ──► ordinal CNN ──► severity ∈ [0,1] per cell
                                                            │
                                                            ▼
                                            severity → single-diode parameters
                                            (photocurrent, R_s, R_sh)
                                                            │
                                                            ▼
              TMY weather (pvlib) ──────► 60-cell mismatch + bypass diodes
                                            MPP solve (SciPy)
                                                            │
                                                            ▼
                                         ΔP at STC, ΔkWh/year, cost/year
```

---

## Two things to know before reading further

**1. ELPV contains no weather data.** It is a set of 2,624 EL cell crops
photographed in a dark lab with the module driven by an external current
source — there is no sun involved anywhere in it. All meteorological input in
this project comes from pvlib (a PVGIS typical meteorological year, or a
synthetic clear-sky year offline). The two datasets meet only at the end: ELPV
supplies the *condition of the cells*, the TMY supplies the *conditions they
operate under*.

**2. The severity → power mapping is not calibrated.** EL shows where charge
carriers recombine; it does not measure power. The coefficients in
`physics/degradation.py` are plausible values from the literature, not values
fitted to paired EL/flash-test data. Until you run
`degradation.fit_from_measurements` against real IV curves, the absolute watt
figures are **indicative, and the rankings are what you should trust**. The
Streamlit app has a sensitivity tab that exists specifically to show you how
wide that uncertainty is. This is the most valuable open experiment in the
project — see [Next steps](#next-steps).

---

## Install

```bash
pip install -e ".[dev]"     # or: pip install -r requirements.txt
python scripts/download_data.py
pytest -q
```

The ELPV **images** are CC BY-NC-SA 4.0 (non-commercial). Cite Buerhop-Lutz
et al. 2018, Deitsch et al. 2019 and Deitsch et al. 2021 in any publication —
BibTeX is in the [upstream repo](https://github.com/zae-bayern/elpv-dataset).

## Run

```bash
make train      # train the classifier          (python -m pvdefect.train)
make app        # Streamlit front end            (localhost:8501)
make test       # 30 tests, no dataset required
```

The Streamlit app runs **without a trained checkpoint** — the physics tabs fall
back to manual severity sliders, so you can explore the simulation on its own.

---

## The machine learning half

**Dataset.** 2,624 cells at 300×300, from 44 modules, each labelled with a
defect probability in `{0, ⅓, ⅔, 1}` — the fraction of expert annotators who
called it defective — plus wafer type. Distribution is `1508 / 295 / 106 / 715`,
so 57% of cells are defect-free and the two middle classes are rare.

**Ordinal, not categorical.** The four labels are ordered, and confusing
"none" with "severe" is a much worse error than confusing "moderate" with
"severe". Plain softmax cross-entropy treats both identically and gives no
monotonicity guarantee, so it can emit `P(severe) > P(moderate)` — which makes
the downstream physics behave erratically. We use **CORN**
(`models/ordinal.py`): K−1 binary heads where head *k* predicts
`P(y > k | y > k−1)`, so cumulative probabilities are monotone by construction.

The number handed to the physics model is the **expected severity** under the
predicted distribution, not the argmax. A cell the model reads as a coin flip
between "none" and "severe" should propagate as real uncertainty in the power
estimate, not as a confident middle answer.

**Preprocessing** (`preprocess/cell_prep.py`) produces a 3-channel stack:

| channel | content | why |
|---|---|---|
| 0 | illumination-flattened + CLAHE | what a human inspector looks at |
| 1 | busbar/finger-suppressed residual | crack candidates without the grid |
| 2 | black-hat crack response | dark linear features |

Per-cell normalisation matters more than it looks. EL brightness depends on
injection current and integration time, both set *per module*, so a network
trained on raw intensities learns each module's exposure rather than its
defects. There is a test (`test_preprocessing_is_invariant_to_exposure`)
pinning this property.

**Splitting is the biggest single lever on the reported number.** Published
ELPV accuracies vary by more than ten points, and most of that gap is leakage,
not modelling. Cells from one module share a wafer batch, an exposure, and
often the same crack running across neighbours. `labels.csv` does not publish
module IDs, but rows are ordered module by module, so `data/splits.py` cuts the
sequence into contiguous pseudo-modules (wafer-type transitions are guaranteed
cuts) and keeps each one wholly inside one subset.

This is an approximation, not a fix — a chunk boundary landing mid-module still
lets two cells of one real module straddle the split. `make train-leaky` runs
the random split for comparison; the gap between the two is worth reporting in
any writeup.

**Metrics** (`evaluate.py`). Accuracy is nearly useless here: predicting "no
defect" for everything scores 57%. The headline is **quadratic-weighted
kappa**, which penalises a none→severe error nine times as hard as a
none→mild one. Also tracked: balanced accuracy, macro F1, defect AUC (threshold-free),
and severe-class recall — missing a class-3 cell is the expensive failure.

**Explainability** (`explain.py`). Grad-CAM is not decoration here: the
pipeline turns a severity into a euro figure that decides whether a technician
climbs onto a roof. Before trusting that, you want to see the network
responding to the crack rather than to a serial-number label or a brightness
gradient.

## The physics half

Everything below is per-cell and vectorised over a 60-cell string.

**Single-diode model** (`physics/cell_model.py`). pvlib's parameter databases
are module-level, so parameters are pushed down to one cell:
`I_L, I_o` unchanged; `R_s, R_sh, a_ref` all divided by `N_s`. That last one
matters — `a_ref` in the De Soto convention already contains the cell count, and
forgetting it inflates every voltage by 60×.

**Three damage mechanisms** (`physics/degradation.py`), each visible in EL:

| mechanism | parameter | worst at |
|---|---|---|
| inactive area (region cut off from busbars) | scales `I_L` | all irradiances |
| series resistance (broken fingers) | raises `R_s` | **high** irradiance (I²R) |
| shunting (crack-induced shorts) | lowers `R_sh` | **low** irradiance |

Mechanisms 2 and 3 have *opposite* irradiance dependence, which is exactly why
this project runs an 8,760-hour simulation instead of scaling a single STC
number. There is a test pinning that opposition.

One subtlety worth flagging: De Soto scales `R_sh` inversely with irradiance,
so a naive multiplier on `R_sh` produces identical relative loss at 100 and
1000 W/m² — wrong, because a crack-induced shunt is a physical resistor that
does not know what the sun is doing. The retention factor is therefore
interpreted as the shunt you would *measure at STC*, converted to a fixed
parallel conductance, and added to the irradiance-scaled healthy one.

**Mismatch and bypass diodes** (`physics/mismatch.py`). Cells in series all
carry the same current, so the string is limited by its worst cell. Each
substring has a bypass diode that clamps it at ≈ −0.5 V, which is what stops one
dead cell from killing the module. The MPP solve is a coarse current sweep to
bracket the peak, then Brent refinement — the sweep is **not** optional, because
a mismatched string with bypass diodes has a genuinely multi-modal P-V curve
(one local peak per bypass configuration) and a bare optimiser returns the
wrong one.

Verified behaviour for a single damaged cell in a 3-diode, 60-cell module:

| one cell's inactive area | module power loss | substrings bypassed |
|---|---|---|
| 10% | 1.9% | 0 |
| 30% | 18.3% | 0 |
| 50% | 34.9% | 1 |
| 90% | 34.9% | 1 |

The loss saturates at exactly one third once the diode conducts. That plateau
is the model reproducing the physics, not an assumption written into it — and
30% area loss on one cell (0.5% of module area) costing 18% of module power is
the mismatch amplification that justifies per-cell classification.

**Weather** (`physics/weather.py`). PVGIS TMY where the network allows, with a
pvlib Ineichen clear-sky fallback that needs no network. The fallback
over-estimates annual yield because it has no clouds — use it for relative
comparisons, never for an absolute yield claim. The frame carries a
`synthetic` attribute so callers can tell which they got.

**Annual energy** (`physics/energy.py`). 8,760 hourly MPP solves per module is
minutes of compute — unusable interactively. But module power depends on the
weather only through two scalars (effective irradiance, cell temperature), so
we solve exactly on a 12×7 grid and interpolate the surface over the year.
~84 solves replace 8,760, and the interpolation error is far below the
degradation model's own uncertainty. Linear rather than cubic interpolation, on
purpose: the surface has a real kink where a bypass diode engages, and a spline
overshoots it.

Example output (clear-sky Erlangen year, generic 300 W module):

| scenario | STC loss | annual loss | yield |
|---|---|---|---|
| healthy | 0.00% | 0.00% | 550 kWh |
| 1 mild cell | 0.04% | 0.03% | 550 kWh |
| 1 severe cell | 14.00% | 11.00% | 490 kWh |
| 5 severe cells (1 substring) | 22.42% | 22.79% | 425 kWh |
| all cells mild | 1.96% | 1.81% | 540 kWh |

Note the mild rows. A hairline crack that has not yet isolated anything costs
essentially nothing — which matches the IEA-PVPS T13 finding that cracked cells
frequently show no measurable power loss. A model that mapped "crack visible"
straight to "power lost" would over-predict badly, and this one is built not to.

## Layout

```
src/pvdefect/
  config.py              YAML-backed configuration
  train.py               training loop, CLI entry point
  evaluate.py            ordinal + imbalance-aware metrics
  explain.py             Grad-CAM
  data/
    elpv.py              dataset index, class weights
    splits.py            pseudo-module leakage-aware splitting
    dataset.py           torch Dataset, EL-appropriate augmentation
  preprocess/cell_prep.py   OpenCV chain + inactive-area estimator
  models/
    ordinal.py           CORN loss and decoding
    classifier.py        backbone + ordinal head
  physics/
    cell_model.py        module → per-cell single-diode parameters
    degradation.py       severity → parameter damage  ← the calibration gap
    mismatch.py          series string, bypass diodes, MPP solve
    weather.py           PVGIS TMY / clear-sky fallback, POA transposition
    energy.py            interpolated annual energy simulation
  app/streamlit_app.py   three-tab front end
tests/                   30 tests; physics tests assert properties, not constants
```

## Next steps

Roughly in order of research value:

1. **Calibrate the degradation model.** Pair EL images with flash-test IV
   curves for 30–50 modules and fit `fit_from_measurements`. This is what turns
   the pipeline from a ranking tool into a measurement tool, and everything
   else is downstream of it.
2. **Get real module IDs** for ELPV (or image your own modules) so the split is
   genuinely module-wise and the reported metrics are defensible.
3. **Cross-validate.** `splits.cross_validation_folds` is written and unused.
   With ~44 modules, single-split numbers carry several points of noise; do not
   claim one architecture beats another without error bars.
4. **Segment rather than classify.** Inactive *area* is what the physics
   actually wants, and a segmentation model would estimate it directly instead
   of going through a 4-level proxy. The current dark-area estimator in
   `cell_prep.py` is a placeholder for this.
5. **Model reverse-bias breakdown** (Bishop's term) if you care about hot-spot
   risk. Deliberately omitted here: it adds three uncalibrated parameters and
   changes no MPP result, since the bypass diode clamps first.
6. **String- and plant-level aggregation.** Modules are series-connected into
   strings, and the same mismatch logic applies one level up.

## References

- Buerhop-Lutz et al. (2018), *A Benchmark for Visual Identification of
  Defective Solar Cells in EL Imagery*, EU PVSEC.
- Deitsch et al. (2019), *Automatic classification of defective PV module cells
  in electroluminescence images*, Solar Energy 185, 455–468.
- Deitsch et al. (2021), *Segmentation of PV module cells in uncalibrated EL
  images*, Machine Vision and Applications 32(4).
- Köntges et al. (2014), *Review of Failures of PV Modules*, IEA-PVPS
  T13-01:2014 — the source for "cracks do not necessarily cost power".
- Shi, Cao & Raschka (2021), *Deep Neural Networks for Rank-Consistent Ordinal
  Regression* (CORN).
- De Soto, Klein & Beckman (2006), *Improvement and validation of a model for
  photovoltaic array performance*, Solar Energy 80(1).
