
import os
import time
import requests


DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

DISCORD_MESSAGE_LIMIT = 1900


def format_value(value):
    """Format a value safely for a Discord message."""

    if value is None:
        return "null"

    return str(value)


def format_event_notification(payload):
    """
    Format an event change as a readable Discord notification.

    payload should contain:
      watch_name
      alert_type
      event_id
      previous_event
      current_event
      changed_fields
    """

    watch_name = payload["watch_name"]
    alert_type = payload["alert_type"]
    event_id = payload["event_id"]

    previous = payload.get("previous_event")
    current = payload.get("current_event")
    changed_fields = payload.get("changed_fields", [])

    lines = [
        f"**Open Data Change Detector**",
        f"Watch: `{watch_name}`",
        f"Change: **{alert_type}**",
        f"Event ID: `{event_id}`",
    ]

    if alert_type == "EVENT_ADDED":
        lines.append("\n**New event details:**")
        lines.append(
            f"```json\n{format_value(current)}\n```"
        )

    elif alert_type == "EVENT_REMOVED":
        lines.append("\n**Previous event details:**")
        lines.append(
            f"```json\n{format_value(previous)}\n```"
        )

    elif alert_type == "EVENT_REVISED":
        lines.append("\n**Changed fields:**")

        for field in changed_fields:
            old_value = previous.get(field)
            new_value = current.get(field)

            lines.append(
                f"- **{field}:** "
                f"`{format_value(old_value)}` → "
                f"`{format_value(new_value)}`"
            )

        lines.append("\n**Previous event:**")
        lines.append(
            f"```json\n{format_value(previous)}\n```"
        )

        lines.append("\n**Current event:**")
        lines.append(
            f"```json\n{format_value(current)}\n```"
        )

    return "\n".join(lines)


def split_discord_message(message):
    """Split long messages to stay within Discord's content limit."""

    return [
        message[i:i + DISCORD_MESSAGE_LIMIT]
        for i in range(0, len(message), DISCORD_MESSAGE_LIMIT)
    ]


def send_discord_message(message):
    """Send a message to the configured Discord webhook."""

    if not DISCORD_WEBHOOK_URL:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL is not configured."
        )

    for chunk in split_discord_message(message):
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": chunk},
            timeout=20,
        )

        if response.status_code == 429:
            retry_after = float(
                response.headers.get("Retry-After", "2")
            )
            raise RuntimeError(
                f"Discord rate limit. Retry after {retry_after} seconds."
            )

        response.raise_for_status()

        # Small delay between multiple chunks.
        time.sleep(0.5)


def send_event_notification(payload):
    """Format and send one event notification."""

    message = format_event_notification(payload)
    send_discord_message(message)
