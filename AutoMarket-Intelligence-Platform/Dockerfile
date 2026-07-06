# Single image that can run either the API or the dashboard (see docker-compose.yml).
FROM python:3.11-slim

WORKDIR /code

# Install dependencies first so Docker caches this layer between code changes.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY scripts ./scripts
COPY dashboard ./dashboard
COPY .streamlit ./.streamlit
COPY docker/entrypoint.sh ./docker/entrypoint.sh
RUN chmod +x docker/entrypoint.sh

EXPOSE 8000

# Seeds the database and trains the model on first start, then serves the API.
CMD ["./docker/entrypoint.sh"]
