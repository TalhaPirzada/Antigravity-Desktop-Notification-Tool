import datetime
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional
from .config import load_config
from .logger import get_logger
from .metrics import record_event
from .webhook import dispatch_webhook_async

# Path references
from .paths import project_root
PROJECT_ROOT = project_root()
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_PNG = ASSETS_DIR / "icon.png"
ICON_ICNS = ASSETS_DIR / "icon.icns"
ICON_ICO = ASSETS_DIR / "icon.ico"
MAC_APP_BUNDLE = PROJECT_ROOT / "bin" / "Antigravity Notifier.app"

# Cooldown cache
COOLDOWN_CACHE = Path("/tmp") / ".agy_notifier_last_notification" if platform.system() != "Windows" else Path(os.environ.get("TEMP", "C:/Temp")) / ".agy_notifier_last_notification"


class Notifier:
    """
    Production-grade cross-platform desktop notification engine:
    - macOS: Native Notification Center via branded applet / AppleScript with official Antigravity icon
    - Windows: WinRT Toast notifications via PowerShell with appLogoOverride icon
    - Linux: freedesktop notify-send with custom icon & PulseAudio/PipeWire sounds
    - Remote Webhook: Async dispatch to Slack, Discord, ntfy, or generic HTTP endpoint
    - Quiet Hours: Automatic audio chime suppression during configured periods
    """

    def __init__(self, config=None):
        self.config = config or load_config()
        self.os_type = platform.system()  # 'Darwin', 'Windows', 'Linux'
        self.logger = get_logger(self.config.get("log_level", "INFO"))

    def _should_suppress(self, message: str) -> bool:
        """Check if notification should be suppressed due to cooldown."""
        cooldown = self.config.get("cooldown_seconds", 3)
        if cooldown <= 0:
            return False

        now = time.time()
        try:
            if COOLDOWN_CACHE.exists():
                content = COOLDOWN_CACHE.read_text().strip()
                if ":::" in content:
                    last_time_str, last_msg = content.split(":::", 1)
                    last_time = float(last_time_str)
                    if (now - last_time) < cooldown and last_msg == message:
                        return True
        except Exception:
            pass

        try:
            COOLDOWN_CACHE.parent.mkdir(parents=True, exist_ok=True)
            COOLDOWN_CACHE.write_text(f"{now}:::{message}")
        except Exception:
            pass
        return False

    def _is_quiet_hours(self) -> bool:
        """Determines if the current time falls inside quiet hours."""
        qh = self.config.get("quiet_hours", {})
        if not qh.get("enabled", False):
            return False

        try:
            now_time = datetime.datetime.now().time()
            start_parts = [int(p) for p in qh.get("start", "22:00").split(":")]
            end_parts = [int(p) for p in qh.get("end", "08:00").split(":")]
            start_t = datetime.time(start_parts[0], start_parts[1])
            end_t = datetime.time(end_parts[0], end_parts[1])

            if start_t <= end_t:
                return start_t <= now_time <= end_t
            else:  # Overnight range, e.g. 22:00 to 08:00
                return now_time >= start_t or now_time <= end_t
        except Exception:
            return False

    def send_notification(
        self,
        title: str,
        subtitle: str,
        message: str,
        event_type: str = "complete",
        sound: Optional[str] = None,
        workspace: str = "",
    ) -> bool:
        """Send a cross-platform desktop notification with custom icon and audio alert."""
        if not self.config.get("enabled", True):
            return False

        start_time = time.time()
        full_message = f"{subtitle} - {message}" if subtitle else message
        if self._should_suppress(full_message):
            self.logger.debug(f"Suppressed duplicate notification: {full_message}")
            return False

        # Determine sound name (mute if quiet hours active)
        sound_name = sound
        quiet = self._is_quiet_hours()
        if quiet:
            sound_name = None
        elif sound_name is None and self.config.get("sound_enabled", True):
            sounds = self.config.get("sounds", {})
            sound_name = sounds.get(event_type, "Ping")

        delivered = True
        try:
            # Dispatch by operating system
            if self.os_type == "Darwin":
                self._notify_macos(title, subtitle, message, sound_name)
            elif self.os_type == "Windows":
                self._notify_windows(title, subtitle, message, sound_name)
            elif self.os_type == "Linux":
                self._notify_linux(title, subtitle, message, sound_name)
            else:
                self._fallback_notification(title, subtitle, message, sound_name)
        except Exception as e:
            delivered = False
            self.logger.error(f"Failed to dispatch notification: {str(e)}")

        duration_ms = (time.time() - start_time) * 1000

        # Record metrics & audit trail
        record_event(
            event_type=event_type,
            title=title,
            subtitle=subtitle,
            message=message,
            workspace=workspace,
            delivered=delivered,
            duration_ms=duration_ms,
        )

        self.logger.info(f"Notification delivered [{event_type}] ({duration_ms:.1f}ms): {title} - {subtitle}")

        # Optional Voice announcement (only if not in quiet hours)
        if self.config.get("voice_enabled", False) and not quiet:
            self._speak(f"{title}: {subtitle or message}")

        # Optional Window focus
        if self.config.get("focus_window_on_alert", False):
            self.focus_antigravity_window()

        # Optional Webhook forwarding
        webhook_url = self.config.get("webhook_url")
        if webhook_url:
            dispatch_webhook_async(
                webhook_url=webhook_url,
                title=title,
                subtitle=subtitle,
                message=message,
                event_type=event_type,
                workspace=workspace,
            )

        return delivered

    # --------------------------------------------------------------------------
    # macOS Implementation (with custom Antigravity icon)
    # --------------------------------------------------------------------------
    def _notify_macos(self, title: str, subtitle: str, message: str, sound_name: Optional[str]) -> None:
        """macOS notification using branded applet or AppleScript with icon."""
        if MAC_APP_BUNDLE.exists():
            try:
                import tempfile
                clean = lambda s: (s or "").replace("\n", " ").replace("\r", " ")
                fd, payload_path = tempfile.mkstemp(prefix="agy_payload_", suffix=".txt")
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write("\n".join([clean(message), clean(title), clean(subtitle), clean(sound_name)]))
                # -n: new instance per notification, -g: do not steal focus
                subprocess.Popen(
                    ["open", "-n", "-g", "--env", f"AGY_PAYLOAD={payload_path}", str(MAC_APP_BUNDLE)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            except Exception:
                pass

        safe_msg = message.replace("\\", "\\\\").replace('"', '\\"')
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_sub = subtitle.replace("\\", "\\\\").replace('"', '\\"')
        sound_clause = f'sound name "{sound_name}"' if sound_name else ""

        script = f'''
        try
            tell application "Antigravity"
                display notification "{safe_msg}" with title "{safe_title}" subtitle "{safe_sub}" {sound_clause}
            end tell
        on error
            display notification "{safe_msg}" with title "{safe_title}" subtitle "{safe_sub}" {sound_clause}
        end try
        '''
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        except Exception:
            self._fallback_notification(title, subtitle, message, sound_name)

    # --------------------------------------------------------------------------
    # Windows Implementation (PowerShell WinRT Toast with appLogoOverride)
    # --------------------------------------------------------------------------
    def _notify_windows(self, title: str, subtitle: str, message: str, sound_name: Optional[str]) -> None:
        """Windows Toast notification via PowerShell with custom icon."""
        icon_path = str(ICON_PNG.resolve()).replace("\\", "/") if ICON_PNG.exists() else ""
        header = f"{title} - {subtitle}" if subtitle else title

        ps_header = header.replace("'", "''")
        ps_msg = message.replace("'", "''")
        ps_icon = icon_path.replace("'", "''")

        image_xml = f'<image placement="appLogoOverride" src="{ps_icon}"/>' if ps_icon else ""

        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
        $xml = @"
        <toast>
            <visual>
                <binding template="ToastGeneric">
                    <text>{ps_header}</text>
                    <text>{ps_msg}</text>
                    {image_xml}
                </binding>
            </visual>
            <audio src="ms-winsoundevent:Notification.Default"/>
        </toast>
"@
        $xmlDoc = [Windows.Data.Xml.Dom.XmlDocument]::new()
        $xmlDoc.LoadXml($xml)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xmlDoc)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Antigravity").Show($toast)
        """

        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self._fallback_notification(title, subtitle, message, sound_name)

    # --------------------------------------------------------------------------
    # Linux Implementation (notify-send with custom icon & PulseAudio sound)
    # --------------------------------------------------------------------------
    def _notify_linux(self, title: str, subtitle: str, message: str, sound_name: Optional[str]) -> None:
        """Linux notification using notify-send with icon and sound."""
        icon_arg = ["-i", str(ICON_PNG.resolve())] if ICON_PNG.exists() else []
        heading = f"{title}: {subtitle}" if subtitle else title

        notify_cmd = ["notify-send", "-a", "Antigravity"] + icon_arg + [heading, message]

        try:
            subprocess.Popen(
                notify_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self._fallback_notification(title, subtitle, message, sound_name)

        if sound_name:
            sound_players = [
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                ["pw-play", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                ["canberra-gtk-play", "-i", "message-new-instant"],
                ["aplay", "/usr/share/sounds/alsa/Front_Center.wav"],
            ]
            for player_cmd in sound_players:
                if shutil.which(player_cmd[0]):
                    try:
                        subprocess.Popen(player_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
                    except Exception:
                        pass

    # --------------------------------------------------------------------------
    # Fallbacks & Extras
    # --------------------------------------------------------------------------
    def _fallback_notification(self, title: str, subtitle: str, message: str, sound_name: Optional[str]) -> None:
        """Terminal / audio fallback."""
        if self.os_type == "Darwin" and sound_name:
            sound_path = f"/System/Library/Sounds/{sound_name}.aiff"
            if os.path.exists(sound_path):
                try:
                    subprocess.Popen(["/usr/bin/afplay", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

    def _speak(self, text: str) -> None:
        """Cross-platform text-to-speech."""
        try:
            if self.os_type == "Darwin" and shutil.which("say"):
                voice = self.config.get("voice_name", "Samantha")
                cmd = ["/usr/bin/say", "-v", voice, text] if voice else ["/usr/bin/say", text]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif self.os_type == "Windows":
                ps_speak = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
                subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_speak], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif self.os_type == "Linux" and shutil.which("espeak"):
                subprocess.Popen(["espeak", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def focus_antigravity_window(self) -> None:
        """Cross-platform bring window to front."""
        try:
            if self.os_type == "Darwin":
                focus_script = """
                tell application "System Events"
                    set procList to every process whose name contains "Antigravity" or name contains "Electron"
                    if (count of procList) > 0 then
                        set frontmost of first item of procList to true
                    end if
                end tell
                """
                subprocess.Popen(["osascript", "-e", focus_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif self.os_type == "Windows":
                ps_focus = """
                $proc = Get-Process | Where-Object { $_.MainWindowTitle -like "*Antigravity*" } | Select-Object -First 1
                if ($proc) {
                    $sig = '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);'
                    Add-Type -MemberDefinition $sig -Namespace Win32 -Name User32
                    [Win32.User32]::SetForegroundWindow($proc.MainWindowHandle)
                }
                """
                subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_focus], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # Convenience methods (Clean subtitles without emojis)
    def notify_permission_required(self, tool_name: str, detail: str = "", workspace: str = "") -> bool:
        app_title = self.config.get("custom_title", "Antigravity")
        subtitle = "Permission Required"
        if tool_name == "run_command":
            msg = f"Command requires approval: {detail}" if detail else "A terminal command requires approval."
        else:
            msg = f"Tool '{tool_name}' requires approval." + (f" ({detail})" if detail else "")
        if workspace:
            msg += f" in [{Path(workspace).name}]"
        return self.send_notification(title=app_title, subtitle=subtitle, message=msg, event_type="permission", workspace=workspace)

    def notify_input_needed(self, question: str = "", workspace: str = "") -> bool:
        app_title = self.config.get("custom_title", "Antigravity")
        subtitle = "Input Needed"
        msg = f"Agent prompt: {question}" if question else "Agent is waiting for response."
        if workspace:
            msg += f" in [{Path(workspace).name}]"
        return self.send_notification(title=app_title, subtitle=subtitle, message=msg, event_type="input", workspace=workspace)

    def notify_task_completed(self, summary: str = "", workspace: str = "") -> bool:
        app_title = self.config.get("custom_title", "Antigravity")
        subtitle = "Task Completed"
        msg = summary if summary else "All steps finished. Ready for review."
        if workspace:
            msg += f" in [{Path(workspace).name}]"
        return self.send_notification(title=app_title, subtitle=subtitle, message=msg, event_type="complete", workspace=workspace)

    def notify_error(self, error_msg: str = "", workspace: str = "") -> bool:
        app_title = self.config.get("custom_title", "Antigravity")
        subtitle = "Execution Error"
        msg = f"Execution halted: {error_msg}" if error_msg else "Agent execution encountered an error."
        if workspace:
            msg += f" in [{Path(workspace).name}]"
        return self.send_notification(title=app_title, subtitle=subtitle, message=msg, event_type="error", workspace=workspace)
