.PHONY: install lint test coverage data train drift serve docker

install:
	pip install -e ".[dev]"

lint:
	ruff check src tests

test:
	pytest -q

coverage:
	pytest -q --cov=fleetpulse --cov-report=term-missing

data:
	fleetpulse generate --out data/telemetry.csv

train: data
	fleetpulse train --data data/telemetry.csv --out artifacts

drift: data
	fleetpulse drift --data data/telemetry.csv

serve:
	fleetpulse serve --artifacts artifacts

docker:
	docker build -t fleetpulse .
