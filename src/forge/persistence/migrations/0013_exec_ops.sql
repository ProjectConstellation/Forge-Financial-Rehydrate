-- FORGE EXECUTIVE OPS: 10-s economic marks, executive objectives, engineering tickets, owner transfers.
CREATE TABLE econ_ticks (
  ts REAL PRIMARY KEY,
  live_total_usd REAL,          -- wallet truth (Coinbase + Kalshi)
  paper_equity_usd REAL,
  realized_cum_usd REAL,        -- paper realized P&L, cumulative
  live_realized_cum_usd REAL,   -- live realized (Kalshi live + live spot), cumulative
  fees_cum_usd REAL,
  inference_cum_usd REAL,
  compute_cum_usd REAL,
  deployed_usd REAL,
  unrealized_usd REAL
);
CREATE TABLE ops_objectives (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,           -- grow_profit | integrate_platform | fix | custom
  objective TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  directive_ids TEXT,
  ticket_id INTEGER,
  summary TEXT,
  done_ts REAL
);
CREATE TABLE eng_tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  title TEXT NOT NULL,
  spec TEXT,
  credential_needed TEXT,
  status TEXT NOT NULL DEFAULT 'OPEN',   -- OPEN | IN_PROGRESS | DONE | REJECTED
  requested_by TEXT,
  resolution TEXT,
  done_ts REAL
);
CREATE TABLE ops_transfers (
  id TEXT PRIMARY KEY,
  ts REAL NOT NULL,
  amount_usd REAL NOT NULL,
  currency TEXT NOT NULL,
  destination TEXT NOT NULL,
  status TEXT NOT NULL,          -- PREVIEWED | EXECUTED | FAILED | BLOCKED | EXPIRED
  fee_usd REAL,
  treasury_before REAL,
  treasury_after REAL,
  venue_ref TEXT,
  detail TEXT
);
