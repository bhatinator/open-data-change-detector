-- 1. Store the complete event JSON for every snapshot.
ALTER TABLE snapshot_events
ADD COLUMN IF NOT EXISTS event_data JSONB;


-- 2. Notification outbox.
CREATE TABLE IF NOT EXISTS notification_outbox (
    id SERIAL PRIMARY KEY,

    watch_id INT NOT NULL
        REFERENCES watches(id),

    alert_type TEXT NOT NULL,

    dedupe_key TEXT NOT NULL UNIQUE,

    payload JSONB NOT NULL,

    status TEXT NOT NULL DEFAULT 'pending',

    attempts INT NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    sent_at TIMESTAMPTZ,

    last_error TEXT
);


-- 3. Index for pending notifications.
CREATE INDEX IF NOT EXISTS
idx_notification_outbox_pending
ON notification_outbox(status, created_at);


-- 4. Index snapshot events by snapshot.
CREATE INDEX IF NOT EXISTS
idx_snapshot_events_snapshot_id
ON snapshot_events(snapshot_id);