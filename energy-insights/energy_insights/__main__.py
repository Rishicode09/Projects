"""
STEP 5 — __main__.py: the command-line interface (the Software Engineer hat).

WHY THIS FILE HAS THIS EXACT NAME:
`python -m energy_insights <command>` runs THIS file. That's the same
mechanism behind `python -m pytest` and `python -m pip` — now your
project behaves like a real tool, not a script you have to open in an
editor to use.

WHY A CLI AT ALL? Because "how do I run it?" should have a one-line
answer for a stranger (or an interviewer, or you in 6 months).

We use argparse from the standard library: no extra install, and its
"subcommand" pattern (generate / clean / analyze / train) is exactly
how git works (git commit, git push, ...).
"""

import argparse

from energy_insights import analysis, cleaning, data_generator, model

RAW_PATH = "data/energy_raw.csv"
CLEAN_PATH = "data/energy_clean.csv"


def cmd_generate(args: argparse.Namespace) -> None:
    """`python -m energy_insights generate --days 365`"""
    df = data_generator.generate_energy_data(days=args.days, seed=args.seed)
    data_generator.save_data(df, RAW_PATH)
    # f-strings: {len(df):,} formats 8760 as 8,760 — small touches read well.
    print(f"Wrote {len(df):,} rows to {RAW_PATH}")
    print(f"Missing values injected: {int(df['consumption_kwh'].isna().sum())}")


def cmd_clean(args: argparse.Namespace) -> None:
    """`python -m energy_insights clean`"""
    df = cleaning.load_data(RAW_PATH)
    clean_df, report = cleaning.clean_data(df, iqr_k=args.iqr_k)
    data_generator.save_data(clean_df, CLEAN_PATH)
    print(f"Wrote {len(clean_df):,} rows to {CLEAN_PATH}")
    for key, value in report.items():  # .items() yields (key, value) pairs
        print(f"  {key}: {value}")


def cmd_analyze(args: argparse.Namespace) -> None:
    """`python -m energy_insights analyze`"""
    df = cleaning.load_data(CLEAN_PATH)

    print("== Summary statistics ==")
    print(analysis.summary_stats(df).round(3).to_string())

    print("\n== Weekday vs weekend ==")
    print(analysis.weekday_weekend_comparison(df).round(3).to_string())

    corr = analysis.temperature_correlation(df)
    print(f"\nTemperature ↔ consumption correlation: {corr:.3f}")
    print("(Negative — but that's only half the story. Read the docstring")
    print(" of temperature_correlation before you trust this number.)")

    path = analysis.plot_overview(df)
    print(f"\nSaved plot to {path}")


def cmd_train(args: argparse.Namespace) -> None:
    """`python -m energy_insights train`"""
    df = cleaning.load_data(CLEAN_PATH)
    scoreboard = model.train_and_compare(df)
    print("\n== Model scoreboard (lower MAE / higher R² is better) ==")
    print(scoreboard.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="energy_insights",
        description="Generate, clean, analyze and forecast household energy data.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="create synthetic raw data")
    p_gen.add_argument("--days", type=int, default=365)
    p_gen.add_argument("--seed", type=int, default=data_generator.DEFAULT_SEED)
    p_gen.set_defaults(func=cmd_generate)  # ties this subcommand to its function

    p_clean = sub.add_parser("clean", help="clean the raw data")
    p_clean.add_argument("--iqr-k", type=float, default=3.0)
    p_clean.set_defaults(func=cmd_clean)

    p_an = sub.add_parser("analyze", help="print stats and save a plot")
    p_an.set_defaults(func=cmd_analyze)

    p_tr = sub.add_parser("train", help="train and compare forecasting models")
    p_tr.set_defaults(func=cmd_train)

    args = parser.parse_args()  # reads sys.argv, validates, or prints usage
    args.func(args)             # dispatch to whichever cmd_* was selected


# This guard means "only run main() when executed directly, not when
# imported". Without it, `import energy_insights.__main__` in a test
# would launch the whole CLI. Interview one-liner: it distinguishes
# 'run as a program' from 'used as a library'.
if __name__ == "__main__":
    main()


# 🔧 EXERCISES FOR YOU:
# 1. EASY   — Add `--out` to the generate subcommand so the user can
#             choose the CSV path instead of hardcoding RAW_PATH.
# 2. MEDIUM — Add a `pipeline` subcommand that runs generate -> clean ->
#             analyze -> train in one go. Reuse the cmd_* functions;
#             don't copy their bodies (copy-paste = design smell).
# 3. HARD   — `clean` crashes with FileNotFoundError if you forgot to run
#             `generate` first. Catch it and print a one-line hint
#             telling the user what to run. Good tools fail helpfully.
