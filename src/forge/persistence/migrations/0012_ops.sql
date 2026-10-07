-- FORGE OPS COMMANDER: operator directives to Hermes roles, full audit trail, out-of-band confirmations.
CREATE TABLE ops_directives (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  role TEXT NOT NULL,              -- governor | alpha_inventor | adversary | critic | doctor | rail_hunter | architect | all
  instruction TEXT NOT NULL,
  priority TEXT NOT NULL DEFAULT 'normal',
  status TEXT NOT NULL DEFAULT 'OPEN',   -- OPEN | DONE | CANCELLED
  requested_by TEXT,
  result TEXT,
  done_ts REAL,
  report_id INTEGER
);
CREATE INDEX ix_ops_directives ON ops_directives(status, role);
CREATE TABLE ops_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  actor TEXT NOT NULL,
  channel TEXT,
  action TEXT NOT NULL,
  args TEXT,
  outcome TEXT NOT NULL,           -- OK | DENIED | ERROR | PENDING_CONFIRMATION | RATE_LIMITED
  detail TEXT
);
CREATE INDEX ix_ops_audit_ts ON ops_audit(ts);
CREATE TABLE ops_pending (
  id TEXT PRIMARY KEY,
  ts REAL NOT NULL,
  action TEXT NOT NULL,
  params TEXT,
  code_hash TEXT NOT NULL,
  expires_ts REAL NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'PENDING',   -- PENDING | EXECUTED | EXPIRED | REJECTED
  decided_ts REAL,
  result TEXT
);
