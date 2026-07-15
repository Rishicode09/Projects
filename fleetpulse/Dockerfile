# Self-contained demo image: trains a model at build time so the container
# serves predictions immediately. In production the artifact would come from
# a model registry instead of being baked in.
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN fleetpulse generate --out /tmp/telemetry.csv \
    && fleetpulse train --data /tmp/telemetry.csv --out /app/artifacts \
    && rm /tmp/telemetry.csv

RUN useradd --create-home appuser
USER appuser

ENV FLEETPULSE_MODEL_DIR=/app/artifacts
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["fleetpulse", "serve", "--artifacts", "/app/artifacts"]
