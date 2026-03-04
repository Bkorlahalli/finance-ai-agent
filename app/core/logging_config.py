"""
Logging configuration module.

Sets up structured logging with rich formatting for development
and JSON formatting for production environments.
"""

import logging
import sys
from typing import Optional

from rich.logging import RichHandler

from app.core.config import get_settings


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        level: Override log level. If None, uses config setting.

    Returns:
        Root application logger.
    """
    settings = get_settings()
    log_level = level or settings.log_level

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler with rich formatting
    console_handler = RichHandler(
        level=log_level,
        rich_tracebacks=True,
        tracebacks_show_locals=settings.debug,
        show_time=False,  # RichHandler has its own time format
        show_path=settings.debug,
    )

    # File handler for persistent logs
    file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # Configure root logger
    root_logger = logging.getLogger("finance_agent")
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    for noisy_logger in ["httpx", "httpcore", "openai", "urllib3", "sqlalchemy.engine"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    root_logger.info("Logging initialized at level: %s", log_level)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger under the application namespace.

    Args:
        name: Logger name (typically module name).

    Returns:
        Named logger instance.
    """
    return logging.getLogger(f"finance_agent.{name}")
