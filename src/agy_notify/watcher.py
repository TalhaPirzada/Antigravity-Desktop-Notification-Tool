"""Fallback monitor that tails Antigravity conversation transcripts."""

from __future__ import annotations

import glob
import json
import os
import time
from pathlib import Path
from typing import Any

from .config import load_config
from .notifier import Notifier
from .tool_alerts import notify_for_tool_call

TRANSCRIPT_PATTERNS = (
    (".system_generated", "logs", "transcript.jsonl"),
    ("transcript.jsonl",),
)
MAX_WATCHED_FILES = 3
MIN_COMPLETION_CHARS = 10


def _mtime(path: str) -> float:
    """Return the modification time of ``path`` or ``0`` if it vanished."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _parse_record(line: str) -> dict[str, Any] | None:
    """Parse one transcript line into a record, or ``None`` if invalid."""
    try:
        record = json.loads(line)
    except ValueError:
        return None
    if isinstance(record, dict):
        return record
    return None


def _is_completion(record: dict[str, Any]) -> bool:
    """Return whether ``record`` is a finished model reply with real content."""
    content = str(record.get("content", "")).strip()
    done = record.get("source") == "MODEL" and record.get("status") == "DONE"
    return done and len(content) > MIN_COMPLETION_CHARS


class TranscriptWatcher:
    """Poll transcripts and alert on questions, approvals and completions."""

    def __init__(self, base_brain_dir: str | None = None) -> None:
        """Watch ``base_brain_dir`` (default: the Antigravity ``brain`` directory)."""
        self.config = load_config()
        self.notifier = Notifier(self.config)
        default = Path.home() / ".gemini" / "antigravity" / "brain"
        self.base_dir = Path(base_brain_dir) if base_brain_dir else default
        self.file_offsets: dict[str, int] = {}
        self.notified_steps: set[str] = set()

    def find_transcripts(self) -> list[str]:
        """Return transcript files, most recently modified first."""
        files: list[str] = []
        for parts in TRANSCRIPT_PATTERNS:
            files.extend(glob.glob(str(self.base_dir.joinpath("*", *parts))))
        return sorted(files, key=_mtime, reverse=True)

    def _alert_for_tools(self, tool_calls: list[dict[str, Any]]) -> bool:
        """Alert for the first tool call that needs attention."""
        notify_all = bool(self.config.get("notify_on_all_commands", False))
        for call in tool_calls:
            name = str(call.get("name", ""))
            if notify_for_tool_call(
                self.notifier, name, call.get("args", {}), "", notify_all
            ):
                return True
        return False

    def _alert_for_record(self, record: dict[str, Any]) -> bool:
        """Alert for ``record`` and return whether an alert was sent."""
        tool_calls = record.get("tool_calls", [])
        if tool_calls:
            return self._alert_for_tools(tool_calls)
        if _is_completion(record):
            self.notifier.notify_task_completed(summary="Agent completed response.")
            return True
        return False

    def process_line(self, line: str, file_path: str) -> None:
        """Handle one transcript line, alerting at most once per step."""
        record = _parse_record(line)
        if record is None:
            return
        step = record.get("step_index", 0)
        key = f"{file_path}:{step}:{record.get('status', '')}"
        if key in self.notified_steps:
            return
        if self._alert_for_record(record):
            self.notified_steps.add(key)

    def _consume(self, path: str, offset: int) -> int:
        """Process lines appended after ``offset``; return the new offset."""
        with open(path, "rb") as stream:
            stream.seek(offset)
            data = stream.read()
        for line in data.decode("utf-8", "ignore").splitlines():
            if line.strip():
                self.process_line(line, path)
        return offset + len(data)

    def _poll_file(self, path: str) -> None:
        """Read new content from ``path``, tracking its offset."""
        size = os.path.getsize(path)
        offset = self.file_offsets.setdefault(path, size)
        if size > offset:
            self.file_offsets[path] = self._consume(path, offset)
        elif size < offset:
            self.file_offsets[path] = 0

    def poll_once(self) -> None:
        """Poll the most recently modified transcripts once."""
        for path in self.find_transcripts()[:MAX_WATCHED_FILES]:
            self._poll_file(path)

    def watch_loop(self, poll_interval: float = 1.0) -> None:
        """Poll until interrupted."""
        print(f"Monitoring Antigravity brain transcripts in: {self.base_dir}")
        print("Press Ctrl+C to terminate.")
        while True:
            try:
                self.poll_once()
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                print("\nMonitoring stopped.")
                break
            except OSError:
                time.sleep(poll_interval)
