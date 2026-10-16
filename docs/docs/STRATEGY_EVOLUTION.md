# Strategy evolution (OP-007 permanent Improvement Loop)
Genome DSL: `src/forge/strategies/genome.py` (declarative, validated, hashed). Seeds: `strategies/seeds.py`.
Search: MAP-Elites quality-diversity (`evolution/search.py`) with adaptive operator weights: jitter, exit jitter, add/remove/swap
condition (thresholds from selection-period quantiles), regime specialize/veto, execution, horizon, crossover; plus DeepSeek-designed
genomes (always explicitly adjudicated; their predicted P is scored → calibration class `llm:<role>`).
Evaluation: selection (older 70%) with 4 chronological folds → promotion gate on untouched newest 30% holdout: P(net>0)≥0.90,
P(alpha vs equal-weighted market drift)≥0.60, fold consistency, parameter-perturbation robustness, deflated Sharpe vs #trials.
Lifecycle (`evolution/arena.py`): EXPERIMENTAL → SHADOW (live-forward re-simulation on post-activation bars) → CHALLENGER
(reduced size, real paper/live outcomes) → PRODUCTION; demotion → SHADOW (+Pro postmortem); HIBERNATING when regimes absent;
RETIRED keeps lineage forever. Compute: local low-priority worker (≤1 core) or Modal bursts (8×2 cores) by EVI + budget state.
