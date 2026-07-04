# conftest.py — pytest's configuration hook file.
# Even EMPTY, its presence makes pytest add this directory to Python's
# import path, so `from energy_insights import ...` works in tests
# without installing the package first. (Installing with
# `pip install -e .` is the proper way; this file is the training wheels.)
