# FORGE architecture (actual, as built)
```
                 ┌──────────── PWA dashboard (127.0.0.1:8470, SSE, STOP ALL TRADING) ─────────────┐
Coinbase WS ─▶ LiveMarket (BBO, L2 books, trade flow) ─┐                                            │
Coinbase REST ─▶ BarEngine 5m/1h (complete bars) ─▶ features + regimes (same code as research)     │
                                                        ▼                                          │
EARNING LOOP:  active genomes ─▶ signals ─▶ Opportunity (calibrated p, velocity, opportunity cost, │
               half-life) ─▶ sizing (fractional Kelly × evidence × velocity) ─▶ RiskGovernor ─▶    │
               ExecutionGateway (maker-first, idempotent, crash-safe) ─▶ Paper/Coinbase ─▶ Ledger ─┘
IMPROVEMENT:   MAP-Elites evolution (local worker / Modal burst) ─▶ promotion gate (holdout, alpha, DSR,
               robustness) ─▶ Arena lifecycle (SHADOW→CHALLENGER→PRODUCTION, demote/hibernate/retire)
BRAIN:         Flash perception (15 min) ─▶ VOI escalation ─▶ V4 Pro scientist/diagnostician (tools) ─▶
               genome queue ─▶ evaluator; Intelligence Attribution Ledger values every call
LEARNING:      counterfactual scoring of every opportunity · calibration (isotonic) · hurdle (velocity) learning
TREASURY:      CapitalRegimeEngine (SURVIVAL/GROWTH/EXPANSION surface) · reserves · wallet-truth reconciliation
```
Code map: `src/forge/` — config, core (bus, ids, clock, state), persistence, audit, ledger, domain, venues (coinbase, paper),
market_data, features, regime, strategies (genome, seeds, mutation, registry), research (backtest, evaluate, stats, calibration),
evolution (search, arena, worker), treasury (regimes, velocity, sizing), risk (governor, breakers), execution (gateway), brain
(deepseek, prompts, tools, agent), compute (modal_client), api (server), web (PWA), runtime, readiness, cli. Modal: `modal_apps/`.
