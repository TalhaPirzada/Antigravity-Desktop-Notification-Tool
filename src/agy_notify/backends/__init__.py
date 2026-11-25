"""Per-platform desktop integration backends."""

from __future__ import annotations

from .base import NULL_BACKEND, Backend
from .linux import BACKEND as LINUX_BACKEND
from .macos import BACKEND as MACOS_BACKEND
from .windows import BACKEND as WINDOWS_BACKEND

BACKENDS: dict[str, Backend] = {
    "Darwin": MACOS_BACKEND,
    "Windows": WINDOWS_BACKEND,
    "Linux": LINUX_BACKEND,
}


def get_backend(system: str) -> Backend:
    """Return the backend for ``system`` (a ``platform.system()`` value)."""
    return BACKENDS.get(system, NULL_BACKEND)
