# FORGE — Autonomous Capital Growth Engine
## Immediate Build Directive for Pi CLI + Opus 5.5

> **Project name:** FORGE  
> **Meaning:** **Find Opportunities, Reinvest, Grow, Evolve**  
> **Category:** Autonomous Capital Growth Engine  
> **Primary runtime brain:** DeepSeek V4.1 Flash (`deepseek-flash`)  
> **Initial live experiment treasury:** **$20**  
> **Primary first execution venue:** Coinbase  
> **Primary local compute target:** 2 vCPU  
> **Hard local FORGE ceiling:** 3 vCPU  
> **Elastic compute:** Modal, up to the operator-authorized $30/month budget  
> **Operating mode:** 24/7 autonomous observation, strategy research, validation, execution, reinvestment, and evolution  
> **Human trade approvals:** None during normal operation  
> **Critical human override:** STOP ALL TRADING

---

# 0. READ THIS FIRST — ABSOLUTE SERVER ISOLATION DIRECTIVE

You are building a **new project on this server**. The project is called **FORGE**.

This server contains several extremely important North Star Imagine SaaS products and active development environments, including projects being built in other terminal sessions.

## **DO NOT TOUCH ANY OTHER PROJECT.**

This instruction is absolute.

FORGE must be created as its **own isolated root folder, isolated codebase, isolated runtime, isolated state, and isolated service boundary**. It must function and thrive independently from every other project on this server.

Use the approved project root:

```text
/srv/forge
```

Do not recursively search the server for source code, `.env` files, project manifests, secrets, databases, or unrelated configuration. Do not inspect other project trees. Do not import code from another project. Do not reuse another project's database, logs, service names, ports, cache, dependencies, Python environment, virtualenv, Node modules, containers, reverse-proxy rules, systemd units, cron jobs, credentials, or runtime directories.

The earlier server-wide search used only to locate this dossier must **not** be repeated.

FORGE must have its own:

- Git repository
- source tree
- environment
- dependency lockfiles
- configuration
- secrets file(s)
- runtime state
- database
- cache
- data directory
- model/tool schemas
- logs
- ports
- API server
- workers
- schedulers
- web application
- tests
- services
- process IDs
- metrics
- documentation
- continuity records
- deployment manifests
- backup/restore procedures
- Modal applications

If a system-level change is required, it must be explicitly namespaced to FORGE and must not alter or interrupt another service.

Create a dedicated `forge` service account if it can be done safely without affecting anything else. Prefer least-privilege isolation.

If an action would require touching another project, changing a shared reverse proxy, editing a shared firewall, altering a shared system package in a risky way, or restarting a shared service, **do not do it automatically**. Record the exact requirement in `docs/operator-actions.md` and continue everything else that can be built safely.

FORGE maintains its own continuity system. Do not write into any other project's continuity files.

---

# 1. YOUR MISSION

You are not building a fixed trading bot.

You are building **FORGE: Find Opportunities, Reinvest, Grow, Evolve** — an autonomous capital growth engine whose purpose is to continuously search for legitimate, permitted, API-accessible economic opportunities, allocate capital intelligently, learn from outcomes, create proprietary strategies, retire weak strategies, scale strong strategies, and reinvest gains.

FORGE must make its name true:

- **Find** — continuously discover opportunities.
- **Opportunities** — detect legitimate positive-expected-value situations across supported markets and venues.
- **Reinvest** — make realized gains available for future allocation under treasury/risk rules.
- **Grow** — maximize true net treasury value over time after all costs.
- **Evolve** — continuously improve strategy logic, market selection, feature engineering, capital allocation, and compute allocation based on measured evidence.

FORGE must operate **24 hours per day, 7 days per week**.

At all times it should be doing economically useful work such as:

- observing
- streaming market data
- measuring
- ranking
- identifying regimes
- detecting anomalies
- discovering candidate edges
- simulating
- backtesting
- replaying
- shadow trading
- validating
- learning
- generating hypotheses
- mutating strategies
- testing challengers
- monitoring live positions
- reallocating capital
- calculating costs
- analyzing failures
- analyzing missed opportunities
- optimizing compute use
- researching new supported venues

Financial inactivity is allowed when acting would have negative expected value. **Intellectual inactivity is not.**

Do not force trades merely to create activity. The objective is **net capital growth**, not trade count.

There is no guarantee of profit, and the system must never fabricate one. It must measure uncertainty explicitly. The ambition is aggressive, but execution must remain evidence-driven.

---

# 2. START NOW — DO NOT REMAIN IN PLANNING MODE

After reading this document:

1. Verify `/srv/forge` is safe to use.
2. Create the isolated FORGE repository.
3. Initialize Git.
4. Create the project structure described below.
5. Create environment/config templates.
6. Build mocks and provider interfaces where live credentials are not yet available.
7. Implement the runtime core.
8. Implement the strategy/evolution system.
9. Implement the DeepSeek tool layer.
10. Implement Modal orchestration.
11. Implement Coinbase integration adapters.
12. Implement live metrics, P&L accounting, and dashboard backend.
13. Implement the mobile-first PWA dashboard.
14. Implement tests.
15. Run local/simulated acceptance tests.
16. Produce a clear credential checklist.
17. When credentials are supplied, wire them in and run connectivity tests.
18. Move from mock -> shadow -> micro-live according to the automated readiness gate.

Do not ask unnecessary architecture questions. Use the dossier and sound engineering judgment. When ambiguity exists, prefer the implementation that makes FORGE more autonomous, safer, more measurable, more extensible, more resource-efficient, and more capable of improving itself.

If you identify a materially better architecture than one described here, you are explicitly authorized to improve it **provided you preserve all hard constraints and document the change**.

---

# 3. CREDENTIAL AND API POLICY

Credentials for Coinbase, DeepSeek, Modal, Kalshi, future venues, and related services will be supplied as needed.

## Build first, plug credentials in second.

Create clean provider boundaries, mocks, fixtures, test doubles, and environment placeholders so the full system can be built before all credentials exist.

Never hardcode secrets.

Never search another project's `.env` or secret store.

Never copy credentials from unrelated projects.

Use FORGE-specific environment variables, for example:

```bash
FORGE_ENV=development
FORGE_DB_URL=...
DEEPSEEK_API_KEY=...
COINBASE_API_KEY=...
COINBASE_API_SECRET=...
COINBASE_WALLET_SECRET=...
MODAL_TOKEN_ID=...
MODAL_TOKEN_SECRET=...
KALSHI_API_KEY=...
```

Exact names may change if provider SDKs require different variables; keep them namespaced and documented.

If a provider credential is missing:

- finish the adapter interface;
- implement request/response schemas;
- implement deterministic mocks;
- write integration tests that can run once credentials exist;
- add the missing item to `docs/CREDENTIALS_REQUIRED.md`;
- continue building everything else.

Do not block the entire project because one key is missing.

---

# 4. RUNTIME RESOURCE CONTRACT

FORGE shares the North Star Imagine Command Center with other important services.

## Local compute

Normal FORGE target:

```text
2 vCPU
```

Absolute local ceiling:

```text
3 vCPU
```

Design the system to stay within this envelope during ordinary operation.

Prefer:

- async I/O
- event-driven processing
- streaming WebSockets
- bounded queues
- efficient vectorized/compiled numerical operations where useful
- batched writes
- low-overhead feature calculation
- worker concurrency limits
- CPU quotas/cgroups/systemd resource controls if appropriate

Do not monopolize the host.

## Modal

Modal is explicitly authorized and encouraged as FORGE's elastic compute extension.

Operator-authorized Modal budget:

```text
$30/month
```

FORGE may use as much of that allowance as economically justified.

Do not artificially conserve Modal credits if spending them materially improves expected net economic outcome.

Do not spend Modal credits merely because they are available.

Modal is an economic resource. Optimize its ROI.

Use Modal for any computation that is economically justified, including but not limited to:

- parallel backtests
- replay simulations
- walk-forward analysis
- Monte Carlo analysis
- feature searches
- candidate strategy tournaments
- parameter optimization
- strategy mutation batches
- regime classifiers
- correlation studies
- large historical scans
- adversarial strategy testing
- probabilistic stress testing
- expensive candidate validation
- alternative model inference if later authorized
- research workloads

FORGE should be able to scale Modal workers upward quickly and scale them to zero when the work is complete.

If keeping a tiny warm worker is measured to be beneficial, FORGE may do so. Do **not** force a permanently warm worker if it wastes budget. The correct behavior is whichever produces higher measured economic value.

Build a `ComputeAllocator` that decides between:

```text
LOCAL_NORMAL
LOCAL_SURGE
MODAL_BURST
```

The allocator should consider:

- urgency
- expected opportunity value
- expected compute cost
- local queue depth
- local CPU saturation
- latency requirements
- estimated value of additional analysis
- historical effectiveness of Modal for similar tasks
- remaining monthly Modal budget
- risk of missing an opportunity while computing

---

# 5. TRUE ECONOMIC ACCOUNTING

FORGE must calculate **true net economic performance**, not vanity P&L.

Maintain an immutable ledger containing at least:

- deposits
- withdrawals
- realized trading gains/losses
- unrealized P&L
- exchange fees
- spread costs
- estimated and realized slippage
- funding costs/rebates
- network/gas costs if applicable
- inference costs
- Modal compute costs
- paid data/API costs
- infrastructure costs explicitly attributable to FORGE
- rebates/incentives
- other revenue

Core metric:

```text
TRUE_NET_PROFIT =
  realized_revenue
  - realized_losses
  - exchange_fees
  - slippage
  - spread_costs
  - funding_costs
  - inference_costs
  - modal_costs
  - paid_data_costs
  - other_operating_costs
  + rebates
  + other_income
```

A strategy that earns $2 while consuming $3 in attributable costs is losing.

A strategy that earns $1 while consuming $0.05 is winning.

Every strategy and agent receives cost attribution.

---

# 6. STARTING TREASURY AND SCALING RULES

Initial live experiment treasury:

```text
$20
```

This is experiment capital and may be lost.

Do not hardcode the architecture for $20.

The exact same system must naturally scale through:

```text
$20
$100
$1,000
$10,000
$100,000+
```

FORGE must dynamically adapt:

- position sizes
- reserve policy
- venue selection
- liquidity requirements
- market impact assumptions
- execution methods
- strategy mix
- maximum correlated exposure
- compute budget per opportunity

## Reserve policy

Before treasury reaches $100, reserve can be dynamic and minimal when an opportunity is unusually strong, but the Risk Governor should normally prefer preserving some restart capital.

Once total treasury is at least $100, maintain at least:

```text
$25 protected reserve
```

unless future operator policy explicitly changes it.

For exceptionally high-confidence opportunities, deployable capital may be concentrated, but **confidence is never certainty**. The Risk Governor should generally preserve approximately 5%–20% when practical, with reserve requirements becoming stricter as treasury grows.

Do not implement a fake “100% guaranteed” confidence state.

---

# 7. AUTONOMY CONTRACT

FORGE is designed to operate without human trade approvals.

Normal operations require:

```text
ZERO MANUAL TRADE APPROVALS
```

Humans define hard boundaries. FORGE makes decisions inside those boundaries.

Autonomous behaviors include:

- discovering opportunities
- choosing strategies
- choosing capital allocations
- opening positions
- reducing positions
- closing positions
- reinvesting gains
- pausing failing strategies
- creating strategy challengers
- launching shadow tests
- requesting Modal compute
- adjusting inference depth
- deciding to remain in cash
- rotating between supported assets
- changing strategy mix

However, sensitive actions must remain deterministic and policy-checked. A language model may **propose** actions through tools; it must not possess raw signing keys or bypass execution policies.

---

# 8. HARD SAFETY BOUNDARIES

Autonomy does not mean lack of controls.

Create a deterministic `RiskGovernor` that the LLM cannot override.

At minimum enforce:

1. credential isolation;
2. no unauthorized withdrawals to unknown destinations;
3. no bypassing exchange/platform protections;
4. no exploitation of vulnerabilities, stolen accounts, or unauthorized systems;
5. no deceptive, manipulative, or illegal market conduct;
6. no uncapped leverage by default;
7. stale-market-data rejection;
8. duplicate-order protection;
9. idempotent execution;
10. maximum position/exposure limits derived from current treasury policy;
11. venue/API rate limits;
12. deterministic emergency stop;
13. immutable audit trail;
14. maximum monthly Modal spend per operator-approved budget;
15. explicit inference spend tracking;
16. automatic safe-state behavior on exchange/API ambiguity;
17. circuit breakers on unexpected order/fill behavior;
18. reconciliation between internal ledger and venue balances.

The word “loophole” in FORGE means legitimate, permitted economic inefficiency such as:

- mispricing
- temporary dislocation
- rebates
- incentives
- structural fee advantages
- market microstructure
- information latency
- regime mismatch
- stale pricing
- cross-market disagreement
- statistical edge

It does **not** mean bypassing controls, abusing vulnerabilities, impersonation, fraud, or violating platform rules.

---

# 9. HIGH-LEVEL ARCHITECTURE

Build FORGE as modular services/packages within one isolated repo initially. Do not prematurely create dozens of independently deployed microservices.

Recommended logical architecture:

```text
                         +------------------------+
                         |    OPERATOR DASHBOARD  |
                         |    PWA / WebSocket UI  |
                         +-----------+------------+
                                     |
                                     v
+----------------+        +----------+-----------+        +----------------+
| Market Adapters | ----> |  Market Data Fabric  | <----> | Historical Data |
+----------------+        +----------+-----------+        +----------------+
                                     |
                                     v
                         +-----------+------------+
                         | Feature / Regime Engine|
                         +-----------+------------+
                                     |
                                     v
                         +-----------+------------+
                         | Opportunity Discovery  |
                         +-----------+------------+
                                     |
                    +----------------+----------------+
                    |                                 |
                    v                                 v
        +-----------+-----------+         +-----------+-----------+
        | Strategy Population   |         | DeepSeek Scientist    |
        | + Strategy Genomes    | <-----> | Tool-Calling Brain    |
        +-----------+-----------+         +-----------+-----------+
                    |                                 |
                    +---------------+-----------------+
                                    |
                                    v
                         +----------+-----------+
                         | Evolution / Arena    |
                         +----------+-----------+
                                    |
                                    v
                         +----------+-----------+
                         | Capital Allocator    |
                         +----------+-----------+
                                    |
                                    v
                         +----------+-----------+
                         | Risk Governor        |
                         +----------+-----------+
                                    |
                                    v
                         +----------+-----------+
                         | Execution Engine     |
                         +----------+-----------+
                                    |
                                    v
                         +----------+-----------+
                         | Coinbase / Future    |
                         | Venue Adapters       |
                         +----------------------+
```

Supporting systems:

- Treasury ledger
- P&L service
- Cost attribution
- Scheduler
- Event bus
- Modal compute manager
- Research memory
- Strategy lineage graph
- Observability
- Alerting
- Reconciliation
- Emergency stop

---

# 10. RECOMMENDED PROJECT TREE

You may improve this layout if you have a materially better design, but preserve the isolation and conceptual boundaries.

```text
/srv/forge/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── uv.lock / requirements.lock
├── .gitignore
├── .env.example
├── config/
│   ├── base.yaml
│   ├── development.yaml
│   ├── production.yaml
│   ├── risk.yaml
│   ├── compute.yaml
│   └── venues.yaml
├── src/forge/
│   ├── __init__.py
│   ├── app.py
│   ├── cli.py
│   ├── config.py
│   ├── domain/
│   │   ├── events.py
│   │   ├── money.py
│   │   ├── markets.py
│   │   ├── positions.py
│   │   ├── orders.py
│   │   └── strategies.py
│   ├── market_data/
│   │   ├── fabric.py
│   │   ├── normalizer.py
│   │   ├── orderbook.py
│   │   ├── candles.py
│   │   └── persistence.py
│   ├── venues/
│   │   ├── base.py
│   │   ├── coinbase/
│   │   │   ├── client.py
│   │   │   ├── websocket.py
│   │   │   ├── execution.py
│   │   │   ├── balances.py
│   │   │   └── schemas.py
│   │   └── kalshi/
│   │       └── placeholder_adapter.py
│   ├── features/
│   │   ├── engine.py
│   │   ├── momentum.py
│   │   ├── volatility.py
│   │   ├── volume.py
│   │   ├── liquidity.py
│   │   ├── microstructure.py
│   │   ├── correlation.py
│   │   └── regime.py
│   ├── opportunities/
│   │   ├── scanner.py
│   │   ├── scorer.py
│   │   └── registry.py
│   ├── strategies/
│   │   ├── base.py
│   │   ├── genome.py
│   │   ├── registry.py
│   │   ├── lineage.py
│   │   ├── evaluator.py
│   │   ├── mutation.py
│   │   ├── crossover.py
│   │   └── seeds/
│   ├── evolution/
│   │   ├── arena.py
│   │   ├── fitness.py
│   │   ├── challenger.py
│   │   ├── retirement.py
│   │   └── scheduler.py
│   ├── research/
│   │   ├── deepseek.py
│   │   ├── prompts.py
│   │   ├── tools.py
│   │   ├── hypotheses.py
│   │   └── postmortems.py
│   ├── backtest/
│   │   ├── engine.py
│   │   ├── replay.py
│   │   ├── walkforward.py
│   │   └── metrics.py
│   ├── shadow/
│   │   ├── engine.py
│   │   └── fills.py
│   ├── treasury/
│   │   ├── ledger.py
│   │   ├── allocator.py
│   │   ├── reserve.py
│   │   └── reconciliation.py
│   ├── risk/
│   │   ├── governor.py
│   │   ├── sizing.py
│   │   ├── circuit_breakers.py
│   │   └── emergency_stop.py
│   ├── execution/
│   │   ├── engine.py
│   │   ├── router.py
│   │   ├── idempotency.py
│   │   └── fills.py
│   ├── compute/
│   │   ├── allocator.py
│   │   ├── modal_client.py
│   │   ├── jobs.py
│   │   └── budgets.py
│   ├── economics/
│   │   ├── costs.py
│   │   ├── pnl.py
│   │   └── roi.py
│   ├── persistence/
│   │   ├── db.py
│   │   ├── models.py
│   │   └── migrations/
│   ├── api/
│   │   ├── server.py
│   │   ├── routes/
│   │   └── websocket.py
│   ├── observability/
│   │   ├── metrics.py
│   │   ├── logging.py
│   │   ├── health.py
│   │   └── events.py
│   └── scheduler/
│       └── runtime.py
├── web/
│   ├── package.json
│   ├── src/
│   └── public/
├── modal/
│   ├── app.py
│   ├── backtest_jobs.py
│   ├── evolution_jobs.py
│   └── research_jobs.py
├── scripts/
│   ├── bootstrap.sh
│   ├── run-dev.sh
│   ├── run-tests.sh
│   ├── healthcheck.sh
│   ├── backup.sh
│   └── stop-all.sh
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── simulation/
│   └── acceptance/
├── data/
│   ├── market/
│   ├── strategies/
│   ├── replay/
│   └── backups/
├── logs/
├── run/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_STATUS.md
│   ├── CURRENT_STATE.md
│   ├── DECISIONS.md
│   ├── CREDENTIALS_REQUIRED.md
│   ├── OPERATOR_ACTIONS.md
│   ├── RISK_POLICY.md
│   ├── STRATEGY_EVOLUTION.md
│   ├── MODAL_POLICY.md
│   ├── DEPLOYMENT.md
│   └── INCIDENTS.md
└── systemd/
    ├── forge.service
    └── forge-worker.service
```

---

# 11. MARKET DATA FABRIC

Build a normalized real-time market-data system.

Coinbase is first, but the architecture must be venue-agnostic.

Every venue adapter should expose consistent concepts:

- instruments
- balances
- tickers
- candles
- trades
- order books where available
- fees
- order constraints
- min notional / min size
- order placement
- order cancellation
- fills
- positions where applicable

Use WebSockets for streaming where available and REST for state reconciliation.

The internal market event model should include:

- venue
- symbol
- base asset
- quote asset
- event timestamp
- receive timestamp
- event type
- bid/ask
- size
- depth
- trade price
- trade size
- sequence number
- source latency

Detect and reject stale or out-of-order data.

Store enough historical data to replay strategies efficiently without consuming unbounded disk.

Create retention tiers:

- high-resolution recent data
- compressed/aggregated older data
- selected event windows around important trades/failures

---

# 12. FEATURE ENGINE

FORGE should continuously derive features useful for discovering edge.

Implement a modular feature registry.

Initial feature families should include:

## Price/trend

- multi-window returns
- momentum
- acceleration
- slope
- trend persistence
- breakout distance
- distance from VWAP
- distance from moving averages

## Volatility

- realized volatility
- ATR-like measures
- volatility expansion
- volatility compression
- volatility-of-volatility
- range compression

## Volume/order flow

- volume acceleration
- relative volume
- buy/sell pressure proxies
- trade imbalance
- signed volume where derivable

## Microstructure

- bid/ask spread
- spread percentile
- order-book imbalance
- depth imbalance
- liquidity concentration
- replenishment rate
- price impact estimates
- short-term book pressure

## Cross-market

- relative strength
- correlations
- lead/lag behavior
- divergence
- beta-adjusted deviation

## Regime

- trend/chop classification
- volatility regime
- liquidity regime
- momentum persistence
- risk-on/risk-off proxies

All features must be timestamp-correct. Prevent lookahead leakage in historical testing.

---

# 13. OPPORTUNITY DISCOVERY

Build an always-on `OpportunityScanner` that converts raw market observations into ranked candidate opportunities.

Each opportunity should contain:

- opportunity ID
- venue
- symbol/market
- strategy family candidates
- expected direction
- expected horizon
- gross expected return
- estimated fees
- estimated spread
- estimated slippage
- expected net return
- confidence estimate
- evidence summary
- liquidity score
- regime fit
- historical analogs
- uncertainty
- estimated compute value
- expiration/staleness time

Rank opportunities by a risk-adjusted score, not raw percentage upside alone.

Suggested conceptual formula:

```text
OpportunityUtility =
    ExpectedNetReturn
    * ConfidenceCalibration
    * LiquidityFactor
    * RegimeFit
    * StrategyReliability
    - DrawdownPenalty
    - TailRiskPenalty
    - ComputeCostPenalty
    - OpportunityDelayPenalty
```

Do not hardcode a single formula if adaptive calibration produces better results. Measure which scoring model predicts realized results best.

---

# 14. STRATEGY GENOME — CORE PROPRIETARY SYSTEM

Every strategy must be represented as a structured, versioned genome rather than anonymous handwritten code.

At minimum a genome must define:

- strategy ID
- family
- version
- parent IDs
- creation reason
- hypothesis
- target venue(s)
- target instrument type(s)
- allowed assets
- feature dependencies
- regime requirements
- entry logic
- exit logic
- stop logic
- profit-taking logic
- sizing logic
- maximum holding period
- confidence model
- cost assumptions
- risk constraints
- parameter values
- feature weights
- expected behavior
- known failure modes
- evidence used to create it
- code/artifact hash
- creation timestamp

Separate declarative genome from executable implementation where possible.

The purpose is to make strategies:

- comparable
- reproducible
- mutable
- composable
- traceable
- testable
- evolvable

---

# 15. DEEPSEEK STRATEGY SCIENTIST

DeepSeek V4.1 Flash is FORGE's primary always-on reasoning brain.

Use the API alias:

```text
deepseek-flash
```

unless the operator later approves a newer official Flash successor.

DeepSeek should not receive raw wallet keys.

DeepSeek should not send exchange requests directly.

Instead expose structured tools.

## Core DeepSeek tools

Implement strict JSON-schema tool definitions for functions such as:

```text
get_system_state
get_treasury_state
get_market_snapshot
get_order_book
get_recent_features
get_market_regime
get_active_positions
get_strategy_metrics
get_strategy_genome
get_strategy_lineage
get_recent_failures
get_missed_opportunities
search_historical_analogs
run_backtest
run_replay
run_walkforward
launch_shadow_candidate
get_shadow_results
create_strategy_candidate
mutate_strategy
combine_strategy_components
compare_strategies
retire_strategy
request_compute
get_compute_status
get_compute_cost
calculate_expected_value
request_trade
request_exit
request_cancel
search_supported_venue_candidates
write_research_note
write_postmortem
```

Sensitive tools such as `request_trade` are proposals routed through deterministic policy enforcement.

## Two-pass reasoning pattern

Where beneficial:

1. **Research/reasoning pass** — DeepSeek explores evidence, failures, market context, and hypotheses.
2. **Structured action pass** — DeepSeek returns concrete tool calls/JSON for deterministic execution.

Do not let free-form prose directly control execution.

## Prompting philosophy

DeepSeek should be prompted as a quantitative research scientist, strategy engineer, and capital-efficiency analyst — not as a hype-driven gambler.

It should be repeatedly reminded:

- maximize true net growth;
- distinguish signal from noise;
- preserve statistical integrity;
- avoid lookahead leakage;
- account for all costs;
- explicitly model uncertainty;
- learn from failures;
- generate hypotheses from evidence;
- prefer falsifiable improvements;
- avoid unnecessary churn;
- measure whether its own reasoning improved outcomes.

---

# 16. ALGORITHMS THAT BUILD BETTER ALGORITHMS

This is a hard requirement.

FORGE must not merely run algorithms. It must contain **meta-algorithms that create, challenge, improve, combine, and retire algorithms**.

Implement a strategy-evolution system with:

- targeted mutation
- parameter optimization
- feature substitution
- feature addition/removal
- regime specialization
- crossover/composition
- behavioral clustering
- novelty search where justified
- lineage tracking
- fitness-based promotion
- controlled exploration

Never respond to a loss with random strategy generation.

Loss/failure workflow:

```text
OBSERVE FAILURE
    ↓
CLASSIFY FAILURE
    ↓
REGIME CHANGE OR STRATEGY DEFECT?
    ↓
IDENTIFY CONTRIBUTING FEATURES
    ↓
FORM HYPOTHESES
    ↓
GENERATE TARGETED CHALLENGERS
    ↓
REPLAY / BACKTEST
    ↓
WALK-FORWARD TEST
    ↓
LIVE SHADOW TEST
    ↓
COMPARE TO INCUMBENT
    ↓
PROMOTE / RETAIN / RETIRE
```

Failures are institutional knowledge.

Retired strategies remain queryable.

FORGE should learn that some strategies are not “bad”; they are regime-specific and should sleep until appropriate conditions return.

---

# 17. STRATEGY FITNESS

Fitness must not be raw profit alone.

Consider metrics such as:

- true net return
- drawdown
- Sharpe-like measures where statistically meaningful
- Sortino-like measures
- win/loss distribution
- profit factor
- expected value per trade
- calibration accuracy
- tail loss
- maximum adverse excursion
- stability across periods
- stability across assets
- regime robustness
- sensitivity to fees
- sensitivity to slippage
- turnover
- compute cost
- capital efficiency
- time-to-profit
- opportunity frequency

Use multi-objective fitness.

Avoid overfitting to one historical period.

---

# 18. BACKTEST / REPLAY / WALK-FORWARD / SHADOW

Build a realistic validation pipeline.

## Backtest

- use only data available at each historical timestamp;
- include fees;
- include realistic spread assumptions;
- model slippage from liquidity where possible;
- obey min order sizes;
- account for latency assumptions;
- reject impossible fills.

## Replay

Replay recorded live market events through the same strategy code used in production.

## Walk-forward

Use rolling train/validate/test windows where appropriate.

## Shadow

Shadow mode consumes live market data and generates hypothetical orders without transmitting them.

Track:

- signal timestamp
- intended order
- expected fill
- simulated fill
- subsequent price path
- fees
- realized hypothetical P&L
- deviation from model assumptions

Candidates should earn promotion based on evidence.

For the initial $20 experiment, do not require days of needless waiting if the system can establish a reasonable minimum readiness using historical replay + live shadow sampling quickly. However, do not skip all validation simply because the operator wants speed.

Build an **automated readiness gate** instead of a fixed waiting period.

---

# 19. CAPITAL ALLOCATION

Build one real treasury with many virtual strategy allocations.

Do not create separate funded wallets for every strategy unless a venue later requires it.

The allocator should continuously decide:

- how much remains in cash;
- which strategies receive capital;
- whether a strategy should be starved;
- whether a strategy should be promoted;
- whether capital should be concentrated;
- whether reserve should increase;
- whether a new venue deserves capital;

Capital allocation should scale with evidence.

Conceptually:

```text
AllocationWeight ∝
  calibrated_confidence
  × expected_net_edge
  × strategy_reliability
  × regime_fit
  × liquidity
  ÷ risk
```

Use dynamic caps.

High confidence may justify high concentration, but the Risk Governor must account for model error and tail risk.

---

# 20. COINBASE FIRST

Coinbase is the first live execution venue because the initial money is there.

Build against the current official Coinbase APIs/SDKs available to the operator account.

Support where available:

- account balances
- product discovery
- live market feeds
- market/limit orders
- order status
- cancellations
- fills
- fee retrieval or fee estimation
- minimum size/notional constraints

Do not assume every asset or order type is available to every account.

Runtime discovery should determine actual capabilities.

Do not hardcode “trade BTC/ETH/SOL only.” Scan supported liquid markets, but filter using liquidity, fee, volatility, execution feasibility, and strategy evidence.

With a $20 starting treasury, explicitly handle minimum order size and fee economics.

If the minimum economically viable trade is larger than current capital, FORGE should know that and not pretend otherwise.

---

# 21. MARKET STRATEGY FAMILIES — SEED POPULATION

The following are **seed families**, not permanent limitations.

Opus should use its highest reasoning to improve these and invent new legitimate families.

## A. Momentum / acceleration

Look for:

- return acceleration
- volume confirmation
- relative strength
- persistence
- liquidity support

## B. Breakout / volatility expansion

Look for:

- compression
- range contraction
- volatility expansion
- volume confirmation
- false breakout filters

## C. Mean reversion

Use only in regimes where reversion is empirically supported.

## D. Microstructure / order-flow

Where data quality allows:

- order-book imbalance
- depth changes
- spread behavior
- short-term pressure
- liquidity withdrawal

## E. Cross-asset relative value

- divergence from correlated assets
- lagged relationships
- relative momentum

## F. Regime rotation

Select strategy family based on measured market state.

## G. Event/news reaction (future adapter)

When an approved data feed exists, incorporate structured events and compare expected price impact to current market pricing.

## H. Prediction-market logic (future Kalshi adapter)

Architecture should later support:

- implied probability
- cross-market consistency
- related-contract constraints
- event-data updates
- order-book pricing

Do not delay Coinbase Phase 1 waiting for Kalshi.

---

# 22. COMPUTE ECONOMICS / INTELLIGENCE ROI

FORGE must reason about whether more intelligence is worth paying for.

Define and track an `IntelligenceROI` concept:

```text
IntelligenceROI =
  expected_incremental_value_from_more_analysis
  / expected_incremental_compute_cost
```

For low-value opportunities:

- deterministic code may be enough.

For promising opportunities:

- call DeepSeek.

For exceptional opportunities:

- use deeper reasoning;
- launch Modal simulations;
- compare multiple candidate models;
- run adversarial checks.

Do not impose a simplistic “never spend more than X cents” rule.

FORGE is **cost-aware, not cost-afraid**.

If $0.50 of compute substantially increases expected value on a $10+ opportunity, it may be rational.

If $1 of compute is being used to chase a $0.10 maximum upside, it is not rational.

Measure this empirically and improve the policy over time.

---

# 23. DEEPSEEK BUDGET

The operator intends to initially fund DeepSeek with approximately:

```text
$5
```

Treat inference spend as operating capital.

Implement:

- per-call token/cost estimates;
- actual cost reconciliation where possible;
- daily/monthly spend tracking;
- per-agent attribution;
- per-strategy attribution;
- cached prompt/context usage where provider support makes this economical;
- model call compression/summarization where appropriate;
- escalation only when expected value justifies it.

FORGE should ultimately aim to fund its own intelligence costs from profit.

Do not fake this accounting.

---

# 24. SELF-FUNDING OPERATING MODEL

Create explicit internal buckets/ledger categories:

- Trading Treasury
- Protected Reserve
- Compute Reserve
- Inference Reserve
- Realized Profit
- Unrealized P&L

Do not necessarily move money on-chain for each bucket. These can be accounting partitions.

Once FORGE is profitable, allow a configurable portion of realized profits to replenish compute/inference operating reserves.

Example policy to implement as configurable rather than hardcoded:

```text
5–15% of realized net gains -> operating reserve
remaining gains -> deployable treasury / protected reserve according to policy
```

The allocator should optimize this over time.

---

# 25. REAL-TIME SYSTEM LOOP

Build a continuous event-driven loop resembling:

```text
STREAM MARKET DATA
    ↓
UPDATE FEATURES
    ↓
DETECT REGIME
    ↓
DISCOVER OPPORTUNITIES
    ↓
RANK OPPORTUNITIES
    ↓
SELECT STRATEGY / GENERATE CHALLENGER IF NEEDED
    ↓
CALCULATE NET EDGE AFTER ALL COSTS
    ↓
RISK GOVERNOR
    ↓
EXECUTE OR WAIT
    ↓
TRACK FILLS / POSITION
    ↓
EXIT
    ↓
TRUE P&L
    ↓
UPDATE STRATEGY FITNESS
    ↓
UPDATE CAPITAL ALLOCATION
    ↓
DIAGNOSE FAILURE / SUCCESS
    ↓
EVOLVE
    ↓
REPEAT
```

Do not use an LLM in a latency-critical tick-by-tick loop if deterministic code can act faster and better.

The LLM's role is research, diagnosis, hypothesis generation, strategy design, tool orchestration, and higher-order adaptation.

---

# 26. DATABASE / PERSISTENCE

Use a robust local database appropriate for the server footprint. PostgreSQL is preferred if safely available as a FORGE-specific instance/schema without touching another project; SQLite may be used for the earliest bootstrap if that keeps isolation simpler, but design migrations so production persistence can scale.

Store at minimum:

- accounts
- balances
- transactions
- ledger entries
- market metadata
- market observations
- feature snapshots
- opportunities
- strategies
- strategy genomes
- lineage edges
- backtests
- replay runs
- shadow trades
- live trades
- orders
- fills
- positions
- P&L
- risk events
- DeepSeek calls/costs
- Modal jobs/costs
- system events
- operator actions
- incidents

Use migrations.

Use timestamps consistently in UTC.

---

# 27. EVENT BUS

Implement an internal asynchronous event bus or lightweight message queue suitable for a 2-vCPU process footprint.

Avoid operationally heavy infrastructure unless needed.

Potential events:

- MARKET_TICK
- ORDER_BOOK_UPDATE
- FEATURE_UPDATE
- REGIME_CHANGED
- OPPORTUNITY_FOUND
- OPPORTUNITY_EXPIRED
- STRATEGY_SIGNAL
- RISK_APPROVED
- RISK_REJECTED
- ORDER_SUBMITTED
- ORDER_FILLED
- ORDER_CANCELLED
- POSITION_OPENED
- POSITION_CLOSED
- STRATEGY_UNDERPERFORMING
- STRATEGY_RETIRED
- CHALLENGER_CREATED
- CHALLENGER_PROMOTED
- MODAL_JOB_STARTED
- MODAL_JOB_COMPLETED
- DEEPSEEK_CALL
- COMPUTE_BUDGET_WARNING
- EMERGENCY_STOP

All major system behavior should be observable through events.

---

# 28. DASHBOARD — PRIVATE DURING BUILD, DOMAIN LATER

During development, keep the dashboard private/local.

Do not alter a shared reverse proxy yet.

Before deployment, the operator will provide a domain/subdomain.

Then deploy a secure mobile-first installable PWA.

## Dashboard philosophy

The dashboard is **observability + override**, not a manual trading console.

FORGE must already know how to operate autonomously.

The dashboard should feel like watching a living economic organism.

## Home screen

Prominently display:

- total treasury
- available cash
- capital deployed
- protected reserve
- realized P&L today
- unrealized P&L
- true net earnings today
- hourly earnings
- lifetime true net earnings
- current ROI
- current operating cost
- DeepSeek spend today
- Modal spend today
- exchange fees today

## Live agent panel

Show active system activity such as:

```text
Market Scout          scanning 387 products
Opportunity Engine    evaluating 12 candidates
DeepSeek Scientist    diagnosing Momentum-v17
Evolution Arena       testing 23 challengers
Modal Lab             8 workers / replay batch
Risk Governor         monitoring exposure
Execution Engine      1 live position
```

## Strategy panel

For each strategy:

- status
- capital allocation
- family
- generation
- lineage
- regime
- confidence
- realized P&L
- win rate
- drawdown
- fitness
- last action

## Opportunity feed

Show current candidate opportunities and why FORGE is or is not acting.

Example:

```text
SOL-USD Momentum Burst
Score: 87/100
Expected net edge: +1.6%
Confidence: 81%
Liquidity: High
Decision: WAIT — spread widened
```

## Live event timeline

Plain-English examples:

- "Momentum-v17 detected abnormal SOL volume acceleration."
- "Candidate Challenger-204 entered shadow validation."
- "Modal burst launched: 48 replay simulations."
- "Candidate rejected: edge disappeared after fee model."
- "Capital allocation increased from 6% to 11%."
- "Position closed: +$0.42 true net."
- "DeepSeek diagnosed false-breakout behavior and created two targeted challengers."

## Visual design

Make it premium, clever, fast, and highly legible on a phone.

Use real-time WebSocket/SSE updates.

Make it installable as a PWA.

Support dark mode.

Keep the first screen useful within seconds.

---

# 29. EMERGENCY STOP

The dashboard must contain one unmistakable protected control:

```text
STOP ALL TRADING
```

On activation:

1. atomically set global trading state to STOPPED;
2. reject all new order requests;
3. cancel eligible pending orders;
4. optionally close positions only according to explicit safe-stop policy (do not panic-liquidate blindly);
5. persist complete state;
6. emit an audit event;
7. display the stopped state prominently;
8. require authenticated deliberate operator action to resume.

Also provide a CLI equivalent:

```bash
forge stop-all
```

and a safe script:

```text
scripts/stop-all.sh
```

---

# 30. AUTHENTICATION

Before public deployment, protect the dashboard with strong authentication.

This is an operator-only application initially.

Do not expose exchange keys to the browser.

The frontend talks only to the FORGE backend.

Use secure session handling, CSRF protection where applicable, HTTPS, rate limiting, and secure cookie settings.

---

# 31. OBSERVABILITY

Implement structured logs and metrics from day one.

Metrics should include:

- uptime
- market feed health
- data latency
- queue depth
- CPU
- RAM
- disk
- API errors
- reconnects
- opportunities/minute
- strategy signals
- trades
- fills
- order rejects
- realized P&L
- true net P&L
- DeepSeek tokens/cost
- Modal job count/cost
- risk rejects
- shadow/live divergence
- strategy promotions/retirements

Build `/health`, `/ready`, and `/metrics` endpoints.

---

# 32. FAILURE RECOVERY

FORGE must survive:

- process restart
- server reboot
- WebSocket disconnect
- Coinbase outage
- DeepSeek outage
- Modal outage
- database reconnect
- partial order fill
- lost network
- stale data
- malformed provider response

On restart:

1. load persisted state;
2. reconcile balances and open orders with Coinbase;
3. reconcile positions;
4. rebuild market subscriptions;
5. ensure no duplicate orders;
6. resume only when state is coherent.

Never assume an order failed merely because a response was lost.

Use client order IDs/idempotency keys.

---

# 33. NEW VENUE DISCOVERY

FORGE should be designed to discover additional legitimate API-accessible markets and services.

It may research:

- Kalshi
- prediction markets
- additional regulated exchanges
- APIs with economic incentives
- fee/rebate programs
- new market venues

But credential provisioning and any legally/account-restricted setup may require operator action.

Build a venue-candidate registry with fields:

- provider
- API availability
- automation permission
- jurisdiction notes
- fees
- minimum capital
- market types
- likely strategy families
- integration complexity
- expected opportunity value

FORGE may recommend integration automatically.

Do not bypass anti-bot systems or browser protections.

---

# 34. MISSED-OPPORTUNITY LEARNING

Do not learn only from trades taken.

Record opportunities FORGE rejected.

Later measure what happened.

Ask:

- Did we correctly avoid a loser?
- Did we miss a winner?
- Was the confidence model calibrated?
- Was the fee/slippage estimate too pessimistic?
- Did compute latency cost us the trade?
- Was the strategy too restrictive?

This is critical for evolution.

---

# 35. CONFIDENCE CALIBRATION

Do not let strategies emit meaningless confidence percentages.

Calibrate confidence against outcomes.

Example:

If events labeled “80% confidence” only succeed 55% of the time, the confidence model is bad.

Track calibration curves by strategy, regime, asset, and horizon.

Use calibration quality as part of fitness.

---

# 36. ANTI-OVERFITTING RULES

Automated algorithm generation creates enormous overfitting risk.

Build defenses:

- out-of-sample testing
- walk-forward testing
- minimum sample requirements where appropriate
- multiple market regimes
- realistic cost assumptions
- parameter stability tests
- perturbation tests
- randomization/bootstrapping where useful
- penalize excessive complexity
- require live shadow evidence for fragile strategies

FORGE should prefer a simple robust edge over a complicated historical miracle.

---

# 37. EXPLORATION VS EXPLOITATION

Maintain an explicit exploration budget.

Most capital should generally follow validated strategies, while a smaller portion of research compute/capital may test promising new ideas.

As treasury grows, allow controlled experimentation without jeopardizing the core.

Do not permanently freeze onto the first strategy that works.

Do not constantly abandon working strategies just to generate novelty.

---

# 38. PROPRIETARY ADVANTAGE

FORGE's proprietary value should accumulate in:

- private strategy genomes
- lineage data
- failure postmortems
- feature performance statistics
- regime mappings
- execution-quality data
- confidence calibration
- compute ROI data
- strategy interaction data
- capital allocation history

Treat these as intellectual property.

Do not leak them into logs or public endpoints unnecessarily.

---

# 39. AUTOMATED RESEARCH CYCLES

Implement research loops at multiple cadences.

## Continuous

- scan markets
- update features
- rank opportunities
- update risk

## Frequent

- evaluate recent trades
- update calibration
- update strategy health

## Periodic

- DeepSeek postmortem on failures
- generate challengers
- run Modal tournaments
- update regime models

## Off-peak / economical windows

Where DeepSeek pricing is lower or compute is cheaper, shift non-urgent heavy research into those windows.

Do not delay a time-sensitive opportunity merely to save inference cost.

---

# 40. BUILD FOR EXTENSION, NOT PREMATURE COMPLEXITY

The initial live product is Coinbase-first.

Do not delay launch because every future venue is not integrated.

The correct sequence is:

```text
FORGE CORE
→ Coinbase market data
→ Coinbase shadow/live execution
→ evolution loop
→ dashboard
→ stable autonomous operation
→ add Kalshi / other venues
```

Provider boundaries must be generic enough that future adapters are straightforward.

---

# 41. TESTING REQUIREMENTS

Write meaningful tests.

## Unit tests

- feature calculations
- fee calculations
- slippage models
- position sizing
- reserve logic
- confidence calibration
- strategy genome serialization
- risk rules
- idempotency
- cost attribution

## Integration tests

- mocked Coinbase API
- mocked WebSocket reconnect
- mocked DeepSeek tools
- mocked Modal jobs
- database
- backend API

## Simulation tests

- feed synthetic market data
- generate signals
- approve/reject risk
- simulate fills
- close positions
- calculate P&L
- evolve strategy

## Failure tests

- duplicate order response
- network timeout after submit
- partial fills
- stale data
- malformed API response
- DeepSeek unavailable
- Modal unavailable
- process restart with open position

---

# 42. FIRST LIVE READINESS GATE

Do not flip from code completion directly into uncontrolled live trading.

Create an automated readiness report.

Live micro-capital may be enabled only when:

- Coinbase connection healthy;
- balances reconcile;
- market feed stable;
- fees/minimum sizes discovered;
- emergency stop tested;
- risk governor tested;
- order idempotency tested;
- at least one strategy has passed minimum replay/shadow criteria;
- P&L accounting works;
- true costs are tracked;
- operator has supplied explicit live credentials;
- live mode environment flag is enabled.

The purpose is not bureaucracy. It is avoiding losing the entire experiment to a software bug.

---

# 43. LIVE MODE SETTINGS

Use explicit modes:

```text
MOCK
REPLAY
SHADOW
LIVE
STOPPED
```

Require explicit configuration for LIVE.

After live mode is enabled, FORGE does not request per-trade confirmation.

---

# 44. FIRST-LAUNCH STRATEGY

Given only $20, immediately discover:

- actual Coinbase product minimums;
- actual fee tier;
- actual tradable products;
- spread/liquidity;
- whether tiny trades are economically sensible.

Do not assume frequent scalping is viable.

FORGE should choose the strategy/horizon that has the best measured economics for the available capital.

This may mean fewer higher-quality trades rather than constant churn.

The architecture must still scale automatically as treasury grows.

---

# 45. TRUE OBJECTIVE FUNCTION

Do **not** optimize for “number of profitable seconds.”

Do **not** optimize for “always have a position.”

Do **not** optimize for “maximum leverage.”

Primary objective:

```text
MAXIMIZE LONG-RUN TRUE NET TREASURY GROWTH
SUBJECT TO SURVIVAL, POLICY, AND RISK CONSTRAINTS
```

Secondary objectives:

- minimize probability of ruin;
- improve calibration;
- improve capital efficiency;
- improve compute efficiency;
- improve strategy discovery rate;
- maintain robust autonomous operation.

---

# 46. OPUS 5.5 — ENGINEERING FREEDOM

You are explicitly encouraged to use your highest reasoning and engineering ability.

If you identify:

- a stronger algorithmic formulation;
- a more efficient data structure;
- a better statistical method;
- a better strategy-selection method;
- a superior evolutionary algorithm;
- a more efficient Modal architecture;
- a safer risk model;
- a better confidence calibration technique;
- a more useful market feature;
- a better dashboard interaction;
- a more scalable provider abstraction;

then improve the design.

Do not follow this dossier mechanically when you can produce a demonstrably better result.

However, never violate the hard requirements:

- project isolation;
- deterministic risk enforcement;
- credential isolation;
- 2-vCPU normal / 3-vCPU local ceiling;
- Modal budget limit;
- true cost accounting;
- autonomous operation;
- auditable strategy evolution;
- emergency stop;
- no unauthorized systems or prohibited behavior.

Every significant departure from this document must be recorded in `docs/DECISIONS.md` with:

- what changed;
- why;
- expected benefit;
- risk;
- rollback.

---

# 47. CONTINUITY FILES

Create and maintain:

## `docs/BUILD_STATUS.md`

What exists, what works, what's blocked.

## `docs/CURRENT_STATE.md`

Current architecture/runtime/deployment state.

## `docs/DECISIONS.md`

Engineering decisions.

## `docs/CREDENTIALS_REQUIRED.md`

Only credentials still needed.

## `docs/STRATEGY_EVOLUTION.md`

How genomes, mutation, validation, promotion, retirement work.

## `docs/MODAL_POLICY.md`

How FORGE uses Modal and tracks ROI.

## `docs/RISK_POLICY.md`

Hard deterministic risk boundaries.

## `docs/INCIDENTS.md`

Any live incidents, anomalies, unexpected fills, or recovery events.

Update these as work proceeds.

---

# 48. PHASED BUILD PLAN

Execute sequentially but overlap work where safe.

## Phase 0 — Isolation + bootstrap

- create `/srv/forge`;
- initialize Git;
- create dedicated environment;
- establish service user if safe;
- verify local resource limits;
- create directory structure;
- create `.env.example`;
- create continuity docs.

## Phase 1 — Core domain + persistence

- configuration
- event models
- ledger
- strategy models
- database/migrations
- logging
- health checks

## Phase 2 — Coinbase market-data adapter

- product discovery
- balances mock/live adapter
- WebSocket feeds
- normalized events
- reconnect logic
- historical persistence

## Phase 3 — Features + regimes

- initial feature families
- feature registry
- regime engine

## Phase 4 — Opportunity engine

- scanner
- scorer
- opportunity lifecycle

## Phase 5 — Strategy genome + seed strategies

- genome schema
- strategy registry
- initial seed families
- lineage graph

## Phase 6 — Backtest/replay/shadow

- common execution simulation
- cost modeling
- walk-forward
- live shadow

## Phase 7 — DeepSeek brain

- tool schemas
- strategy scientist prompts
- postmortem workflow
- mutation/hypothesis generation

## Phase 8 — Evolution Arena

- challengers
- fitness
- promotion
- retirement
- strategy sleeping by regime

## Phase 9 — Modal

- authenticated client
- burst jobs
- budget tracking
- compute allocator

## Phase 10 — Treasury / risk / execution

- allocator
- reserve logic
- deterministic risk governor
- Coinbase execution
- idempotency
- reconciliation

## Phase 11 — Dashboard backend

- REST/API
- WebSockets
- metrics
- live event feed

## Phase 12 — PWA frontend

- mobile-first operator portal
- live cards
- strategies
- opportunities
- compute
- costs
- event timeline
- emergency stop

## Phase 13 — End-to-end simulation

- simulated treasury
- mock Coinbase
- DeepSeek mock/live if key exists
- Modal mock/live if credentials exist
- strategy evolution
- dashboard

## Phase 14 — Live readiness

- credentials
- account discovery
- fee discovery
- min order discovery
- shadow evidence
- emergency stop test
- live-mode gate

## Phase 15 — Micro-live $20 experiment

- enable LIVE only after readiness passes;
- FORGE operates autonomously;
- monitor true net performance;
- evolve based on evidence.

---

# 49. FIRST TERMINAL ACTIONS

Begin now.

Suggested first actions (adapt safely to host):

```bash
# Verify location only; do not scan unrelated projects.
mkdir -p /srv/forge
cd /srv/forge

git init

# Create isolated Python environment using the safest available tool.
# Prefer uv if available, otherwise python venv.

mkdir -p docs config src tests data logs run scripts modal web systemd
```

Do not blindly execute package-manager or system-wide commands if they could affect other projects.

Record every host-level dependency you need.

---

# 50. FIRST SUCCESS MILESTONE

The first meaningful success is **not** a pretty UI.

The first milestone is:

> FORGE can ingest live Coinbase market data, normalize it, compute features, generate ranked opportunities, run at least one strategy through realistic replay/shadow execution, track true net economics, invoke DeepSeek through tools, launch a Modal research job, and display the entire process in a live private dashboard — all inside its isolated resource envelope.

The next milestone is:

> FORGE passes its automated live-readiness gate and can autonomously execute a tiny permitted live position using the $20 experiment treasury with no per-trade human approval.

The next milestone is:

> FORGE successfully learns from its own results, generates a targeted challenger, validates it, and promotes or rejects it based on evidence.

That third milestone proves FORGE is more than a bot.

---

# 51. DEFINITION OF DONE FOR V1

FORGE V1 is complete only when all of the following are true:

- isolated project root established;
- no dependency on other SaaS projects;
- clean install/bootstrap documented;
- local CPU limits enforced;
- Coinbase adapter works;
- real-time market data works;
- feature engine works;
- opportunity ranking works;
- strategy genomes work;
- lineage works;
- backtest/replay works;
- shadow works;
- DeepSeek tool orchestration works;
- strategy postmortem works;
- targeted strategy mutation works;
- evolution arena works;
- Modal jobs work;
- Modal cost tracking works;
- treasury works;
- true net P&L works;
- risk governor works;
- execution is idempotent;
- emergency stop works;
- restart/reconciliation works;
- private dashboard works;
- PWA works;
- real-time event stream works;
- credentials are externalized;
- tests pass;
- live readiness report works;
- operator documentation exists.

---

# 52. WHAT NOT TO DO

Do not:

- build one giant script;
- hardcode $20 assumptions everywhere;
- let DeepSeek directly hold private keys;
- require human approval for every trade;
- force trades when no edge exists;
- claim guaranteed profit;
- ignore fees/slippage;
- optimize only on backtests;
- discard losing-strategy knowledge;
- generate random strategies with no hypothesis;
- allow uncontrolled model-generated code directly into live trading without validation;
- consume all server CPU;
- keep Modal permanently warm without evidence it is worth the cost;
- expose a public dashboard before authentication/domain configuration;
- touch another North Star Imagine project;
- scan unrelated directories for secrets;
- bypass platform protections;
- perform unauthorized actions.

---

# 53. BUILD PHILOSOPHY

FORGE should behave like an economic organism with a research laboratory attached.

The execution engine is deterministic.

The research brain is adaptive.

The strategy population evolves.

The treasury compounds.

Compute is allocated economically.

Failures become knowledge.

Winning strategies earn more resources.

Weak strategies lose capital and enter research/archive state.

New markets can be added through adapters.

The operator should be able to open the dashboard at any time and immediately understand:

- what FORGE owns;
- what FORGE is risking;
- what FORGE is earning;
- what FORGE is spending;
- what FORGE is learning;
- what FORGE is testing;
- what FORGE is doing right now;
- whether FORGE is actually profitable after every cost.

---

# 54. FINAL DIRECTIVE TO OPUS 5.5

You have sufficient direction to begin.

**Proceed into full autonomous build mode now.**

Do not wait for more conceptual discussion.

Use your highest reasoning to turn this specification into a production-quality, isolated, extensible FORGE codebase.

Where a credential is missing, build the adapter and continue.

Where a better implementation is evident, improve it and document why.

Where a strategy fails, preserve the evidence and use it to build a better challenger.

Where compute can materially increase expected economic value, use the authorized resources intelligently.

Where no trade is justified, do not trade — continue searching, learning, testing, and evolving.

The system must be autonomous by default, observable at all times, deterministic where money or safety is involved, and continuously capable of becoming better at its core purpose:

# **FIND OPPORTUNITIES. REINVEST. GROW. EVOLVE.**

Build FORGE.

