# AutoMarket Intelligence Platform

Market analytics, ML price prediction and an AI market analyst for the used-car market.

> 🚧 Under active development, built module by module. This README will grow with the project.

## Why

Thousands of used-car listings appear daily, but buyers and sellers have no intelligent way to
answer: *Is this car overpriced? How fast will it depreciate? How long will it take to sell?
When is the best time to buy?* This platform collects listing data, runs it through an ETL
pipeline, and serves analytics, ML predictions and RAG-grounded AI recommendations on top.

## Tech stack

FastAPI · PostgreSQL · SQLAlchemy · Alembic · Redis · Celery · Docker ·
Pandas · Scikit-Learn · XGBoost · LightGBM · Prophet · LangChain · FAISS · Streamlit

## Quickstart (current state)

```bash
cd AutoMarket-Intelligence-Platform
python -m venv .venv && source .venv/bin/activate
make install          # pip install -e ".[dev]"
cp .env.example .env
make run              # http://localhost:8000/docs
make test             # unit tests
make lint             # black + ruff
```

## Project layout

```
app/
├── main.py          # FastAPI application factory
├── core/            # config, logging, exceptions (cross-cutting)
├── api/v1/          # HTTP layer, versioned routers
├── schemas/         # Pydantic request/response contracts
├── models/          # SQLAlchemy ORM models
├── repositories/    # all database access (Repository pattern)
├── services/        # business logic
├── ml/              # training, registry, inference
├── analytics/       # market statistics & aggregations
├── workers/         # Celery background jobs (scraping, ETL, retraining)
└── utils/           # shared helpers
tests/               # unit + integration suites
data/                # raw / processed datasets (git-ignored)
docs/                # architecture docs & diagrams
```

## Build log

- [x] **Module 1 — Foundation**: app factory, typed settings, logging, error hierarchy, health endpoint, tooling (black/ruff/pytest), CI
- [ ] Module 2 — Database schema & migrations
- [ ] Module 3 — Repository + service layers
- [ ] Module 4 — Authentication (JWT)
- [ ] Module 5 — Core listings API
- [ ] Module 6 — Data collection pipelines
- [ ] Module 7 — ETL & feature engineering
- [ ] Module 8 — Analytics engine
- [ ] Module 9 — ML models & evaluation
- [ ] Module 10 — Forecasting & anomaly detection
- [ ] Module 11 — AI market analyst (RAG)
- [ ] Module 12 — Streamlit dashboard
- [ ] Module 13 — Caching, rate limiting, hardening
- [ ] Module 14 — Docker & deployment
- [ ] Module 15 — Documentation & diagrams
