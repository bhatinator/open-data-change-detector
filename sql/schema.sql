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