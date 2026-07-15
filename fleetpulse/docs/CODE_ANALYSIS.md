# FleetPulse — Code Analysis

A module-by-module walkthrough of the codebase: what each part is responsible for, the
design decisions behind it, and the trade-offs those decisions accept. Written for a
reviewer who wants to judge the engineering, not just run the demo.

## Contents

1. [System overview and data flow](#1-system-overview-and-data-flow)
2. [Module analysis](#2-module-analysis)
3. [Cross-cutting design decisions](#3-cross-cutting-design-decisions)
4. [Testing strategy](#4-testing-strategy)
5. [Failure modes considered](#5-failure-modes-considered)
6. [Deliberate trade-offs](#6-deliberate-trade-offs)

---

## 1. System overview and data flow

FleetPulse has four layers with one-way dependencies — serving depends on models, models
depend on features, features depend on config. Nothing depends back on the API:

```text
config.py  ──►  data/  ──►  features/  ──►  models/  ──►  api/
   ▲                                          │
   └────────── monitoring/ ◄──────────────────┘
```

**Training-time flow:** `generate_fleet_telemetry` produces one row per vehicle per day →
`build_features` adds trailing rolling-window features → `train_model` splits by vehicle,
fits two candidates, selects by PR-AUC, and persists a pipeline + JSON model card →
`AnomalyDetector.fit` learns "normal" from healthy rows only.

**Serving-time flow:** a `VehicleHistory` request (≥ 8 days of readings) → Pydantic
validation → `PredictionService` converts it to a DataFrame and calls **the same
`build_features` function used in training** → the persisted pipeline scores the latest
day → response includes probability, threshold, and risk band.

That shared feature function is the single most important line of architecture in the
project: train/serve skew (training features computed one way, serving features another)
is the classic way ML systems rot, and here it is impossible by construction.

## 2. Module analysis

### `config.py` — the single source of truth

Column names, vehicle types, the rolling-window size, and default hyperparameters live in
one module as frozen dataclasses and tuples. The feature pipeline derives its output
names from `SENSOR_COLUMNS`; the API schemas derive their minimum history length from
`ROLLING_WINDOW_DAYS`; the tests import the same constants. A rename in one place
propagates everywhere or fails loudly — there is no string that must be kept in sync by
human discipline.

*Trade-off:* frozen dataclasses instead of a settings framework (Dynaconf, pydantic-settings).
For one env var (`FLEETPULSE_MODEL_DIR`) a framework would be ceremony.

### `data/generator.py` — physics-informed simulation

Real telemetry is proprietary, so the generator must earn credibility. It does this by
simulating the *causal structure* of degradation rather than sampling labels directly:

* A hidden wear state increases by gamma-distributed daily increments (always positive,
  occasionally jumpy — like real mechanical wear).
* Sensors are noisy functions of wear with deliberately different signatures: linear
  (engine temperature), inverted (oil pressure), super-linear (`vibration ∝ wear^1.5`,
  the way bearing degradation actually presents).
* Failures repair *imperfectly* — wear resets to 0.05–0.15, not zero — so second
  failure cycles are shorter, as in real fleets.
* The label (`failure_within_horizon`) is computed from the future of the wear
  trajectory. The hidden state itself never appears in the output, so a model can only
  score well by reading degradation out of the observable sensor history.

Determinism per seed is a contract (tested), which makes every experiment reproducible.

*Trade-off:* the private helpers (`_simulate_wear`) use a Python loop over days rather
than vectorised numpy. Wear resets make vectorisation genuinely awkward, and at 60
vehicles × 365 days the loop costs milliseconds — clarity wins.

### `features/engineering.py` — trends, not snapshots

Fifteen lines of logic, but they encode the domain insight that degradation is visible
in *trends*: each sensor gets a trailing rolling mean, rolling std, and a delta against
the reading one window ago. Three properties are enforced and tested:

1. **No look-ahead.** Windows are strictly trailing. The test corrupts all data after
   day 100 and asserts features up to day 100 are byte-identical.
2. **No cross-vehicle bleed.** Rolling windows are computed per `groupby(vehicle_id)`
   group; the test verifies a vehicle's features are identical whether it is processed
   alone or in the full fleet frame.
3. **No NaNs downstream.** Warm-up rows (each vehicle's first 7 days) are dropped
   explicitly, and the row count is asserted exactly — silent row loss is a bug, priced
   in and tested.

`FEATURE_COLUMNS` is derived programmatically from config, so the model card's feature
list can never drift from what the pipeline actually produces.

### `models/train.py` — the two decisions that matter

The algorithm choice is almost the least interesting thing here. Two decisions carry the
scientific weight:

1. **Grouped splitting.** Rows from one vehicle are heavily autocorrelated; a random row
   split would put day 100 in train and day 101 in test and inflate every metric.
   `GroupShuffleSplit` on `vehicle_id` guarantees evaluation on unseen vehicles. A test
   asserts train/test vehicle sets are disjoint.
2. **Baseline-anchored selection.** A logistic regression is trained beside the
   gradient-boosted model in every run. The boosted model must *demonstrate* its value
   in held-out PR-AUC (0.966 vs 0.905), and both results are recorded in the model card.
   If a future data change makes the linear model competitive, the card will show it.

Preprocessing is honest about what each model needs: the linear pipeline scales numeric
features; the tree pipeline passes them through untouched (trees are scale-invariant —
scaling them anyway is a cargo-cult tell).

Persistence is an *artifact directory*, not a bare pickle: `model.joblib` plus
`model_card.json` carrying metrics for all candidates, the operating threshold, the
feature list, library versions, timestamp, and held-out vehicle IDs. The API's
`/model/info` endpoint serves the card, so the deployed system can always account for
itself. A round-trip test asserts a reloaded model produces identical probabilities.

### `models/evaluate.py` — metrics for an imbalanced problem

Accuracy is a misleading headline when ~31% of vehicle-days are positive; a
"never maintain" classifier gets 69% accuracy and destroys the fleet. The primary
selection metric is **PR-AUC** (average precision), with ROC-AUC for ranking quality and
the **Brier score** for probability calibration — probabilities feed a maintenance
scheduler, so calibration is not optional.

`select_threshold` maximises F1 on held-out data but the docstring says the quiet part
out loud: the real threshold is a business decision balancing workshop-visit cost
against roadside-breakdown cost. The code makes the neutral default explicit and
auditable rather than pretending the question doesn't exist.

### `models/anomaly.py` — the complementary question

The classifier answers "is this vehicle degrading towards a failure mode I was trained
on?" The `IsolationForest` answers "does this reading look like anything I saw at all?"
— catching stuck sensors, firmware faults, and novel failure modes. It is fitted on
**healthy rows only** (label = 0), so pre-failure telemetry doesn't contaminate its
notion of normal. The wrapper class fixes the feature contract (raw sensor columns
only) and negates sklearn's decision function so that *bigger score = more anomalous* —
a small API-design courtesy that avoids a classic sign-confusion bug in callers.

### `monitoring/drift.py` — knowing when the model has gone stale

Population Stability Index per sensor channel, comparing a serving window against the
training reference. Two implementation details show care:

* Bin edges are **quantiles of the reference distribution** (not uniform-width bins), so
  each reference bin holds ~10% of the data and outliers can't dominate the statistic.
* Fractions are clipped at ε before the log-ratio, so an empty bin yields a large finite
  PSI instead of infinity.

The 0.10 / 0.25 severity cut-offs are the standard ones from credit-risk model
monitoring, encoded in one place so alerting stays consistent.

### `api/` — contracts at the boundary

Three files with distinct jobs:

* **`schemas.py`** validates *physical plausibility*: engine temperature within
  −40…150 °C, battery voltage 6–16 V, history in strictly increasing day order, at least
  8 readings (derived from the rolling window size in config), batches capped at 100.
  Implausible data is a 422 at the boundary, not a silent garbage prediction.
  Statistical oddities *within* plausible bounds are deliberately left to the anomaly
  detector — the schema layer and the ML layer answer different questions.
* **`service.py`** is the only place that translates between Pydantic models and
  DataFrames. It reuses the training feature function and owns the risk-band policy
  (high ≥ threshold, medium ≥ threshold/2).
* **`main.py`** is an app factory: `create_app(artifact_dir)` takes the model location
  as a parameter, so tests inject a temporary model without patching globals or
  environment variables. Artifacts load once in the lifespan hook, not per request.

### `cli.py` — the workflow as a user interface

`generate → train → drift → serve` mirrors the ML lifecycle. Plain `argparse` from the
standard library — a dependency like Typer would buy prettier help text at the cost of a
dependency; at four subcommands that trade is declined. The CLI is covered by an
end-to-end test that runs the documented three-step workflow against a temp directory
and asserts on files produced and output printed.

## 3. Cross-cutting design decisions

* **`src/` layout.** The package cannot be imported accidentally from the repo root;
  tests exercise the *installed* package, the same artifact CI and Docker build.
* **One-way dependency flow.** `api` imports `models` imports `features` imports
  `config`; nothing imports upward. The ML core is usable without FastAPI installed.
* **Derived constants over repeated literals.** Feature names, minimum history length,
  and API validation limits are all computed from config values.
* **Frozen dataclasses for configs.** Immutability makes configs safe to share across
  fixtures and prevents spooky action at a distance in tests.
* **Docstrings explain *why*, comments are rare.** The code states its reasoning where
  the reasoning is the point (leakage, imbalance, imperfect repair), not what the next
  line does.

## 4. Testing strategy

31 tests, 98% line coverage — but the design principle is that tests assert
**properties an ML system can silently lose**, not just endpoints returning 200:

| Property | Test |
|---|---|
| Reproducibility | same seed ⇒ identical dataset; round-trip ⇒ identical probabilities |
| No temporal leakage | corrupting future data leaves past features byte-identical |
| No entity leakage | train/test vehicle sets provably disjoint |
| No cross-entity bleed | per-vehicle features identical alone vs in fleet frame |
| Model earns its keep | PR-AUC > 2× positive rate, ROC-AUC > 0.7 on unseen vehicles |
| Contract enforcement | 422 for implausible values, short history, unordered days |
| Monitoring correctness | PSI ≈ 0 on identical distributions; shifted sensor flagged, others stable |
| Workflow integrity | CLI generate → train → drift runs end-to-end in a temp dir |

Fixtures are session-scoped: one small dataset and one trained model shared by the whole
suite keeps the run ~10 s so it is actually run, not skipped.

CI (GitHub Actions) runs ruff and the suite with a **90% coverage gate** across Python
3.10–3.12, then an independent end-to-end training smoke job — a fresh install must be
able to produce a working model from nothing.

## 5. Failure modes considered

| Failure mode | Defence |
|---|---|
| Sensor fault sends garbage values | Plausibility bounds in schemas → 422 |
| Novel failure mode classifier never saw | IsolationForest anomaly endpoint |
| Fleet composition changes over time | PSI drift report with severity levels |
| Feature code diverges between train & serve | Single shared `build_features` |
| Metric inflation via autocorrelated rows | Grouped train/test split |
| "Which model is even deployed?" | Model card served at `/model/info` |
| Requests before model load / oversized batches | 503 guard; batch cap of 100 |

## 6. Deliberate trade-offs

Choices made knowingly, with what they cost:

* **Synthetic data** buys full reproducibility and a clean causal story; it costs
  realism (no missing days, no mixed sampling rates). The generator is quarantined in
  `data/` so a real ingestion layer can replace it without touching the pipeline.
* **Sequential batch scoring** is simple and correct; at real fleet scale the histories
  should be concatenated into one frame and scored in a single pipeline call. The
  feature function already supports this — the change is confined to `service.py`.
* **F1-optimal threshold** is a neutral default standing in for a cost-weighted
  decision; the model card records it precisely so it can be revisited with real costs.
* **No model registry / experiment tracker.** The JSON model card covers provenance at
  this scale; MLflow would be the next step, and the artifact-directory design maps
  directly onto it.
* **No auth on the API** — appropriate for a service behind a gateway, stated openly in
  the README rather than discovered in a pen test.
