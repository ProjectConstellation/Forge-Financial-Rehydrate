-- Kalshi LIVE orders for the pre-registered TAKE_THRESH signal (real money; P&L from fills + real settlement).
CREATE TABLE kalshi_live_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  signal_id INTEGER NOT NULL,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL,
  limit_price REAL NOT NULL,
  count INTEGER NOT NULL,
  client_order_id TEXT NOT NULL UNIQUE,
  order_id TEXT,
  status TEXT NOT NULL,           -- SUBMITTED | FILLED | NO_FILL | REJECTED | SETTLED
  fill_count INTEGER,
  avg_price REAL,
  fee REAL,
  cost REAL,
  close_ts REAL,
  payout REAL,
  pnl REAL,
  shadow_pnl REAL,
  settled_ts REAL,
  error TEXT
);
CREATE INDEX ix_kalshi_live_orders ON kalshi_live_orders(status, close_ts);
