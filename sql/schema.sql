CREATE TABLE IF NOT EXISTS watches (
    id SERIAL PRIMARY KEY, 
    name TEXT UNIQUE NOT NULL, 
    config JSONB NOT NULL
    );
    

CREATE TABLE IF NOT EXISTS snapshots (
  id SERIAL PRIMARY KEY, 
  watch_id INT REFERENCES watches(id),
  fetched_at TIMESTAMPTZ DEFAULT now(), 
  status TEXT,
  event_count INT, 
  schema_json JSONB, 
  content_hash TEXT,
  newest_event_ms BIGINT, 
  fetch_ms INT
  );


CREATE TABLE IF NOT EXISTS event_state (
  watch_id INT, 
  event_id TEXT, 
  event_hash TEXT,
  first_seen TIMESTAMPTZ, 
  last_seen TIMESTAMPTZ, 
  last_changed TIMESTAMPTZ,
  PRIMARY KEY (watch_id, event_id)
  );


CREATE TABLE IF NOT EXISTS alerts (
  id SERIAL PRIMARY KEY, 
  watch_id INT, 
  created_at TIMESTAMPTZ DEFAULT now(),
  alert_type TEXT, 
  details JSONB
  );

  
CREATE TABLE IF NOT EXISTS snapshot_events (
    snapshot_id INT REFERENCES snapshots(id) ON DELETE CASCADE,
    event_id TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_watch_fetched
ON snapshots (watch_id, fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_watch_created
ON alerts (watch_id, created_at DESC);
