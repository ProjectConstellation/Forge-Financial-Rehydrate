-- P0.5 Research Trial Ledger: every adjudicated genome, which data it has seen, and its one-time sealed exam.
CREATE TABLE research_trials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  genome_id TEXT NOT NULL,
  family TEXT,
  interval_s INTEGER,
  generation INTEGER,
  parents TEXT,                 -- json list (ancestors)
  origin TEXT,                  -- mutation operator / llm / seed / crossover
  features TEXT,                -- json list of features used
  params_hash TEXT,
  where_run TEXT,               -- local / modal
  segments_seen TEXT,           -- json list: selection, holdout(validation), sealed
  dataset TEXT,                 -- json fingerprint (symbols, days per segment, sealed_start_ts)
  trials_cumulative INTEGER,    -- multiple-testing count at the time
  selection TEXT, holdout TEXT, -- json metrics (sealed metrics stored separately; never exposed to search/LLM)
  passed_validation INTEGER,
  sealed_exam INTEGER NOT NULL DEFAULT 0,
  sealed_passed INTEGER,
  sealed TEXT,
  sealed_start_ts REAL,
  promoted INTEGER NOT NULL DEFAULT 0,
  reasons TEXT
);
CREATE INDEX ix_research_trials_genome ON research_trials(genome_id);
CREATE INDEX ix_research_trials_sealed ON research_trials(sealed_exam, ts);
