
from watcher.detectors import (
    detect_schema_changes,
    detect_row_count_changes,
    classify_events,
    run_detectors,
)


def test_schema_change():
    previous = {
        "schema": ["mag", "place", "time"]
    }

    current = {
        "schema": ["mag", "place", "updated"]
    }

    alerts = detect_schema_changes(previous, current)

    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "SCHEMA_CHANGED"

    details = alerts[0]["details"]

    assert details["added_columns"] == ["updated"]
    assert details["removed_columns"] == ["time"]


def test_no_schema_change():
    previous = {"schema": ["mag", "place"]}
    current = {"schema": ["mag", "place"]}

    assert detect_schema_changes(previous, current) == []


def test_row_count_increase():
    previous = {"count": 100}
    current = {"count": 200}

    config = {
        "min_count_change": 20,
        "max_count_change_pct": 50,
    }

    alerts = detect_row_count_changes(
        previous,
        current,
        config,
    )

    assert alerts[0]["alert_type"] == "ROW_COUNT_INCREASE"


def test_small_row_count_change():
    previous = {"count": 100}
    current = {"count": 105}

    config = {
        "min_count_change": 20,
        "max_count_change_pct": 50,
    }

    alerts = detect_row_count_changes(
        previous,
        current,
        config,
    )

    assert alerts == []


def test_event_classification():
    previous = {
        "event_A": "hash_1",
        "event_B": "hash_2",
        "event_C": "hash_3",
    }

    current = {
        "event_A": "hash_1",
        "event_B": "hash_NEW",
        "event_D": "hash_4",
    }

    result = classify_events(
        previous,
        current,
        alert_on_removal=True,
        alert_on_revision=True,
    )

    assert result["appended"] == ["event_D"]
    assert result["removed"] == ["event_C"]
    assert result["revised"] == ["event_B"]
    assert result["unchanged"] == ["event_A"]

    assert result["appended_count"] == 1
    assert result["removed_count"] == 1
    assert result["revised_count"] == 1


def test_rolling_window_suppresses_removal_alert():
    previous = {"event_A": "hash_1"}
    current = {}

    result = classify_events(
        previous,
        current,
        alert_on_removal=False,
    )

    assert result["removed_count"] == 1
    assert result["alerts"] == []


def test_closed_window_generates_removal_alert():
    previous = {"event_A": "hash_1"}
    current = {}

    result = classify_events(
        previous,
        current,
        alert_on_removal=True,
    )

    assert result["removed_count"] == 1
    assert result["alerts"][0]["alert_type"] == "EVENTS_REMOVED"


def test_run_detectors():
    previous = {
        "count": 100,
        "schema": ["mag", "place"],
        "content_hash": "old_hash",
    }

    current = {
        "count": 200,
        "schema": ["mag", "place", "updated"],
        "content_hash": "new_hash",
    }

    previous_events = {
        "event_A": "hash_1",
        "event_B": "hash_2",
    }

    current_events = {
        "event_A": "hash_NEW",
        "event_C": "hash_3",
    }

    config = {
        "min_count_change": 20,
        "max_count_change_pct": 50,
        "alert_on_revision": True,
        "alert_on_content_change": False,
    }

    result = run_detectors(
        previous,
        current,
        previous_events,
        current_events,
        config,
        closed_window=True,
    )

    alert_types = {
        alert["alert_type"]
        for alert in result["alerts"]
    }

    assert "SCHEMA_CHANGED" in alert_types
    assert "ROW_COUNT_INCREASE" in alert_types
    assert "EVENTS_REMOVED" in alert_types
    assert "EVENTS_REVISED" in alert_types

    assert result["event_summary"] == {
        "appended": 1,
        "removed": 1,
        "revised": 1,
        "unchanged": 0,
    }
