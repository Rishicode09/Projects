.PHONY: install data test train train-fast train-accurate train-leaky detection-data train-detector clean

install:
	pip install -e ".[dev]"

data:
	python scripts/download_data.py

test:
	pytest -q

# --- classification ---------------------------------------------------
# ~55 min on 4 CPU cores, minutes on a GPU. The exact figure for your machine
# is measured and printed before training starts.
train:
	python -m pvdefect.train --config configs/default.yaml

# ~9 min. Checks the pipeline runs end to end; not a result worth quoting.
train-fast:
	python -m pvdefect.train --config configs/fast.yaml

# ~3.9 h on CPU. The ResNet-50 arm, for the backbone comparison.
train-accurate:
	python -m pvdefect.train --config configs/accurate.yaml

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
