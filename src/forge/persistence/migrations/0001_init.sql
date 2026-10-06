-- FORGE baseline schema. Money is stored as TEXT decimals (exact). Timestamps are UTC ISO-8601 or ns ints.

CREATE TABLE kv_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Immutable journal of every value movement. book = live | paper | shadow | sim
CREATE TABLE ledger_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  book TEXT NOT NULL,
  account TEXT NOT NULL,
  kind TEXT NOT NULL,
  asset TEXT NOT NULL DEFAULT 'USD',
  qty TEXT NOT NULL DEFAULT '0',
  amount_usd TEXT NOT NULL,
  strategy_id TEXT,
  ref_type TEXT,
  ref_id TEXT,
  idem_key TEXT UNIQUE,
  memo TEXT
);
CREATE INDEX ix_ledger_book_ts ON ledger_entries(book, ts);
CREATE INDEX ix_ledger_strategy ON ledger_entries(strategy_id);
CREATE TRIGGER ledger_no_update BEFORE UPDATE ON ledger_entries
BEGIN SELECT RAISE(ABORT, 'ledger_entries is append-only'); END;
CREATE TRIGGER ledger_no_delete BEFORE DELETE ON ledger_entries
BEGIN SELECT RAISE(ABORT, 'ledger_entries is append-only'); END;

CREATE TABLE strategies (
  id TEXT PRIMARY KEY,
  family TEXT NOT NULL,
  generation INTEGER NOT NULL DEFAULT 0,
  population TEXT NOT NULL,           -- CHAMPION | CHALLENGER | RESEARCH | HIBERNATING | RETIRED | QUARANTINED
  genome TEXT NOT NULL,
  genome_hash TEXT NOT NULL,
  parent_ids TEXT NOT NULL DEFAULT '[]',
  hypothesis TEXT,
  fitness REAL,
  virtual_allocation_usd TEXT NOT NULL DEFAULT '0',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  status_reason TEXT
);
CREATE INDEX ix_strategies_pop ON strategies(population);

CREATE TABLE strategy_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  strategy_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  from_population TEXT,
  to_population TEXT NOT NULL,
  reason TEXT,
  evidence TEXT
);

CREATE TABLE lineage_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_id TEXT NOT NULL,
  child_id TEXT NOT NULL,
  edge_type TEXT NOT NULL,            -- MUTATED_FROM | CROSSOVER_OF | REGIME_SPECIALIZATION_OF | RESURRECTED_FROM | OUTPERFORMED_BY | RETIRED_BY
  created_at TEXT NOT NULL,
  data TEXT
);
CREATE INDEX ix_lineage_parent ON lineage_edges(parent_id);
CREATE INDEX ix_lineage_child ON lineage_edges(child_id);

CREATE TABLE mutations (
  id TEXT PRIMARY KEY,
  parent_id TEXT NOT NULL,
  child_id TEXT NOT NULL,
  operator TEXT NOT NULL,
  source TEXT NOT NULL,               -- failure | success | regime | feature | parameter | structural | crossover | novel | missed | adversarial | discovery
  rationale TEXT NOT NULL,
  created_at TEXT NOT NULL,
  result TEXT,
  promoted INTEGER,
  evaluated_at TEXT
);

CREATE TABLE experiments (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,                 -- backtest | walkforward | montecarlo | perturbation | shadow | tournament
  strategy_id TEXT,
  params TEXT,
  status TEXT NOT NULL,
  result TEXT,
  location TEXT,                      -- local | modal
  cost_usd TEXT NOT NULL DEFAULT '0',
  hypotheses_tested INTEGER NOT NULL DEFAULT 1,
  started_at TEXT NOT NULL,
  finished_at TEXT
);
CREATE INDEX ix_experiments_strategy ON experiments(strategy_id);

CREATE TABLE strategy_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  strategy_id TEXT NOT NULL,
  scope TEXT NOT NULL,                -- backtest | walkforward | shadow | paper | live
  regime TEXT NOT NULL DEFAULT 'ALL',
  window_start TEXT,
  window_end TEXT,
  metrics TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX ix_smetrics ON strategy_metrics(strategy_id, scope, regime);

CREATE TABLE opportunities (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  ts_ns INTEGER NOT NULL,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  strategy_id TEXT,
  family TEXT,
  direction TEXT NOT NULL,
  score REAL NOT NULL,
  expected_net_bps REAL NOT NULL,
  probability REAL,
  components TEXT NOT NULL,
  status TEXT NOT NULL,               -- NEW | ACTED | REJECTED | EXPIRED
  reason TEXT,
  ref_price TEXT,
  horizon_s INTEGER,
  expires_ns INTEGER,
  outcome TEXT,                       -- counterfactual evaluation (missed-opportunity learning)
  evaluated_at TEXT
);
CREATE INDEX ix_opp_status ON opportunities(status, ts_ns);
CREATE INDEX ix_opp_eval ON opportunities(evaluated_at, ts_ns);

CREATE TABLE trade_intents (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  book TEXT NOT NULL,
  opportunity_id TEXT,
  strategy_id TEXT NOT NULL,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  purpose TEXT NOT NULL,              -- entry | exit | cashout | emergency
  requested_notional TEXT NOT NULL,
  approved_notional TEXT,
  order_type TEXT NOT NULL,
  limit_price TEXT,
  max_slippage_bps TEXT NOT NULL,
  exit_plan TEXT,
  evidence TEXT,
  status TEXT NOT NULL,               -- PROPOSED | APPROVED | REDUCED | REJECTED | SUBMITTED | DONE | FAILED
  idem_key TEXT NOT NULL UNIQUE
);

CREATE TABLE risk_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  intent_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  decision TEXT NOT NULL,             -- APPROVE | REDUCE | REJECT
  approved_notional TEXT,
  reasons TEXT NOT NULL,
  checks TEXT NOT NULL
);
CREATE INDEX ix_risk_intent ON risk_decisions(intent_id);

CREATE TABLE orders (
  id TEXT PRIMARY KEY,
  intent_id TEXT,
  book TEXT NOT NULL,
  venue TEXT NOT NULL,
  client_order_id TEXT NOT NULL UNIQUE,
  venue_order_id TEXT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  order_type TEXT NOT NULL,
  limit_price TEXT,
  base_size TEXT,
  quote_size TEXT,
  post_only INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,               -- PENDING | OPEN | FILLED | PARTIAL | CANCELLED | REJECTED | EXPIRED | UNKNOWN
  filled_size TEXT NOT NULL DEFAULT '0',
  avg_fill_price TEXT,
  fees TEXT NOT NULL DEFAULT '0',
  submitted_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  reject_reason TEXT,
  raw TEXT
);
CREATE INDEX ix_orders_status ON orders(book, status);

CREATE TABLE fills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT NOT NULL,
  book TEXT NOT NULL,
  venue TEXT NOT NULL,
  trade_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  price TEXT NOT NULL,
  size TEXT NOT NULL,
  fee TEXT NOT NULL,
  liquidity TEXT,
  ts TEXT NOT NULL,
  UNIQUE(venue, book, trade_id)
);

CREATE TABLE positions (
  id TEXT PRIMARY KEY,
  book TEXT NOT NULL,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  strategy_id TEXT NOT NULL,
  opportunity_id TEXT,
  status TEXT NOT NULL,               -- OPENING | OPEN | CLOSING | CLOSED
  qty TEXT NOT NULL DEFAULT '0',
  cost_usd TEXT NOT NULL DEFAULT '0',
  entry_price TEXT,
  exit_price TEXT,
  fees_usd TEXT NOT NULL DEFAULT '0',
  realized_pnl_usd TEXT NOT NULL DEFAULT '0',
  opened_at TEXT NOT NULL,
  closed_at TEXT,
  exit_plan TEXT,
  exit_reason TEXT,
  meta TEXT
);
CREATE INDEX ix_positions_status ON positions(book, status);

CREATE TABLE balance_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  book TEXT NOT NULL,
  venue TEXT NOT NULL,
  asset TEXT NOT NULL,
  available TEXT NOT NULL,
  hold TEXT NOT NULL,
  source TEXT NOT NULL
);

CREATE TABLE inference_calls (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  agent TEXT NOT NULL,
  purpose TEXT NOT NULL,
  model TEXT NOT NULL,
  effort TEXT,
  prompt_version TEXT,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  cached_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  cost_usd TEXT NOT NULL DEFAULT '0',
  latency_ms INTEGER,
  tool_calls TEXT,
  result_class TEXT,
  affected_live INTEGER NOT NULL DEFAULT 0,
  strategy_id TEXT,
  opportunity_id TEXT,
  error TEXT
);

CREATE TABLE compute_jobs (
  id TEXT PRIMARY KEY,
  ts_start TEXT NOT NULL,
  ts_end TEXT,
  kind TEXT NOT NULL,
  location TEXT NOT NULL,             -- LOCAL_NORMAL | LOCAL_SURGE | MODAL_BURST
  parent_id TEXT,
  strategy_ids TEXT,
  cpu REAL,
  memory_mb INTEGER,
  duration_s REAL,
  est_cost_usd TEXT NOT NULL DEFAULT '0',
  status TEXT NOT NULL,
  changed_decision INTEGER,
  value_estimate_usd TEXT,
  error TEXT
);

CREATE TABLE episodes (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  kind TEXT NOT NULL,
  summary TEXT NOT NULL,
  strategy_id TEXT,
  family TEXT,
  regime TEXT,
  importance REAL NOT NULL DEFAULT 0.5,
  data TEXT
);
CREATE INDEX ix_episodes_kind ON episodes(kind, ts);

CREATE TABLE lessons (
  id TEXT PRIMARY KEY,
  statement TEXT NOT NULL,
  family TEXT,
  regime TEXT,
  confidence REAL NOT NULL,
  supporting TEXT NOT NULL DEFAULT '[]',
  contradicting TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TEXT NOT NULL,
  last_validated_at TEXT
);

CREATE TABLE timeline (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  agent TEXT NOT NULL,
  level TEXT NOT NULL DEFAULT 'info',
  message TEXT NOT NULL,
  data TEXT
);
CREATE INDEX ix_timeline_ts ON timeline(ts);

CREATE TABLE alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  level TEXT NOT NULL,
  code TEXT NOT NULL,
  message TEXT NOT NULL,
  acked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE market_rules (
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (venue, symbol)
);

CREATE TABLE calibration_points (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  strategy_id TEXT,
  family TEXT,
  regime TEXT,
  predicted REAL NOT NULL,
  outcome INTEGER NOT NULL,
  source TEXT NOT NULL,               -- backtest | shadow | paper | live | counterfactual
  ts TEXT NOT NULL
);
CREATE INDEX ix_calib ON calibration_points(strategy_id, source);

CREATE TABLE venue_catalog (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  category TEXT NOT NULL,
  status TEXT NOT NULL,
  data TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE config_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  actor TEXT NOT NULL,
  change TEXT NOT NULL
);

CREATE TABLE research_notes (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  author TEXT NOT NULL,
  kind TEXT NOT NULL,                 -- note | postmortem | hypothesis | self_review
  strategy_id TEXT,
  title TEXT NOT NULL,
  body TEXT NOT NULL
);
