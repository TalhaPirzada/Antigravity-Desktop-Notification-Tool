import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from lib.config import load_config, save_config, update_config_value
from lib.doctor import run_diagnostics
from lib.hooks import handle_hook_event
from lib.installer import check_status, get_hook_entry
from lib.metrics import get_history, get_metrics, record_event
from lib.notifier import Notifier


def test_config():
    print("Testing config module...")
    cfg = load_config()
    assert "sounds" in cfg
    assert cfg["sounds"]["complete"] == "Hero"
    print("[PASS] Config defaults verified")


def test_hook_entry():
    print("Testing hook entry generator...")
    entry = get_hook_entry("/usr/local/bin/agy-notify")
    assert entry["enabled"] is True
    assert "PreToolUse" in entry
    assert "Stop" in entry
    print("[PASS] Hook entry structure verified")


@patch("lib.hooks.Notifier")
def test_pre_tool_use_ask_question(mock_notifier_cls):
    print("Testing PreToolUse hook on ask_question...")
    mock_instance = MagicMock()
    mock_notifier_cls.return_value = mock_instance

    payload = {
        "hookEventName": "PreToolUse",
        "toolCall": {
            "name": "ask_question",
            "args": {
                "questions": [{"question": "Would you like to deploy to staging or prod?"}]
            }
        },
        "cwd": "/test/workspace"
    }

    stdin_backup = sys.stdin
    stdout_backup = sys.stdout
    sys.stdin = io.StringIO(json.dumps(payload))
    sys.stdout = io.StringIO()

    try:
        handle_hook_event()
        output = sys.stdout.getvalue().strip()
        resp = json.loads(output)
        assert resp == {"decision": "allow"}
        mock_instance.notify_input_needed.assert_called_once()
        args, kwargs = mock_instance.notify_input_needed.call_args
        assert "staging or prod" in kwargs["question"]
        print("[PASS] PreToolUse correctly intercepted ask_question, notified user, and allowed continuation")
    finally:
        sys.stdin = stdin_backup
        sys.stdout = stdout_backup


@patch("lib.hooks.Notifier")
def test_pre_tool_use_permission(mock_notifier_cls):
    print("Testing PreToolUse hook on command requiring permission...")
    mock_instance = MagicMock()
    mock_notifier_cls.return_value = mock_instance

    payload = {
        "hookEventName": "PreToolUse",
        "toolCall": {
            "name": "run_command",
            "args": {
                "CommandLine": "rm -rf build/",
                "BypassSandbox": True,
                "toolSummary": "Clean build directory"
            }
        },
        "cwd": "/test/workspace"
    }

    stdin_backup = sys.stdin
    stdout_backup = sys.stdout
    sys.stdin = io.StringIO(json.dumps(payload))
    sys.stdout = io.StringIO()

    try:
        handle_hook_event()
        output = sys.stdout.getvalue().strip()
        resp = json.loads(output)
        assert resp == {"decision": "allow"}
        mock_instance.notify_permission_required.assert_called_once()
        args, kwargs = mock_instance.notify_permission_required.call_args
        assert kwargs["tool_name"] == "run_command"
        assert kwargs["detail"] == "Clean build directory"
        print("[PASS] PreToolUse correctly intercepted permission-required command")
    finally:
        sys.stdin = stdin_backup
        sys.stdout = stdout_backup


@patch("lib.hooks.Notifier")
def test_stop_hook_task_completion(mock_notifier_cls):
    print("Testing Stop hook on task completion...")
    mock_instance = MagicMock()
    mock_notifier_cls.return_value = mock_instance

    payload = {
        "hookEventName": "Stop",
        "terminationReason": "NO_TOOL_CALL",
        "lastUserInput": "Build the new authentication flow",
        "cwd": "/test/workspace"
    }

    stdin_backup = sys.stdin
    stdout_backup = sys.stdout
    sys.stdin = io.StringIO(json.dumps(payload))
    sys.stdout = io.StringIO()

    try:
        handle_hook_event()
        output = sys.stdout.getvalue().strip()
        resp = json.loads(output)
        assert resp == {}
        mock_instance.notify_task_completed.assert_called_once()
        print("[PASS] Stop hook correctly intercepted task completion and notified user")
    finally:
        sys.stdin = stdin_backup
        sys.stdout = stdout_backup


def test_doctor_diagnostics():
    print("Testing doctor diagnostics...")
    res = run_diagnostics()
    assert len(res) >= 5
    print("[PASS] System diagnostics executed successfully")


def test_metrics_and_history():
    print("Testing metrics and history tracking...")
    record_event("test_event", "Title", "Sub", "Msg", "/test", True, 12.5)
    hist = get_history(limit=5)
    assert len(hist) > 0
    metrics = get_metrics()
    assert metrics["total_events"] > 0
    print("[PASS] Metrics and audit ledger verified")


if __name__ == "__main__":
    test_config()
    test_hook_entry()
    test_pre_tool_use_ask_question()
    test_pre_tool_use_permission()
    test_stop_hook_task_completion()
    test_doctor_diagnostics()
    test_metrics_and_history()
    print("\nALL TEST SUITES PASSED SUCCESSFULLY.")
