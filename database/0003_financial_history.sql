-- Private, additive revision journal for the V46 research warehouse.
CREATE TABLE IF NOT EXISTS financial_revision (
 subject TEXT NOT NULL, period_end TEXT NOT NULL, period_label TEXT NOT NULL,
 currency TEXT NOT NULL, fingerprint TEXT NOT NULL, observed_at TEXT NOT NULL,
 published_at TEXT, source_url TEXT NOT NULL, payload TEXT NOT NULL,
 previous_fingerprint TEXT,
 PRIMARY KEY(subject,period_end,period_label,currency,fingerprint)
);
CREATE INDEX IF NOT EXISTS financial_revision_lookup ON financial_revision(subject,period_end,observed_at);
CREATE TABLE IF NOT EXISTS identity_revision (
 ticker TEXT NOT NULL, fingerprint TEXT NOT NULL, observed_at TEXT NOT NULL,
 source_url TEXT, payload TEXT NOT NULL, previous_fingerprint TEXT,
 PRIMARY KEY(ticker,fingerprint)
);
CREATE TABLE IF NOT EXISTS corporate_event_revision (
 ticker TEXT NOT NULL, event_type TEXT NOT NULL, event_date TEXT NOT NULL,
 fingerprint TEXT NOT NULL, observed_at TEXT NOT NULL,
 source_url TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(ticker,event_type,event_date,fingerprint)
);
