# EXERCISES.md — your work, not mine

This project is 80% finished **on purpose**. The remaining 20% — the
exercises below — is what turns it from "another AI-generated repo"
into *your* project. In an interview, you will only be able to defend
code you have personally fought with.

**Rules of engagement**
1. Work on a branch: `git checkout -b exercise/<name>` — practice real workflow.
2. After every change: rerun the pipeline AND `python -m pytest`.
3. Commit each finished exercise with a message that says *why*, not just *what*.
4. If you break something — good. Read the traceback top-to-bottom before Googling.

---

## Level 0 — Read & run (30 min)
- [ ] Run all four CLI commands. Open `data/overview.png`.
- [ ] Read every file top to bottom, including comments. Write down the
      3 lines you understand least. (We'll use that list.)
- [ ] Change the seed in `generate --seed 7`. Which downstream numbers
      change and which stay identical? Why do the *tests* still pass?

## Level 1 — Turn the knobs (each is a 🔧 TRY THIS in the code)
- [ ] `data_generator.py`: crank `missing_fraction` to 0.30 — how much does model MAE degrade?
- [ ] `cleaning.py`: IQR `k` = 1.0 vs 10.0 — find the false-positive / false-negative trade-off.
- [ ] `model.py`: shuffle the split and watch R² lie to you. Explain the lie in one sentence.
- [ ] `model.py`: `n_estimators` = 5 / 50 / 300 — plot score vs runtime, find the knee.

## Level 2 — Extend (the numbered exercises at the bottom of each module)
Do at least: solar panels (generator #2), ffill-vs-interpolate measurement
(cleaning #2), peak-hours finder (analysis #2), the `pipeline` CLI
subcommand (CLI #2), and the failing-first test (tests #3).

## Level 3 — The bug hunt (do this before any interview)
`model.py` exercise #3 describes a **real bug shipped in this repo**:
lag features silently assume rows are 1 hour apart, but cleaning drops
rows. Quantify it, fix it, and write the test that would have caught it.
Being able to tell this story — found, measured, fixed, regression-tested —
is worth more than any feature you could add.

## Level 4 — Make it yours (pick ONE, go deep)
- Swap synthetic data for a real dataset (e.g. UCI "Individual household
  electric power consumption") and make the pipeline survive contact
  with reality. Expect everything to break; that's the exercise.
- Add a `forecast` CLI command that predicts the NEXT 24 hours
  (careful: you won't have future lag values — that's the hard part).
- Wrap `train` results in a tiny FastAPI endpoint (`/predict`).

---

## Interview questions you should now be able to answer
1. Why is a random train/test split wrong for time series? *Show* it with this repo.
2. Why IQR instead of mean ± 3σ for outliers?
3. Your correlation was ≈ 0 but the relationship was strong. How? What did you do about it?
4. Why does your cleaning function return a report dict?
5. What's your baseline and why does a model that can't beat it have zero value?
6. What do your tests assert, and why not exact metric values?
7. (After Level 3) Tell me about a bug you found in your own project.

If you can answer all 7 without notes, this project is application-ready.
