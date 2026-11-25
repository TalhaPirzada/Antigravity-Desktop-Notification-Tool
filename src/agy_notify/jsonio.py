"""Small JSON and JSON-lines persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_dict(path: Path) -> dict[str, Any]:
    """Read a JSON object from ``path``; return ``{}`` if unreadable or not an object."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(data, dict):
        return data
    return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` as indented JSON, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _parse_line(line: str) -> dict[str, Any] | None:
    """Parse one JSON-lines record, returning ``None`` for invalid lines."""
    try:
        data = json.loads(line)
    except ValueError:
        return None
    if isinstance(data, dict):
        return data
    return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read all valid JSON-object lines from ``path``."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    parsed = (_parse_line(line) for line in text.splitlines())
    return [entry for entry in parsed if entry is not None]


def append_jsonl(path: Path, entry: dict[str, Any]) -> None:
    """Append ``entry`` as one JSON line, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry) + "\n")
