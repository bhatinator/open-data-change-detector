
from copy import deepcopy

from watcher.fingerprint import compute_fingerprint


def sample_events():
    return [
        {
            "type": "Feature",
            "id": "event-a",
            "properties": {
                "mag": 3.2,
                "place": "Example City",
                "time": 1790000000000,
                "status": "reviewed",
                "updated": 1790001000000,
            },
            "geometry": {
                "coordinates": [-120.5, 35.2, 8.4]
            },
        },
        {
            "type": "Feature",
            "id": "event-b",
            "properties": {
                "mag": 4.1,
                "place": "Example Region",
                "time": 1790002000000,
                "status": "automatic",
            },
            "geometry": {
                "coordinates": [-118.3, 34.7, 5.0]
            },
        },
    ]


def test_same_data_produces_same_content_hash():
    events = sample_events()

    first = compute_fingerprint(events)
    second = compute_fingerprint(deepcopy(events))

    assert first["content_hash"] == second["content_hash"]
    assert first["schema"] == second["schema"]
    assert first["count"] == 2


def test_event_order_does_not_change_content_hash():
    events = sample_events()

    first = compute_fingerprint(events)
    second = compute_fingerprint(list(reversed(events)))

    assert first["content_hash"] == second["content_hash"]


def test_changed_magnitude_changes_content_hash():
    original = sample_events()
    changed = deepcopy(original)

    changed[0]["properties"]["mag"] = 3.5

    first = compute_fingerprint(original)
    second = compute_fingerprint(changed)

    assert first["content_hash"] != second["content_hash"]
    assert (
        first["event_hashes"]["event-a"]
        != second["event_hashes"]["event-a"]
    )


def test_schema_is_sorted():
    fingerprint = compute_fingerprint(sample_events())

    assert fingerprint["schema"] == sorted(fingerprint["schema"])
