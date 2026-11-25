"""Persistent user configuration."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .jsonio import read_json_dict, write_json
from .paths import path_exists, project_root

CONFIG_NAME = "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "sound_enabled": True,
    "sounds": {
        "permission": "Ping",
        "input": "Glass",
        "complete": "Hero",
        "error": "Basso",
    },
    "voice_enabled": False,
    "voice_name": "Samantha",
    "focus_window_on_alert": False,
    "cooldown_seconds": 3,
    "notify_on_all_commands": False,
    "custom_title": "Antigravity",
    "webhook_url": None,
    "quiet_hours": {"enabled": False, "start": "22:00", "end": "08:00"},
    "log_level": "INFO",
}


def home_config_dir() -> Path:
    """Return the per-user configuration directory."""
    return Path.home() / ".config" / "antigravity-notifier"


def fallback_config_dir() -> Path:
    """Return the project-local directory used when the home directory is read-only."""
    return project_root() / ".config"


def get_config_paths() -> tuple[Path, Path]:
    """Return ``(config_dir, config_file)``, preferring the home directory."""
    home_dir = home_config_dir()
    if path_exists(home_dir / CONFIG_NAME):
        return home_dir, home_dir / CONFIG_NAME
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback = fallback_config_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback, fallback / CONFIG_NAME
    return home_dir, home_dir / CONFIG_NAME


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of ``base`` updated recursively with ``override``."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _merge(current, value)
        else:
            merged[key] = value
    return merged


def _saved_config() -> dict[str, Any]:
    """Load the first existing configuration file, or an empty mapping."""
    for candidate in (
        home_config_dir() / CONFIG_NAME,
        fallback_config_dir() / CONFIG_NAME,
    ):
        if path_exists(candidate):
            return read_json_dict(candidate)
    return {}


def load_config() -> dict[str, Any]:
    """Load the configuration merged over the built-in defaults."""
    return _merge(DEFAULT_CONFIG, _saved_config())


def save_config(config: dict[str, Any]) -> None:
    """Persist ``config``, falling back to the project directory if needed."""
    _, config_file = get_config_paths()
    try:
        write_json(config_file, config)
    except OSError:
        write_json(fallback_config_dir() / CONFIG_NAME, config)


def _set_nested(config: dict[str, Any], key: str, value: Any) -> None:
    """Set ``key`` (supporting a single ``parent.child`` level) on ``config``."""
    parent, _, child = key.partition(".")
    if not child:
        config[key] = value
        return
    section = config.get(parent)
    if not isinstance(section, dict):
        section = {}
        config[parent] = section
    section[child] = value


def update_config_value(key: str, value: Any) -> dict[str, Any]:
    """Update one configuration value and persist the result."""
    config = load_config()
    _set_nested(config, key, value)
    save_config(config)
    return config
