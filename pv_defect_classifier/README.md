# PV Defect Detection → Power Loss

Detects physical defects in silicon solar cells from electroluminescence (EL)
images, then simulates what those defects cost in electrical power and annual
energy yield.

The point of the project is the coupling. A defect model on its own answers "is
this cell cracked?", which nobody can act on. The question a plant operator has
is "which modules should I replace this year?", and answering that means turning
a visual defect into kilowatt-hours. That conversion is where the physics lives,
and it is not a proportionality constant — a single badly damaged cell in a
60-cell series string costs far more power than its share of the module's area,
and how much more depends on irradiance, temperature and where the bypass diodes
sit.

```
module photo ──► OpenCV crop & rectify ──► per-cell EL images
                                                  │
                        ┌─────────────────────────┴──────────────────────┐
                        ▼                                                ▼
          ResNet-50 binary classifier                    YOLO defect detector
          functional / cracked                           boxes + measured area
                        │                                                │
                        └────────────────────┬───────────────────────────┘
                                             ▼
                          defect → single-diode parameters
                          (photocurrent, R_s, R_sh)
                                             │
       TMY weather (pvlib) ─────────────►  60-cell mismatch + bypass diodes
                                          MPP solve (SciPy)
                                             │
                                             ▼
                          ΔP at STC, ΔkWh/year, cost/year
```

---

## Three things to know before reading further

**1. ELPV contains no weather data.** It is a set of EL cell crops photographed
in a dark lab with the module driven by an external current source — no sun
involved. All meteorological input comes from pvlib (a PVGIS typical
meteorological year, or a synthetic clear-sky year offline). The two datasets
meet only at the end: ELPV supplies the *condition of the cells*, the TMY
supplies the *conditions they operate under*.

**2. ELPV has no bounding boxes.** It ships one probability per cell — image
labels only. A YOLO detector cannot be trained on that as-is. This repo includes
a bootstrap labeller that proposes boxes from the classical crack response, but
**the boxes must be reviewed by a human before training**. See
[Detection](#the-detection-half) for measured proposal quality; it is good on
dark inactive regions and poor on hairline cracks.

**3. The defect → power mapping is not calibrated.** EL shows where charge
carriers recombine; it does not measure power. The coefficients in
`physics/degradation.py` are plausible values from the literature, not values
fitted to paired EL/flash-test data. Until you run
`degradation.fit_from_measurements` against real IV curves, absolute watt
figures are **indicative, and the rankings are what you should trust**. This is
the most valuable open experiment in the project — see [Next steps](#next-steps).

---

## Install

```bash
pip install -e ".[dev]"     # or: pip install -r requirements.txt
python scripts/download_data.py
pytest -q                    # 60 tests, no dataset required
```

The ELPV **images** are CC BY-NC-SA 4.0 (non-commercial). Cite Buerhop-Lutz
et al. 2018, Deitsch et al. 2019 and Deitsch et al. 2021 in any publication —
BibTeX is in the [upstream repo](https://github.com/zae-bayern/elpv-dataset).

> **Network note.** torchvision fetches ImageNet weights from
> `download.pytorch.org`. If your environment blocks that host, the classifier
> falls back to random initialisation with a loud warning — and on 2,624 images
> that is a pipeline smoke test, not a result. Pre-download the weights into
> `$TORCH_HOME/hub/checkpoints` somewhere with access. Ultralytics fetches from
> GitHub releases, which is usually reachable when the PyTorch CDN is not.

## Run

```bash
make train              # binary classifier          (python -m pvdefect.train)
make detection-data     # build YOLO dataset + bootstrap boxes  ← review these
make train-detector     # fine-tune YOLO on reviewed boxes
make test

# end to end: images in, kWh and cost out
python scripts/analyse_module.py --module-image module_01.png --rows 6 --columns 10
python scripts/analyse_module.py --cells path/to/cells/ --detector artifacts/detection/elpv/weights/best.pt
```

`analyse_module.py` runs with or without a trained model — it degrades to the
classical area estimator, and tells you it is doing so.

---

## The image pipeline

**Module cropping** (`preprocess/module_crop.py`). ELPV ships pre-cropped cells,
but a real inspection campaign produces one photograph per *module*. This is the
front door: threshold + largest-contour to find the laminate, fit a quadrilateral
and warp it to a rectangle, then split the grid — refining the nominal cut lines
against the dark inter-cell gaps so a slightly non-square laminate does not shear
the crops.

Perspective correction is not cosmetic. EL photographs are rarely taken
square-on, and an uncorrected perspective makes every cell in the far row a
different size, which the classifier reads as a defect signal. When the module
outline cannot be found confidently the code returns `None` and skips
rectification rather than guessing — a wrong warp silently mis-crops every cell
in the module, and a crop landing half on a busbar looks exactly like a defect.

**Cell enhancement** (`preprocess/cell_prep.py`) produces a 3-channel stack:

| channel | content | why |
|---|---|---|
| 0 | illumination-flattened + CLAHE | what a human inspector looks at |
| 1 | busbar/finger-suppressed residual | crack candidates without the grid |
| 2 | black-hat crack response | dark linear features |

Per-cell normalisation matters more than it looks. EL brightness depends on
injection current and integration time, both set *per module*, so a network
trained on raw intensities learns each module's exposure rather than its
defects. A test pins this property.

**Augmentation** (`data/transforms.py`, Albumentations). Constrained by EL
physics rather than by what looks reasonable on photographs:

- **Rotation and flips are free** — a cell has no canonical orientation, so all
  eight dihedral symmetries are label-preserving. Reflective border padding, so
  no black wedge appears at the corners (a black wedge reads as a dead region).
- **Contrast/brightness jitter is the important one** — it is what enforces
  exposure invariance.
- **Blur is capped at a 3-pixel kernel.** The difference between a healthy cell
  and a mildly cracked one is a hairline feature a few pixels wide; aggressive
  blur destroys exactly the signal being learned.
- **No colour ops** (single-channel NIR sensor), **no large translations** (crops
  are already cell-aligned, and edge cracks live at the border).

Ordering matters: OpenCV preprocessing runs first, Albumentations augments the
result. Augmenting first would let brightness jitter feed into CLAHE, which
re-normalises it straight back out.

## The classification half

**Task.** Binary — functional vs cracked. ELPV's raw annotation is the fraction
of experts who called a cell defective (0, ⅓, ⅔, 1); `data.elpv` collapses that
at a configurable threshold. The threshold is a real choice, not a detail:
`0.5` (default) puts the ambiguous ⅓ level on the functional side, giving high
precision and missing hairline cracks; `0.1` counts any disagreement as cracked,
raising recall and false alarms. At the default the split is 1803 functional /
821 cracked.

The graded probability is kept in the frame regardless, because the physics model
consumes a continuous severity.

**Model.** torchvision ResNet-50 (default) or EfficientNet-B0, ImageNet
pretrained, with a **single-logit** head. One logit rather than two: it pairs
directly with `BCEWithLogitsLoss` and its `pos_weight` (how the imbalance is
handled), and it keeps the decision threshold an explicit knob at inference
instead of hiding it in an argmax.

**Imbalance** is handled twice over — `pos_weight` in the loss, and a capped
oversampler. The cap matters: uncapped inverse-frequency sampling repeats the
minority images often enough that the model memorises them.

**Splitting is the biggest single lever on the reported number.** Published ELPV
accuracies vary by more than ten points, and most of that gap is leakage. Cells
from one module share a wafer batch, an exposure, and often the same crack
running across neighbours. `labels.csv` does not publish module IDs, but rows are
ordered module by module, so `data/splits.py` cuts the sequence into contiguous
pseudo-modules (wafer-type transitions are guaranteed cuts) and keeps each wholly
inside one subset. On the real dataset this recovers 45 pseudo-modules against 44
real ones.

It is an approximation, not a fix — a chunk boundary landing mid-module still
lets two cells of one real module straddle the split. `make train-leaky` runs the
random split; the gap between the two is worth reporting.

**Metrics** (`evaluate.py`). Accuracy is near-useless: predicting "functional"
for everything scores 69%. Model selection uses **average precision**
(threshold-free, and on an imbalanced binary task it tracks the minority class
better than ROC-AUC). **MCC** is the best fixed-threshold summary — unlike F1 it
accounts for true negatives, so it cannot be inflated by predicting the majority
class. `best_threshold()` reports the operating point for a target recall,
because "90% of cracked cells caught, at this false-alarm cost" is the actual
deployment decision.

## The detection half

**Why detection earns its place.** The physics model's dominant input is
*inactive area* — what fraction of the cell stopped contributing photocurrent. A
classifier cannot supply that; it emits a probability that must be mapped to an
area through the uncalibrated table in `physics/degradation.py`. A detector
measures the geometry directly. `detector.defect_area_fraction` is therefore the
path by which detection removes the largest guess in the pipeline, and that —
not benchmark accuracy — is the argument for spending annotation effort on boxes.

**Two classes**, `crack` and `inactive_area`, separated in the bootstrap
generator by shape (elongated/low-fill vs blob). They enter the physics through
different parameters, which is why they are kept apart.

**The area→physics rule encodes real physics, not just box arithmetic.** A
detected inactive area counts at its full box area. A detected crack does not: a
crack is a line, its bounding box is mostly intact silicon, and a crack only
costs power once it *isolates* material. Counting crack boxes at face value is
exactly the over-prediction the IEA-PVPS T13 review warns about, so cracks are
down-weighted (`crack_area_weight`, default 0.25 — a placeholder worth
calibrating). Boxes are unioned on a mask, so overlapping detections of one
defect are not double-counted.

**Bootstrap labelling, and its measured limits.**
`scripts/build_detection_dataset.py` proposes boxes from the classical crack
response on cells already labelled cracked. On real ELPV cells:

- *Dark inactive regions: good.* Boxed tightly and classified correctly. This is
  the more valuable half, since inactive area is what the physics consumes.
- *Hairline diagonal cracks: poor.* Faint branching cracks common in
  polycrystalline cells frequently go unboxed. Expect to draw most crack boxes
  by hand.
- *Metallisation: filtered, imperfectly.* Busbars and fingers are dark lines and
  were the largest junk source until `is_grid_structure` rejected axis-aligned
  thin regions — 3164 proposals dropped to 1348, with corner slivers and most
  finger boxes gone. Some finger segments survive.

Look at `proposal_preview.png` before trusting any of it. If your imagery is
mostly hairline cracking, `--no-proposals` and annotating from scratch may be
faster than correcting these.

One trap worth naming: the obvious threshold for the crack response is Otsu, and
it is wrong. Otsu always returns a split, even on pure sensor noise, so on a
clean cell it lights up ~68% of the image. The generator uses a median-absolute-
deviation noise floor instead, which answers "is anything far above the noise?"
and answers "no" when nothing is.

**Model size.** `yolo11n` (nano) is the default and is the right choice: ELPV has
at most a few thousand boxes after annotation, and a larger backbone has more
parameters than there are labelled objects.

## The physics half

Everything below is per-cell and vectorised over a 60-cell string.

**Single-diode model** (`physics/cell_model.py`). pvlib's parameter databases are
module-level, so parameters are pushed down to one cell: `I_L, I_o` unchanged;
`R_s, R_sh, a_ref` all divided by `N_s`. That last one matters — `a_ref` in the
De Soto convention already contains the cell count, and forgetting it inflates
every voltage by 60×.

**Three damage mechanisms** (`physics/degradation.py`), each visible in EL:

| mechanism | parameter | worst at |
|---|---|---|
| inactive area (region cut off from busbars) | scales `I_L` | all irradiances |
| series resistance (broken fingers) | raises `R_s` | **high** irradiance (I²R) |
| shunting (crack-induced shorts) | lowers `R_sh` | **low** irradiance |

Mechanisms 2 and 3 have *opposite* irradiance dependence, which is exactly why
this project runs an 8,760-hour simulation instead of scaling a single STC
number. A test pins that opposition.

One subtlety: De Soto scales `R_sh` inversely with irradiance, so a naive
multiplier on `R_sh` produces identical relative loss at 100 and 1000 W/m² —
wrong, because a crack-induced shunt is a physical resistor that does not know
what the sun is doing. The retention factor is interpreted as the shunt you would
*measure at STC*, converted to a fixed parallel conductance, and added to the
irradiance-scaled healthy one.

**Evidence precedence.** `inactive_area` accepts three sources in ascending order
of trust: the classifier's probability through the level table; the crude
dark-pixel estimate; and a detector-measured area, which dominates when present
(weight 0.8) because it is the only one that measures the physical quantity. It
stays gated on classifier confidence — a detector firing on a cell the classifier
calls clean is more likely a false positive than a defect both stages agree on.

**Mismatch and bypass diodes** (`physics/mismatch.py`). Cells in series carry the
same current, so the string is limited by its worst cell. Each substring has a
bypass diode clamping it at ≈ −0.5 V, which stops one dead cell killing the
module. The MPP solve is a coarse current sweep to bracket the peak, then Brent
refinement — the sweep is **not** optional, because a mismatched string with
bypass diodes has a genuinely multi-modal P-V curve (one local peak per bypass
configuration) and a bare optimiser returns the wrong one.

Verified behaviour for a single damaged cell in a 3-diode, 60-cell module:

| one cell's inactive area | module power loss | substrings bypassed |
|---|---|---|
| 10% | 1.9% | 0 |
| 30% | 18.3% | 0 |
| 50% | 34.9% | 1 |
| 90% | 34.9% | 1 |

The loss saturates at exactly one third once the diode conducts. That plateau is
the model reproducing the physics, not an assumption written into it — and 30%
area loss on one cell (0.5% of module area) costing 18% of module power is the
mismatch amplification that justifies per-cell analysis.

**Weather** (`physics/weather.py`). PVGIS TMY where the network allows, with a
pvlib Ineichen clear-sky fallback that needs none. The fallback over-estimates
annual yield because it has no clouds — relative comparisons only. The frame
carries a `synthetic` attribute so callers can tell which they got.

**Annual energy** (`physics/energy.py`). 8,760 hourly MPP solves per module is
minutes of compute. But module power depends on the weather only through two
scalars (effective irradiance, cell temperature), so we solve exactly on a 12×7
grid and interpolate over the year — ~84 solves replace 8,760, with
interpolation error far below the degradation model's own uncertainty. Linear
rather than cubic, because the surface has a real kink where a bypass diode
engages and a spline overshoots it.

Example output (clear-sky Erlangen year, generic 300 W module):

| scenario | STC loss | annual loss | yield |
|---|---|---|---|
| healthy | 0.00% | 0.00% | 550 kWh |
| 1 mild cell | 0.04% | 0.03% | 550 kWh |
| 1 severe cell | 14.00% | 11.00% | 490 kWh |
| 5 severe cells (1 substring) | 22.42% | 22.79% | 425 kWh |
| all cells mild | 1.96% | 1.81% | 540 kWh |

Note the mild rows. A hairline crack that has not yet isolated anything costs
essentially nothing — matching the IEA-PVPS T13 finding that cracked cells
frequently show no measurable power loss. A model mapping "crack visible"
straight to "power lost" would over-predict badly; this one is built not to.

## Layout

```
src/pvdefect/
  config.py                 YAML-backed configuration
  train.py                  classifier training loop, CLI entry point
  evaluate.py               binary metrics + operating-point selection
  explain.py                Grad-CAM
  data/
    elpv.py                 dataset index, binary thresholding, pos_weight
    splits.py               pseudo-module leakage-aware splitting
    dataset.py              torch Dataset
    transforms.py           Albumentations pipelines
  preprocess/
    module_crop.py          module photo -> rectified cell crops (OpenCV)
    cell_prep.py            EL enhancement + inactive-area estimator
  models/classifier.py      ResNet-50 / EfficientNet + single-logit head
  detection/
    pseudo_label.py         bootstrap box proposals  ← review the output
    dataset.py              YOLO dataset layout
    detector.py             Ultralytics train/infer + area -> physics
  physics/
    cell_model.py           module -> per-cell single-diode parameters
    degradation.py          defect -> parameter damage  ← the calibration gap
    mismatch.py             series string, bypass diodes, MPP solve
    weather.py              PVGIS TMY / clear-sky fallback, POA transposition
    energy.py               interpolated annual energy simulation
scripts/
  download_data.py          fetch ELPV
  build_detection_dataset.py  YOLO dataset + bootstrap boxes + preview
  train_detector.py         Ultralytics fine-tuning
  analyse_module.py         end to end: images -> kWh and cost
tests/                      60 tests; physics tests assert properties, not constants
```

## Next steps

Roughly in order of research value:

1. **Calibrate the degradation model.** Pair EL images with flash-test IV curves
   for 30–50 modules and fit `fit_from_measurements`. This is what turns the
   pipeline from a ranking tool into a measurement tool; everything else is
   downstream of it. `crack_area_weight` is the second number to fit.
2. **Annotate boxes properly.** The bootstrap proposals handle inactive regions
   but not hairline cracks. A few hundred hand-drawn crack boxes would make the
   detector — and therefore the measured-area path into the physics — real.
3. **Get real module IDs** for ELPV (or image your own modules) so the split is
   genuinely module-wise and the metrics are defensible.
4. **Cross-validate.** `splits.cross_validation_folds` is written and unused.
   With ~44 modules, single-split numbers carry several points of noise.
5. **Segment rather than detect.** Inactive area is what the physics wants, and a
   mask measures it better than a box does — a diagonal crack's bounding box
   badly over-states its extent, which is why `crack_area_weight` exists at all.
6. **Model reverse-bias breakdown** (Bishop's term) for hot-spot risk.
   Deliberately omitted: three more uncalibrated parameters, and it changes no
   MPP result because the bypass diode clamps first.
7. **String- and plant-level aggregation.** The same mismatch logic applies one
   level up.

## References

- Buerhop-Lutz et al. (2018), *A Benchmark for Visual Identification of Defective
  Solar Cells in EL Imagery*, EU PVSEC.
- Deitsch et al. (2019), *Automatic classification of defective PV module cells in
  electroluminescence images*, Solar Energy 185, 455–468.
- Deitsch et al. (2021), *Segmentation of PV module cells in uncalibrated EL
  images*, Machine Vision and Applications 32(4).
- Köntges et al. (2014), *Review of Failures of PV Modules*, IEA-PVPS
  T13-01:2014 — the source for "cracks do not necessarily cost power".
- De Soto, Klein & Beckman (2006), *Improvement and validation of a model for
  photovoltaic array performance*, Solar Energy 80(1).
