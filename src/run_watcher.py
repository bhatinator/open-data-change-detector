
import time
import json

from watcher.fetcher import fetch_all_earthquakes
from watcher.watches import load_watches, build_query
from watcher.fingerprint import compute_fingerprint

from watcher.db import (
    upsert_watch,
    get_latest_snapshot,
    get_snapshot_events,
    save_run,
)

from watcher.detectors import run_detectors


def main():
    # STEP 1: Load watch configurations
    watches = load_watches()

    # STEP 2: Select the watch
    watch = next(
        (
            item for item in watches
            if item["name"] == "rolling-7d"
        ),
        None,
    )

    if watch is None:
        raise ValueError(
            "The rolling-7d watch was not found."
        )

    # STEP 3: Build USGS API query
    query = build_query(watch)

    print(f"Running watch: {watch['name']}")
    print(f"Query: {query}")

    # STEP 4: Register watch and load previous state
    watch_id = upsert_watch(watch["name"], watch)

    previous = get_latest_snapshot(watch_id)

    if previous is None:
        previous_events = {}
        print("No previous snapshot found.")
    else:
        previous_events = get_snapshot_events(
            previous["id"]
        )
        print(
            f"Previous snapshot ID: {previous['id']}"
        )

    # STEP 5: Fetch earthquake records
    start = time.perf_counter()

    records = fetch_all_earthquakes(
        query=query,
        page_size=100,
        max_records=500,
    )

    fetch_duration = time.perf_counter() - start

    print(f"Records fetched: {len(records)}")

    # STEP 6: Compute fingerprint
    fingerprint = compute_fingerprint(
        records,
        fetch_duration_seconds=fetch_duration,
        fetch_status="success",
    )

    current_events = fingerprint["event_hashes"]

    # STEP 7: Load detector thresholds
    detector_config = watch.get("detectors", {})

    # STEP 8: Compare previous and current states
    # Older Step 5 snapshots do not have snapshot_events.
    # Treat the first Step 6 run as a baseline.
    has_baseline = (
        previous is not None
        and len(previous_events) > 0
    )

    result = run_detectors(
        previous=previous if has_baseline else None,
        current=fingerprint,
        previous_events=(
            previous_events if has_baseline else {}
        ),
        current_events=current_events,
        config=detector_config,
        closed_window=(watch["kind"] == "closed"),
    )

    # STEP 9: Display event classification
    summary = result["event_summary"]
    alerts = result["alerts"]

    print("\nEvent classification:")
    print(json.dumps(summary, indent=2))

    print(f"\nAlerts generated: {len(alerts)}")

    for alert in alerts:
        print(
            f"- {alert['alert_type']}: "
            f"{alert['details']}"
        )

    # STEP 10: Save all results in PostgreSQL
    snapshot_id = save_run(
        watch_id=watch_id,
        fingerprint=fingerprint,
        alerts=alerts,
        event_hashes=current_events,
    )

    print(f"\nSaved watch ID: {watch_id}")
    print(f"Saved snapshot ID: {snapshot_id}")
    print(f"Saved event records: {len(current_events)}")
    print(f"Saved alerts: {len(alerts)}")


if __name__ == "__main__":
    main()
