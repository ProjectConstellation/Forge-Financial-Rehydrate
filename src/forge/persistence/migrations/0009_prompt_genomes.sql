-- Agent cognitive architecture: prompt genomes, attributed runs, structured reports, scored predictions, snapshots, panels.
CREATE TABLE prompt_genomes (
  id TEXT PRIMARY KEY,                 -- "<role>@v<n>"
  role TEXT NOT NULL,
  version INTEGER NOT NULL,
  parent_id TEXT,
  hypothesis TEXT,
  sections TEXT NOT NULL,              -- json {section: text}
  status TEXT NOT NULL,                -- CHAMPION | CHALLENGER | ARCHIVED
  author TEXT,
  constitution_version TEXT,
  created_at TEXT NOT NULL,
  decided_at TEXT,
  decision_reason TEXT,
  metrics TEXT
);
CREATE INDEX ix_prompt_genomes_role ON prompt_genomes(role, status);
CREATE TABLE world_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE prompt_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  role TEXT NOT NULL,
  prompt_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  snapshot_id INTEGER,
  paired_run_id INTEGER,               -- champion run whose snapshot this challenger replays (identical task)
  cost_usd REAL NOT NULL DEFAULT 0,
  report_status TEXT,                  -- ACTED | SILENT | NONE
  kpi REAL,
  kpi_detail TEXT,
  scored_at REAL
);
CREATE INDEX ix_prompt_runs_session ON prompt_runs(session_id);
CREATE INDEX ix_prompt_runs_role ON prompt_runs(role, prompt_id);
CREATE TABLE role_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  role TEXT NOT NULL,
  prompt_id TEXT,
  session_id TEXT,
  status TEXT,
  report TEXT NOT NULL
);
CREATE INDEX ix_role_reports_role ON role_reports(role, ts);
CREATE TABLE agent_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  role TEXT NOT NULL,
  prompt_id TEXT,
  session_id TEXT,
  ref_id TEXT,
  kind TEXT,                           -- survive | generic
  p REAL NOT NULL,
  claim TEXT,
  outcome REAL,
  scored_at REAL
);
CREATE INDEX ix_agent_predictions_ref ON agent_predictions(ref_id, outcome);
CREATE TABLE agent_panels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,                  -- strategy_promotion | rail_unlock | other
  ref_id TEXT NOT NULL UNIQUE,
  question TEXT NOT NULL,
  roles TEXT NOT NULL,                 -- json list of roles that must answer independently
  status TEXT NOT NULL,                -- OPEN | READY | RECONCILED
  verdicts TEXT,                       -- json {role: {p, reasoning}}
  reconciliation TEXT
);
