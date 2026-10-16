-- Durable reservations across autonomous paid callers. Estimated and actual costs stay distinct.
CREATE TABLE spend_reservations (
 id TEXT PRIMARY KEY, provider TEXT NOT NULL, owner TEXT NOT NULL,
 objective_id TEXT NOT NULL, experiment_key TEXT NOT NULL,
 max_cost_usd REAL NOT NULL CHECK(max_cost_usd > 0), actual_cost_usd REAL,
 state TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL,
 outcome_ref TEXT, cost_basis TEXT NOT NULL DEFAULT 'worst_case_estimate'
);
CREATE INDEX spend_admission_active ON spend_reservations(provider,state,expires_at);
CREATE UNIQUE INDEX spend_admission_experiment ON spend_reservations(provider,experiment_key) WHERE state='RESERVED';
