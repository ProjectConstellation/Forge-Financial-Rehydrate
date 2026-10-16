# System map and ownership

## Hosts

Command center `/home/NorthStarImagine` coordinates SSH and engineering. Production is the dedicated `forge` host, IPv4 `104.237.131.109`, `/srv/forge`, user `forgeadmin`. SSH key stays on command center. Do not treat command-center Pi’s DeepSeek V4 Pro/high default as Forge workforce configuration; these are separate configurations.

## Components

| Component | Source/state | Responsibility |
|---|---|---|
| Runtime and supervision | src/forge/runtime.py, core/supervisor.py | Market/execution/research loops, heartbeat and restart |
| Market fabric | market_data/, venues/coinbase/ | Live WS/L2/trades, REST bars, fees and account capabilities |
| Strategy creation | strategies/, research/, evolution/ | Declarative genomes, search, causal evaluation, sealed exam, arena |
| Treasury | treasury/truth.py, regime.py, regimes.py, sizing.py, profit_velocity.py | Wallet/paper reporting, reserves, allocation, marginal economics |
| Protected money path | risk/, execution/gateway.py, ledger/, audit/ | Deterministic approval, order idempotency, reconciliation and accounting |
| DeepSeek research | brain/, treasury/intelligence.py | Typed tool reasoning, escalation, attribution |
| Institutional workforce | agents/workflow_engine.py, employment_accountability.py, results_enforcer.py | Ownership, event wakes, mandatory handoffs, evidence/results |
| Institutional memory | agents/opportunity_memory.py; role_reports, lessons, agent_results in DB | Failures, successful mechanisms, uncertainty and reopening conditions |
| Coinbase alternative rails | opportunities/pegmaker.py, surface.py, treasury/idle_yield.py | Stable shadow simulations, discovery, idle yield |
| Prediction markets | opportunities/crossrail.py, probability.py, settlement_window.py, kalshi_live.py | Settlement modeling, independent clusters, per-rail execution gating |
| Equities/data | intel/ and opportunities/alpaca_*.py, venues/alpaca.py | SEC/Twelve Data inputs and Alpaca PAPER training |
| Founder API/PWA | api/server.py, firm_v1.py, ops_api.py, web/ | Authenticated telemetry, controls, dashboard |
| Luke | hermes/ops/SOUL.md; runtime/ops/home; ops/executive.py | Owner-facing natural-language planning/reporting/authorized actions |
| Compute | compute/, modal_apps/forge_research.py | Modal jobs within $30/month and attribution |
| Engineering deploy | scripts/forge_deployer.py, forge-eng service | Existing sandbox/queue/deploy machinery; inspect before using |
| Continuity | docs/continuity/ | Engineering journals, evidence, progress and handoff |

## Service boundaries

`forge.service`, `forge-hermes.service`, `forge-ops.service`, `forge-eng.service`, `forge-tunnel.service`; guardian/deployer/credential paths and timers are Forge-namespaced. All constrained by Forge units/slice. Dedicated-host deployment D-028 supersedes older shared-host CPU/RAM descriptions: observed slice CPU 400% and MemoryMax 7 GiB, Forge service ~5.6 GiB limit. Preserve OS headroom and measure peaks; do not expand limits solely because they appear stale in old docs.

## State and configuration

SQLite `/srv/forge/var/state/forge.sqlite`; market history `/srv/forge/var/market`; logs/audit/backups under `/srv/forge/var`; secrets `/etc/forge/forge.env` and isolated Hermes environments. API listens on `127.0.0.1:8470`, published through Forge’s own tunnel at `forge.northstarimagine.com`.

## Named responsibilities

Luke: financial advisor/managing partner/ops. Cyrus: governor/CIO. Quinn: alpha invention. Ada: evidence/science gate. Vale: adversarial risk. Tess: economic intelligence. Reid: execution. Ellis: treasury/capital allocation. Nolan: prediction markets. Mira: intelligence/prompt evolution. Sloane: new rails. Rowan: engineering. Casey: reliability. Verify runtime role IDs; legacy prompts have conflicting mappings.

Income chain: observe → mechanism+algorithm → execution feasibility → evidence → risk → allocation → commit → execution plan → measure → close/learn. Diagnostic chains answer a measurable uncertainty; they must not silently become earnings proof or LIVE authorization.

## Forensic activation and ownership addendum — 2026-10-09

`forge.service` starts the Python runtime; runtime startup registers supervised market, execution, treasury, research, allocation, monitoring, sports and settlement loops, then a watchdog supervises loop heartbeats/restarts. Loop silence thresholds are recovery controls, not necessarily work cadence. The main execution loop ticks near 2s; the main-book PositionVigil was previously set to 5s. Separate Alpaca paper management was observed at 15s in market session / 60s closed. Never imply one interval covers every rail.

`forge-hermes.service` runs as the Hermes service user. Its cron registry is `/srv/forge/runtime/hermes/home/cron/jobs.json`: 13 enabled schedules. Governor, Alpha Inventor, Adversary, Critic, Scout, Execution and Treasury every 15m; Doctor and Prediction every 30m; Rail Hunter every 120m; Architect and Intelligence every 180m; Daily Report at 12:00 UTC. Jobs inherit global provider/model when their overrides are null. Registry `last_status=ok` is dispatch status, not proof of a useful artifact or income. Query the service user’s registry/history, not a different user’s bare Hermes CLI.

Separate `forge-ops.service` is Luke’s private owner Telegram/control plane; `forge-eng.service` is a sandboxed coding worker whose service contract does not deploy. `forge-deployer.timer` checks the queue every 2m, guardian every 60s, continuity export every 15m, Alpaca broker paper every 15m, Alpaca curriculum 3x daily, and equity forward-paper hourly. A timer wake or active process is not a financial result. Role names, prompt identities and runtime IDs have drifted; verify each mapping against the actual service-user prompt and durable output.

See [2026-10-09 forensic passover](reports/2026-10-09-FORGE-FORENSIC-PASSOVER.md) for all role remits, current role evidence, one-hour outcome, uncertainty, and rehydration steps.
