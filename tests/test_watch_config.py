
from datetime import datetime, timezone

from watcher.watches import load_watches, build_query


def test_closed_watch_query():
    watches = load_watches()
    watch = next(w for w in watches if w["name"] == "closed-month")

    query = build_query(watch)

    assert query["starttime"] == "2026-08-01"
    assert query["endtime"] == "2026-09-01"
    assert query["minmagnitude"] == 2.5


def test_rolling_watch_query():
    watches = load_watches()
    watch = next(w for w in watches if w["name"] == "rolling-7d")

    now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    query = build_query(watch, now=now)

    assert query["starttime"] == "2026-10-07T12:00:00"
    assert query["endtime"] == "2026-10-14T12:00:00"
    assert query["minmagnitude"] == 2.5
