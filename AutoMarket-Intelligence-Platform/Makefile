.PHONY: install run test test-cov lint format

install:  ## Install the app with dev dependencies
	pip install -e ".[dev]"

run:  ## Run the API locally with hot reload
	uvicorn app.main:app --reload --port 8000

test:  ## Run the fast unit test suite
	pytest -m unit

test-cov:  ## Run all tests with a coverage report
	pytest --cov

lint:  ## Check formatting and lint rules (CI runs this)
	black --check app tests
	ruff check app tests

format:  ## Auto-format and auto-fix lint issues
	black app tests
	ruff check --fix app tests
