-- Separate private SQLite warehouse. Never place the database in public Pages assets.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS listing_observation (
 ticker TEXT NOT NULL, observed_at TEXT NOT NULL, fingerprint TEXT NOT NULL,
 name TEXT NOT NULL, mic TEXT, isin TEXT, source_url TEXT, status TEXT NOT NULL,
 PRIMARY KEY(ticker,observed_at,fingerprint)
);
CREATE TABLE IF NOT EXISTS corporate_action_evidence (
 ticker TEXT NOT NULL, fingerprint TEXT NOT NULL, predecessor_ticker TEXT,
 predecessor_isin TEXT, successor_isin TEXT, effective_date TEXT,
 history_policy TEXT NOT NULL, source_url TEXT NOT NULL,
 PRIMARY KEY(ticker,fingerprint)
);
CREATE TABLE IF NOT EXISTS filing_fact (
 issuer TEXT NOT NULL, period_end TEXT NOT NULL, period_label TEXT NOT NULL,
 published_at TEXT NOT NULL, currency TEXT NOT NULL, metric TEXT NOT NULL,
 amount REAL NOT NULL, source_url TEXT NOT NULL, fingerprint TEXT NOT NULL,
 PRIMARY KEY(issuer,period_end,metric,fingerprint)
);
CREATE TABLE IF NOT EXISTS open_snapshot (
 dataset_id TEXT NOT NULL, fingerprint TEXT NOT NULL, source_url TEXT NOT NULL,
 license TEXT NOT NULL, retrieved_at TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(dataset_id,fingerprint)
);
CREATE TABLE IF NOT EXISTS licensed_bar (
 ticker TEXT NOT NULL, session TEXT NOT NULL, provider TEXT NOT NULL,
 isin TEXT NOT NULL, mic TEXT NOT NULL, currency TEXT NOT NULL,
 adjusted INTEGER NOT NULL CHECK(adjusted IN(0,1)), close REAL NOT NULL CHECK(close>0),
 volume INTEGER CHECK(volume>=0), entitlement_hash TEXT NOT NULL,
 PRIMARY KEY(ticker,session,provider,entitlement_hash)
);
CREATE INDEX IF NOT EXISTS licensed_bar_history ON licensed_bar(ticker,session);
CREATE TABLE IF NOT EXISTS research_indicator (
 subject TEXT NOT NULL, date TEXT NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL,
 methodology TEXT NOT NULL, evidence_hash TEXT NOT NULL,
 export_allowed INTEGER NOT NULL DEFAULT 0 CHECK(export_allowed IN(0,1)),
 PRIMARY KEY(subject,date,metric,methodology,evidence_hash)
);
