-- Step 8: Notification outbox

CREATE TABLE IF NOT EXISTS notification_outbox (
    id SERIAL PRIMARY KEY,

    watch_id INT REFERENCES watches(id),

    alert_id INT REFERENCES alerts(id),

    created_at TIMESTAMPTZ DEFAULT now(),

    status TEXT NOT NULL DEFAULT 'pending',

    notification_type TEXT NOT NULL,

    dedupe_key TEXT UNIQUE NOT NULL,

    payload JSONB NOT NULL,

    sent_at TIMESTAMPTZ,

    attempts INT NOT NULL DEFAULT 0,

    last_error TEXT
);


-- Find pending notifications efficiently
CREATE INDEX IF NOT EXISTS idx_notification_outbox_pending
ON notification_outbox(status, created_at);


-- Find notifications for a watch
CREATE INDEX IF NOT EXISTS idx_notification_outbox_watch
ON notification_outbox(watch_id);


-- Find notifications for an alert
CREATE INDEX IF NOT EXISTS idx_notification_outbox_alert
ON notification_outbox(alert_id);