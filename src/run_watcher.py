
import time
import json

from watcher.fetcher import fetch_all_earthquakes
from watcher.watches import load_watches, build_query
from watcher.fingerprint import compute_fingerprint


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

    # 6. Display the fingerprint
    print("\nFingerprint:")
    print(json.dumps(fingerprint, indent=2))


if __name__ == "__main__":
    main()
