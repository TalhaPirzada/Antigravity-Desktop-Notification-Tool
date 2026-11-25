"""Environment diagnostics for ``agy-notify doctor``."""

from __future__ import annotations

import platform
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from . import installer
from .config import home_config_dir
from .jsonio import read_json_dict
from .paths import assets_dir, mac_app_bundle, path_exists

Check = tuple[str, str, str]
MIN_PYTHON = (3, 9)
LINUX_PLAYERS = ("paplay", "pw-play", "canberra-gtk-play", "aplay")
DISPATCHER = "Notification Dispatcher"
AUDIO = "Audio Engine"


def _check_os(os_name: str) -> Check:
    """Report the operating system and CPU architecture."""
    return ("OS Environment", "PASS", f"{os_name} ({platform.machine()})")


def _check_python() -> Check:
    """Report whether the Python runtime meets the minimum version."""
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info >= MIN_PYTHON:
        return ("Python Runtime", "PASS", f"Python {version}")
    return ("Python Runtime", "WARN", f"Python {version} (3.9+ recommended)")


def _dispatcher_macos() -> Check:
    """Report the macOS notification backend."""
    applet = mac_app_bundle() / "Contents" / "MacOS" / "applet"
    if path_exists(applet):
        return (DISPATCHER, "PASS", "macOS Branded Applet (Antigravity Notifier.app)")
    if shutil.which("osascript"):
        return (DISPATCHER, "PASS", "macOS AppleScript (/usr/bin/osascript)")
    return (DISPATCHER, "FAIL", "No notification backend available")


def _dispatcher_windows() -> Check:
    """Report the Windows notification backend."""
    if shutil.which("powershell"):
        return (DISPATCHER, "PASS", "Windows PowerShell WinRT Toast Engine")
    return (DISPATCHER, "FAIL", "PowerShell not found in PATH")


def _dispatcher_linux() -> Check:
    """Report the Linux notification backend."""
    if shutil.which("notify-send"):
        return (DISPATCHER, "PASS", "freedesktop notify-send")
    return (DISPATCHER, "WARN", "notify-send not installed (install libnotify-bin)")


def _audio_macos() -> Check:
    """Report the macOS audio backend."""
    if shutil.which("afplay"):
        return (AUDIO, "PASS", "CoreAudio afplay")
    return (AUDIO, "WARN", "afplay not found")


def _audio_windows() -> Check:
    """Report the Windows audio backend."""
    return (AUDIO, "PASS", "Windows System Sound Events")


def _audio_linux() -> Check:
    """Report the Linux audio backend."""
    for player in LINUX_PLAYERS:
        if shutil.which(player):
            return (AUDIO, "PASS", f"Linux audio backend ({player})")
    return (AUDIO, "WARN", "No audio player found (install pulseaudio-utils)")


DISPATCHERS: dict[str, Callable[[], Check]] = {
    "Darwin": _dispatcher_macos,
    "Windows": _dispatcher_windows,
    "Linux": _dispatcher_linux,
}
AUDIO_ENGINES: dict[str, Callable[[], Check]] = {
    "Darwin": _audio_macos,
    "Windows": _audio_windows,
    "Linux": _audio_linux,
}


def _lookup(table: dict[str, Callable[[], Check]], os_name: str, label: str) -> Check:
    """Run the check registered for ``os_name`` or report an untested platform."""
    handler = table.get(os_name)
    if handler is None:
        return (label, "WARN", f"Untested platform: {os_name}")
    return handler()


def _size(path: Path) -> int:
    """Return the file size in bytes, or ``0`` when it cannot be read."""
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _asset_check(label: str, name: str, missing_status: str) -> Check:
    """Verify that the asset ``name`` exists and is not empty."""
    path = assets_dir() / name
    size = _size(path)
    if size > 0:
        return (label, "PASS", f"{name} ({size // 1024} KB)")
    return (label, missing_status, f"assets/{name} missing or empty")


def _check_state() -> Check:
    """Verify that the state directory is writable."""
    directory = home_config_dir()
    probe = directory / ".write_test"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as error:
        return ("State Storage", "WARN", f"Non-writable: {error}")
    return ("State Storage", "PASS", str(directory))


def _check_hook() -> Check:
    """Verify that the global hook is registered."""
    data = read_json_dict(installer.GLOBAL_HOOKS_FILE)
    if installer.HOOK_IDENTIFIER in data:
        return ("Global Hook", "PASS", "Registered in ~/.gemini/config/hooks.json")
    return ("Global Hook", "WARN", "Not registered or unreadable. Run: agy-notify install")


def run_diagnostics(workspace_path: str = "") -> list[Check]:
    """Run all diagnostic checks; ``workspace_path`` is kept for compatibility."""
    del workspace_path
    os_name = platform.system()
    results = [
        _check_os(os_name),
        _check_python(),
        _lookup(DISPATCHERS, os_name, DISPATCHER),
        _lookup(AUDIO_ENGINES, os_name, AUDIO),
        _asset_check("Icon Asset (PNG)", "icon.png", "FAIL"),
    ]
    if os_name == "Darwin":
        results.append(_asset_check("Icon Asset (ICNS)", "icon.icns", "WARN"))
    return [*results, _check_state(), _check_hook()]
