import json
import time
from pathlib import Path
from typing import Any, Dict, List
from .config import get_config_paths

MAX_HISTORY_ENTRIES = 500


def get_history_file() -> Path:
    cfg_dir, _ = get_config_paths()
    return cfg_dir / "history.jsonl"


def record_event(
    event_type: str,
    title: str,
    subtitle: str,
    message: str,
    workspace: str = "",
    delivered: bool = True,
    duration_ms: float = 0.0,
) -> None:
    """Appends an event to the local history ledger."""
    entry = {
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
        hfile = get_history_file()
        hfile.parent.mkdir(parents=True, exist_ok=True)
        with open(hfile, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def get_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves the most recent N events from history."""
    hfile = get_history_file()
    if not hfile.exists():
        return []

    entries: List[Dict[str, Any]] = []
    try:
        with open(hfile, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        return []

    return entries[-limit:]


def get_metrics() -> Dict[str, Any]:
    """Computes aggregate performance and event metrics."""
    hfile = get_history_file()
    if not hfile.exists():
        return {
            "total_events": 0,
            "delivered_events": 0,
            "delivery_rate_pct": 100.0,
            "by_type": {},
            "first_event": None,
            "last_event": None,
        }

    total = 0
    delivered = 0
    by_type: Dict[str, int] = {}
    first_ts = None
    last_ts = None

    try:
        with open(hfile, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    total += 1
                    if data.get("delivered", True):
                        delivered += 1
                    etype = data.get("event_type", "unknown")
                    by_type[etype] = by_type.get(etype, 0) + 1
                    ts = data.get("timestamp")
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts
                except Exception:
                    continue
    except Exception:
        pass

    rate = round((delivered / total * 100), 1) if total > 0 else 100.0

    return {
        "total_events": total,
        "delivered_events": delivered,
        "delivery_rate_pct": rate,
        "by_type": by_type,
        "first_event": first_ts,
        "last_event": last_ts,
    }
