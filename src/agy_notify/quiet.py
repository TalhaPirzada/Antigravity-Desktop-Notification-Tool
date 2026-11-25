"""Quiet-hours evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, time
from typing import Any


def _parse_clock(value: str) -> time:
    """Parse ``HH:MM`` into a ``time``; raise ``ValueError`` when malformed."""
    hours, minutes = (int(part) for part in value.split(":")[:2])
    return time(hours, minutes)


def _in_window(current: time, start: time, end: time) -> bool:
    """Return whether ``current`` lies in the window, which may span midnight."""
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def _current_clock(now: time | None) -> time:
    """Return ``now`` or the local wall-clock time when it is ``None``."""
    if now is None:
        return datetime.now().time()
    return now


def is_quiet_time(settings: Mapping[str, Any], now: time | None = None) -> bool:
    """Return whether quiet hours are enabled and currently active."""
    if not settings.get("enabled", False):
        return False
    try:
        start = _parse_clock(str(settings.get("start", "22:00")))
        end = _parse_clock(str(settings.get("end", "08:00")))
    except ValueError:
        return False
    return _in_window(_current_clock(now), start, end)
