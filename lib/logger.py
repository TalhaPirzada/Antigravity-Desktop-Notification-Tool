import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from .config import get_config_paths

LOGGER_NAME = "antigravity_notifier"
MAX_BYTES = 2 * 1024 * 1024  # 2 MB
BACKUP_COUNT = 3


def get_logger(level: Optional[str] = None) -> logging.Logger:
    """Returns a configured rotating logger for antigravity-notifier."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    logger.addHandler(console_handler)

    # File handler with rotation
    try:
        log_dir, _ = get_config_paths()
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "notifier.log",
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    except Exception:
        pass

    return logger
