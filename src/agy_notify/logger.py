"""Rotating file logger."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import get_config_paths

LOGGER_NAME = "antigravity_notifier"
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _attach_file_handler(logger: logging.Logger, level: int) -> None:
    """Attach a size-rotating file handler when the log directory is writable."""
    try:
        log_dir, _ = get_config_paths()
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "notifier.log",
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError:
        return
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    handler.setLevel(level)
    logger.addHandler(handler)


def get_logger(level: str | None = None) -> logging.Logger:
    """Return the configured package logger, creating handlers on first use."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)
    logger.propagate = False
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    console.setLevel(logging.WARNING)
    logger.addHandler(console)
    _attach_file_handler(logger, log_level)
    return logger
