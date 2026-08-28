.PHONY: install data test train train-leaky detection-data train-detector clean

install:
	pip install -e ".[dev]"

data:
	python scripts/download_data.py

test:
	pytest -q

# --- classification ---------------------------------------------------
train:
	python -m pvdefect.train --config configs/default.yaml

# Measures the leakage gap: this number will look better than `train`, and
# that gap is the thing worth reporting.
train-leaky:
	python -m pvdefect.train --config configs/default.yaml --split random --output-dir artifacts/leaky

# --- detection --------------------------------------------------------
# Builds a YOLO dataset with bootstrap boxes. REVIEW THE LABELS before
# training -- see scripts/build_detection_dataset.py for why.
detection-data:
	python scripts/build_detection_dataset.py --dest data/yolo --overwrite

train-detector:
	python scripts/train_detector.py --data data/yolo/data.yaml

clean:
	rm -rf artifacts .pytest_cache **/__pycache__
