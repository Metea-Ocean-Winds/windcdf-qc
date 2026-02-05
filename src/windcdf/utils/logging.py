"""Logging utilities."""

from __future__ import annotations

import logging
import sys


def setup_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
) -> None:
    """Configure logging for windcdf-qc.

    Args:
        level: Logging level.
        log_file: Optional file path for logging.
    """
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.

    Args:
        name: Logger name (usually __name__).

    Returns:
        Configured logger.
    """
    return logging.getLogger(f"windcdf.{name}")
