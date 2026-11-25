"""Backend contract shared by all platform implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Backend:
    """Callables implementing desktop integration for one operating system."""

    notify: Callable[[str, str, str, str | None], None]
    speak: Callable[[str, str], None]
    focus: Callable[[], None]


def _ignore(*_arguments: object) -> None:
    """Accept any arguments and do nothing."""


NULL_BACKEND = Backend(notify=_ignore, speak=_ignore, focus=_ignore)
