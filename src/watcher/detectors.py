
def detect_schema_changes(previous, current):
    """Detect fields added to or removed from the dataset."""

    if previous is None:
        return []

    previous_schema = set(previous.get("schema", []))
    current_schema = set(current.get("schema", []))

    added = sorted(current_schema - previous_schema)
    removed = sorted(previous_schema - current_schema)

    if not added and not removed:
        return []

    return [
        {
            "alert_type": "SCHEMA_CHANGED",
            "details": {
                "added_columns": added,
                "removed_columns": removed,
            },
        }
    ]


def detect_row_count_changes(previous, current, config):
    """Detect unusually large changes in the record count."""

    if previous is None:
        return []

    previous_count = previous.get("count", 0)
    current_count = current.get("count", 0)

    difference = current_count - previous_count
    absolute_difference = abs(difference)

    if previous_count == 0:
        percentage_change = (
            100.0 if current_count > 0 else 0.0
        )
    else:
        percentage_change = (
            absolute_difference / previous_count
        ) * 100

    minimum_change = config.get("min_count_change", 20)
    maximum_percentage = config.get(
        "max_count_change_pct", 50
    )

    if (
        absolute_difference < minimum_change
        or percentage_change < maximum_percentage
    ):
        return []

    if difference > 0:
        alert_type = "ROW_COUNT_INCREASE"
    else:
        alert_type = "ROW_COUNT_DECREASE"

    return [
        {
            "alert_type": alert_type,
            "details": {
                "previous_count": previous_count,
                "current_count": current_count,
                "difference": difference,
                "percentage_change": round(
                    percentage_change, 2
                ),
            },
        }
    ]


def classify_events(
    previous_events,
    current_events,
    alert_on_removal=True,
    alert_on_revision=True,
):
    """
    Classify event changes using event IDs and hashes.

    previous_events and current_events are dictionaries:
        {event_id: event_hash}
    """

    previous_ids = set(previous_events)
    current_ids = set(current_events)

    appended = sorted(current_ids - previous_ids)
    removed = sorted(previous_ids - current_ids)

    common_ids = previous_ids & current_ids

    revised = sorted(
        event_id
        for event_id in common_ids
        if previous_events[event_id] != current_events[event_id]
    )

    unchanged = sorted(
        event_id
        for event_id in common_ids
        if previous_events[event_id] == current_events[event_id]
    )

    alerts = []

    if removed and alert_on_removal:
        alerts.append(
            {
                "alert_type": "EVENTS_REMOVED",
                "details": {
                    "count": len(removed),
                    "event_ids": removed,
                },
            }
        )

    if revised and alert_on_revision:
        alerts.append(
            {
                "alert_type": "EVENTS_REVISED",
                "details": {
                    "count": len(revised),
                    "event_ids": revised,
                },
            }
        )

    return {
        "appended": appended,
        "removed": removed,
        "revised": revised,
        "unchanged": unchanged,
        "appended_count": len(appended),
        "removed_count": len(removed),
        "revised_count": len(revised),
        "unchanged_count": len(unchanged),
        "alerts": alerts,
    }


def detect_content_changes(previous, current, config):
    """Optionally alert when the overall content hash changes."""

    if previous is None:
        return []

    if not config.get("alert_on_content_change", False):
        return []

    previous_hash = previous.get("content_hash")
    current_hash = current.get("content_hash")

    if previous_hash == current_hash:
        return []

    return [
        {
            "alert_type": "CONTENT_CHANGED",
            "details": {
                "previous_hash": previous_hash,
                "current_hash": current_hash,
            },
        }
    ]


def run_detectors(
    previous,
    current,
    previous_events,
    current_events,
    config,
    closed_window=False,
):
    """Run all detectors and return their combined results."""

    alerts = []

    alerts.extend(
        detect_schema_changes(previous, current)
    )

    alerts.extend(
        detect_row_count_changes(
            previous,
            current,
            config,
        )
    )

    # A rolling window naturally loses old records as time passes.
    # Do not classify those records as unexpected removals.
    event_result = classify_events(
        previous_events,
        current_events,
        alert_on_removal=closed_window,
        alert_on_revision=config.get(
            "alert_on_revision", True
        ),
    )

    alerts.extend(event_result["alerts"])

    alerts.extend(
        detect_content_changes(
            previous,
            current,
            config,
        )
    )

    return {
        "alerts": alerts,
        "event_summary": {
            "appended": event_result["appended_count"],
            "removed": event_result["removed_count"],
            "revised": event_result["revised_count"],
            "unchanged": event_result["unchanged_count"],
        },
    }
