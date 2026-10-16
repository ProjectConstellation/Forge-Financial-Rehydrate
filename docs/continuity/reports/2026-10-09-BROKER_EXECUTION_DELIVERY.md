# Broker-paper execution and autonomous trial delivery

Checkpoint: 2026-10-09T01:47:33.497113+00:00. Owner authorized continuation of Forge engineering and asked to focus reporting on completed verified work. Separate later question requests strategic assessment of missing income capabilities. Neither instruction establishes profitable outcomes or enables LIVE/funding/transfers/public marketing.

## Implemented behavior

- New Alpaca normalized paper adapter runs through existing RiskGovernor → persisted intent/decision → gateway → broker → individual FILL activities → isolated double-entry ledger and position manager.
- Only official paper endpoints; no LIVE or transfers. Broker sandbox balances do not grant virtual training capital. Unsupported post-only orders reject. Regular-session clock, account/asset status, virtual cash/exposure caps and owned sell quantity are verified before submit. Cancel and protective owned sells remain available under STOPPED; entries reject.
- Broker activities use unique fill IDs, bounded pagination and exact quantity comparison. Lag/unknown outcomes block rather than inventing fills. Definite API errors differ from ambiguous network/server failures. Remotely persistent paper orders are reconciled after restart instead of being treated as lost in-memory orders.
- Fill insertion, ledger posting and position quantity update are now one DB transaction. Injected accounting failure rolls back all three; retry posts exactly once. Main gateway uses the same repaired transaction.
- Typed experiment contracts and append-only decision history: READY → PAPER_RUNNING → MEASURED → RETAINED/RETIRED. Unique position identities and entries/closures after registration are required. Paper outcomes never grant LIVE authority.
- Agents get submit_paper_experiment and get_research_results through the existing authenticated tool surface. Proposals are validated/deduplicated and consumed automatically. Eligible symbols QQQ/SPY/IWM/GLD/TLT; mechanism library relative momentum, dip reversion, trend following; preregistered lookback 10/20/40 sessions. Arbitrary code, LIVE flags, broker keys and risk changes are not proposal fields.
- Successful mechanism parameters persist into a new future block; unsuccessful reviews select replacements, including changed lookback on later generations. Existing local forward trials continue as an independent improvement lane.
- Training capital stage increases are explicit simulated deposits, idempotent and excluded from earned income. Future trial allocations use bounded cash fractions and current policy caps. Lifetime loss stops and fees remain active.
- Allocator discovery cards now have zero fabricated samples and are separated from measured allocation rankings. Contaminated cards are excluded. Repeated open reallocation directives deduplicate transactionally.
- Research/capability API includes broker experiment identity/status/capital/reconciliation/freshness; exceptions produce explicit blocked status rather than retaining a fresh success label.

## Scope and verification

Changed resources:
- `src/forge/venues/alpaca.py`
- `src/forge/agents/research_accountability.py`
- `src/forge/treasury/capabilities.py`
- `src/forge/venues/alpaca_paper_adapter.py`
- `src/forge/research/experiment_registry.py`
- `src/forge/research/alpaca_broker_engine.py`
- `src/forge/execution/gateway.py`
- `src/forge/brain/tools.py`
- `src/forge/treasury/reallocator.py`
- `tests/unit/test_broker_experiments.py`
- `scripts/forge-alpaca-broker.service`

New unit: `/etc/systemd/system/forge-alpaca-broker.service`, enabled under forge.slice, 30% CPU / 384MB ceiling, restart on failure. Existing Forge services restored active; workforce restarted to fetch new tool schemas.

Full isolated suite: **140 passed**, one warning. Tests cover complete mocked broker entry/exit, restart, idempotent fills, emergency flatten, unowned inventory, cap enforcement, registry transitions, future-only identity, automatic proposal consumption/rotation, simulated capital scaling and transactional crash rollback. Production official paper account/clock/positions/open-orders calls returned HTTP 200; independent inventory and local ledger reconciliation passed. Broker session was closed at verification; no production paper fill is claimed. Authenticated health/research/capabilities/tools returned HTTP 200, new schemas present, broker status fresh. All 62 deployment hashes verified. Training balance reached $50 via stage-policy simulated deposit, not investment earnings. No LIVE orders, funds, transfers, new subscriptions or Telegram messages.

## Persistent artifacts and rollback

- `/srv/forge/var/alpaca-broker/state/forge.sqlite`: isolated paper ledger, intents/orders/fills, contracts, experiment decisions.
- `/srv/forge/var/alpaca-broker/audit/`: hash-chained order/fill journal.
- `/srv/forge/var/alpaca_broker_trials.json`: current compact broker-paper status for Luke/API.
- Main `research.paper_proposals` KV: typed agent proposal queue; isolated broker.consumed_proposals records consumption.
- `docs/continuity/evidence/2026-10-09-broker-execution-delivery.json`: production readback and current file verification.
- Original source backups plus deployment manifest remain in `.engineering/20261009-overhaul`. Staged rollback now disables/removes added timer/service units before reverting their modules, verifies no unit drift, preserves additive financial tables and newer fills. Rollback was prepared, not executed.

## Strategic assessment requested by owner

Current Forge source has x402 purchase/discovery placeholders but no demonstrated customer-funded service fulfillment/billing rail. This is a promising diversification hypothesis, not verified demand. A potential product should first establish an independent payer, contracted deliverable, delivery acceptance, net margin after inference/compute/payment/refund costs, and repeat business. External customer messages, accounts and publishing require existing owner authorization; do not invent paid demand or book an invoice as collected revenue. More trading capital, calibrated edge, execution quality and portfolio dependence affect market scalability. Growth is empirical and never guaranteed exponential.
