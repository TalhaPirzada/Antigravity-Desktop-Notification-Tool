import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "sound_enabled": True,
    "sounds": {
        "permission": "Ping",      # Ping, Submarine, Funk
        "input": "Glass",          # Glass, Tink, Bottle
        "complete": "Hero",        # Hero, Purr, Pop
        "error": "Basso",          # Basso, Sosumi
    },
    "voice_enabled": False,        # Text-to-speech announcement
    "voice_name": "Samantha",      # System voice name
    "focus_window_on_alert": False,# Bring Antigravity window to foreground
    "cooldown_seconds": 3,         # Minimum seconds between duplicate notifications
    "notify_on_all_commands": False,# If true, notify on all commands, not just permission-gated
    "custom_title": "Antigravity", # Application title in banners
    "webhook_url": None,           # Optional remote webhook (Slack, Discord, ntfy, generic)
    "quiet_hours": {
        "enabled": False,
        "start": "22:00",
        "end": "08:00",
    },
    "log_level": "INFO",
}

from .paths import project_root
PROJECT_DIR = project_root()
FALLBACK_CONFIG_DIR = PROJECT_DIR / ".config"


def get_config_paths() -> tuple[Path, Path]:
    """Return (config_dir, config_file) preferring ~/.config, falling back to project local."""
    home_config_dir = Path.home() / ".config" / "antigravity-notifier"
    home_config_file = home_config_dir / "config.json"

    if home_config_file.exists():
        return home_config_dir, home_config_file

    try:
        home_config_dir.mkdir(parents=True, exist_ok=True)
        return home_config_dir, home_config_file
    except Exception:
        FALLBACK_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        return FALLBACK_CONFIG_DIR, FALLBACK_CONFIG_DIR / "config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration with defaults."""
    config = dict(DEFAULT_CONFIG)
    home_file = Path.home() / ".config" / "antigravity-notifier" / "config.json"
    fallback_file = FALLBACK_CONFIG_DIR / "config.json"

    target_file = home_file if home_file.exists() else (fallback_file if fallback_file.exists() else None)
    if target_file and target_file.exists():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if "sounds" in saved and isinstance(saved["sounds"], dict):
                    config["sounds"].update(saved["sounds"])
                    del saved["sounds"]
                if "quiet_hours" in saved and isinstance(saved["quiet_hours"], dict):
                    config["quiet_hours"].update(saved["quiet_hours"])
                    del saved["quiet_hours"]
                config.update(saved)
        except Exception:
            pass
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration."""
    cfg_dir, cfg_file = get_config_paths()
    try:
        cfg_dir.mkdir(parents=True, exist_ok=True)
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        FALLBACK_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(FALLBACK_CONFIG_DIR / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)


def update_config_value(key: str, value: Any) -> Dict[str, Any]:
    """Update a specific configuration value (supports dot-notation)."""
    cfg = load_config()
    if "." in key:
        parent, child = key.split(".", 1)
        if parent not in cfg or not isinstance(cfg[parent], dict):
            cfg[parent] = {}
        cfg[parent][child] = value
    else:
        cfg[key] = value
    save_config(cfg)
    return cfg
