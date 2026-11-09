import time
import json

from watcher.fetcher import (
    fetch_all_earthquakes,
    fetch_realtime_earthquakes,
)

from watcher.watches import (
    load_watches,
    build_query,
)

from watcher.fingerprint import compute_fingerprint

from watcher.db import (
    upsert_watch,
    get_latest_snapshot,
    get_snapshot_events,
    get_snapshot_event_data,
    save_run,
)

from watcher.detectors import run_detectors


# Check both watches every 5 minutes
POLL_INTERVAL_SECONDS = 300


def run_watch(watch):
    """
    Run one configured watch.

    rolling:
        Uses the USGS historical API for the configured
        rolling time window.

    live:
        Uses the USGS real-time GeoJSON feed.
    """

    watch_name = watch["name"]
    watch_kind = watch["kind"]

    print("\n" + "=" * 60)
    print(f"Running watch: {watch_name}")
    print("=" * 60)

    # ---------------------------------------------------------
    # STEP 1: Register watch and load previous state
    # ---------------------------------------------------------

    watch_id = upsert_watch(
        watch_name,
        watch,
    )

    previous = get_latest_snapshot(
        watch_id
    )

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
    # STEP 2: Fetch data according to watch type
    # ---------------------------------------------------------

    print("\nFetching USGS earthquake data...")

    start = time.perf_counter()

    if watch_kind == "rolling":

        query = build_query(watch)

        print(
            "Using USGS historical API."
        )

        print(
            f"Query: {query}"
        )

        records = fetch_all_earthquakes(
            query=query,
            page_size=100,
            max_records=5000,
        )

    elif watch_kind == "live":

        print(
            "Using USGS real-time feed."
        )

        records = fetch_realtime_earthquakes(
            minmagnitude=float(
                watch["minmagnitude"]
            )
        )

    else:

        raise ValueError(
            f"Unsupported watch kind: {watch_kind}"
        )

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
    # STEP 3: Compute fingerprint
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
    # STEP 4: Load detector configuration
    # ---------------------------------------------------------

    detector_config = watch.get(
        "detectors",
        {}
    )

    # ---------------------------------------------------------
    # STEP 5: Determine whether a baseline exists
    # ---------------------------------------------------------

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
    # STEP 6: Detect changes
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

        # Neither rolling nor live is a closed dataset.
        #
        # For rolling-7d, an event leaving the 7-day window
        # is not necessarily "removed".
        #
        # For live, an event leaving the real-time feed
        # is also not necessarily "removed".
        closed_window=False,
    )

    # ---------------------------------------------------------
    # STEP 7: Display results
    # ---------------------------------------------------------

    summary = result[
        "event_summary"
    ]

    alerts = result[
        "alerts"
    ]

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
    # STEP 8: Save everything to PostgreSQL
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
        f"Watch '{watch_name}' "
        f"completed successfully."
    )


def run_once():
    """
    Run all configured watches once.

    Each watch is processed independently so that
    rolling-7d and live maintain separate database
    histories and baselines.
    """

    print("\n" + "#" * 60)
    print("STARTING WATCHER CYCLE")
    print("#" * 60)

    watches = load_watches()

    print(
        f"Configured watches: "
        f"{len(watches)}"
    )

    for watch in watches:

        try:

            run_watch(watch)

        except Exception as error:

            print(
                "\nWatch failed:"
            )

            print(
                f"Watch: {watch.get('name')}"
            )

            print(
                f"Error: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            print(
                "The remaining watches will "
                "still be attempted."
            )


def main():
    """
    Continuously run all watches every 5 minutes.
    """

    print("=" * 60)
    print("USGS OPEN DATA CHANGE DETECTOR")
    print("=" * 60)

    print(
        "Configured polling interval: "
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
                "\nWatcher cycle failed:"
            )

            print(
                f"{type(error).__name__}: "
                f"{error}"
            )

            print(
                "The watcher will retry "
                "on the next cycle."
            )

        print(
            "\nWaiting 5 minutes "
            "before the next cycle..."
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