#!/bin/sh
# Prepare data and model on first start, then run the API.
set -e

python scripts/seed_data.py
python -m app.ml.train

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
