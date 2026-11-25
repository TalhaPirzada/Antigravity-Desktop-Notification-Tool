"""Notification wording."""

from __future__ import annotations

from pathlib import Path

SUBTITLES = {
    "permission": "Permission Required",
    "input": "Input Needed",
    "complete": "Task Completed",
    "error": "Execution Error",
}


def with_workspace(text: str, workspace: str) -> str:
    """Append the workspace folder name to ``text`` when a workspace is given."""
    if not workspace:
        return text
    return f"{text} in [{Path(workspace).name}]"


def permission_message(tool_name: str, detail: str = "") -> str:
    """Return the body for a permission request."""
    if tool_name == "run_command":
        if detail:
            return f"Command requires approval: {detail}"
        return "A terminal command requires approval."
    suffix = f" ({detail})" if detail else ""
    return f"Tool '{tool_name}' requires approval.{suffix}"


def input_message(question: str = "") -> str:
    """Return the body for an input request."""
    if question:
        return f"Agent prompt: {question}"
    return "Agent is waiting for response."


def completed_message(summary: str = "") -> str:
    """Return the body for a completed task."""
    return summary or "All steps finished. Ready for review."


def error_message(error: str = "") -> str:
    """Return the body for an execution error."""
    if error:
        return f"Execution halted: {error}"
    return "Agent execution encountered an error."


def truncate(text: str, limit: int) -> str:
    """Shorten ``text`` to ``limit`` characters, marking the cut with an ellipsis."""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
