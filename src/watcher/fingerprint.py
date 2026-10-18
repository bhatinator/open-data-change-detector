
import hashlib
import json
import time

from datetime import datetime, timezone


IMPORTANT_FIELDS = (
    "mag",
    "place",
    "time",
    "status",
    "updated",
)


def canonical_json(value):
    """Serialize data consistently for reproducible hashing."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hash(value):
    """Return the SHA-256 hash of a string."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def event_payload(feature):
    """Extract the important, stable fields from one GeoJSON event."""

    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}

    payload = {
        field: properties.get(field)
        for field in IMPORTANT_FIELDS
        if field != "updated" or field in properties
    }

    payload["coordinates"] = geometry.get("coordinates")

    return payload


def event_hash(feature):
    """Calculate a hash for one earthquake event."""

    payload = event_payload(feature)
    serialized = canonical_json(payload)

    return sha256_hash(serialized)


def compute_fingerprint(
    features,
    fetch_duration_seconds=0.0,
    fetch_status="success",
    fetched_at=None,
):
    """
    Create a dataset fingerprint from a complete list of GeoJSON features.

    `features` must contain the complete result set for one watch,
    not just one page.
    """

    started_at = time.perf_counter()

    if fetch_status != "success":
        raise ValueError(
            "Cannot fingerprint an unsuccessful fetch. "
            "Preserve the last successful fingerprint instead."
        )

    if fetched_at is None:
        fetched_at = datetime.now(timezone.utc)

    if fetched_at.tzinfo is None:
        raise ValueError("fetched_at must be timezone-aware.")

    fetched_at = fetched_at.astimezone(timezone.utc)

    event_hashes = {}
    schema = set()
    newest_event_time = None

    for feature in features:
        if not isinstance(feature, dict):
            raise ValueError("Every event must be a dictionary.")

        event_id = feature.get("id")

        if not isinstance(event_id, str) or not event_id:
            raise ValueError("Every event must have a non-empty ID.")

        properties = feature.get("properties") or {}

        if not isinstance(properties, dict):
            raise ValueError(
                f"Event {event_id} has invalid properties."
            )

        schema.update(properties.keys())

        if event_id in event_hashes:
            raise ValueError(f"Duplicate event ID: {event_id}")

        event_hashes[event_id] = event_hash(feature)

        event_time = properties.get("time")

        if isinstance(event_time, (int, float)):
            if (
                newest_event_time is None
                or event_time > newest_event_time
            ):
                newest_event_time = event_time

    # Sort by event ID so API response ordering does not affect the hash.
    sorted_event_hashes = dict(sorted(event_hashes.items()))

    content_hash = sha256_hash(
        canonical_json(sorted_event_hashes)
    )

    newest_event_iso = None

    if newest_event_time is not None:
        newest_event_iso = (
            datetime.fromtimestamp(
                newest_event_time / 1000,
                tz=timezone.utc,
            ).isoformat()
        )

    fingerprint_duration = time.perf_counter() - started_at

    return {
        "schema": sorted(schema),
        "count": len(features),
        "event_hashes": sorted_event_hashes,
        "content_hash": content_hash,
        "fetch_duration_seconds": round(
            float(fetch_duration_seconds), 6
        ),
        "fingerprint_duration_seconds": round(
            fingerprint_duration, 6
        ),
        "fetch_status": fetch_status,
        "newest_event_time": newest_event_iso,
        "fetched_at": fetched_at.isoformat(),
    }
