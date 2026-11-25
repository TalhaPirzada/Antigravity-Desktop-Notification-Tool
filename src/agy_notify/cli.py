"""Command-line interface for ``agy-notify``."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .config import load_config, update_config_value
from .doctor import run_diagnostics
from .hooks import handle_hook_event
from .installer import check_status, install_hooks, uninstall_hooks
from .metrics import get_history, get_metrics
from .notifier import Notifier
from .watcher import TranscriptWatcher

BANNER = (
    "==================================================\n"
    "Antigravity Desktop Notifier (agy-notify)\n"
    "Event-driven lifecycle notifications for Antigravity\n"
    "=================================================="
)
TEST_PAUSE_SECONDS = 1.2
SOUND_SETTINGS = (
    ("Permission", "permission", "Ping"),
    ("Input", "input", "Glass"),
    ("Complete", "complete", "Hero"),
    ("Error", "error", "Basso"),
)
BOOLEANS = {"true": True, "false": False}

Handler = Callable[[argparse.Namespace], None]
TestCase = Callable[[Notifier, str], bool]


def _alert_permission(notifier: Notifier, workspace: str) -> bool:
    """Send a sample permission notification."""
    return notifier.notify_permission_required(
        tool_name="run_command",
        detail="npm run build --prod (Sandbox elevation)",
        workspace=workspace,
    )


def _alert_input(notifier: Notifier, workspace: str) -> bool:
    """Send a sample input-needed notification."""
    question = "Specify deployment target environment (staging / production):"
    return notifier.notify_input_needed(question=question, workspace=workspace)


def _alert_complete(notifier: Notifier, workspace: str) -> bool:
    """Send a sample task-completed notification."""
    summary = "Refactored middleware and completed test suite verification."
    return notifier.notify_task_completed(summary=summary, workspace=workspace)


def _alert_error(notifier: Notifier, workspace: str) -> bool:
    """Send a sample error notification."""
    error = "Command failed with exit code 127: binary not found in PATH"
    return notifier.notify_error(error_msg=error, workspace=workspace)


TEST_CASES: tuple[tuple[str, str, TestCase], ...] = (
    ("permission", "Permission Required", _alert_permission),
    ("input", "Input Needed", _alert_input),
    ("complete", "Task Completed", _alert_complete),
    ("error", "Execution Error", _alert_error),
)


def cmd_hook(_args: argparse.Namespace) -> None:
    """Run the Antigravity lifecycle hook handler."""
    handle_hook_event()


def cmd_test(args: argparse.Namespace) -> None:
    """Send sample notifications of the requested type."""
    target = args.type.lower()
    notifier = Notifier(load_config())
    workspace = str(Path.cwd())
    selected = [case for case in TEST_CASES if target in ("all", case[0])]
    print(f"Executing notification test: target='{target}'")
    for index, (_, label, alert) in enumerate(selected):
        print(f"[TEST] Dispatching: {label} notification...")
        alert(notifier, workspace)
        if index < len(selected) - 1:
            time.sleep(TEST_PAUSE_SECONDS)
    print("[SUCCESS] Test dispatch sequence completed.")


def cmd_install(args: argparse.Namespace) -> None:
    """Register the hook with Antigravity."""
    success, message = install_hooks(not args.workspace, str(Path.cwd()))
    print(message)
    if success:
        print("[OK] Lifecycle hooks registered.")
        print("Antigravity will now dispatch desktop notifications on lifecycle events.")


def cmd_uninstall(args: argparse.Namespace) -> None:
    """Remove the hook from Antigravity."""
    _, message = uninstall_hooks(not args.workspace, str(Path.cwd()))
    print(message)


def _yes_no(flag: object) -> str:
    """Render a boolean as ``YES`` or ``NO``."""
    return "YES" if flag else "NO"


def _enabled(flag: object) -> str:
    """Render a boolean as ``ENABLED`` or ``DISABLED``."""
    return "ENABLED" if flag else "DISABLED"


def _print_components(status: dict[str, Any]) -> None:
    """Print where the hook is installed."""
    print("\n[Component Status]")
    print(f"  CLI Binary:          {status['cli_path']}")
    print(f"  Platform:            {status['platform']}")
    print(f"  Global Configuration: {status['global_hooks_file']}")
    print(f"    Hook Installed:    {_yes_no(status['global_installed'])}")
    if status["global_hook_cmd"]:
        print(f"    Command:           {status['global_hook_cmd']}")
    print(f"  Workspace Hooks:     {status['workspace_hooks_file']}")
    print(f"    Hook Installed:    {_yes_no(status['workspace_installed'])}")


def _quiet_hours_label(settings: dict[str, Any]) -> str:
    """Describe the quiet-hours setting."""
    if not settings.get("enabled"):
        return "DISABLED"
    return f"ENABLED ({settings.get('start')} - {settings.get('end')})"


def _print_settings(config: dict[str, Any]) -> None:
    """Print the active configuration."""
    sounds = config.get("sounds", {})
    print("\n[Configuration]")
    print(f"  Notifications:       {_enabled(config.get('enabled'))}")
    print(f"  Audio Alerts:        {_enabled(config.get('sound_enabled'))}")
    for label, key, default in SOUND_SETTINGS:
        print(f"    {label} Sound:".ljust(24) + str(sounds.get(key, default)))
    print(f"  Voice Announcements: {_enabled(config.get('voice_enabled'))}")
    print(f"  Focus Window:        {_enabled(config.get('focus_window_on_alert'))}")
    print(f"  Cooldown Window:     {config.get('cooldown_seconds', 3)}s")
    print(f"  Quiet Hours:         {_quiet_hours_label(config.get('quiet_hours', {}))}")
    print(f"  Webhook Forwarding:  {config.get('webhook_url') or 'DISABLED'}")


def cmd_status(_args: argparse.Namespace) -> None:
    """Show installation status and configuration."""
    print(BANNER)
    _print_components(check_status(str(Path.cwd())))
    _print_settings(load_config())


def cmd_doctor(_args: argparse.Namespace) -> None:
    """Run diagnostics and print a summary."""
    print(BANNER)
    print("\nRunning system diagnostics...\n")
    results = run_diagnostics(str(Path.cwd()))
    for check, status, detail in results:
        print(f"{f'[{status}]'.ljust(8)} {check.ljust(26)} : {detail}")
    print("\n" + "=" * 50)
    if all(status == "PASS" for _, status, _ in results):
        print("Diagnostic summary: All checks passed. System ready for production.")
    else:
        print("Diagnostic summary: Review warnings/failures listed above.")


def cmd_metrics(_args: argparse.Namespace) -> None:
    """Display aggregate delivery metrics."""
    metrics = get_metrics()
    print(BANNER)
    print("\n[Delivery Metrics]")
    print(f"  Total Notifications: {metrics['total_events']}")
    print(f"  Successfully Sent:   {metrics['delivered_events']}")
    print(f"  Delivery Success:    {metrics['delivery_rate_pct']}%")
    print(f"  First Recorded:      {metrics['first_event'] or 'N/A'}")
    print(f"  Last Recorded:       {metrics['last_event'] or 'N/A'}")
    print("\n[Breakdown by Event Type]")
    if not metrics["by_type"]:
        print("  No events recorded yet.")
    for event_type, count in sorted(metrics["by_type"].items()):
        print(f"  - {event_type.ljust(22)}: {count}")


def _history_row(entry: dict[str, Any]) -> str:
    """Format one history entry as a table row."""
    subtitle = entry.get("subtitle", "")
    message = entry.get("message", "")
    summary = f"{subtitle}: {message}" if subtitle else message
    if len(summary) > 40:
        summary = summary[:37] + "..."
    stamp = str(entry.get("timestamp", "")).ljust(20)
    kind = str(entry.get("event_type", "")).ljust(15)
    latency = f"{entry.get('duration_ms', 0):.1f}ms".ljust(10)
    return f"{stamp} {kind} {latency} {summary}"


def cmd_history(args: argparse.Namespace) -> None:
    """Display recent notification history."""
    entries = get_history(limit=args.limit)
    print(BANNER)
    print(f"\n[Recent Event History (last {len(entries)} entries)]\n")
    if not entries:
        print("No history entries found.")
        return
    print(f"{'TIMESTAMP'.ljust(20)} {'TYPE'.ljust(15)} {'LATENCY'.ljust(10)} MESSAGE")
    print("-" * 75)
    for entry in entries:
        print(_history_row(entry))


def _coerce(raw: str) -> bool | int | str:
    """Convert a command-line string into a boolean, integer or string."""
    lowered = raw.lower()
    if lowered in BOOLEANS:
        return BOOLEANS[lowered]
    if raw.isdigit():
        return int(raw)
    return raw


def _config_list(config: dict[str, Any], _key: str | None, _value: str | None) -> None:
    """Print the whole configuration."""
    print(json.dumps(config, indent=2))


def _config_get(config: dict[str, Any], key: str | None, _value: str | None) -> None:
    """Print one configuration value."""
    if not key:
        print("Error: Missing key name, e.g. `agy-notify config get sound_enabled`")
        return
    print(f"{key} = {config.get(key)}")


def _config_set(_config: dict[str, Any], key: str | None, value: str | None) -> None:
    """Update one configuration value."""
    if not key or value is None:
        print("Error: Missing key or value, e.g. `agy-notify config set voice_enabled true`")
        return
    coerced = _coerce(value)
    update_config_value(key, coerced)
    print(f"[OK] Configuration updated: {key} = {coerced}")


CONFIG_ACTIONS: dict[str, Callable[[dict[str, Any], str | None, str | None], None]] = {
    "list": _config_list,
    "get": _config_get,
    "set": _config_set,
}


def cmd_config(args: argparse.Namespace) -> None:
    """Get, set or list configuration values."""
    CONFIG_ACTIONS[args.action or "list"](load_config(), args.key, args.val)


def cmd_watch(args: argparse.Namespace) -> None:
    """Run the transcript watcher."""
    TranscriptWatcher().watch_loop(poll_interval=args.interval)


COMMANDS: dict[str, Handler] = {
    "hook": cmd_hook,
    "test": cmd_test,
    "doctor": cmd_doctor,
    "metrics": cmd_metrics,
    "history": cmd_history,
    "install": cmd_install,
    "uninstall": cmd_uninstall,
    "status": cmd_status,
    "config": cmd_config,
    "watch": cmd_watch,
}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all sub-commands."""
    parser = argparse.ArgumentParser(
        description="Antigravity Desktop Notifier: Cross-platform lifecycle notifications."
    )
    commands = parser.add_subparsers(dest="command", help="Command to run")
    commands.add_parser("hook", help="Antigravity lifecycle hook runner (invoked by IDE)")
    test = commands.add_parser("test", help="Test desktop notifications and sounds")
    test.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=[name for name, _, _ in TEST_CASES] + ["all"],
        help="Type of notification to test",
    )
    commands.add_parser("doctor", help="Run system diagnostics and health checks")
    commands.add_parser("metrics", help="Display notification delivery metrics")
    history = commands.add_parser("history", help="Show recent notification history")
    history.add_argument("--limit", type=int, default=15, help="Number of records")
    for name, verb in (("install", "Install hooks into"), ("uninstall", "Remove hooks from")):
        sub = commands.add_parser(name, help=f"{verb} Antigravity configuration")
        sub.add_argument("--workspace", action="store_true", help="Use workspace scope")
    commands.add_parser("status", help="Show installation and configuration status")
    config = commands.add_parser("config", help="Manage configuration options")
    config.add_argument("action", nargs="?", default="list", choices=sorted(CONFIG_ACTIONS))
    config.add_argument("key", nargs="?", help="Configuration key (e.g. sounds.permission)")
    config.add_argument("val", nargs="?", help="Configuration value")
    watch = commands.add_parser("watch", help="Watch active conversation transcripts")
    watch.add_argument("--interval", type=float, default=1.0, help="Polling seconds")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Parse ``argv`` and run the selected command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = COMMANDS.get(args.command)
    if handler is None:
        print(BANNER)
        parser.print_help()
        return
    handler(args)
