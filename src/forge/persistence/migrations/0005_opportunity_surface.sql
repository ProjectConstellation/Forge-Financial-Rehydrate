-- OP-013 Opportunity Surface Registry, cross-rail evidence, Listing Sentinel.
CREATE TABLE rail_registry (
  id TEXT PRIMARY KEY,                 -- e.g. coinbase.spot, coinbase.equity, kalshi.events
  provider TEXT NOT NULL,
  category TEXT NOT NULL,
  status TEXT NOT NULL,                -- DISCOVERED | DATA_ONLY | CANDIDATE | SHADOW | LIVE_ELIGIBLE | LIVE | BLOCKED | UNAVAILABLE
  executable INTEGER NOT NULL DEFAULT 0,
  blockers TEXT,                       -- json list (what is missing: credentials, eligibility, policy)
  capabilities TEXT,                   -- json (discovered facts: product counts, fee model, minimums, sessions, settlement)
  economics TEXT,                      -- json (rail score inputs and output)
  first_seen TEXT NOT NULL,
  last_probe TEXT NOT NULL,
  probe_ok INTEGER NOT NULL DEFAULT 1,
  probe_error TEXT
);
CREATE TABLE rail_probes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  rail_id TEXT NOT NULL,
  ok INTEGER NOT NULL,
  status TEXT,
  summary TEXT
);
CREATE INDEX ix_rail_probes ON rail_probes(rail_id, ts);
CREATE TABLE listing_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  product_id TEXT NOT NULL,
  product_type TEXT,
  event TEXT NOT NULL,                 -- NEW_PRODUCT | STATUS_CHANGE | DELISTED | TRADING_ENABLED | TRADING_DISABLED
  before TEXT,
  after TEXT
);
CREATE INDEX ix_listing_events ON listing_events(ts);
CREATE TABLE crossrail_signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,                  -- TAKE | MAKE | MODEL_RAW | LADDER_ARB | RANGE_ARB
  ticker TEXT NOT NULL,
  event_ticker TEXT,
  series TEXT,
  underlying TEXT,
  ref_price REAL,
  sigma_min REAL,
  minutes REAL,
  side TEXT NOT NULL,
  price REAL NOT NULL,
  fee REAL NOT NULL,
  edge REAL NOT NULL,
  p_model REAL, p_market REAL, p_stacked REAL, p_lcb REAL,
  kelly REAL,
  close_ts REAL,
  expires_ts REAL,
  fill_ts REAL,
  status TEXT NOT NULL,                -- QUOTED | OPEN | EXPIRED | SETTLED
  payout REAL, pnl REAL, settled_ts REAL,
  detail TEXT
);
CREATE INDEX ix_crossrail_signals ON crossrail_signals(status, close_ts);
CREATE INDEX ix_crossrail_signals_t ON crossrail_signals(ticker, side, kind);
CREATE TABLE crossrail_calibration (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  ticker TEXT NOT NULL,
  series TEXT, underlying TEXT,
  ref_price REAL, sigma_min REAL, minutes REAL,
  p_model REAL NOT NULL, p_market REAL NOT NULL, p_stacked REAL,
  spread REAL,
  close_ts REAL,
  outcome INTEGER
);
CREATE INDEX ix_crossrail_calibration ON crossrail_calibration(outcome, close_ts);
CREATE INDEX ix_crossrail_calibration_t ON crossrail_calibration(ticker);
