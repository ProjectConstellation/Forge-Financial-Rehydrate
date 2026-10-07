# BUILD STATUS (evidence-backed only) — 2026-10-07
| Area | Status | Evidence |
|---|---|---|
| Isolation, service user, secrets, systemd unit (CPUQuota 300%, MemoryMax 2G, hardening) | DONE | `systemctl show forge`; running as `forge` |
| Source-of-truth anchor + OPERATOR_POLICY OP-001…009 | DONE | `scripts/dossier.sh verify` |
| Credentials DeepSeek / Modal / Coinbase | VERIFIED | live API checks |
| Config, bus, DB+migrations, audit chain, immutable ledger, true net P&L | DONE | tests/unit (property + tamper tests) |
| Coinbase REST/JWT/WS/L2 adapter (personal Advanced Trade) | WORKING LIVE | live sessions; perms/fees/balances |
| Features (causal), regimes, genome DSL, seeds, backtester, stats, alpha-vs-drift gate | DONE | tests/unit/test_features (no-lookahead), research runs |
| MAP-Elites evolution, promotion gate, arena lifecycle, worker | WORKING | runtime cycles 3,610 genomes / ~80s locally |
| Risk governor, breakers, emergency stop, paper venue, execution gateway | DONE | tests/simulation (TP, SL, duplicate, stale, stopped) |
| Capital regimes, velocity + opportunity cost, sizing, calibration, counterfactuals | DONE (live data accruing) | runtime |
| DeepSeek brain (Flash perception, Pro tool sessions, attribution ledger) | WORKING LIVE | inference_calls; cost ledgered |
| Modal compute (forge env, volume, bursts, budget states) | WORKING LIVE | 2×workers 6,740 genomes $0.004 |
| API (/health /ready /metrics /api/*, SSE) + PWA + STOP ALL TRADING | WORKING | 127.0.0.1:8470 |
| Readiness gate | DONE | `forge readiness` |
| 24/7 liveness: supervisor auto-restart + systemd notify watchdog (3 min) | DONE | tests/unit/test_supervisor; `systemctl show forge -p WatchdogUSec` |
| OP-010 confidence/earnings-scaled AI budget, near-miss racing (16× Modal) | DONE | runtime |
| ≥1 strategy through gate → SHADOW → CHALLENGER | IN PROGRESS | evolution running 24/7 |
| LIVE trading | NOT ENABLED | blocked by readiness gate until evidence exists |
