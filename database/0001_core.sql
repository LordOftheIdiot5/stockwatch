-- Stockwatch research database (Cloudflare D1 / SQLite)
-- Headlines and source metadata only; do not store publisher article bodies.
CREATE TABLE IF NOT EXISTS news_items (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    company_name TEXT NOT NULL,
    sector TEXT,
    kind TEXT NOT NULL CHECK(kind IN ('news','disclosure')),
    headline TEXT NOT NULL,
    original_language TEXT,
    translated_headline TEXT,
    publisher TEXT,
    original_url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    source_match TEXT NOT NULL DEFAULT 'unverified',
    regulatory INTEGER NOT NULL DEFAULT 0,
    CHECK(length(id) BETWEEN 1 AND 512),
    CHECK(substr(original_url,1,8)='https://')
);
CREATE INDEX IF NOT EXISTS news_by_date ON news_items(published_at DESC,id DESC);
CREATE INDEX IF NOT EXISTS news_by_ticker_date ON news_items(ticker,published_at DESC);
CREATE INDEX IF NOT EXISTS news_by_sector_date ON news_items(sector,published_at DESC);
CREATE INDEX IF NOT EXISTS news_by_kind_date ON news_items(kind,published_at DESC);

CREATE TABLE IF NOT EXISTS corporate_events (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    event_date TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    source_url TEXT NOT NULL,
    verification TEXT NOT NULL CHECK(verification IN ('verified','provisional')),
    retrieved_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS corporate_events_by_date ON corporate_events(event_date,ticker);

-- Store freight observations only with a licensed redistribution entitlement.
CREATE TABLE IF NOT EXISTS freight_observations (
    route_code TEXT NOT NULL,
    observation_date TEXT NOT NULL,
    provider TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    source_url TEXT,
    redistribution_permitted INTEGER NOT NULL DEFAULT 0 CHECK(redistribution_permitted IN (0,1)),
    PRIMARY KEY (route_code,observation_date,provider)
);
CREATE INDEX IF NOT EXISTS freight_by_route_date ON freight_observations(route_code,observation_date DESC);

CREATE TABLE IF NOT EXISTS share_class_observations (
    pair_id TEXT NOT NULL,
    observation_date TEXT NOT NULL,
    a_ticker TEXT NOT NULL,
    b_ticker TEXT NOT NULL,
    a_close REAL NOT NULL CHECK(a_close>0),
    b_close REAL NOT NULL CHECK(b_close>0),
    currency TEXT NOT NULL,
    adjusted INTEGER NOT NULL DEFAULT 0 CHECK(adjusted IN (0,1)),
    source TEXT NOT NULL,
    PRIMARY KEY (pair_id,observation_date)
);
CREATE INDEX IF NOT EXISTS pair_by_date ON share_class_observations(pair_id,observation_date DESC);

CREATE TABLE IF NOT EXISTS source_health_daily (
    source TEXT NOT NULL,
    scan_timestamp TEXT NOT NULL,
    requests INTEGER NOT NULL,
    succeeded INTEGER NOT NULL,
    failed INTEGER NOT NULL,
    PRIMARY KEY(source,scan_timestamp)
);
