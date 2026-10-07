-- Intelligence Attribution Ledger (OP-006): DeepSeek call → artifact → downstream decisions → economic value.
CREATE TABLE intel_artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  call_id TEXT NOT NULL,
  role TEXT NOT NULL,
  model TEXT NOT NULL,
  kind TEXT NOT NULL,                 -- genome | lesson | regime_call | research_focus | diagnosis | escalation
  ref_id TEXT,
  prediction REAL,                    -- the model's stated probability (scored → calibration class llm:<role>)
  detail TEXT,
  value_usd TEXT NOT NULL DEFAULT '0',
  value_basis TEXT,
  valued_at TEXT
);
CREATE INDEX ix_intel_call ON intel_artifacts(call_id);
CREATE INDEX ix_intel_ref ON intel_artifacts(kind, ref_id);
