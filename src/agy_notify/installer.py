"""Registration of the notifier hook in Antigravity's ``hooks.json``."""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from .jsonio import read_json_dict, write_json
from .paths import is_frozen, path_exists, project_root

HOOK_IDENTIFIER = "antigravity-notifier"
GLOBAL_CONFIG_DIR = Path.home() / ".gemini" / "config"
GLOBAL_HOOKS_FILE = GLOBAL_CONFIG_DIR / "hooks.json"
GLOBAL_SCOPE = "Global (~/.gemini/config/hooks.json)"


def _is_windows() -> bool:
    """Return whether the host operating system is Windows."""
    return platform.system() == "Windows"


def _candidate_paths() -> list[Path]:
    """List the places the ``agy-notify`` launcher may live, best first."""
    bin_dir = project_root() / "bin"
    launcher = "agy-notify.bat" if _is_windows() else "agy-notify"
    candidates = [bin_dir / launcher, bin_dir / "agy-notify"]
    found = shutil.which("agy-notify")
    if found:
        candidates.append(Path(found))
    candidates.append(Path.home() / ".local" / "bin" / "agy-notify")
    return candidates


def find_cli_path() -> str:
    """Return the path of the ``agy-notify`` executable or launcher."""
    if is_frozen():
        return str(Path(sys.executable).resolve())
    candidates = _candidate_paths()
    for candidate in candidates:
        if path_exists(candidate):
            return str(candidate.resolve())
    return str(candidates[1].resolve())


def _hook_command(cli_path: str) -> str:
    """Return the shell command Antigravity runs for each hook event."""
    if is_frozen() or not _is_windows():
        return f'"{cli_path}" hook'
    entry = Path(cli_path).resolve().parent.parent / "bin" / "agy-notify"
    return f'python "{entry}" hook'


def get_hook_entry(cli_path: str) -> dict[str, Any]:
    """Build the ``hooks.json`` entry that wires events to ``cli_path``."""
    handler = {"type": "command", "command": _hook_command(cli_path), "timeout": 10}
    return {
        "enabled": True,
        "PreToolUse": [{"matcher": ".*", "hooks": [dict(handler)]}],
        "Stop": [dict(handler)],
    }


def _resolve_target(is_global: bool, workspace_path: str | None) -> tuple[Path, str]:
    """Return the ``hooks.json`` path and a human-readable scope label."""
    if is_global:
        return GLOBAL_HOOKS_FILE, GLOBAL_SCOPE
    root = Path(workspace_path) if workspace_path else Path.cwd()
    target = root / ".agents" / "hooks.json"
    return target, f"Workspace ({target})"


def _backup(path: Path) -> None:
    """Copy ``path`` to a ``.json.bak`` sibling when it exists."""
    if path_exists(path):
        shutil.copy2(path, path.with_suffix(".json.bak"))


def install_hooks(
    is_global: bool = True, workspace_path: str | None = None
) -> tuple[bool, str]:
    """Register the hook, preserving other entries; return ``(ok, message)``."""
    cli_path = find_cli_path()
    target, scope = _resolve_target(is_global, workspace_path)
    try:
        _backup(target)
        data = read_json_dict(target)
        data[HOOK_IDENTIFIER] = get_hook_entry(cli_path)
        write_json(target, data)
    except OSError as error:
        return False, f"Failed to install to {scope}: {error}"
    return True, f"Successfully installed {scope} pointing to '{cli_path}'."


def uninstall_hooks(
    is_global: bool = True, workspace_path: str | None = None
) -> tuple[bool, str]:
    """Remove the hook, preserving other entries; return ``(ok, message)``."""
    target, scope = _resolve_target(is_global, workspace_path)
    if not path_exists(target):
        return True, f"{scope} does not exist. Nothing to uninstall."
    data = read_json_dict(target)
    if HOOK_IDENTIFIER not in data:
        return True, f"{HOOK_IDENTIFIER} was not found in {scope}."
    del data[HOOK_IDENTIFIER]
    try:
        write_json(target, data)
    except OSError as error:
        return False, f"Failed to uninstall from {scope}: {error}"
    return True, f"Successfully removed {HOOK_IDENTIFIER} from {scope}."


def _stop_command(entry: dict[str, Any]) -> str | None:
    """Return the command registered for the ``Stop`` event, if any."""
    handlers = entry.get("Stop")
    if not isinstance(handlers, list) or not handlers or not isinstance(handlers[0], dict):
        return None
    command = handlers[0].get("command")
    return command if isinstance(command, str) else None


def _registration(path: Path) -> tuple[bool, str | None]:
    """Return ``(installed, stop_command)`` for the hooks file at ``path``."""
    entry = read_json_dict(path).get(HOOK_IDENTIFIER)
    if not isinstance(entry, dict):
        return False, None
    return True, _stop_command(entry)


def check_status(workspace_path: str | None = None) -> dict[str, Any]:
    """Report where the hook is registered, never raising on unreadable files."""
    workspace_file, _ = _resolve_target(False, workspace_path)
    global_installed, global_command = _registration(GLOBAL_HOOKS_FILE)
    workspace_installed, workspace_command = _registration(workspace_file)
    return {
        "platform": platform.system(),
        "cli_path": find_cli_path(),
        "global_hooks_file": str(GLOBAL_HOOKS_FILE),
        "global_installed": global_installed,
        "global_hook_cmd": global_command,
        "workspace_hooks_file": str(workspace_file),
        "workspace_installed": workspace_installed,
        "workspace_hook_cmd": workspace_command,
    }
