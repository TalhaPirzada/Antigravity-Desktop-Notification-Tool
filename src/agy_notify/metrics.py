"""Notification history ledger and aggregate metrics."""

from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Any

from .config import get_config_paths
from .jsonio import append_jsonl, read_jsonl


def get_history_file() -> Path:
    """Return the path of the JSON-lines history ledger."""
    config_dir, _ = get_config_paths()
    return config_dir / "history.jsonl"


def record_event(
    event_type: str,
    title: str,
    subtitle: str,
    message: str,
    workspace: str = "",
    delivered: bool = True,
    duration_ms: float = 0.0,
) -> None:
    """Append one notification event to the history ledger."""
    entry: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
        "event_type": event_type,
        "title": title,
        "subtitle": subtitle,
        "message": message,
        "workspace": workspace,
        "delivered": delivered,
        "duration_ms": round(duration_ms, 2),
    }
    try:
        append_jsonl(get_history_file(), entry)
    except OSError:
        return


def get_history(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent ``limit`` events, oldest first."""
    return read_jsonl(get_history_file())[-limit:]


def _delivery_rate(delivered: int, total: int) -> float:
    """Return the delivery success percentage, defaulting to 100 when empty."""
    if total == 0:
        return 100.0
    return round(delivered / total * 100, 1)


def _edge_timestamp(entries: list[dict[str, Any]], index: int) -> str | None:
    """Return the timestamp of the entry at ``index`` or ``None`` if there are none."""
    if not entries:
        return None
    return str(entries[index].get("timestamp"))


def get_metrics() -> dict[str, Any]:
    """Compute aggregate event and delivery metrics from the history ledger."""
    entries = read_jsonl(get_history_file())
    delivered = sum(1 for entry in entries if entry.get("delivered", True))
    by_type = Counter(str(entry.get("event_type", "unknown")) for entry in entries)
    return {
        "total_events": len(entries),
        "delivered_events": delivered,
        "delivery_rate_pct": _delivery_rate(delivered, len(entries)),
        "by_type": dict(by_type),
        "first_event": _edge_timestamp(entries, 0),
        "last_event": _edge_timestamp(entries, -1),
    }
