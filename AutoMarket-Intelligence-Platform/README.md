# AutoMarket Intelligence Platform

A used-car market analytics platform: browse and filter listings through a REST API,
explore market statistics on an interactive dashboard, and get ML-powered price estimates.

> 🚧 Built incrementally, module by module — see the build log below.

## The problem

Thousands of used cars are listed every day, but buyers and sellers have no easy way to
answer basic questions: *Is this car overpriced? What does a fair price look like for this
model, year and mileage? Which models hold their value?* This project collects listing data,
stores it in a database, analyses it, and trains a machine-learning model to estimate fair
prices.

## Tech stack

| Area | Tools |
|---|---|
| API | Python, FastAPI, Pydantic |
| Database | SQLite, SQLAlchemy |
| Data & ML | Pandas, scikit-learn |
| Dashboard | Streamlit, Plotly |
| Quality | pytest, black, ruff, GitHub Actions CI |

## Quickstart

```bash
cd AutoMarket-Intelligence-Platform
python -m venv .venv && source .venv/bin/activate
make install        # pip install -e ".[dev]"
make run            # API at http://localhost:8000/docs
make test           # run the test suite
make lint           # check formatting and lint rules
```

## Project layout

```
app/
├── main.py       # FastAPI app: wires everything together
├── config.py     # typed settings loaded from environment variables
└── routes/       # API endpoints, one file per feature
tests/            # pytest suite (runs in CI on every push)
```

Coming as the project grows: `app/database.py`, `app/models.py`, `app/schemas.py`,
`app/ml/` (model training and prediction) and `dashboard/` (Streamlit app).

## Build log

- [x] **Module 1 — Foundation**: FastAPI app, typed settings, health endpoint, tests, CI
- [ ] **Module 2 — Database & data**: SQLAlchemy model for listings, realistic seed dataset
- [ ] **Module 3 — Listings API**: browse, filter and paginate listings; market statistics endpoint
- [ ] **Module 4 — ML price prediction**: compare models, evaluate (MAE/R²), serve via the API
- [ ] **Module 5 — Streamlit dashboard**: market overview charts, listing explorer, price estimator
- [ ] **Module 6 — Polish**: README with screenshots, final test pass, stretch goals
