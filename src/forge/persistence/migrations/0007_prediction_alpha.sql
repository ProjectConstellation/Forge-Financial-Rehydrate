-- Hermes dossier §9–§11: surface residuals, order flow in calibration, lead/lag ticks, edge decay, RTI proxy error.
ALTER TABLE crossrail_calibration ADD COLUMN flow REAL;
ALTER TABLE crossrail_calibration ADD COLUMN direction INTEGER;
ALTER TABLE crossrail_calibration ADD COLUMN p_surface REAL;
CREATE TABLE crossrail_ticks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  underlying TEXT NOT NULL,
  event_ticker TEXT NOT NULL,
  spot REAL NOT NULL,
  implied_median REAL NOT NULL
);
CREATE INDEX ix_crossrail_ticks ON crossrail_ticks(underlying, ts);
CREATE TABLE edge_decay (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id INTEGER NOT NULL,
  dt_s REAL NOT NULL,
  edge REAL NOT NULL
);
CREATE INDEX ix_edge_decay ON edge_decay(signal_id);
CREATE TABLE rti_proxy (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  ticker TEXT NOT NULL UNIQUE,
  underlying TEXT,
  close_ts REAL,
  settlement_value REAL,
  coinbase_close REAL,
  log_error REAL
);
