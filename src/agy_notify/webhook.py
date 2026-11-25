"""Asynchronous webhook forwarding (Slack, Discord, ntfy, or generic HTTP)."""

from __future__ import annotations

import json
import threading
import urllib.request


def build_payload(
    title: str,
    subtitle: str,
    message: str,
    event_type: str,
    workspace: str,
) -> dict[str, str]:
    """Build a JSON payload compatible with Slack and Discord style webhooks."""
    text = f"*{title} - {subtitle}*\n{message}"
    if workspace:
        text += f"\nWorkspace: `{workspace}`"
    return {
        "source": "antigravity-notifier",
        "event": event_type,
        "title": title,
        "subtitle": subtitle,
        "message": message,
        "workspace": workspace,
        "text": text,
    }


def is_valid_url(url: str | None) -> bool:
    """Return whether ``url`` is a usable HTTP(S) webhook endpoint."""
    return bool(url) and str(url).startswith(("http://", "https://"))


def post_json(url: str, payload: dict[str, str]) -> bool:
    """POST ``payload`` as JSON; return whether the request succeeded."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "AntigravityNotifier/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=4):
            return True
    except (OSError, ValueError):
        return False


def dispatch_webhook_async(
    webhook_url: str | None,
    title: str,
    subtitle: str,
    message: str,
    event_type: str,
    workspace: str = "",
) -> None:
    """Send the webhook in a daemon thread so the caller is never blocked."""
    if webhook_url is None or not is_valid_url(webhook_url):
        return
    payload = build_payload(title, subtitle, message, event_type, workspace)
    threading.Thread(target=post_json, args=(webhook_url, payload), daemon=True).start()
