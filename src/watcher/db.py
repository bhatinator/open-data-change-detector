
import os
import psycopg
from psycopg.types.json import Jsonb





def get_connection():
    """Open a connection to the PostgreSQL database."""
    return psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "dataset_watcher"),
        user=os.environ.get("PGUSER", "watcher"),
        password=os.environ["PGPASSWORD"],
    )


def test_connection():
    """Check that Python can connect to PostgreSQL."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT current_database(), version();"
            )
            database, version = cur.fetchone()

            print(f"Connected to database: {database}")
            print(f"PostgreSQL version: {version}")


def upsert_watch(name, config):
    """Insert a watch, or update its config if it already exists."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO watches (name, config)
                VALUES (%s, %s)
                ON CONFLICT (name)
                DO UPDATE SET config = EXCLUDED.config
                RETURNING id;
                """,
                (name, Jsonb(config)),
            )
            return cur.fetchone()[0]



def save_snapshot(watch_id, fingerprint):
    """Save one successful fetch's fingerprint."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO snapshots (
                    watch_id,
                    status,
                    event_count,
                    schema_json,
                    content_hash,
                    newest_event_ms,
                    fetch_ms
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    watch_id,
                    fingerprint.get("fetch_status", "success"),
                    fingerprint.get("count", 0),
                    Jsonb(fingerprint.get("schema", [])),
                    fingerprint.get("content_hash"),
                    fingerprint.get("newest_event_ms"),
                    round(
                        fingerprint.get(
                            "fetch_duration_seconds", 0
                        ) * 1000
                    ),
                ),
            )

            return cur.fetchone()[0]


def upsert_event_state(watch_id, event_id, event_hash):
    """
    Insert a new earthquake event or update an existing event.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_state (
                    watch_id,
                    event_id,
                    event_hash,
                    first_seen,
                    last_seen,
                    last_changed
                )
                VALUES (%s, %s, %s, NOW(), NOW(), NOW())

                ON CONFLICT (watch_id, event_id)

                DO UPDATE SET
                    last_changed = CASE
                        WHEN event_state.event_hash
                             IS DISTINCT FROM EXCLUDED.event_hash
                        THEN NOW()
                        ELSE event_state.last_changed
                    END,
                    last_seen = NOW(),
                    event_hash = EXCLUDED.event_hash;
                """,
                (watch_id, event_id, event_hash),
            )


def get_latest_snapshot(watch_id):
    """Get the most recent successful snapshot for a watch."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    event_count,
                    schema_json,
                    content_hash,
                    newest_event_ms,
                    fetched_at
                FROM snapshots
                WHERE watch_id = %s
                  AND status = 'success'
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1;
                """,
                (watch_id,),
            )

            row = cur.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "count": row[1],
                "schema": row[2],
                "content_hash": row[3],
                "newest_event_ms": row[4],
                "fetched_at": row[5],
            }


def get_snapshot_events(snapshot_id):
    """Load all event hashes belonging to one snapshot."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id, event_hash
                FROM snapshot_events
                WHERE snapshot_id = %s;
                """,
                (snapshot_id,),
            )

            return dict(cur.fetchall())


def save_run(
    watch_id,
    fingerprint,
    alerts,
    event_hashes,
):
    """
    Save snapshot, snapshot event hashes, event state,
    and alerts together in one database transaction.
    """

    from psycopg.types.json import Jsonb

    with get_connection() as conn:
        with conn.cursor() as cur:

            # 1. Insert the snapshot.
            cur.execute(
                """
                INSERT INTO snapshots (
                    watch_id,
                    status,
                    event_count,
                    schema_json,
                    content_hash,
                    newest_event_ms,
                    fetch_ms
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    watch_id,
                    fingerprint.get("fetch_status", "success"),
                    fingerprint.get("count", 0),
                    Jsonb(fingerprint.get("schema", [])),
                    fingerprint.get("content_hash"),
                    fingerprint.get("newest_event_ms"),
                    round(
                        fingerprint.get(
                            "fetch_duration_seconds", 0
                        ) * 1000
                    ),
                ),
            )

            snapshot_id = cur.fetchone()[0]

            # 2. Save the event hashes for this snapshot.
            snapshot_rows = [
                (snapshot_id, event_id, event_hash_value)
                for event_id, event_hash_value
                in event_hashes.items()
            ]

            if snapshot_rows:
                cur.executemany(
                    """
                    INSERT INTO snapshot_events (
                        snapshot_id,
                        event_id,
                        event_hash
                    )
                    VALUES (%s, %s, %s);
                    """,
                    snapshot_rows,
                )

            # 3. Update the latest known event state.
            event_rows = [
                (watch_id, event_id, event_hash_value)
                for event_id, event_hash_value
                in event_hashes.items()
            ]

            if event_rows:
                cur.executemany(
                    """
                    INSERT INTO event_state (
                        watch_id,
                        event_id,
                        event_hash,
                        first_seen,
                        last_seen,
                        last_changed
                    )
                    VALUES (
                        %s, %s, %s, NOW(), NOW(), NOW()
                    )
                    ON CONFLICT (watch_id, event_id)
                    DO UPDATE SET
                        last_changed = CASE
                            WHEN event_state.event_hash
                                 IS DISTINCT FROM EXCLUDED.event_hash
                            THEN NOW()
                            ELSE event_state.last_changed
                        END,
                        last_seen = NOW(),
                        event_hash = EXCLUDED.event_hash;
                    """,
                    event_rows,
                )

            # 4. Save all generated alerts.
            alert_rows = [
                (
                    watch_id,
                    alert["alert_type"],
                    Jsonb(alert["details"]),
                )
                for alert in alerts
            ]

            if alert_rows:
                cur.executemany(
                    """
                    INSERT INTO alerts (
                        watch_id,
                        alert_type,
                        details
                    )
                    VALUES (%s, %s, %s);
                    """,
                    alert_rows,
                )

            return snapshot_id




if __name__ == "__main__":
    test_connection()
