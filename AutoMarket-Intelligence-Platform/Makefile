.PHONY: install run seed train dashboard test test-cov lint format

install:  ## Install the app with dev dependencies
	pip install -e ".[dev]"

run:  ## Run the API locally with hot reload
	uvicorn app.main:app --reload --port 8000

seed:  ## Fill the database with 5000 synthetic listings
	python scripts/seed_data.py

train:  ## Train the price prediction model
	python -m app.ml.train

dashboard:  ## Run the Streamlit dashboard
	streamlit run dashboard/dashboard.py

test:  ## Run the test suite
	pytest

test-cov:  ## Run all tests with a coverage report
	pytest --cov

lint:  ## Check formatting and lint rules (CI runs this)
	black --check app tests
	ruff check app tests

format:  ## Auto-format and auto-fix lint issues
	black app tests
	ruff check --fix app tests
