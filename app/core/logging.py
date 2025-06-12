"""Logging configuration for the application."""

import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Configure specific loggers
    loggers = {
        "uvicorn": {"level": log_level},
        "sqlalchemy.engine": {"level": logging.WARNING},
        "alembic": {"level": logging.INFO},
    }

    for logger_name, config in loggers.items():
        _configure_logger(logger_name, config)


def _configure_logger(name: str, config: dict[str, Any]) -> None:
    """Configure a specific logger with given settings."""
    logger = logging.getLogger(name)
    logger.setLevel(config.get("level", logging.INFO))
    # Add specific handlers if needed

    # Prevent propagation to root logger if desired
    logger.propagate = config.get("propagate", True)


# Initialize logging on module import
setup_logging()
