"""Antigravity lifecycle hook handler (``PreToolUse`` and ``Stop`` events)."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from .config import load_config
from .messages import truncate
from .notifier import Notifier
from .tool_alerts import notify_for_tool_call

ALLOW: dict[str, Any] = {"decision": "allow"}
LIMIT_REASONS = ("MAX_INVOCATIONS", "MAX_FORCED_INVOCATIONS")
SUMMARY_INPUT_LIMIT = 40


def _read_payload() -> dict[str, Any] | None:
    """Read the hook payload from stdin; return ``None`` when empty or invalid."""
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if isinstance(data, dict):
        return data
    return None


def _matches(payload: dict[str, Any], event: str, marker: str) -> bool:
    """Return whether ``payload`` is the ``event`` hook or carries ``marker``."""
    return payload.get("hookEventName") == event or marker in payload


def classify_event(payload: dict[str, Any]) -> str:
    """Return the hook kind: ``pre_tool``, ``stop``, ``session_start`` or ``other``."""
    if _matches(payload, "PreToolUse", "toolCall"):
        return "pre_tool"
    if _matches(payload, "Stop", "terminationReason"):
        return "stop"
    if payload.get("hookEventName") == "SessionStart":
        return "session_start"
    return "other"


def _workspace(payload: dict[str, Any]) -> str:
    """Return the first workspace path, falling back to the working directory."""
    paths = payload.get("workspacePaths") or []
    if paths:
        return str(paths[0])
    return str(payload.get("cwd", ""))


def _handle_pre_tool_use(payload: dict[str, Any]) -> None:
    """Alert when the pending tool call needs the user's attention."""
    config = load_config()
    call = payload.get("toolCall", {})
    notify_for_tool_call(
        Notifier(config),
        str(call.get("name", "")),
        call.get("args", {}),
        _workspace(payload),
        bool(config.get("notify_on_all_commands", False)),
    )


def _completion_summary(payload: dict[str, Any]) -> str:
    """Describe the finished turn using the last user input."""
    last_input = str(payload.get("lastUserInput", ""))
    if not last_input:
        return ""
    return f'Finished turn for: "{truncate(last_input, SUMMARY_INPUT_LIMIT)}"'


def _handle_stop(payload: dict[str, Any]) -> None:
    """Alert when the agent loop terminates."""
    notifier = Notifier(load_config())
    reason = payload.get("terminationReason", "NO_TOOL_CALL")
    workspace = _workspace(payload)
    if reason == "NO_TOOL_CALL":
        notifier.notify_task_completed(_completion_summary(payload), workspace)
    elif reason == "ERROR":
        notifier.notify_error(str(payload.get("error", "")), workspace)
    elif reason in LIMIT_REASONS:
        message = f"Reached invocation step limit ({reason})"
        notifier.notify_error(message, workspace)


HANDLERS: dict[str, Callable[[dict[str, Any]], None]] = {
    "pre_tool": _handle_pre_tool_use,
    "stop": _handle_stop,
}
RESPONSES: dict[str, dict[str, Any]] = {
    "pre_tool": ALLOW,
    "stop": {},
    "session_start": {},
    "other": ALLOW,
}


def handle_hook_event() -> None:
    """Read one hook event from stdin, alert if needed, and answer on stdout."""
    payload = _read_payload()
    if payload is None:
        print(json.dumps(ALLOW))
        return
    kind = classify_event(payload)
    handler = HANDLERS.get(kind)
    if handler:
        handler(payload)
    print(json.dumps(RESPONSES[kind]))
