-- Institutional workforce: workflows, handoffs, results ledger, role heartbeats
CREATE TABLE IF NOT EXISTS agent_workflows (
  workflow_id TEXT PRIMARY KEY,
  objective_id TEXT,
  type TEXT NOT NULL,
  stage TEXT NOT NULL,
  owner TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at REAL NOT NULL,
  due_at REAL,
  completed_at REAL,
  result_type TEXT,
  confidence REAL,
  inputs_json TEXT,
  outputs_json TEXT,
  evidence_refs TEXT,
  skip_reason TEXT
);

CREATE TABLE IF NOT EXISTS agent_handoffs (
  handoff_id TEXT PRIMARY KEY,
  workflow_id TEXT NOT NULL,
  from_role TEXT NOT NULL,
  to_role TEXT NOT NULL,
  payload_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  evidence_refs TEXT,
  due_at REAL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  accepted_at REAL,
  completed_at REAL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_handoffs_to_status ON agent_handoffs(to_role, status);

CREATE TABLE IF NOT EXISTS agent_results (
  report_id TEXT PRIMARY KEY,
  role TEXT NOT NULL,
  objective_id TEXT,
  workflow_id TEXT,
  action_type TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence_refs TEXT,
  metrics_before TEXT,
  metrics_after TEXT,
  economic_attribution TEXT,
  next_action TEXT,
  next_owner TEXT,
  next_review_at REAL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_results_role ON agent_results(role, created_at);

CREATE TABLE IF NOT EXISTS agent_heartbeats (
  role TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  last_seen REAL,
  last_meaningful_action REAL,
  current_objective TEXT,
  next_wake REAL,
  blocker TEXT,
  health TEXT,
  reason TEXT,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS economic_events (
  event_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  ts REAL NOT NULL,
  primary_owner TEXT,
  secondary TEXT,
  payload_json TEXT,
  urgency TEXT,
  routed INTEGER DEFAULT 0,
  consumed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_econ_events_ts ON economic_events(ts);
