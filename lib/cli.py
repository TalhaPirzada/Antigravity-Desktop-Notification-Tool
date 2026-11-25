import argparse
import json
import os
import sys
import time
from pathlib import Path

from lib.config import DEFAULT_CONFIG, load_config, save_config, update_config_value
from lib.doctor import run_diagnostics
from lib.hooks import handle_hook_event
from lib.installer import check_status, install_hooks, uninstall_hooks
from lib.metrics import get_history, get_metrics
from lib.notifier import Notifier
from lib.watcher import TranscriptWatcher


def print_banner():
    banner = """==================================================
Antigravity Desktop Notifier (agy-notify)
Event-driven lifecycle notifications for Antigravity
=================================================="""
    print(banner)


def cmd_test(args):
    """Test desktop notifications and sounds."""
    config = load_config()
    notifier = Notifier(config)
    target = args.type.lower()

    print(f"Executing notification test: target='{target}'")

    if target in ("permission", "all"):
        print("[TEST] Dispatching: Permission Required notification...")
        notifier.notify_permission_required(
            tool_name="run_command",
            detail="npm run build --prod (Sandbox elevation)",
            workspace=str(Path.cwd()),
        )
        if target == "all":
            time.sleep(1.2)

    if target in ("input", "all"):
        print("[TEST] Dispatching: Input Needed notification...")
        notifier.notify_input_needed(
            question="Specify deployment target environment (staging / production):",
            workspace=str(Path.cwd()),
        )
        if target == "all":
            time.sleep(1.2)

    if target in ("complete", "all"):
        print("[TEST] Dispatching: Task Completed notification...")
        notifier.notify_task_completed(
            summary="Refactored middleware and completed test suite verification.",
            workspace=str(Path.cwd()),
        )
        if target == "all":
            time.sleep(1.2)

    if target in ("error", "all"):
        print("[TEST] Dispatching: Execution Error notification...")
        notifier.notify_error(
            error_msg="Command failed with exit code 127: binary not found in PATH",
            workspace=str(Path.cwd()),
        )

    print("[SUCCESS] Test dispatch sequence completed.")


def cmd_install(args):
    """Install hooks into Antigravity hooks.json."""
    is_global = not args.workspace
    success, message = install_hooks(is_global=is_global, workspace_path=str(Path.cwd()))
    print(message)
    if success:
        print("[OK] Lifecycle hooks registered.")
        print("Antigravity will now dispatch desktop notifications on permissions, inputs, and completions.")


def cmd_uninstall(args):
    """Uninstall hooks from Antigravity hooks.json."""
    is_global = not args.workspace
    success, message = uninstall_hooks(is_global=is_global, workspace_path=str(Path.cwd()))
    print(message)


def cmd_status(args):
    """Show installation status and current configuration."""
    print_banner()
    status = check_status(str(Path.cwd()))
    cfg = load_config()

    print("\n[Component Status]")
    print(f"  CLI Binary:          {status['cli_path']}")
    print(f"  Platform:            {status['platform']}")
    print(f"  Global Configuration: {status['global_hooks_file']}")
    print(f"    Hook Installed:    {'YES' if status['global_installed'] else 'NO'}")
    if status['global_hook_cmd']:
        print(f"    Command:           {status['global_hook_cmd']}")
    print(f"  Workspace Hooks:     {status['workspace_hooks_file']}")
    print(f"    Hook Installed:    {'YES' if status['workspace_installed'] else 'NO'}")

    print("\n[Configuration]")
    print(f"  Notifications:       {'ENABLED' if cfg.get('enabled') else 'DISABLED'}")
    print(f"  Audio Alerts:        {'ENABLED' if cfg.get('sound_enabled') else 'DISABLED'}")
    sounds = cfg.get("sounds", {})
    print(f"    Permission Sound:  {sounds.get('permission', 'Ping')}")
    print(f"    Input Sound:       {sounds.get('input', 'Glass')}")
    print(f"    Complete Sound:    {sounds.get('complete', 'Hero')}")
    print(f"    Error Sound:       {sounds.get('error', 'Basso')}")
    print(f"  Voice Announcements: {'ENABLED' if cfg.get('voice_enabled') else 'DISABLED'}")
    print(f"  Focus Window:        {'ENABLED' if cfg.get('focus_window_on_alert') else 'DISABLED'}")
    print(f"  Cooldown Window:     {cfg.get('cooldown_seconds', 3)}s")

    qh = cfg.get("quiet_hours", {})
    qh_status = f"ENABLED ({qh.get('start', '22:00')} - {qh.get('end', '08:00')})" if qh.get("enabled") else "DISABLED"
    print(f"  Quiet Hours:         {qh_status}")

    webhook = cfg.get("webhook_url")
    print(f"  Webhook Forwarding:  {webhook if webhook else 'DISABLED'}")


def cmd_doctor(args):
    """Run diagnostic checks."""
    print_banner()
    print("\nRunning system diagnostics...\n")
    results = run_diagnostics(str(Path.cwd()))

    for check, status, detail in results:
        tag = f"[{status}]".ljust(8)
        print(f"{tag} {check.ljust(26)} : {detail}")

    all_passed = all(status == "PASS" for _, status, _ in results)
    print("\n" + ("=" * 50))
    if all_passed:
        print("Diagnostic summary: All checks passed. System ready for production.")
    else:
        print("Diagnostic summary: Review warnings/failures listed above.")


def cmd_metrics(args):
    """Display notification metrics."""
    metrics = get_metrics()
    print_banner()
    print("\n[Delivery Metrics]")
    print(f"  Total Notifications: {metrics['total_events']}")
    print(f"  Successfully Sent:   {metrics['delivered_events']}")
    print(f"  Delivery Success:    {metrics['delivery_rate_pct']}%")
    print(f"  First Recorded:      {metrics['first_event'] or 'N/A'}")
    print(f"  Last Recorded:       {metrics['last_event'] or 'N/A'}")

    print("\n[Breakdown by Event Type]")
    by_type = metrics.get("by_type", {})
    if by_type:
        for etype, count in sorted(by_type.items()):
            print(f"  - {etype.ljust(22)}: {count}")
    else:
        print("  No events recorded yet.")


def cmd_history(args):
    """Display recent notification history."""
    entries = get_history(limit=args.limit)
    print_banner()
    print(f"\n[Recent Event History (last {len(entries)} entries)]\n")

    if not entries:
        print("No history entries found.")
        return

    header = f"{'TIMESTAMP'.ljust(20)} {'TYPE'.ljust(15)} {'LATENCY'.ljust(10)} {'MESSAGE'}"
    print(header)
    print("-" * 75)
    for e in entries:
        ts = e.get("timestamp", "").ljust(20)
        etype = e.get("event_type", "").ljust(15)
        lat = f"{e.get('duration_ms', 0):.1f}ms".ljust(10)
        sub = e.get("subtitle", "")
        msg = e.get("message", "")
        summary = f"{sub}: {msg}" if sub else msg
        if len(summary) > 40:
            summary = summary[:37] + "..."
        print(f"{ts} {etype} {lat} {summary}")


def cmd_config(args):
    """Get, set or view config parameters."""
    cfg = load_config()

    if args.action == "list" or not args.action:
        print(json.dumps(cfg, indent=2))
    elif args.action == "get":
        if not args.key:
            print("Error: Missing key name, e.g. `agy-notify config get sound_enabled`")
            return
        val = cfg.get(args.key)
        print(f"{args.key} = {val}")
    elif args.action == "set":
        if not args.key or args.val is None:
            print("Error: Missing key or value, e.g. `agy-notify config set voice_enabled true`")
            return
        raw_val = args.val
        if raw_val.lower() == "true":
            val = True
        elif raw_val.lower() == "false":
            val = False
        elif raw_val.isdigit():
            val = int(raw_val)
        else:
            val = raw_val

        update_config_value(args.key, val)
        print(f"[OK] Configuration updated: {args.key} = {val}")


def cmd_watch(args):
    """Run standalone transcript watcher daemon."""
    watcher = TranscriptWatcher()
    watcher.watch_loop(poll_interval=args.interval)


def main():
    parser = argparse.ArgumentParser(
        description="Antigravity Desktop Notifier: Cross-platform lifecycle notifications."
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # hook (called by Antigravity)
    subparsers.add_parser("hook", help="Antigravity lifecycle hook runner (invoked by IDE)")

    # test
    test_parser = subparsers.add_parser("test", help="Test desktop notifications and sounds")
    test_parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["permission", "input", "complete", "error", "all"],
        help="Type of notification to test",
    )

    # doctor
    subparsers.add_parser("doctor", help="Run system diagnostics and health checks")

    # metrics
    subparsers.add_parser("metrics", help="Display notification delivery metrics and breakdown")

    # history
    history_parser = subparsers.add_parser("history", help="Show recent notification audit history")
    history_parser.add_argument("--limit", type=int, default=15, help="Number of records to show")

    # install
    install_parser = subparsers.add_parser("install", help="Install hooks into Antigravity configuration")
    install_parser.add_argument(
        "--workspace",
        action="store_true",
        help="Install in workspace (.agents/hooks.json) instead of globally",
    )

    # uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Remove hooks from Antigravity configuration")
    uninstall_parser.add_argument(
        "--workspace",
        action="store_true",
        help="Uninstall from workspace instead of global",
    )

    # status
    subparsers.add_parser("status", help="Show current installation and configuration status")

    # config
    config_parser = subparsers.add_parser("config", help="Manage configuration options")
    config_parser.add_argument("action", nargs="?", default="list", choices=["list", "get", "set"])
    config_parser.add_argument("key", nargs="?", help="Configuration key (e.g. voice_enabled, sounds.permission)")
    config_parser.add_argument("val", nargs="?", help="Configuration value")

    # watch
    watch_parser = subparsers.add_parser("watch", help="Run background watcher on active conversation transcripts")
    watch_parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")

    args = parser.parse_args()

    if args.command == "hook":
        handle_hook_event()
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "metrics":
        cmd_metrics(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "uninstall":
        cmd_uninstall(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "watch":
        cmd_watch(args)
    else:
        print_banner()
        parser.print_help()


