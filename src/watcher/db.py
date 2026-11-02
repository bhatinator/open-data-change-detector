
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





if __name__ == "__main__":
    test_connection()
