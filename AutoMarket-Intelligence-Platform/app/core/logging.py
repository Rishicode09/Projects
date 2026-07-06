"""Centralised logging configuration.

Two output modes:

* human-readable console lines for local development, and
* single-line JSON records for production, so log aggregators
  (CloudWatch, Loki, Datadog...) can index fields without regex parsing.

Modules obtain loggers with ``logging.getLogger(__name__)`` as usual; only the
root handler configuration lives here.
"""

import json
import logging
import logging.config
from datetime import UTC, datetime

from app.core.config import Settings


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON documents."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(settings: Settings) -> None:
    """Configure the root logger once at application startup."""
    formatter = "json" if settings.log_json else "console"
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                },
                "json": {"()": JsonFormatter},
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter,
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"level": settings.log_level, "handlers": ["default"]},
            "loggers": {
                # uvicorn installs its own handlers; route them through ours instead.
                "uvicorn": {"handlers": ["default"], "propagate": False},
                "uvicorn.access": {"handlers": ["default"], "propagate": False},
            },
        }
    )
