"""Filesystem locations shared across the package."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return whether the code runs from a PyInstaller-packaged executable."""
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Return the directory that holds ``assets/`` and ``bin/``.

    A source checkout resolves to the repository root. A packaged binary
    resolves to the directory containing the executable.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def assets_dir() -> Path:
    """Return the directory holding the icon assets."""
    return project_root() / "assets"


def mac_app_bundle() -> Path:
    """Return the path of the branded macOS notifier application."""
    return project_root() / "bin" / "Antigravity Notifier.app"


def path_exists(path: Path) -> bool:
    """Return whether ``path`` exists, treating permission errors as absent."""
    try:
        return path.exists()
    except OSError:
        return False
