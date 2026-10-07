-- SAGE-1 settlement-window engine: model vs market in the final 5 minutes of CF-settled Kalshi crypto markets.
CREATE TABLE sw_calibration (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  ticker TEXT NOT NULL,
  series TEXT,
  underlying TEXT,
  secs_to_close REAL,
  n_realized INTEGER,
  p_model REAL,
  p_cons_yes REAL,
  p_cons_no REAL,
  yes_bid REAL,
  yes_ask REAL,
  close_ts REAL,
  outcome INTEGER
);
CREATE INDEX ix_sw_cal_ticker ON sw_calibration(ticker, outcome);
CREATE INDEX ix_sw_cal_close ON sw_calibration(close_ts);
