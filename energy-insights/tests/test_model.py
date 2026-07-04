"""
Tests for model.py — note what we test and what we DON'T.

We do NOT test "MAE == 0.0834" (exact scores change whenever data or
library versions change — that test would cry wolf forever).
We DO test PROPERTIES that must always hold:
  - features come out with no NaNs and the right columns
  - the split never shuffles time
  - the trained models beat the dumb baseline

Testing properties instead of exact numbers is the core skill of
testing anything statistical. Remember this distinction.
"""

from energy_insights.cleaning import clean_data
from energy_insights.data_generator import generate_energy_data
from energy_insights.model import FEATURES, build_features, time_split, train_and_compare


def make_clean_dataset():
    df = generate_energy_data(days=90, seed=7)
    clean_df, _ = clean_data(df)
    return clean_df


def test_build_features_has_expected_columns_and_no_nans():
    data = build_features(make_clean_dataset())
    for col in FEATURES:
        assert col in data.columns, f"missing feature column: {col}"
    assert data[FEATURES].isna().sum().sum() == 0


def test_time_split_preserves_order():
    data = build_features(make_clean_dataset())
    train, test = time_split(data, train_fraction=0.8)
    # Every training timestamp must come BEFORE every test timestamp.
    # If someone introduces shuffling, this single line catches it.
    assert train["timestamp"].max() < test["timestamp"].min()
    # And roughly 80/20 (integer cut, so allow 1 row of slack).
    assert abs(len(train) - 0.8 * len(data)) <= 1


def test_models_beat_baseline():
    # The most important test in the project: if ML can't beat
    # "same hour yesterday", the whole model.py is decoration.
    scoreboard = train_and_compare(make_clean_dataset())
    scores = scoreboard.set_index("model")["mae_kwh"]
    assert scores["linear_regression"] < scores["baseline_yesterday"]
    assert scores["random_forest"] < scores["baseline_yesterday"]


# 🔧 EXERCISES FOR YOU:
# 1. EASY   — Add an assertion to test_models_beat_baseline that every
#             R² is above 0. What would a negative R² mean? (Answer is
#             in evaluate()'s docstring — but write it in your own words.)
# 2. MEDIUM — Time the test suite (python -m pytest --durations=5).
#             Which test is slowest and which single line inside it
#             costs the most? Cut the cost without weakening the test.
# 3. HARD   — These tests all use synthetic data from OUR generator, so
#             a bug in the generator could hide a bug in the model
#             ("correlated failures"). Design one test that does not
#             depend on generate_energy_data at all.
