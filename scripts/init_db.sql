CREATE TABLE IF NOT EXISTS events (
    event_id   TEXT PRIMARY KEY,
    ts         TIMESTAMPTZ NOT NULL DEFAULT now(),
    source     TEXT,
    log_type   TEXT,
    severity   TEXT,
    message    TEXT,
    fields     JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id      TEXT PRIMARY KEY,
    event_id      TEXT NOT NULL REFERENCES events(event_id),
    score         REAL NOT NULL,
    label         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new',
    model_version TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_severity ON events (severity);
CREATE INDEX IF NOT EXISTS idx_events_source ON events (source);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);
CREATE INDEX IF NOT EXISTS idx_alerts_score ON alerts (score);
CREATE INDEX IF NOT EXISTS idx_alerts_event_id ON alerts (event_id);
