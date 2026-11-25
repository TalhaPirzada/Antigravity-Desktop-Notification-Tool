import json
import threading
import urllib.request
from typing import Optional


def dispatch_webhook_async(
    webhook_url: Optional[str],
    title: str,
    subtitle: str,
    message: str,
    event_type: str,
    workspace: str = "",
) -> None:
    """Dispatches webhook asynchronously in a non-blocking daemon thread."""
    if not webhook_url or not webhook_url.startswith("http"):
        return

    thread = threading.Thread(
        target=_send_webhook,
        args=(webhook_url, title, subtitle, message, event_type, workspace),
        daemon=True,
    )
    thread.start()


def _send_webhook(
    url: str,
    title: str,
    subtitle: str,
    message: str,
    event_type: str,
    workspace: str,
) -> None:
    """Sends JSON POST request to configured webhook URL."""
    payload = {
        "source": "antigravity-notifier",
        "event": event_type,
        "title": title,
        "subtitle": subtitle,
        "message": message,
        "workspace": workspace,
        # Slack / Discord compatibility
        "text": f"*{title} - {subtitle}*\n{message}" + (f"\nWorkspace: `{workspace}`" if workspace else ""),
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AntigravityNotifier/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            pass
    except Exception:
        # Webhook delivery failure must not crash or block execution
        pass
