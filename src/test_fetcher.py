import logging

from watcher.fetcher import (
    FetchError,
    fetch_all_earthquakes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

try:
    records = fetch_all_earthquakes(
        page_size=10,
        max_records=25,
        timeout=10,
        max_retries=3,
        page_delay=0.5,
    )

    print(f"\nSuccessfully fetched {len(records)} earthquakes.")

    if records:
        print("First earthquake ID:", records[0].get("id"))

except FetchError as error:
    print(f"\nDataset fetch failed: {error}")
    print("The program handled the failure without an unhandled exception.")
