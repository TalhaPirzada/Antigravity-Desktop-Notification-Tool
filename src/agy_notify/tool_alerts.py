"""Translate agent tool calls into user alerts (shared by hooks and watcher)."""

from __future__ import annotations

from typing import Any

from .messages import truncate
from .notifier import Notifier

COMMAND_DETAIL_LIMIT = 60


def first_question(args: dict[str, Any]) -> str:
    """Extract the first question text from ``ask_question`` arguments."""
    questions = args.get("questions", [])
    if not isinstance(questions, list) or not questions:
        return ""
    first = questions[0]
    if isinstance(first, dict):
        return str(first.get("question", ""))
    return str(first)


def command_detail(args: dict[str, Any]) -> str:
    """Return a short description of a ``run_command`` call."""
    summary = str(args.get("toolSummary", ""))
    command = str(args.get("CommandLine", ""))
    return summary or truncate(command, COMMAND_DETAIL_LIMIT)


def _notify_run_command(
    notifier: Notifier, args: dict[str, Any], workspace: str, notify_all: bool
) -> bool:
    """Alert for a command that bypasses the sandbox (or for every command)."""
    if not (args.get("BypassSandbox", False) or notify_all):
        return False
    notifier.notify_permission_required(
        tool_name="run_command", detail=command_detail(args), workspace=workspace
    )
    return True


def notify_for_tool_call(
    notifier: Notifier,
    tool_name: str,
    args: dict[str, Any],
    workspace: str,
    notify_all: bool,
) -> bool:
    """Alert the user for ``tool_name`` when needed; return whether one was sent."""
    if tool_name == "ask_question":
        notifier.notify_input_needed(question=first_question(args), workspace=workspace)
        return True
    if tool_name == "run_command":
        return _notify_run_command(notifier, args, workspace, notify_all)
    if notify_all:
        detail = truncate(str(args), COMMAND_DETAIL_LIMIT)
        notifier.notify_permission_required(
            tool_name=tool_name, detail=detail, workspace=workspace
        )
        return True
    return False
