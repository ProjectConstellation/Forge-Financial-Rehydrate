-- FORGE Profit Velocity history (15-min snapshots): realized/expected $/h, target, verified idle rewards baseline.
CREATE TABLE velocity_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  treasury REAL,
  realized_1h REAL,
  realized_24h REAL,
  live_usd_per_h REAL,
  proven_usd_per_h REAL,
  potential_usd_per_h REAL,
  target REAL,
  rewards_usdc REAL,
  payload TEXT
);
CREATE INDEX ix_velocity_history_ts ON velocity_history(ts);
