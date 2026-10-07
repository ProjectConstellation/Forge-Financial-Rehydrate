-- Event-loop stall fix (2026-10-07): admit() looked up genome_hash with a full scan per candidate (×hundreds per Modal
-- burst) → 10–50 s loop stalls (Coinbase WS keepalive timeouts, API timeouts). Index the hot lookups.
CREATE INDEX IF NOT EXISTS ix_strategies_hash ON strategies(genome_hash);
CREATE INDEX IF NOT EXISTS ix_strategy_metrics_sid ON strategy_metrics(strategy_id, scope);
CREATE INDEX IF NOT EXISTS ix_research_trials_interval ON research_trials(interval_s, sealed_exam);
CREATE INDEX IF NOT EXISTS ix_inference_calls_ts ON inference_calls(ts);
CREATE INDEX IF NOT EXISTS ix_inference_calls_agent ON inference_calls(agent, ts);
CREATE INDEX IF NOT EXISTS ix_timeline_ts ON timeline(ts);
