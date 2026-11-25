import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .paths import is_frozen, project_root

HOOK_IDENTIFIER = "antigravity-notifier"
GLOBAL_CONFIG_DIR = Path.home() / ".gemini" / "config"
GLOBAL_HOOKS_FILE = GLOBAL_CONFIG_DIR / "hooks.json"


def find_cli_path() -> str:
    """Find the path of agy-notify or Python script entry point."""
    is_windows = platform.system() == "Windows"
    if is_frozen():
        return str(Path(sys.executable).resolve())
    root = project_root()

    candidate = root / "bin" / ("agy-notify.bat" if is_windows else "agy-notify")
    if candidate.exists():
        return str(candidate.resolve())

    candidate_no_ext = root / "bin" / "agy-notify"
    if candidate_no_ext.exists():
        return str(candidate_no_ext.resolve())

    which_path = shutil.which("agy-notify")
    if which_path:
        return which_path

    local_bin = Path.home() / ".local" / "bin" / "agy-notify"
    try:
        if local_bin.exists():
            return str(local_bin.resolve())
    except Exception:
        pass

    return str(candidate_no_ext.resolve())


def get_hook_entry(cli_path: str) -> Dict[str, Any]:
    """Generate the hook configuration dictionary for Antigravity (cross-platform)."""
    is_windows = platform.system() == "Windows"
    if is_frozen():
        cmd = f'"{cli_path}" hook'
    elif is_windows:
        py_entry = Path(cli_path).resolve().parent.parent / "bin" / "agy-notify"
        cmd = f'python "{py_entry}" hook'
    else:
        cmd = f'"{cli_path}" hook'

    return {
        "enabled": True,
        "PreToolUse": [
            {
                "matcher": ".*",
                "hooks": [
                    {
                        "type": "command",
                        "command": cmd,
                        "timeout": 10,
                    }
                ],
            }
        ],
        "Stop": [
            {
                "type": "command",
                "command": cmd,
                "timeout": 10,
            }
        ],
    }


def install_hooks(is_global: bool = True, workspace_path: Optional[str] = None) -> Tuple[bool, str]:
    """Install hooks into hooks.json (cross-platform)."""
    cli_path = find_cli_path()
    if is_global:
        target_dir = GLOBAL_CONFIG_DIR
        target_file = GLOBAL_HOOKS_FILE
        scope_name = "Global (~/.gemini/config/hooks.json)"
    else:
        root = Path(workspace_path) if workspace_path else Path.cwd()
        target_dir = root / ".agents"
        target_file = target_dir / "hooks.json"
        scope_name = f"Workspace ({target_file})"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        existing_data: Dict[str, Any] = {}
        if target_file.exists():
            backup_file = target_file.with_suffix(".json.bak")
            shutil.copy2(target_file, backup_file)
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = {}

        existing_data[HOOK_IDENTIFIER] = get_hook_entry(cli_path)

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2)

        return True, f"Successfully installed {scope_name} pointing to '{cli_path}'."
    except Exception as e:
        return False, f"Failed to install to {scope_name}: {str(e)}"


def uninstall_hooks(is_global: bool = True, workspace_path: Optional[str] = None) -> Tuple[bool, str]:
    """Remove hooks from hooks.json."""
    if is_global:
        target_file = GLOBAL_HOOKS_FILE
        scope_name = "Global (~/.gemini/config/hooks.json)"
    else:
        root = Path(workspace_path) if workspace_path else Path.cwd()
        target_file = root / ".agents" / "hooks.json"
        scope_name = f"Workspace ({target_file})"

    try:
        if not target_file.exists():
            return True, f"{scope_name} does not exist. Nothing to uninstall."

        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if HOOK_IDENTIFIER in data:
            del data[HOOK_IDENTIFIER]
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True, f"Successfully removed {HOOK_IDENTIFIER} from {scope_name}."
        else:
            return True, f"{HOOK_IDENTIFIER} was not found in {scope_name}."
    except Exception as e:
        return False, f"Failed to uninstall from {scope_name}: {str(e)}"


def check_status(workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """Check status of hooks safely without throwing permission errors."""
    global_installed = False
    global_hook_cmd = None
    try:
        if GLOBAL_HOOKS_FILE.exists():
            with open(GLOBAL_HOOKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if HOOK_IDENTIFIER in data:
                    global_installed = True
                    global_hook_cmd = data[HOOK_IDENTIFIER].get("Stop", [{}])[0].get("command")
    except Exception:
        # Expected in sandboxed environment where ~/.gemini/config is inaccessible
        pass

    ws_root = Path(workspace_path) if workspace_path else Path.cwd()
    ws_file = ws_root / ".agents" / "hooks.json"
    ws_installed = False
    ws_hook_cmd = None
    try:
        if ws_file.exists():
            with open(ws_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if HOOK_IDENTIFIER in data:
                    ws_installed = True
                    ws_hook_cmd = data[HOOK_IDENTIFIER].get("Stop", [{}])[0].get("command")
    except Exception:
        pass

    return {
        "platform": platform.system(),
        "cli_path": find_cli_path(),
        "global_hooks_file": str(GLOBAL_HOOKS_FILE),
        "global_installed": global_installed,
        "global_hook_cmd": global_hook_cmd,
        "workspace_hooks_file": str(ws_file),
        "workspace_installed": ws_installed,
        "workspace_hook_cmd": ws_hook_cmd,
    }
