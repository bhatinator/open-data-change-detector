
import time
import json
import hashlib
from watcher.fetcher import fetch_all_earthquakes
from watcher.watches import load_watches, build_query
from watcher.fingerprint import compute_fingerprint
from watcher.db import upsert_watch, save_snapshot, upsert_event_state
from watcher.db import upsert_watch, save_snapshot, upsert_event_state


def main():
    # 1. Load the watch configurations
    watches = load_watches()

    # 2. Choose one watch to run
    watch = next(
        (item for item in watches if item["name"] == "rolling-7d"),
        None,
    )

    if watch is None:
        raise ValueError("The rolling-7d watch was not found.")

    # 3. Build the USGS API query
    query = build_query(watch)
    print(f"Running watch: {watch['name']}")
    print(f"Query: {query}")

    # 4. Fetch the actual earthquake records
    start = time.perf_counter()

    records = fetch_all_earthquakes(
        query=query,
        page_size=100,
        max_records=500,
    )

    fetch_duration = time.perf_counter() - start

    print(f"Records fetched: {len(records)}")

    # 5. Calculate the fingerprint
    fingerprint = compute_fingerprint(
        records,
        fetch_duration_seconds=fetch_duration,
        fetch_status="success",
    )

    # Save the watch configuration and get its database ID.
    watch_id = upsert_watch(watch["name"], watch)

    # Save the fingerprint from this run.
    snapshot_id = save_snapshot(watch_id, fingerprint)

    print(f"Saved watch ID: {watch_id}")
    print(f"Saved snapshot ID: {snapshot_id}")

    # Save each event's hash from the fingerprint.
    for event_id, event_hash_value in fingerprint["event_hashes"].items():
        upsert_event_state(
        watch_id,
        event_id,
        event_hash_value
    )

    print(
    f"Updated event state for "
    f"{len(fingerprint['event_hashes'])} events."
    )

    # Save each earthquake's latest known hash.
    for record in records:
        event_id = record.get("id")

        if not event_id:
            continue

    canonical_record = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    )

    event_hash = hashlib.sha256(
        canonical_record.encode("utf-8")
    ).hexdigest()

    upsert_event_state(watch_id, event_id, event_hash)

    print(f"Updated event state for {len(records)} fetched records.")

if __name__ == "__main__":
    main()
