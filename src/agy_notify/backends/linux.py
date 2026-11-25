"""Linux backend using ``notify-send`` and common sound players."""

from __future__ import annotations

import shutil

from ..paths import assets_dir, path_exists
from .base import Backend
from .common import first_available, spawn

SOUND_PLAYERS = (
    ("paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"),
    ("pw-play", "/usr/share/sounds/freedesktop/stereo/complete.oga"),
    ("canberra-gtk-play", "-i", "message-new-instant"),
    ("aplay", "/usr/share/sounds/alsa/Front_Center.wav"),
)


def _icon_arguments() -> list[str]:
    """Return the ``notify-send`` icon arguments when the icon file exists."""
    icon = assets_dir() / "icon.png"
    if path_exists(icon):
        return ["-i", str(icon)]
    return []


def _play_sound() -> None:
    """Play the first available notification sound."""
    player = first_available(SOUND_PLAYERS)
    if player:
        spawn(player)


def notify(title: str, subtitle: str, message: str, sound: str | None) -> None:
    """Show a desktop notification and optionally play a sound."""
    heading = f"{title}: {subtitle}" if subtitle else title
    spawn(["notify-send", "-a", "Antigravity", *_icon_arguments(), heading, message])
    if sound:
        _play_sound()


def speak(text: str, voice: str) -> None:
    """Speak ``text`` with ``espeak`` when it is installed."""
    del voice
    if shutil.which("espeak"):
        spawn(["espeak", text])


def focus() -> None:
    """Window focusing is not supported on Linux desktops."""


BACKEND = Backend(notify=notify, speak=speak, focus=focus)
