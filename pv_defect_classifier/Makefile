.PHONY: install data test train app lint clean

install:
	pip install -e ".[dev]"

data:
	python scripts/download_data.py

test:
	pytest -q

train:
	python -m pvdefect.train --config configs/default.yaml

# Measures the leakage gap: this number will look better than `train`, and that
# gap is the thing worth reporting.
train-leaky:
	python -m pvdefect.train --config configs/default.yaml --split random --output-dir artifacts/leaky

app:
	streamlit run src/pvdefect/app/streamlit_app.py

clean:
	rm -rf artifacts .pytest_cache **/__pycache__
