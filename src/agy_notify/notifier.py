"""Cross-platform desktop notification engine."""

from __future__ import annotations

import platform
import time
from typing import Any

from . import cooldown, messages
from .backends import get_backend
from .backends.base import Backend
from .config import load_config
from .logger import get_logger
from .metrics import record_event
from .quiet import is_quiet_time
from .webhook import dispatch_webhook_async


class Notifier:
    """Deliver notifications with sound, voice, focus and webhook extras."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Create a notifier using ``config`` or the persisted configuration."""
        self.config: dict[str, Any] = config or load_config()
        self.os_type = platform.system()
        self.logger = get_logger(str(self.config.get("log_level", "INFO")))

    @property
    def backend(self) -> Backend:
        """Return the backend matching the current operating system."""
        return get_backend(self.os_type)

    def _resolve_sound(self, event_type: str, sound: str | None, quiet: bool) -> str | None:
        """Pick the alert sound, honouring quiet hours and the sound setting."""
        if quiet:
            return None
        if sound is not None or not self.config.get("sound_enabled", True):
            return sound
        return str(self.config.get("sounds", {}).get(event_type, "Ping"))

    def _deliver(self, title: str, subtitle: str, message: str, sound: str | None) -> bool:
        """Show the notification through the backend; return whether it succeeded."""
        try:
            self.backend.notify(title, subtitle, message, sound)
        except OSError as error:
            self.logger.error("Failed to dispatch notification: %s", error)
            return False
        return True

    def _speak(self, title: str, subtitle: str, message: str) -> None:
        """Announce the notification aloud when voice is enabled."""
        if self.config.get("voice_enabled", False):
            voice = str(self.config.get("voice_name", ""))
            self.backend.speak(f"{title}: {subtitle or message}", voice)

    def _focus(self) -> None:
        """Bring the IDE window forward when focus-on-alert is enabled."""
        if self.config.get("focus_window_on_alert", False):
            self.backend.focus()

    def send_notification(
        self,
        title: str,
        subtitle: str,
        message: str,
        event_type: str = "complete",
        sound: str | None = None,
        workspace: str = "",
    ) -> bool:
        """Send one notification; return whether it was delivered."""
        if not self.config.get("enabled", True):
            return False
        summary = f"{subtitle} - {message}" if subtitle else message
        if cooldown.is_duplicate(summary, float(self.config.get("cooldown_seconds", 3))):
            self.logger.debug("Suppressed duplicate notification: %s", summary)
            return False
        quiet = is_quiet_time(self.config.get("quiet_hours", {}))
        started = time.time()
        delivered = self._deliver(
            title, subtitle, message, self._resolve_sound(event_type, sound, quiet)
        )
        elapsed_ms = (time.time() - started) * 1000
        record_event(event_type, title, subtitle, message, workspace, delivered, elapsed_ms)
        self.logger.info("Notification [%s] (%.1fms): %s", event_type, elapsed_ms, title)
        if not quiet:
            self._speak(title, subtitle, message)
        self._focus()
        dispatch_webhook_async(
            self.config.get("webhook_url"), title, subtitle, message, event_type, workspace
        )
        return delivered

    def _notify_event(self, event_type: str, body: str, workspace: str) -> bool:
        """Send a standard lifecycle notification of ``event_type``."""
        return self.send_notification(
            title=str(self.config.get("custom_title", "Antigravity")),
            subtitle=messages.SUBTITLES[event_type],
            message=messages.with_workspace(body, workspace),
            event_type=event_type,
            workspace=workspace,
        )

    def notify_permission_required(
        self, tool_name: str, detail: str = "", workspace: str = ""
    ) -> bool:
        """Notify that a tool needs approval."""
        body = messages.permission_message(tool_name, detail)
        return self._notify_event("permission", body, workspace)

    def notify_input_needed(self, question: str = "", workspace: str = "") -> bool:
        """Notify that the agent is waiting for an answer."""
        return self._notify_event("input", messages.input_message(question), workspace)

    def notify_task_completed(self, summary: str = "", workspace: str = "") -> bool:
        """Notify that the agent finished its turn."""
        return self._notify_event("complete", messages.completed_message(summary), workspace)

    def notify_error(self, error_msg: str = "", workspace: str = "") -> bool:
        """Notify that execution stopped with an error."""
        return self._notify_event("error", messages.error_message(error_msg), workspace)
