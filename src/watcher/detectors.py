def detect_schema_changes(previous, current):
    """Detect fields added to or removed from the dataset."""

    if previous is None:
        return []

    previous_schema = set(
        previous.get("schema", [])
    )

    current_schema = set(
        current.get("schema", [])
    )

    added = sorted(
        current_schema - previous_schema
    )

    removed = sorted(
        previous_schema - current_schema
    )

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


def detect_row_count_changes(
    previous,
    current,
    config,
):
    """Detect unusually large changes in the record count."""

    if previous is None:
        return []

    previous_count = previous.get(
        "count",
        0
    )

    current_count = current.get(
        "count",
        0
    )

    difference = (
        current_count - previous_count
    )

    absolute_difference = abs(
        difference
    )

    if previous_count == 0:

        percentage_change = (
            100.0
            if current_count > 0
            else 0.0
        )

    else:

        percentage_change = (
            absolute_difference
            / previous_count
        ) * 100

    minimum_change = config.get(
        "min_count_change",
        20
    )

    maximum_percentage = config.get(
        "max_count_change_pct",
        50
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
                "previous_count":
                    previous_count,

                "current_count":
                    current_count,

                "difference":
                    difference,

                "percentage_change":
                    round(
                        percentage_change,
                        2
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

    previous_ids = set(
        previous_events
    )

    current_ids = set(
        current_events
    )

    appended = sorted(
        current_ids - previous_ids
    )

    removed = sorted(
        previous_ids - current_ids
    )

    common_ids = (
        previous_ids
        & current_ids
    )

    revised = sorted(
        event_id
        for event_id in common_ids
        if (
            previous_events[event_id]
            != current_events[event_id]
        )
    )

    unchanged = sorted(
        event_id
        for event_id in common_ids
        if (
            previous_events[event_id]
            == current_events[event_id]
        )
    )

    alerts = []

    if removed and alert_on_removal:

        alerts.append(
            {
                "alert_type":
                    "EVENTS_REMOVED",

                "details": {
                    "count":
                        len(removed),

                    "event_ids":
                        removed,
                },
            }
        )

    if revised and alert_on_revision:

        alerts.append(
            {
                "alert_type":
                    "EVENTS_REVISED",

                "details": {
                    "count":
                        len(revised),

                    "event_ids":
                        revised,
                },
            }
        )

    return {
        "appended":
            appended,

        "removed":
            removed,

        "revised":
            revised,

        "unchanged":
            unchanged,

        "appended_count":
            len(appended),

        "removed_count":
            len(removed),

        "revised_count":
            len(revised),

        "unchanged_count":
            len(unchanged),

        "alerts":
            alerts,
    }


def detect_content_changes(
    previous,
    current,
    config,
):
    """Optionally alert when the overall content hash changes."""

    if previous is None:
        return []

    if not config.get(
        "alert_on_content_change",
        False
    ):
        return []

    previous_hash = previous.get(
        "content_hash"
    )

    current_hash = current.get(
        "content_hash"
    )

    if previous_hash == current_hash:
        return []

    return [
        {
            "alert_type":
                "CONTENT_CHANGED",

            "details": {
                "previous_hash":
                    previous_hash,

                "current_hash":
                    current_hash,
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
    previous_event_data=None,
    current_event_data=None,
):
    """Run all detectors and return their combined results."""

    alerts = []

    # ------------------------------------------------
    # Schema changes
    # ------------------------------------------------

    alerts.extend(
        detect_schema_changes(
            previous,
            current,
        )
    )

    # ------------------------------------------------
    # Row count changes
    # ------------------------------------------------

    alerts.extend(
        detect_row_count_changes(
            previous,
            current,
            config,
        )
    )

    # ------------------------------------------------
    # Event changes
    # ------------------------------------------------

    # If complete event data is available, use the
    # detailed detector. This allows us to ignore
    # routine metadata changes such as:
    #
    # properties.updated
    # properties.ids
    # properties.sources

    if (
        previous_event_data is not None
        and current_event_data is not None
    ):
        alerts.extend(
            detect_event_data_changes(
                previous_event_data,
                current_event_data,
                alert_on_removal=closed_window,
            )
        )

    else:
        # Backward-compatible fallback.
        #
        # If complete event data is not available,
        # use the event hashes.

        event_result = classify_events(
            previous_events,
            current_events,
            alert_on_removal=closed_window,
            alert_on_revision=config.get(
                "alert_on_revision",
                True,
            ),
        )

        alerts.extend(
            event_result["alerts"]
        )

    # ------------------------------------------------
    # Overall content change
    # ------------------------------------------------

    alerts.extend(
        detect_content_changes(
            previous,
            current,
            config,
        )
    )

    # ------------------------------------------------
    # Return results
    # ------------------------------------------------

    return {
        "alerts": alerts,

        "event_summary": {
            "appended": len(
                set(current_events)
                - set(previous_events)
            ),

            "removed": len(
                set(previous_events)
                - set(current_events)
            ),

            "revised": len(
                set(previous_events)
                & set(current_events)
                & {
                    event_id
                    for event_id in current_events
                    if (
                        event_id in previous_events
                        and previous_events[event_id]
                        != current_events[event_id]
                    )
                }
            ),

            "unchanged": len(
                set(previous_events)
                & set(current_events)
                & {
                    event_id
                    for event_id in current_events
                    if (
                        event_id in previous_events
                        and previous_events[event_id]
                        == current_events[event_id]
                    )
                }
            ),
        },
    }

def flatten_dict(
    value,
    prefix=""
):
    """
    Flatten nested dictionaries.

    Example:

    {
        "properties": {
            "mag": 4.2
        }
    }

    becomes:

    {
        "properties.mag": 4.2
    }
    """

    result = {}

    if isinstance(
        value,
        dict
    ):

        for key, child in value.items():

            new_prefix = (
                f"{prefix}.{key}"
                if prefix
                else key
            )

            result.update(
                flatten_dict(
                    child,
                    new_prefix,
                )
            )

    else:

        result[prefix] = value

    return result


def find_changed_fields(
    old_event,
    new_event,
):
    """
    Compare two complete events and return
    meaningful changed fields with old/new values.

    Routine USGS metadata changes are ignored:

    - properties.updated
    - properties.ids
    - properties.sources
    """

    old_flat = flatten_dict(
        old_event
    )

    new_flat = flatten_dict(
        new_event
    )

    all_fields = (
        set(old_flat)
        | set(new_flat)
    )

    # These fields can change routinely in the
    # USGS dataset without representing a
    # meaningful earthquake revision.
    ignored_fields = {
        "properties.updated",
        "properties.ids",
        "properties.sources",
    }

    changes = []

    MISSING = object()

    for field in sorted(
        all_fields
    ):

        # Ignore routine metadata changes.
        if field in ignored_fields:
            continue

        old_value = old_flat.get(
            field,
            MISSING
        )

        new_value = new_flat.get(
            field,
            MISSING
        )

        if old_value != new_value:

            changes.append(
                {
                    "field":
                        field,

                    "old_value": (
                        "FIELD_MISSING"
                        if old_value is MISSING
                        else old_value
                    ),

                    "new_value": (
                        "FIELD_MISSING"
                        if new_value is MISSING
                        else new_value
                    ),
                }
            )

    return changes


def detect_event_data_changes(
    previous_event_data,
    current_event_data,
    alert_on_removal=True,
):
    """
    Create detailed alerts for:

    - additions
    - removals
    - meaningful revisions
    """

    previous_ids = set(
        previous_event_data
    )

    current_ids = set(
        current_event_data
    )

    added_ids = sorted(
        current_ids
        - previous_ids
    )

    removed_ids = sorted(
        previous_ids
        - current_ids
    )

    common_ids = (
        previous_ids
        & current_ids
    )

    revised_events = []

    for event_id in sorted(
        common_ids
    ):

        old_event = (
            previous_event_data[
                event_id
            ]
        )

        new_event = (
            current_event_data[
                event_id
            ]
        )

        changed_fields = (
            find_changed_fields(
                old_event,
                new_event,
            )
        )

        # Only classify the event as revised
        # if at least one meaningful field changed.
        #
        # If the only changes were:
        #   properties.updated
        #   properties.ids
        #   properties.sources
        #
        # find_changed_fields() returns []
        # and no EVENTS_REVISED alert is created.

        if changed_fields:

            revised_events.append(
                {
                    "event_id":
                        event_id,

                    "changed_fields":
                        changed_fields,

                    "old_event":
                        old_event,

                    "new_event":
                        new_event,
                }
            )

    alerts = []

    # ------------------------------------------------
    # Added
    # ------------------------------------------------

    if added_ids:

        alerts.append(
            {
                "alert_type":
                    "EVENTS_ADDED",

                "details": {
                    "count":
                        len(added_ids),

                    "events": [
                        {
                            "event_id":
                                event_id,

                            "event_data":
                                current_event_data[
                                    event_id
                                ],
                        }

                        for event_id
                        in added_ids
                    ],
                },
            }
        )

    # ------------------------------------------------
    # Removed
    # ------------------------------------------------

    if (
        removed_ids
        and alert_on_removal
    ):

        alerts.append(
            {
                "alert_type":
                    "EVENTS_REMOVED",

                "details": {
                    "count":
                        len(removed_ids),

                    "events": [
                        {
                            "event_id":
                                event_id,

                            "event_data":
                                previous_event_data[
                                    event_id
                                ],
                        }

                        for event_id
                        in removed_ids
                    ],
                },
            }
        )

    # ------------------------------------------------
    # Revised
    # ------------------------------------------------

    if revised_events:

        alerts.append(
            {
                "alert_type":
                    "EVENTS_REVISED",

                "details": {
                    "count":
                        len(revised_events),

                    "events":
                        revised_events,
                },
            }
        )

    return alerts