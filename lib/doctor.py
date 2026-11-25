import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from .paths import project_root
PROJECT_ROOT = project_root()
ASSETS_DIR = PROJECT_ROOT / "assets"
MAC_LAUNCHER = PROJECT_ROOT / "bin" / "Antigravity Notifier.app" / "Contents" / "MacOS" / "agy-launcher"
GLOBAL_HOOKS_FILE = Path.home() / ".gemini" / "config" / "hooks.json"


def run_diagnostics(workspace_path: str = "") -> List[Tuple[str, str, str]]:
    """
    Executes a comprehensive system and configuration diagnostic.
    Returns list of tuples: (check_name, status, detail)
    where status is 'PASS', 'WARN', or 'FAIL'.
    """
    results: List[Tuple[str, str, str]] = []
    os_name = platform.system()

    # 1. Operating System & Architecture
    arch = platform.machine()
    results.append(("OS Environment", "PASS", f"{os_name} ({arch})"))

    # 2. Python Runtime
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 8):
        results.append(("Python Runtime", "PASS", f"Python {py_ver}"))
    else:
        results.append(("Python Runtime", "WARN", f"Python {py_ver} (Python 3.8+ recommended)"))

    # 3. Notification Dispatcher
    if os_name == "Darwin":
        if (MAC_LAUNCHER.parent.parent.parent / "Contents" / "MacOS" / "applet").exists():
            results.append(("Notification Dispatcher", "PASS", "macOS Branded Applet (Antigravity Notifier.app)"))
        elif shutil.which("osascript"):
            results.append(("Notification Dispatcher", "PASS", "macOS AppleScript (/usr/bin/osascript)"))
        else:
            results.append(("Notification Dispatcher", "FAIL", "No notification backend available"))
    elif os_name == "Windows":
        if shutil.which("powershell"):
            results.append(("Notification Dispatcher", "PASS", "Windows PowerShell WinRT Toast Engine"))
        else:
            results.append(("Notification Dispatcher", "FAIL", "PowerShell not found in PATH"))
    elif os_name == "Linux":
        if shutil.which("notify-send"):
            results.append(("Notification Dispatcher", "PASS", "freedesktop notify-send"))
        else:
            results.append(("Notification Dispatcher", "WARN", "notify-send not installed (install libnotify-bin)"))
    else:
        results.append(("Notification Dispatcher", "WARN", f"Untested platform: {os_name}"))

    # 4. Audio Subsystem
    if os_name == "Darwin":
        if shutil.which("afplay"):
            results.append(("Audio Engine", "PASS", "CoreAudio afplay"))
        else:
            results.append(("Audio Engine", "WARN", "afplay not found"))
    elif os_name == "Windows":
        results.append(("Audio Engine", "PASS", "Windows System Sound Events"))
    elif os_name == "Linux":
        audio_backend = None
        for cmd in ["paplay", "pw-play", "canberra-gtk-play", "aplay"]:
            if shutil.which(cmd):
                audio_backend = cmd
                break
        if audio_backend:
            results.append(("Audio Engine", "PASS", f"Linux audio backend ({audio_backend})"))
        else:
            results.append(("Audio Engine", "WARN", "No audio player found (install pulseaudio-utils or pipewire)"))

    # 5. Asset Verification
    png_icon = ASSETS_DIR / "icon.png"
    if png_icon.exists() and png_icon.stat().st_size > 0:
        results.append(("Icon Asset (PNG)", "PASS", f"{png_icon.name} ({png_icon.stat().st_size // 1024} KB)"))
    else:
        results.append(("Icon Asset (PNG)", "FAIL", "assets/icon.png missing or empty"))

    if os_name == "Darwin":
        icns_icon = ASSETS_DIR / "icon.icns"
        if icns_icon.exists() and icns_icon.stat().st_size > 0:
            results.append(("Icon Asset (ICNS)", "PASS", f"{icns_icon.name} ({icns_icon.stat().st_size // 1024} KB)"))
        else:
            results.append(("Icon Asset (ICNS)", "WARN", "assets/icon.icns missing"))

    # 6. Configuration & State Directory
    cfg_dir = Path.home() / ".config" / "antigravity-notifier"
    try:
        cfg_dir.mkdir(parents=True, exist_ok=True)
        test_file = cfg_dir / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        results.append(("State Storage", "PASS", str(cfg_dir)))
    except Exception as e:
        results.append(("State Storage", "WARN", f"Non-writable: {str(e)}"))

    # 7. Antigravity Hook Registration
    try:
        import json
        if GLOBAL_HOOKS_FILE.exists():
            with open(GLOBAL_HOOKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "antigravity-notifier" in data:
                    results.append(("Global Hook", "PASS", "Registered in ~/.gemini/config/hooks.json"))
                else:
                    results.append(("Global Hook", "WARN", "Not registered. Run: agy-notify install"))
        else:
            results.append(("Global Hook", "WARN", "~/.gemini/config/hooks.json not found. Run: agy-notify install"))
    except Exception:
        results.append(("Global Hook", "WARN", "Cannot inspect ~/.gemini/config/hooks.json"))

    return results
