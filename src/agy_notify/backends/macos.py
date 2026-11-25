"""macOS backend using the branded notifier app with AppleScript fallback."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

from ..paths import mac_app_bundle, path_exists
from .base import Backend
from .common import quote_applescript, run_quiet, spawn

PAYLOAD_PREFIX = "agy_payload_"
STALE_SECONDS = 3600
SOUND_DIR = Path("/System/Library/Sounds")
FOCUS_SCRIPT = (
    'tell application "System Events"\n'
    'set procs to every process whose name contains "Antigravity"'
    ' or name contains "Electron"\n'
    "if (count of procs) > 0 then set frontmost of first item of procs to true\n"
    "end tell"
)


def _single_line(text: str) -> str:
    """Collapse line breaks so each payload field stays on one line."""
    return text.replace("\r", " ").replace("\n", " ")


def _unlink_if_older(path: Path, cutoff: float) -> None:
    """Delete ``path`` when it was last modified before ``cutoff``."""
    try:
        if path.stat().st_mtime < cutoff:
            path.unlink()
    except OSError:
        return


def purge_stale_payloads(now: float) -> None:
    """Remove payload files left behind by earlier notifications."""
    pattern = f"{PAYLOAD_PREFIX}*.txt"
    for stale in Path(tempfile.gettempdir()).glob(pattern):
        _unlink_if_older(stale, now - STALE_SECONDS)


def write_payload(fields: Sequence[str]) -> Path:
    """Write the applet payload (one field per line) to a temporary file."""
    handle, name = tempfile.mkstemp(prefix=PAYLOAD_PREFIX, suffix=".txt")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write("\n".join(_single_line(field) for field in fields))
    return Path(name)


def build_script(title: str, subtitle: str, message: str, sound: str | None) -> str:
    """Build the AppleScript used when the branded app is unavailable."""
    sound_clause = f'sound name "{quote_applescript(sound)}"' if sound else ""
    body = (
        f'display notification "{quote_applescript(message)}"'
        f' with title "{quote_applescript(title)}"'
        f' subtitle "{quote_applescript(subtitle)}" {sound_clause}'
    )
    return (
        f'try\ntell application "Antigravity"\n{body}\nend tell\n'
        f"on error\n{body}\nend try"
    )


def _notify_via_bundle(
    title: str, subtitle: str, message: str, sound: str | None
) -> bool:
    """Post the notification through the branded app; return whether it launched."""
    bundle = mac_app_bundle()
    if not path_exists(bundle):
        return False
    payload = write_payload([message, title, subtitle, sound or ""])
    return spawn(["open", "-n", "-g", "--env", f"AGY_PAYLOAD={payload}", str(bundle)])


def _play_sound(sound: str | None) -> None:
    """Play a system sound directly when no notification could be posted."""
    if not sound:
        return
    path = SOUND_DIR / f"{sound}.aiff"
    if path_exists(path):
        spawn(["/usr/bin/afplay", str(path)])


def notify(title: str, subtitle: str, message: str, sound: str | None) -> None:
    """Show a notification, preferring the branded Antigravity app."""
    purge_stale_payloads(time.time())
    if _notify_via_bundle(title, subtitle, message, sound):
        return
    script = build_script(title, subtitle, message, sound)
    if not run_quiet(["osascript", "-e", script]):
        _play_sound(sound)


def speak(text: str, voice: str) -> None:
    """Speak ``text`` with the macOS ``say`` command."""
    if not shutil.which("say"):
        return
    command = ["/usr/bin/say"]
    if voice:
        command.extend(["-v", voice])
    spawn([*command, text])


def focus() -> None:
    """Bring the Antigravity window to the foreground."""
    spawn(["osascript", "-e", FOCUS_SCRIPT])


BACKEND = Backend(notify=notify, speak=speak, focus=focus)
