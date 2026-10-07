-- Generic paper/shadow round trips for any non-core rail (peg maker, future rails): the allocator scores rails from these.
CREATE TABLE shadow_trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  rail TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  qty REAL NOT NULL,
  entry REAL NOT NULL,
  exit REAL,
  fee_usd REAL NOT NULL DEFAULT 0,
  pnl_usd REAL,
  hold_s REAL,
  detail TEXT
);
CREATE INDEX ix_shadow_trades ON shadow_trades(rail, ts);
