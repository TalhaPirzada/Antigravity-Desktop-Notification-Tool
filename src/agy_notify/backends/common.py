"""Process helpers shared by the platform backends."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable, Sequence


def spawn(command: Sequence[str]) -> bool:
    """Start ``command`` detached and silent; return whether it launched."""
    try:
        subprocess.Popen(
            list(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except OSError:
        return False
    return True


def run_quiet(command: Sequence[str], timeout: float = 5) -> bool:
    """Run ``command`` to completion with captured output; return whether it ran."""
    try:
        subprocess.run(
            list(command), capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def first_available(commands: Iterable[Sequence[str]]) -> Sequence[str] | None:
    """Return the first command whose executable is on ``PATH``, if any."""
    for command in commands:
        if shutil.which(command[0]):
            return command
    return None


def quote_applescript(text: str) -> str:
    """Escape ``text`` for embedding inside an AppleScript string literal."""
    return text.replace("\\", "\\\\").replace('"', '\\"')
