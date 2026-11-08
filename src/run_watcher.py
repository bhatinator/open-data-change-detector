import time
import json

from watcher.fetcher import fetch_realtime_earthquakes
from watcher.watches import load_watches

from watcher.fingerprint import compute_fingerprint

from watcher.db import (
    upsert_watch,
    get_latest_snapshot,
    get_snapshot_events,
    get_snapshot_event_data,
    save_run,
)

from watcher.detectors import run_detectors


# Check the USGS real-time feed every 5 minutes
POLL_INTERVAL_SECONDS = 30


def run_once():
    """
    Run the watcher once.

    This function:
    1. Loads the watch configuration
    2. Gets the previous snapshot
    3. Fetches the latest USGS real-time earthquake data
    4. Computes the fingerprint
    5. Detects changes
    6. Saves everything to PostgreSQL
    """

    print("\n" + "=" * 60)
    print("Starting watcher run")
    print("=" * 60)

    # ---------------------------------------------------------
    # STEP 1: Load watch configurations
    # ---------------------------------------------------------

    watches = load_watches()

    # ---------------------------------------------------------
    # STEP 2: Select the watch
    # ---------------------------------------------------------

    watch = next(
        (
            item
            for item in watches
            if item["name"] == "rolling-7d"
        ),
        None,
    )

    if watch is None:
        raise ValueError(
            "The rolling-7d watch was not found."
        )

    print(f"Running watch: {watch['name']}")

    # ---------------------------------------------------------
    # STEP 3: Register watch and load previous state
    # ---------------------------------------------------------

    watch_id = upsert_watch(
        watch["name"],
        watch,
    )

    previous = get_latest_snapshot(watch_id)

    if previous is None:

        previous_events = {}
        previous_event_data = {}

        print(
            "No previous snapshot found."
        )

    else:

        previous_events = get_snapshot_events(
            previous["id"]
        )

        previous_event_records = (
            get_snapshot_event_data(
                previous["id"]
            )
        )

        previous_event_data = {
            event_id: item["event_data"]
            for event_id, item
            in previous_event_records.items()
        }

        print(
            f"Previous snapshot ID: "
            f"{previous['id']}"
        )

        print(
            f"Previous event count: "
            f"{len(previous_events)}"
        )

    # ---------------------------------------------------------
    # STEP 4: Fetch real-time USGS earthquake records
    # ---------------------------------------------------------

    print(
        "\nFetching USGS real-time earthquake feed..."
    )

    start = time.perf_counter()

    records = fetch_realtime_earthquakes()

    fetch_duration = (
        time.perf_counter() - start
    )

    print(
        f"Records fetched: {len(records)}"
    )

    print(
        f"Fetch time: "
        f"{fetch_duration:.2f} seconds"
    )

    # ---------------------------------------------------------
    # STEP 5: Compute fingerprint
    # ---------------------------------------------------------

    fingerprint = compute_fingerprint(
        records,
        fetch_duration_seconds=fetch_duration,
        fetch_status="success",
    )

    current_events = fingerprint[
        "event_hashes"
    ]

    current_event_data = {
        event.get("id"): event
        for event in records
        if event.get("id")
    }

    print(
        f"Events fingerprinted: "
        f"{len(current_events)}"
    )

    # ---------------------------------------------------------
    # STEP 6: Load detector thresholds
    # ---------------------------------------------------------

    detector_config = watch.get(
        "detectors",
        {}
    )

    # ---------------------------------------------------------
    # STEP 7: Determine whether a valid baseline exists
    # ---------------------------------------------------------

    # The first run becomes the baseline.
    #
    # We only compare against the previous snapshot
    # if it actually contains event data.

    has_baseline = (
        previous is not None
        and len(previous_events) > 0
    )

    if has_baseline:

        print(
            "Previous snapshot will be used "
            "as the comparison baseline."
        )

    else:

        print(
            "No valid event baseline found. "
            "This run will establish the baseline."
        )

    # ---------------------------------------------------------
    # STEP 8: Compare previous and current states
    # ---------------------------------------------------------

    result = run_detectors(
        previous=(
            previous
            if has_baseline
            else None
        ),

        current=fingerprint,

        previous_events=(
            previous_events
            if has_baseline
            else {}
        ),

        current_events=current_events,

        previous_event_data=(
            previous_event_data
            if has_baseline
            else {}
        ),

        current_event_data=current_event_data,

        config=detector_config,

        # IMPORTANT:
        # The real-time feed is not a closed historical
        # dataset, so removed events should not be treated
        # as actual dataset removals.
        closed_window=False,
    )

    # ---------------------------------------------------------
    # STEP 9: Display event classification
    # ---------------------------------------------------------

    summary = result["event_summary"]
    alerts = result["alerts"]

    print("\nEvent classification:")

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    print(
        f"\nAlerts generated: "
        f"{len(alerts)}"
    )

    for alert in alerts:

        print(
            f"- {alert['alert_type']}"
        )

    # ---------------------------------------------------------
    # STEP 10: Save all results in PostgreSQL
    # ---------------------------------------------------------

    snapshot_id = save_run(
        watch_id=watch_id,
        fingerprint=fingerprint,
        alerts=alerts,
        event_hashes=current_events,
        records=records,
    )

    print(
        f"\nSaved watch ID: "
        f"{watch_id}"
    )

    print(
        f"Saved snapshot ID: "
        f"{snapshot_id}"
    )

    print(
        f"Saved event records: "
        f"{len(current_events)}"
    )

    print(
        f"Saved alerts: "
        f"{len(alerts)}"
    )

    print(
        "Watcher run completed successfully."
    )


def main():
    """
    Continuously run the watcher every 5 minutes.
    """

    print("=" * 60)
    print("LIVE USGS EARTHQUAKE WATCHER")
    print("=" * 60)

    print(
        "Polling interval: "
        f"{POLL_INTERVAL_SECONDS} seconds "
        "(5 minutes)"
    )

    print(
        "Press Ctrl+C to stop the watcher."
    )

    while True:

        try:

            run_once()

        except KeyboardInterrupt:

            print(
                "\nWatcher stopped by user."
            )

            break

        except Exception as error:

            print(
                "\nWatcher run failed:"
            )

            print(
                f"{type(error).__name__}: "
                f"{error}"
            )

            print(
                "The watcher will continue "
                "and retry on the next cycle."
            )

        print(
            "\nWaiting 5 minutes "
            "before the next check..."
        )

        try:

            time.sleep(
                POLL_INTERVAL_SECONDS
            )

        except KeyboardInterrupt:

            print(
                "\nWatcher stopped by user."
            )

            break


if __name__ == "__main__":
    main()