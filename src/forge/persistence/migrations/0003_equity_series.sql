-- Real-time portal history: one row per minute (book equity, true net, real Coinbase account total).
CREATE TABLE equity_series (
  ts TEXT NOT NULL,
  book TEXT NOT NULL,
  equity_usd REAL,
  true_net_usd REAL,
  account_total_usd REAL,
  invested_usd REAL
);
CREATE INDEX ix_equity_series ON equity_series(book, ts);
