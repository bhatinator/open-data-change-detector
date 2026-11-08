import json
import os
import requests

from dotenv import load_dotenv


load_dotenv()


DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL"
)


def send_discord_message(message):
    """
    Send one message to Discord.
    """

    if not DISCORD_WEBHOOK_URL:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL is not configured."
        )

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json={
            "content": message
        },
        timeout=15,
    )

    response.raise_for_status()


def format_alert(alert):
    """
    Convert an alert dictionary into a
    concise Discord-friendly message.
    """

    alert_type = alert["alert_type"]
    details = alert["details"]

    lines = []

    lines.append("🚨 **Dataset Change Detected**")
    lines.append(f"**Type:** `{alert_type}`")

    # ------------------------------------------------
    # Added events
    # ------------------------------------------------

    if alert_type == "EVENTS_ADDED":

        events = details.get("events", [])

        lines.append(
            f"\n🟢 **New earthquake events: {len(events)}**"
        )

        for event in events:

            event_data = event.get(
                "event_data",
                {}
            )

            properties = event_data.get(
                "properties",
                {}
            )

            event_id = event.get(
                "event_id",
                event_data.get("id", "unknown")
            )

            lines.append("")
            lines.append(
                f"**Event `{event_id}`**"
            )

            lines.append(
                f"Magnitude: `{properties.get('mag')}`"
            )

            lines.append(
                f"Location: `{properties.get('place')}`"
            )

            lines.append(
                f"Time: `{properties.get('time')}`"
            )

            lines.append(
                f"Status: `{properties.get('status')}`"
            )

            url = properties.get("url")

            if url:
                lines.append(
                    f"[View on USGS]({url})"
                )

    # ------------------------------------------------
    # Removed events
    # ------------------------------------------------

    elif alert_type == "EVENTS_REMOVED":

        events = details.get("events", [])

        lines.append(
            f"\n🔴 **Removed earthquake events: {len(events)}**"
        )

        for event in events:

            event_data = event.get(
                "event_data",
                {}
            )

            properties = event_data.get(
                "properties",
                {}
            )

            event_id = event.get(
                "event_id",
                event_data.get("id", "unknown")
            )

            lines.append("")
            lines.append(
                f"**Event `{event_id}`**"
            )

            lines.append(
                f"Magnitude: `{properties.get('mag')}`"
            )

            lines.append(
                f"Location: `{properties.get('place')}`"
            )

            lines.append(
                f"Time: `{properties.get('time')}`"
            )

            lines.append(
                f"Status: `{properties.get('status')}`"
            )

            url = properties.get("url")

            if url:
                lines.append(
                    f"[View on USGS]({url})"
                )

    # ------------------------------------------------
    # Revised events
    # ------------------------------------------------

    elif alert_type == "EVENTS_REVISED":

        events = details.get("events", [])

        lines.append(
            f"\n🟡 **Revised earthquake events: {len(events)}**"
        )

        for event in events:

            event_id = event.get(
                "event_id",
                "unknown"
            )

            lines.append("")
            lines.append(
                f"**Event `{event_id}`**"
            )

            for change in event.get(
                "changed_fields",
                []
            ):

                old_value = change.get(
                    "old_value"
                )

                new_value = change.get(
                    "new_value"
                )

                lines.append(
                    f"\n**{change['field']}**"
                )

                lines.append(
                    f"OLD: `{old_value}`"
                )

                lines.append(
                    f"NEW: `{new_value}`"
                )

    # ------------------------------------------------
    # Schema change
    # ------------------------------------------------

    elif alert_type == "SCHEMA_CHANGED":

        lines.append("\n📐 **Schema change**")

        lines.append(
            f"Added fields: "
            f"`{details.get('added_columns', [])}`"
        )

        lines.append(
            f"Removed fields: "
            f"`{details.get('removed_columns', [])}`"
        )

    # ------------------------------------------------
    # Row count
    # ------------------------------------------------

    elif alert_type in (
        "ROW_COUNT_INCREASE",
        "ROW_COUNT_DECREASE",
    ):

        lines.append("\n📊 **Row count change**")

        lines.append(
            f"Previous: `{details.get('previous_count')}`"
        )

        lines.append(
            f"Current: `{details.get('current_count')}`"
        )

        lines.append(
            f"Difference: `{details.get('difference')}`"
        )

        lines.append(
            f"Percentage: `{details.get('percentage_change')}%`"
        )

    return "\n".join(lines)


def send_alert(alert):
    """
    Format and send one alert to Discord.
    """

    message = format_alert(alert)

    # Discord content has a practical 2000-character limit.
    # Split long messages into chunks.
    chunks = []

    while len(message) > 1900:

        split_at = message.rfind(
            "\n",
            0,
            1900,
        )

        if split_at == -1:
            split_at = 1900

        chunks.append(
            message[:split_at]
        )

        message = message[
            split_at:
        ].lstrip()

    if message:
        chunks.append(message)

    for chunk in chunks:
        send_discord_message(chunk)