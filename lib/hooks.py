import json
import sys
from pathlib import Path
from typing import Any, Dict
from .notifier import Notifier
from .config import load_config


def handle_hook_event() -> None:
    """
    Antigravity Lifecycle Hook Handler.
    Receives JSON on stdin, evaluates event, sends notification, and responds on stdout.
    Always returns {"decision": "allow"} for PreToolUse to ensure tools are never blocked.
    """
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        print(json.dumps({"decision": "allow"}))
        return

    try:
        payload: Dict[str, Any] = json.loads(raw_input)
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return

    event_name = payload.get("hookEventName", "")
    workspace_paths = payload.get("workspacePaths", [])
    workspace = workspace_paths[0] if workspace_paths else payload.get("cwd", "")
    config = load_config()
    notifier = Notifier(config)

    # 1. PreToolUse: Agent is about to execute a tool (or prompt for permission/input)
    if event_name == "PreToolUse" or "toolCall" in payload:
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        # Scenario A: Agent asks a clarifying or multiple-choice question
        if tool_name == "ask_question":
            questions = args.get("questions", [])
            q_text = ""
            if isinstance(questions, list) and len(questions) > 0:
                first_q = questions[0]
                if isinstance(first_q, dict):
                    q_text = first_q.get("question", "")
                elif isinstance(first_q, str):
                    q_text = first_q
            notifier.notify_input_needed(question=q_text, workspace=workspace)

        # Scenario B: Command requiring elevated permission (BypassSandbox or permission gate)
        elif tool_name == "run_command":
            cmd_line = args.get("CommandLine", "")
            bypass = args.get("BypassSandbox", False)
            tool_summary = args.get("toolSummary", "")
            detail = tool_summary or (cmd_line[:60] + "..." if len(cmd_line) > 60 else cmd_line)

            if bypass or config.get("notify_on_all_commands", False):
                notifier.notify_permission_required(
                    tool_name="run_command",
                    detail=detail,
                    workspace=workspace,
                )

        # Scenario C: Other tools that could require approval
        elif config.get("notify_on_all_commands", False):
            notifier.notify_permission_required(
                tool_name=tool_name,
                detail=str(args)[:60],
                workspace=workspace,
            )

        # REQUIRED: In Antigravity PreToolUse, return {"decision": "allow"} so execution continues
        print(json.dumps({"decision": "allow"}))
        return

    # 2. Stop: Agent execution loop has terminated
    elif event_name == "Stop" or "terminationReason" in payload:
        term_reason = payload.get("terminationReason", "NO_TOOL_CALL")
        error_msg = payload.get("error", "")

        if term_reason == "NO_TOOL_CALL":
            last_user_input = payload.get("lastUserInput", "")
            summary = ""
            if last_user_input:
                short_input = (last_user_input[:40] + "...") if len(last_user_input) > 40 else last_user_input
                summary = f"Finished turn for: \"{short_input}\""
            notifier.notify_task_completed(summary=summary, workspace=workspace)

        elif term_reason == "ERROR":
            notifier.notify_error(error_msg=error_msg, workspace=workspace)

        elif term_reason in ("MAX_INVOCATIONS", "MAX_FORCED_INVOCATIONS"):
            notifier.notify_error(
                error_msg=f"Reached invocation step limit ({term_reason})",
                workspace=workspace,
            )

        print(json.dumps({}))
        return

    # 3. SessionStart or generic event
    elif event_name == "SessionStart":
        print(json.dumps({}))
        return

    # Default fallback
    print(json.dumps({"decision": "allow"}))
