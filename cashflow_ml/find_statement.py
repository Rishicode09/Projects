"""
Finding the bank statement CSV, in one place.

Every script in this project needs to answer the same question: which file am
I supposed to read? They used to answer it differently, which meant one script
could find your statement and another could not.

Nothing here needs editing. If the default locations do not suit you, pass the
path on the command line instead -- that is what the argument is for.
"""

from __future__ import annotations

import sys
from pathlib import Path


def candidates(base_dir: Path, name: str = "bank_company.csv") -> tuple[Path, ...]:
    """Where to look when no path is given, in order of preference."""
    return (
        base_dir / "data" / name,   # the tidy layout
        base_dir / name,            # loose beside the script
    )


def nearby_csvs(base_dir: Path) -> list[Path]:
    """Every CSV we can see near the script, for the error message."""
    return sorted(base_dir.glob("*.csv")) + sorted(base_dir.glob("data/*.csv"))


def find_csv(positional: list[str], base_dir: Path) -> Path | None:
    """The path you named, else the first default that exists, else nothing."""
    if positional:
        given = Path(positional[0]).expanduser()
        return given if given.exists() else None
    return next((path for path in candidates(base_dir) if path.exists()), None)


def explain_missing(positional: list[str], base_dir: Path,
                    script: str = "the script") -> None:
    """Say where we looked and what we can actually see."""
    print("Could not find the bank statement CSV.", file=sys.stderr)

    if positional:
        print(f"  You asked for: {Path(positional[0]).expanduser()}",
              file=sys.stderr)
    else:
        print("  Looked in:", file=sys.stderr)
        for path in candidates(base_dir):
            print(f"    {path}", file=sys.stderr)

    found = nearby_csvs(base_dir)
    if found:
        print("\n  CSV files I can see near the script:", file=sys.stderr)
        for path in found:
            print(f"    {path}", file=sys.stderr)
        print("\n  Run it again naming the one you want, e.g.:", file=sys.stderr)
        print(f'    python "{script}" "{found[0]}"', file=sys.stderr)
    else:
        print(f"\n  No CSV files found in {base_dir}."
              "\n  Put the statement beside the script, or pass its full path.",
              file=sys.stderr)


def collect_csvs(arguments: list[str], base_dir: Path) -> list[Path]:
    """Files, folders, or nothing at all -- for the database loader, which
    can take several statements at once."""
    if arguments:
        paths: list[Path] = []
        for argument in arguments:
            path = Path(argument).expanduser()
            paths.extend(sorted(path.glob("*.csv")) if path.is_dir() else [path])
        return paths

    # No arguments: take every CSV from the first folder that has any, so the
    # loader works whether or not you keep a data/ directory.
    for folder in (base_dir / "data", base_dir):
        found = sorted(folder.glob("*.csv")) if folder.is_dir() else []
        if found:
            return found
    return []
