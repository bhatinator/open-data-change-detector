
from datetime import datetime, timezone

from watcher.watches import load_watches, build_query


watches = load_watches()

# Use a fixed time so the rolling-watch output is predictable.
test_now = datetime(
    2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc
)

for watch in watches:
    query = build_query(
        watch,
        now=test_now,
        limit=100,
        offset=1,
    )

    print(f"\nWatch: {watch['name']}")
    print("Kind:", watch["kind"])
    print("Query parameters:")

    for key, value in query.items():
        print(f"  {key}: {value}")
