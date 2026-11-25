"""Duplicate-notification suppression using a short-lived cache file."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

SEPARATOR = ":::"


def default_cache_path() -> Path:
    """Return the location of the last-notification cache file."""
    return Path(tempfile.gettempdir()) / ".agy_notifier_last_notification"


def _read_last(cache: Path) -> tuple[float, str] | None:
    """Return ``(timestamp, message)`` of the last notification, if recorded."""
    try:
        content = cache.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    stamp, separator, message = content.partition(SEPARATOR)
    if not separator:
        return None
    try:
        return float(stamp), message
    except ValueError:
        return None


def _write_last(cache: Path, stamp: float, message: str) -> None:
    """Record the last notification, ignoring storage failures."""
    try:
        cache.write_text(f"{stamp}{SEPARATOR}{message}", encoding="utf-8")
    except OSError:
        return


def _is_recent(
    last: tuple[float, str] | None, message: str, now: float, cooldown: float
) -> bool:
    """Return whether ``message`` repeats the last one within ``cooldown`` seconds."""
    if last is None:
        return False
    stamp, saved = last
    return saved == message and now - stamp < cooldown


def _current_time(now: float | None) -> float:
    """Return ``now`` or the wall clock when it is ``None``."""
    if now is None:
        return time.time()
    return now


def is_duplicate(
    message: str,
    cooldown: float,
    cache: Path | None = None,
    now: float | None = None,
) -> bool:
    """Return whether ``message`` should be suppressed as a recent duplicate."""
    if cooldown <= 0:
        return False
    cache_path = cache or default_cache_path()
    current = _current_time(now)
    duplicate = _is_recent(_read_last(cache_path), message, current, cooldown)
    if not duplicate:
        _write_last(cache_path, current, message)
    return duplicate
