"""Windows backend using PowerShell WinRT toast notifications."""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..paths import assets_dir, path_exists
from .base import Backend
from .common import spawn

POWERSHELL = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
FOCUS_SCRIPT = (
    '$p = Get-Process | Where-Object { $_.MainWindowTitle -like "*Antigravity*" }'
    " | Select-Object -First 1\n"
    "if ($p) {\n"
    "  $sig = '[DllImport(\"user32.dll\")] public static extern bool "
    "SetForegroundWindow(IntPtr hWnd);'\n"
    "  Add-Type -MemberDefinition $sig -Namespace Win32 -Name User32\n"
    "  [Win32.User32]::SetForegroundWindow($p.MainWindowHandle)\n"
    "}"
)


def _icon_xml() -> str:
    """Return the toast ``<image>`` element for the app icon, if the file exists."""
    icon = assets_dir() / "icon.png"
    if not path_exists(icon):
        return ""
    source = escape(str(icon).replace("\\", "/"), {'"': "&quot;"})
    return f'<image placement="appLogoOverride" src="{source}"/>'


def build_script(title: str, subtitle: str, message: str) -> str:
    """Build the PowerShell script that shows the toast notification."""
    header = escape(f"{title} - {subtitle}" if subtitle else title)
    return (
        "[Windows.UI.Notifications.ToastNotificationManager, "
        "Windows.UI.Notifications, ContentType = WindowsRuntime] > $null\n"
        "$xml = @'\n"
        '<toast><visual><binding template="ToastGeneric">'
        f"<text>{header}</text><text>{escape(message)}</text>{_icon_xml()}"
        "</binding></visual>"
        '<audio src="ms-winsoundevent:Notification.Default"/></toast>\n'
        "'@\n"
        "$doc = [Windows.Data.Xml.Dom.XmlDocument]::new()\n"
        "$doc.LoadXml($xml)\n"
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($doc)\n"
        "[Windows.UI.Notifications.ToastNotificationManager]"
        '::CreateToastNotifier("Antigravity").Show($toast)'
    )


def notify(title: str, subtitle: str, message: str, sound: str | None) -> None:
    """Show a toast notification; the system sound event replaces ``sound``."""
    del sound
    spawn([*POWERSHELL, build_script(title, subtitle, message)])


def speak(text: str, voice: str) -> None:
    """Speak ``text`` with the .NET speech synthesizer."""
    del voice
    safe = text.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Speech; "
        f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"
    )
    spawn([*POWERSHELL, script])


def focus() -> None:
    """Bring the Antigravity window to the foreground."""
    spawn([*POWERSHELL, FOCUS_SCRIPT])


BACKEND = Backend(notify=notify, speak=speak, focus=focus)
