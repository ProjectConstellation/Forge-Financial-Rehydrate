# FORGE — Master Build Dossier
## Autonomous Capital Growth Engine
### **F**ind Opportunities · **R**einvest · **G**row · **E**volve

**Audience:** Fresh Pi CLI session running Opus 5.5 on the North Star Imagine Command Center server  
**Project:** FORGE  
**Build mode:** New isolated project, greenfield implementation  
**Primary runtime brain:** DeepSeek V4.1 Flash (`deepseek-flash`)  
**Primary first execution rail:** Coinbase / Coinbase Developer Platform  
**Elastic compute:** Modal  
**Initial live experimental treasury:** **$20 USD-equivalent maximum**  
**Local compute target:** **2 vCPU normal / 3 vCPU hard ceiling**  
**Modal compute allowance:** **up to the full $30/month included compute budget**  
**Operating mode:** 24/7 autonomous observation, research, strategy generation, testing, capital allocation, execution, accounting, and evolution

---

# 0. READ THIS FIRST — ABSOLUTE PROJECT-ISOLATION DIRECTIVE

## You are building a NEW project on this server. The project is called **FORGE**.

You are operating on a server that contains **several very important North Star Imagine SaaS products and active development environments**. One of those projects is **Imagine Compass**, an autonomous building platform, and it is being actively developed in another terminal/session.

## **DO NOT TOUCH ANY OTHER PROJECT.**

There is no ambiguity in this instruction.

FORGE must be created as a completely independent project with its own:

- isolated root folder;
- isolated Git repository;
- isolated source tree;
- isolated Python virtual environment and lock file;
- isolated frontend dependencies;
- isolated runtime configuration;
- isolated `.env` and secret references;
- isolated database and data files;
- isolated caches;
- isolated logs;
- isolated PID/runtime directories;
- isolated ports;
- isolated service names;
- isolated systemd/cgroup configuration;
- isolated Modal application namespace;
- isolated tests;
- isolated build/deployment scripts;
- isolated documentation;
- isolated backups;
- isolated temporary files.

FORGE must **function and thrive independently from every other project on this server**.

### Forbidden actions

Do **not**:

- recursively scan the server;
- recursively inspect unrelated home directories;
- enter or inspect another SaaS project's repository;
- read another project's `.env`, secrets, source code, databases, logs, caches, prompts, or runtime state;
- import code from another project;
- reuse another project's virtual environment, node modules, database, Redis instance, port, service name, PID file, logs, or cron/systemd unit;
- stop/restart/modify another project's process;
- run destructive host-wide commands;
- change firewall rules globally unless explicitly required and approved;
- change host packages in a way that could break unrelated applications;
- modify global shell configuration unless absolutely necessary;
- bind FORGE to a port already in use;
- assume that any existing directory belongs to FORGE;
- use broad commands such as `find /`, `grep -R /`, or recursive searches through unrelated paths.

### Allowed host inspection

Before creating FORGE, perform a **minimal non-invasive host inventory only**. It is acceptable to run commands such as:

```bash
pwd
whoami
hostname
uname -a
nproc
free -h
df -h
python3 --version
git --version
node --version || true
npm --version || true
modal --version || true
modal token info || true
modal config show --redact || true
ss -ltnp
```

Do not inspect unrelated application directories to learn how they work.

### Project root

Prefer a clean dedicated path such as:

```text
~/forge
```

or, if operating with an appropriate service account and permissions:

```text
/srv/forge
```

Before using the path, verify it is not an existing unrelated project. If it exists and is not clearly FORGE, **do not overwrite it**. Choose another isolated root and document the choice.

Create FORGE's Git repository inside that root. FORGE must never be nested inside the Imagine Compass repository or another product repository.

### Dedicated OS identity — preferred

If safely possible without affecting other projects, create or use a dedicated Unix service account named `forge` for runtime services. If that would require unsafe host-wide changes or permissions are unavailable, keep development under the current user but enforce isolation with project-local paths, cgroups/systemd scope, and strict service names.

---

# 1. WHAT YOU ARE BUILDING

FORGE stands for:

> **Find Opportunities · Reinvest · Grow · Evolve**

FORGE is an **Autonomous Capital Growth Engine**.

It is **not** a single trading bot. It is **not** a static collection of strategies. It is **not** an LLM that blindly decides whether to buy or sell.

FORGE is a persistent economic system whose purpose is to:

1. continuously observe legitimate, API-accessible markets and economic opportunities;
2. detect potential edges, inefficiencies, dislocations, incentives, and asymmetric opportunities;
3. construct and evolve proprietary strategies from evidence;
4. test those strategies rigorously before granting meaningful live capital;
5. allocate capital dynamically among competing strategies;
6. execute approved actions autonomously;
7. immediately account for realized gains and losses;
8. reinvest available earnings when the expected opportunity justifies it;
9. preserve knowledge from failures rather than repeating them;
10. continuously discover better algorithms, better features, better venues, and better uses of compute;
11. operate 24/7 without requiring routine human trade approval;
12. measure success on **true net treasury growth after every cost**.

The engine's highest-level objective is:

> **Maximize long-run net treasury growth and compounding velocity while controlling probability of ruin, continuously improving the quality of the algorithms used to deploy capital.**

FORGE should always be doing economically useful work: observing, analyzing, learning, testing, validating, comparing, waiting strategically, or executing.

**Do not force a trade simply because time has passed.** Financial inactivity can be the highest-value action when no sufficiently strong edge exists. FORGE must be intellectually active 24/7, not financially hyperactive for its own sake.

The user wants aggressive growth and accepts that the initial **$20 experiment may be lost**. That does not remove the obligation to act intelligently. A system that repeatedly gambles until it gets lucky is a failure even if one outcome is profitable.

---

# 2. NON-NEGOTIABLE PRODUCT PRINCIPLES

## 2.1 Autonomous by default

Once credentials are configured and live mode is explicitly enabled, routine operation must require **zero manual trade approvals**.

Autonomy includes:

- market-data ingestion;
- opportunity detection;
- feature computation;
- strategy hypothesis creation;
- strategy mutation;
- backtesting;
- walk-forward validation;
- shadow execution;
- strategy promotion/demotion;
- capital allocation;
- order placement/cancellation;
- position monitoring;
- realized/unrealized P&L accounting;
- compute escalation;
- Modal job submission;
- DeepSeek inference decisions;
- daily/weekly self-analysis;
- failure diagnosis;
- service recovery;
- alert generation;
- venue research and adapter prototyping.

Human involvement should be reserved for initial credentials, policy changes, legal/account onboarding that cannot be automated, and emergency override.

## 2.2 Market-agnostic architecture

Coinbase is the first live venue, **not the architectural boundary**.

Build every market integration behind a standard `VenueAdapter` interface so future adapters can include, when permitted and available:

- Coinbase;
- Kalshi;
- prediction markets;
- other regulated exchanges;
- DeFi protocols;
- yield/carry markets;
- equities/ETFs if exposed by an authorized API;
- market-neutral opportunities;
- machine-payable economic services;
- other legitimate API-driven income channels.

Do not hardwire core strategy logic to Coinbase-specific payloads.

## 2.3 Proprietary algorithms are a first-class requirement

FORGE must continuously develop **custom proprietary algorithms**.

A strategy must not merely be an LLM-written blob of code. It must have a structured, inspectable identity including:

- strategy ID;
- strategy family;
- semantic purpose;
- hypothesis;
- feature dependencies;
- parameters;
- entry conditions;
- exit conditions;
- sizing logic;
- applicable market regimes;
- excluded regimes;
- expected holding period;
- expected turnover;
- expected fee burden;
- expected slippage sensitivity;
- parent strategy IDs;
- mutation history;
- generation number;
- training/evaluation dataset references;
- historical fitness;
- shadow fitness;
- live fitness;
- failure reasons;
- retirement reason;
- resurrection conditions;
- confidence calibration history.

FORGE must produce algorithm families that can create, improve, combine, and retire other algorithms.

## 2.4 Evidence before confidence

Do not allow an LLM to declare a trade “almost guaranteed.” Confidence must come from empirical calibration.

Any confidence value used for capital sizing must be tied to:

- historical out-of-sample performance;
- walk-forward results;
- current market-regime match;
- live shadow performance;
- sample size;
- uncertainty bounds;
- expected costs;
- liquidity;
- strategy freshness;
- model drift;
- cross-validation or comparable robustness test.

A raw LLM statement such as “95% confident” has **zero authority** by itself.

## 2.5 Learn from losses — never random reset

When a strategy underperforms:

1. reduce or remove live capital according to policy;
2. preserve the complete strategy genome and execution record;
3. attribute the failure where possible;
4. compare expected vs actual behavior;
5. identify whether failure arose from regime mismatch, execution, latency, fees, slippage, parameter instability, overfitting, faulty data, correlation change, or pure variance;
6. create one or more reasoned successor hypotheses;
7. test successors against the parent and current champions;
8. promote only if evidence supports promotion.

A strategy may be **retired**, **hibernated**, or **retrained**. Never delete useful lineage.

## 2.6 True profit means net profit

FORGE accounting must include:

```text
True Net P&L =
    realized trading profit/loss
  + realized yield/reward income
  + other realized authorized income
  - trading fees
  - spread costs
  - slippage
  - blockchain/gas costs
  - exchange/venue fees
  - DeepSeek inference costs
  - Modal compute costs attributable to FORGE
  - paid market-data costs
  - x402/API payments
  - other operating costs
```

If a strategy earns $5 gross and consumes $6 in total costs, it lost $1. FORGE must know this.

## 2.7 Cost-aware, never artificially cost-paralyzed

FORGE is **cost-aware, not cheap**.

It is encouraged to spend more compute or inference when the expected benefit materially exceeds the cost.

The decision rule should resemble:

```text
Expected Net Opportunity Value =
  P(success | calibrated evidence) * expected_gain
  - P(failure | calibrated evidence) * expected_loss
  - trading_costs
  - slippage_costs
  - inference_costs
  - compute_costs
  - liquidity_penalty
  - uncertainty_penalty
  - tail_risk_penalty
```

When a potentially important opportunity warrants deeper validation, FORGE may escalate from cheap deterministic logic to DeepSeek reasoning to Modal-parallel simulation.

---

# 3. CURRENT RESOURCE ENVELOPE

## Local server

FORGE runs on the North Star Imagine Command Center server.

FORGE's local resource policy is:

- normal target: **2 vCPUs**;
- hard ceiling: **3 vCPUs**;
- memory target: design to remain comfortably below the host's available memory and avoid interfering with other SaaS projects;
- IO: avoid sustained heavy disk writes on hot host paths;
- network: maintain persistent market WebSockets efficiently;
- no GPU requirement for baseline operation.

Use Linux cgroups/systemd resource controls or an equivalent mechanism so the local FORGE runtime cannot accidentally monopolize CPU.

Recommended service-level resource controls where systemd is available:

```ini
CPUQuota=300%
CPUWeight=50
MemoryHigh=<sensible value after host inspection>
MemoryMax=<sensible hard limit after host inspection>
Nice=5
IOSchedulingClass=best-effort
```

Do not blindly apply a memory value before checking available RAM and current host pressure.

FORGE should typically stay around **200% CPU** aggregate when busy and never exceed **300% CPU** aggregate locally except for a short bootstrap task explicitly executed by the developer before service launch. Heavy analytical jobs belong on Modal.

---

# 4. MODAL — AUTHORIZED AND ENCOURAGED ELASTIC COMPUTE

## 4.1 Modal is part of FORGE's architecture

Modal is **explicitly authorized and encouraged**.

The user has approximately **$30/month in Modal included compute** and authorizes FORGE to use as much of that allowance as needed when doing so improves its economic objective.

FORGE should not attempt to “save” Modal credits merely for the sake of saving them. It should maximize **return on compute**.

However, it must track the remaining allowance and avoid unknowingly creating out-of-pocket Modal spend beyond the authorized monthly budget unless the user later changes that policy.

## 4.2 Modal credential boundary

Modal credentials already exist on this server.

Use only standard host/user-level Modal authentication mechanisms. Current Modal documentation indicates configuration may be read from the active profile in `~/.modal.toml`, or from `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` environment variables.

Allowed verification commands include:

```bash
modal token info
modal config show --redact
```

**Never inspect unrelated project `.env` files to obtain Modal credentials.**

If Modal is already authenticated, use the existing authorized user-level authentication. If it is not authenticated, create the integration with placeholders and explicitly request the missing credentials.

## 4.3 Warm capacity

Where supported and within budget, maintain approximately **0.5 cloud vCPU equivalent** of warm Modal capacity for low-latency research dispatch.

Modal currently prices CPU in physical cores where one physical core is roughly two cloud vCPUs, and supports fractional CPU requests. Therefore approximately `cpu=0.25` physical core corresponds to roughly 0.5 vCPU equivalent.

Use `min_containers=1` only where the economics make sense. The minimum Modal CPU request is currently smaller than this, so the warm baseline may be adjusted automatically if keeping 0.5 vCPU warm would reduce the remaining burst budget too aggressively.

The warm pool is **not a sacred fixed resource**. The economic controller may choose:

- `0.125` physical core minimum for extremely light warm state;
- `0.25` physical core for ~0.5 vCPU equivalent;
- zero warm containers when keeping one alive has negative expected value;
- larger temporary CPU allocations during active opportunity analysis.

## 4.4 Modal burst authority

FORGE may spin up Modal resources for:

- historical replay;
- Monte Carlo simulation;
- parameter sweeps;
- feature discovery;
- correlation scans;
- market-regime clustering;
- walk-forward optimization;
- strategy tournaments;
- candidate strategy generation validation;
- ensemble evaluation;
- large-batch backtesting;
- stress testing;
- synthetic adverse scenarios;
- execution simulation;
- slippage simulation;
- large-scale data transforms;
- probabilistic calibration;
- opportunity-ranking experiments;
- venue adapter tests;
- any other legitimate computation that plausibly improves expected net economic return.

When FORGE detects an unusually valuable opportunity, it may immediately allocate more Modal compute if expected benefit exceeds compute cost and latency permits.

When the job ends, scale unnecessary resources down automatically.

## 4.5 Modal spend accounting

Build a `ComputeLedger` that records for every Modal job:

- job ID;
- parent opportunity ID;
- strategy ID(s);
- start/end time;
- requested CPU/memory/GPU;
- actual compute time;
- estimated and actual cost when available;
- output artifact;
- whether the output changed a decision;
- incremental value estimate;
- realized downstream P&L attribution when measurable.

FORGE must learn whether its compute purchases pay for themselves.

## 4.6 Modal app namespace

Create dedicated Modal resources such as:

```text
forge-research
forge-backtest
forge-sim
forge-optimizer
forge-sandbox
```

Do not reuse another project's Modal app names, volumes, secrets, or queues.

---

# 5. CREDENTIAL AND API-KEY DIRECTIVE

The following providers may require credentials:

- DeepSeek;
- Coinbase/CDP;
- Coinbase Advanced Trade if used;
- Modal;
- Kalshi later;
- market-data services later;
- x402-capable services later;
- any future authorized venue.

## Build first; plug credentials in cleanly

Build the infrastructure with:

- provider interfaces;
- environment-variable placeholders;
- validation code;
- mocks;
- fixtures;
- paper/sandbox adapters;
- dependency injection;
- graceful “credential unavailable” states.

Credentials will be supplied **as needed**.

Do not block the entire build because one provider credential is absent.

If a credential is required to continue a specific integration:

1. finish everything possible without it;
2. clearly list the exact variable(s) required;
3. mark that adapter `CONFIG_REQUIRED`;
4. proceed with the remainder of the system;
5. never invent a credential;
6. never harvest a credential from another project's files.

Create an `.env.example` containing names only, such as:

```dotenv
FORGE_ENV=development
FORGE_LIVE_TRADING=false
FORGE_INITIAL_TREASURY_USD=20
FORGE_LOCAL_CPU_TARGET=2
FORGE_LOCAL_CPU_MAX=3
FORGE_MODAL_MONTHLY_BUDGET_USD=30
FORGE_DEEPSEEK_BUDGET_START_USD=5

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash

COINBASE_CDP_API_KEY_ID=
COINBASE_CDP_API_KEY_SECRET=
COINBASE_ADVANCED_API_KEY=
COINBASE_ADVANCED_API_SECRET=

MODAL_PROFILE=
# Prefer existing authenticated host-level Modal profile where authorized.

KALSHI_API_KEY_ID=
KALSHI_PRIVATE_KEY_PATH=
```

Never commit `.env`, private keys, bearer tokens, wallet seeds, or secret config.

---

# 6. PRIMARY BRAIN — DEEPSEEK V4.1 FLASH

Use **DeepSeek V4.1 Flash** as FORGE's default background reasoning brain.

Current official API alias:

```text
deepseek-flash
```

Design against the alias rather than a hardcoded retired model identifier so the runtime can be upgraded deliberately later.

DeepSeek is currently suitable because it supports large context, thinking/non-thinking operation, JSON output, tool calls, and an agent-friendly API.

## 6.1 DeepSeek does not directly hold credentials

The model must never receive raw private keys, wallet secrets, exchange secrets, or Modal secret values in its prompt.

DeepSeek receives **capabilities through typed tools**.

Example:

```text
DeepSeek: "I want to test Strategy X over the last 14 days across BTC-USD and ETH-USD."
↓
FORGE tool router validates request
↓
Backtest service / Modal executes it
↓
Structured result returned to DeepSeek
↓
DeepSeek reasons about result
```

## 6.2 Two-path inference architecture

Implement two reasoning pathways:

### Analysis path
Use thinking mode for:

- failure diagnosis;
- novel strategy hypotheses;
- regime interpretation;
- feature proposals;
- experiment design;
- postmortems;
- cross-strategy analysis;
- venue/opportunity research;
- complex decisions.

### Structured action path
Use a constrained structured/tool-call pass for:

- requesting backtests;
- querying market state;
- creating a candidate strategy;
- shadow deployment;
- promoting/retiring candidates;
- requesting Modal jobs;
- requesting opportunity comparisons;
- asking deterministic services for exact values.

Do not depend on the LLM to perform arithmetic that deterministic code can perform exactly.

## 6.3 Inference effort must be dynamic

Implement `InferenceGovernor` levels:

```text
L0 — deterministic only
L1 — cheap non-thinking DeepSeek
L2 — thinking / higher effort DeepSeek
L3 — multi-pass DeepSeek with critic
L4 — DeepSeek + parallel Modal simulation / ensemble validation
```

Escalate according to:

- expected economic value;
- novelty;
- uncertainty;
- capital at risk;
- strategy importance;
- disagreement among deterministic models;
- historical value of additional reasoning;
- cost remaining in the inference budget.

Do not spend $0.50 worth of inference to chase an opportunity whose maximum plausible profit is $0.03.

Conversely, do not refuse a $0.50 inference expense if it is plausibly necessary to validate a high-value opportunity whose expected incremental profit is many multiples of the expense.

## 6.4 Inference ledger

Every DeepSeek call must record:

- request ID;
- agent identity;
- purpose;
- opportunity/strategy IDs;
- prompt version;
- model alias/version returned by provider if available;
- thinking mode/effort;
- input tokens;
- cached input tokens;
- output tokens;
- estimated cost;
- latency;
- tool calls requested;
- result classification;
- whether the call affected a live decision;
- downstream realized P&L attribution when practical.

FORGE must learn **which kinds of thinking are worth buying**.

---

# 7. THE CORE ARCHITECTURE

Use a modular monorepo. Do not create a sprawling microservice fleet unless profiling proves it necessary.

Recommended baseline:

- Python 3.12+ backend/runtime;
- `asyncio` + `uvloop` for market streams and concurrent IO;
- FastAPI for local control/dashboard API;
- Pydantic v2 for typed contracts;
- SQLite in WAL mode for transactional state initially;
- DuckDB + Parquet for analytical/history workloads;
- Polars/NumPy for efficient vectorized research;
- lightweight React + TypeScript + Vite dashboard compiled to static assets, or equally lightweight alternative;
- Modal Python SDK for burst compute;
- provider SDKs only where they improve reliability;
- direct WebSocket/REST adapters where needed.

Avoid infrastructure vanity. The system must fit inside the 2-vCPU normal budget.

## 7.1 Suggested high-level process topology

```text
┌───────────────────────────────────────────────────────────────┐
│                        FORGE LOCAL CORE                       │
│                                                               │
│  Venue WebSockets ─► Market Fabric ─► Feature Engine          │
│                              │               │                │
│                              ▼               ▼                │
│                       Opportunity Bus    Regime Engine         │
│                              │               │                │
│                              └──────┬────────┘                │
│                                     ▼                         │
│                             Strategy Population               │
│                                     │                         │
│                 ┌───────────────────┼───────────────────┐     │
│                 ▼                   ▼                   ▼     │
│          Shadow Evaluator     Live Allocator     DeepSeek Lab │
│                 │                   │                   │     │
│                 └──────────────┬────┘                   │     │
│                                ▼                        │     │
│                           Risk Governor ◄───────────────┘     │
│                                │                              │
│                                ▼                              │
│                        Execution Gateway                      │
│                                │                              │
│                                ▼                              │
│                         Coinbase/CDP                           │
│                                                               │
│  Ledger ◄── every action      Compute Governor ───────┐       │
│  Memory ◄── every result                             │       │
│  Dashboard ◄── live state                            ▼       │
└─────────────────────────────────────────────────── Modal ─────┘
```

---

# 8. REPOSITORY / FILE TREE

Create a clean structure similar to the following. Improve it if a superior organization is obvious, but preserve separation of responsibilities.

```text
forge/
├── README.md
├── AGENTS.md
├── ARCHITECTURE.md
├── SECURITY.md
├── OPERATIONS.md
├── STRATEGY_SPEC.md
├── pyproject.toml
├── uv.lock                     # or equivalent deterministic lock
├── .python-version
├── .gitignore
├── .env.example
├── Makefile
├── docker-compose.dev.yml      # optional, project-local only
│
├── config/
│   ├── forge.example.yaml
│   ├── risk.example.yaml
│   ├── compute.example.yaml
│   ├── venues.example.yaml
│   └── logging.example.yaml
│
├── src/forge/
│   ├── __init__.py
│   ├── main.py
│   ├── bootstrap.py
│   ├── settings.py
│   ├── lifecycle.py
│   │
│   ├── core/
│   │   ├── clock.py
│   │   ├── ids.py
│   │   ├── events.py
│   │   ├── bus.py
│   │   ├── health.py
│   │   └── exceptions.py
│   │
│   ├── market/
│   │   ├── fabric.py
│   │   ├── symbols.py
│   │   ├── orderbook.py
│   │   ├── bars.py
│   │   ├── features.py
│   │   ├── regimes.py
│   │   ├── correlations.py
│   │   └── quality.py
│   │
│   ├── venues/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── coinbase/
│   │   │   ├── adapter.py
│   │   │   ├── market_data.py
│   │   │   ├── execution.py
│   │   │   ├── balances.py
│   │   │   ├── agentic_wallet.py
│   │   │   └── normalization.py
│   │   ├── paper/
│   │   │   └── adapter.py
│   │   └── future/
│   │       └── README.md
│   │
│   ├── opportunities/
│   │   ├── detector.py
│   │   ├── scorer.py
│   │   ├── registry.py
│   │   └── types.py
│   │
│   ├── strategies/
│   │   ├── genome.py
│   │   ├── compiler.py
│   │   ├── primitives.py
│   │   ├── runtime.py
│   │   ├── registry.py
│   │   ├── lineage.py
│   │   ├── fitness.py
│   │   ├── mutation.py
│   │   ├── crossover.py
│   │   ├── retirement.py
│   │   ├── promotion.py
│   │   └── families/
│   │       ├── momentum.py
│   │       ├── breakout.py
│   │       ├── mean_reversion.py
│   │       ├── microstructure.py
│   │       ├── volatility.py
│   │       └── relative_value.py
│   │
│   ├── research/
│   │   ├── deepseek.py
│   │   ├── scientist.py
│   │   ├── critic.py
│   │   ├── experiments.py
│   │   ├── backtest.py
│   │   ├── walk_forward.py
│   │   ├── shadow.py
│   │   ├── calibration.py
│   │   ├── monte_carlo.py
│   │   └── replay.py
│   │
│   ├── agents/
│   │   ├── base.py
│   │   ├── orchestrator.py
│   │   ├── market_scout.py
│   │   ├── strategy_scientist.py
│   │   ├── strategy_critic.py
│   │   ├── allocator.py
│   │   ├── risk_governor.py
│   │   ├── execution_agent.py
│   │   ├── compute_governor.py
│   │   ├── venue_explorer.py
│   │   └── accountant.py
│   │
│   ├── treasury/
│   │   ├── state.py
│   │   ├── allocator.py
│   │   ├── sizing.py
│   │   ├── reserves.py
│   │   ├── compounding.py
│   │   └── pnl.py
│   │
│   ├── risk/
│   │   ├── governor.py
│   │   ├── limits.py
│   │   ├── exposure.py
│   │   ├── drawdown.py
│   │   ├── liquidity.py
│   │   ├── slippage.py
│   │   ├── stale_data.py
│   │   └── circuit_breakers.py
│   │
│   ├── execution/
│   │   ├── gateway.py
│   │   ├── intent.py
│   │   ├── validator.py
│   │   ├── orders.py
│   │   ├── reconciliation.py
│   │   └── idempotency.py
│   │
│   ├── compute/
│   │   ├── governor.py
│   │   ├── local.py
│   │   ├── modal_client.py
│   │   ├── jobs.py
│   │   ├── budgets.py
│   │   └── roi.py
│   │
│   ├── memory/
│   │   ├── store.py
│   │   ├── episodes.py
│   │   ├── lessons.py
│   │   └── retrieval.py
│   │
│   ├── ledger/
│   │   ├── journal.py
│   │   ├── cost.py
│   │   ├── attribution.py
│   │   └── audit.py
│   │
│   ├── storage/
│   │   ├── sqlite.py
│   │   ├── migrations.py
│   │   ├── parquet.py
│   │   ├── duckdb.py
│   │   └── retention.py
│   │
│   ├── discovery/
│   │   ├── venue_catalog.py
│   │   ├── api_research.py
│   │   ├── x402.py
│   │   └── integration_queue.py
│   │
│   ├── api/
│   │   ├── app.py
│   │   ├── routes/
│   │   ├── websocket.py
│   │   └── auth.py
│   │
│   └── observability/
│       ├── logging.py
│       ├── metrics.py
│       ├── tracing.py
│       ├── alerts.py
│       └── status.py
│
├── modal/
│   ├── app.py
│   ├── backtest_worker.py
│   ├── optimizer_worker.py
│   ├── simulation_worker.py
│   └── README.md
│
├── dashboard/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│
├── data/
│   ├── .gitkeep
│   ├── state/
│   ├── market/
│   ├── parquet/
│   ├── research/
│   └── exports/
│
├── logs/
│   └── .gitkeep
│
├── runtime/
│   └── .gitkeep
│
├── scripts/
│   ├── bootstrap.sh
│   ├── doctor.sh
│   ├── run-dev.sh
│   ├── run-paper.sh
│   ├── run-live.sh
│   ├── deploy-modal.sh
│   ├── backup.sh
│   └── restore.sh
│
├── deploy/
│   ├── systemd/
│   │   ├── forge.service
│   │   └── forge-dashboard.service
│   └── cgroups/
│
└── tests/
    ├── unit/
    ├── integration/
    ├── property/
    ├── replay/
    ├── chaos/
    └── acceptance/
```

If Opus 5.5 can make the structure cleaner while preserving the boundaries, it is explicitly encouraged to do so.

---
# 9. MARKET FABRIC — REAL-TIME INPUT LAYER

The Market Fabric is the nervous system of FORGE. It must normalize live information from every connected venue into stable internal event contracts.

## 9.1 Core event types

Define typed events such as:

```python
@dataclass(frozen=True)
class TradeTick:
    venue: str
    symbol: str
    price: Decimal
    size: Decimal
    side: Literal["buy", "sell", "unknown"]
    exchange_ts_ns: int
    recv_ts_ns: int

@dataclass(frozen=True)
class OrderBookDelta:
    venue: str
    symbol: str
    bids: tuple[Level, ...]
    asks: tuple[Level, ...]
    sequence: int | None
    exchange_ts_ns: int
    recv_ts_ns: int

@dataclass(frozen=True)
class BestBidAsk:
    venue: str
    symbol: str
    bid: Decimal
    bid_size: Decimal
    ask: Decimal
    ask_size: Decimal
    recv_ts_ns: int

@dataclass(frozen=True)
class Candle:
    venue: str
    symbol: str
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    start_ts: int
    end_ts: int
```

Add comparable contracts for balances, positions, fees, funding, yields, event contracts, prediction probabilities, and other venue-specific signals as those adapters are added.

## 9.2 Data quality is mandatory

Maintain a `DataQualityState` per venue/symbol:

- websocket connected/disconnected;
- last heartbeat;
- packet delay;
- sequence gaps;
- stale book threshold;
- crossed book detection;
- outlier tick detection;
- exchange timestamp drift;
- reconnect count;
- REST reconciliation timestamp.

No live strategy may trade from data that fails freshness/integrity checks.

## 9.3 Local history

Persist enough market history to allow FORGE to replay its own experiences.

Recommended:

- live state and metadata in SQLite;
- compact tick/order-book features into rolling Parquet partitions;
- raw full-depth data only where justified by a strategy, because raw depth can become enormous;
- aggregate bars at multiple horizons;
- record every market snapshot actually used to make a live decision.

At minimum, every executed decision must be reproducible from recorded inputs.

---

# 10. FEATURE ENGINE — THE RAW MATERIAL FOR PROPRIETARY ALGORITHMS

Create a feature engine that computes a broad, extensible library of features. This is not the strategy itself. These are building blocks from which strategies are composed and evolved.

## 10.1 Price and return features

Examples:

- log returns across 1s/5s/15s/30s/1m/5m/15m/1h;
- realized volatility;
- volatility-of-volatility;
- range expansion/contraction;
- normalized distance from VWAP;
- trend slope;
- acceleration / second derivative of smoothed price;
- gap/dislocation metrics;
- breakout distance from rolling extrema;
- mean-reversion z-score;
- autocorrelation at multiple lags;
- return asymmetry;
- downside semivariance;
- rolling Sharpe-like local metrics.

## 10.2 Volume and flow features

- volume acceleration;
- relative volume vs time-of-day baseline;
- signed trade imbalance;
- cumulative volume delta;
- large-trade detection;
- buyer/seller aggressor imbalance;
- volume concentration;
- trade-arrival rate;
- burstiness;
- block-like event detection;
- trade size distribution shift.

## 10.3 Order-book / microstructure features

Where supported by the venue:

- bid/ask spread;
- effective spread;
- top-of-book imbalance;
- depth imbalance at N levels;
- depth-weighted midprice;
- microprice;
- order-book slope;
- liquidity vacuum score;
- replenishment rate;
- cancellation rate where observable;
- queue pressure proxy;
- book resilience;
- spread compression/expansion;
- slippage curve at candidate position sizes;
- expected fill probability;
- local price impact estimate.

## 10.4 Cross-asset / relative features

- rolling correlation;
- beta;
- residual return;
- lead/lag relationships;
- spread z-score;
- cointegration diagnostics where appropriate;
- relative momentum;
- market breadth;
- dominance / benchmark-relative strength;
- synchronized volatility break;
- dispersion metrics.

## 10.5 Regime features

Build a regime classifier that labels conditions such as:

```text
TREND_UP
TREND_DOWN
RANGE_LOW_VOL
RANGE_HIGH_VOL
BREAKOUT_EXPANSION
PANIC_SELLING
EUPHORIA_BUYING
LIQUIDITY_THIN
LIQUIDITY_DEEP
NEWS_SHOCK
TRANSITION / UNCERTAIN
```

Do not treat these as permanent labels. Produce probabilities and uncertainty.

Use multiple methods:

- deterministic thresholds;
- Bayesian/change-point detection;
- clustering trained on historical feature vectors;
- hidden-state models if justified;
- online drift detectors;
- ensemble voting.

A strategy's fitness must be measured **by regime**, not only in aggregate.

---

# 11. OPPORTUNITY ENGINE

An opportunity is a structured claim that there may be positive expected value available now.

Create:

```python
class Opportunity(BaseModel):
    id: UUID
    created_at: datetime
    venue: str
    instruments: list[str]
    strategy_family: str
    direction: str
    hypothesis: str
    expected_gross_return: float
    expected_net_return: float
    expected_value_usd: float
    estimated_fees_usd: float
    estimated_slippage_usd: float
    estimated_compute_cost_usd: float
    max_capital_useful_usd: float
    holding_horizon_seconds: int | None
    calibrated_success_probability: float | None
    uncertainty: float
    liquidity_score: float
    regime_match: float
    freshness_score: float
    evidence_refs: list[str]
    expires_at: datetime
```

## 11.1 Opportunity families for Coinbase Phase 1

At minimum research and implement candidate detectors for:

### A. Momentum ignition
Identify coordinated increases in:

- return acceleration;
- volume acceleration;
- buyer aggressor imbalance;
- expanding depth asymmetry;
- break of recent local structure.

Avoid naïve “price went up, buy” logic.

### B. Breakout + confirmation
Detect compression followed by statistically abnormal expansion, with confirmation from volume and liquidity.

### C. Mean reversion
Identify temporary price deviations from robust local equilibrium, but disable or heavily downweight during regime transitions where “mean” is moving.

### D. Microstructure imbalance
Use microprice/order-book imbalance and short-term trade flow to estimate very short horizon price pressure.

### E. Relative value / cross-asset residual
Estimate when a related asset deviates from a learned relationship enough to justify a trade after costs.

### F. Volatility regime opportunities
Detect transition from compression to expansion or vice versa and select strategies appropriate to that regime.

### G. Fee-aware limit-order edge
Where viable, test whether passive liquidity placement can capture spread without adverse selection overwhelming returns.

### H. Event-driven crypto response
Create a pluggable event channel for future structured public information. Do not block Phase 1 on this.

## 11.2 Opportunity scoring

Use a composite score, but preserve its components. Example conceptual form:

```text
score =
  expected_net_value
  * confidence_calibration_factor
  * regime_match
  * liquidity_factor
  * freshness_factor
  * strategy_health_factor
  - uncertainty_penalty
  - tail_risk_penalty
  - correlation_concentration_penalty
```

Do not bury everything in one opaque number. The allocator must be able to explain why one opportunity outranked another.

---

# 12. THE STRATEGY GENOME — CORE PROPRIETARY IP

This is one of the most important systems in FORGE.

A strategy is represented as a **declarative genome** that can be mutated, combined, tested, versioned, and audited.

Do not let DeepSeek directly hot-deploy arbitrary Python code into live execution.

## 12.1 Strategy DSL

Build a constrained Strategy DSL consisting of whitelisted primitives.

A genome could resemble:

```yaml
strategy_id: stg_momentum_0042
family: momentum_microstructure
generation: 7
parents:
  - stg_momentum_0038
hypothesis: >
  Breakouts following low realized-volatility compression have higher
  continuation probability when aggressive-buy imbalance and microprice
  displacement agree while top-of-book liquidity is not collapsing.
universe:
  venue: coinbase
  symbols: dynamic_liquid_usd_pairs
regimes:
  allow:
    - TREND_UP
    - BREAKOUT_EXPANSION
  deny:
    - LIQUIDITY_THIN
features:
  - ret_15s
  - realized_vol_5m
  - relative_volume_1m
  - aggressor_imbalance_10s
  - microprice_displacement
  - depth_imbalance_5
entry:
  all:
    - op: gt
      feature: relative_volume_1m
      value: 2.15
    - op: gt
      feature: aggressor_imbalance_10s
      value: 0.63
    - op: gt
      feature: microprice_displacement
      value: 0.0007
  any:
    - op: breakout
      window: 120
      sigma: 2.1
    - op: acceleration
      feature: ret_15s
      threshold: 0.0018
exit:
  take_profit:
    type: volatility_scaled
    multiplier: 1.35
  stop:
    type: volatility_scaled
    multiplier: 0.72
  time_stop_seconds: 240
position:
  sizing_model: confidence_liquidity
  max_fraction: 0.65
execution:
  prefer_post_only: false
  max_slippage_bps: 12
```

This is illustrative. Opus should design a strong schema, validation layer, and compiler.

## 12.2 Whitelisted primitives

Build primitives for:

- comparisons;
- rolling statistics;
- crossovers;
- z-scores;
- breakouts;
- volatility-scaled thresholds;
- volume confirmations;
- order-book imbalance;
- microprice;
- trend filters;
- correlation/residual signals;
- regime checks;
- time filters;
- spread/liquidity filters;
- entry/exit composition;
- stop/target models;
- trailing exits;
- time stops;
- position sizing;
- cooldowns;
- portfolio constraints.

FORGE can expand this primitive library over time, but additions must be code-reviewed by tests before becoming available to live strategies.

## 12.3 Why a DSL matters

The DSL gives FORGE evolutionary freedom without handing an LLM unrestricted execution rights.

DeepSeek can generate millions of different structured algorithms from safe components. The runtime can validate and backtest them deterministically.

For genuinely novel research that requires a new primitive, DeepSeek may propose a primitive specification. Opus-built code should support:

```text
PROPOSED_PRIMITIVE
→ generated implementation in isolated research sandbox
→ unit/property tests
→ static checks
→ replay tests
→ benchmark
→ human-readable diff/audit
→ mark as AVAILABLE_TO_RESEARCH
→ later mark as LIVE_ALLOWED only after validation
```

No automatically generated primitive gets direct live privilege merely because DeepSeek wrote it.

---

# 13. STRATEGY LINEAGE GRAPH

Every strategy is part of an evolutionary graph.

Store edges such as:

```text
PARENT_OF
MUTATED_FROM
CROSSOVER_OF
REGIME_SPECIALIZATION_OF
RESURRECTED_FROM
RETIRED_BY
OUTPERFORMED_BY
```

A lineage example:

```text
Momentum-001
  └── Momentum-014
       + volume confirmation
       └── Momentum-021
            + volatility gating
            ├── Momentum-033
            │    + microprice filter  ← current champion
            └── Momentum-034
                 + deeper-book filter ← retired: latency too high
```

For every mutation, save:

- what changed;
- why it changed;
- evidence motivating the mutation;
- expected improvement;
- evaluation result;
- whether it was promoted;
- what was learned.

This lineage is the proprietary memory of FORGE.

---

# 14. THE EVOLUTION ENGINE

FORGE must continuously generate better strategies without devolving into random search.

## 14.1 Mutation sources

New candidate strategies may come from:

1. **Failure-driven mutation** — fix a measured weakness.
2. **Success amplification** — isolate what seems to create edge and test whether it generalizes.
3. **Regime specialization** — derive specialized variants for specific market conditions.
4. **Feature substitution** — replace an unstable feature with a more robust proxy.
5. **Parameter mutation** — alter thresholds, windows, exits, or sizing.
6. **Structural mutation** — add/remove logical conditions.
7. **Crossover** — combine useful components from two proven strategies.
8. **Novel hypothesis generation** — DeepSeek proposes an entirely new family based on observed data.
9. **Missed-opportunity analysis** — generate strategies from profitable moves FORGE observed but failed to capture.
10. **Adversarial critique** — critic agent attacks current champions and proposes exploits against their weaknesses.

## 14.2 Mutation must have a reason

Every generated candidate requires a `MutationRationale`:

```json
{
  "parent": "stg_0042",
  "problem_observed": "false breakouts increased in high-volatility transition regimes",
  "evidence": ["exp_193", "live_window_2026-10-06T14:00Z"],
  "change": "add regime-transition veto and reduce maximum hold from 240s to 150s",
  "expected_effect": "reduce tail losses and adverse follow-through",
  "risk": "may reject genuine early breakouts"
}
```

Candidates without a coherent rationale may still be explored in a limited “discovery” pool, but they must never dominate the research budget.

## 14.3 Evolution cadence

Do not mutate on every loss.

Use triggers:

- statistically meaningful degradation;
- calibration failure;
- drawdown threshold;
- change-point detection;
- persistent live-vs-shadow divergence;
- missed opportunity cluster;
- new regime;
- new feature availability;
- scheduled research cycle;
- strategy stagnation.

A single losing trade is not proof of failure.

## 14.4 Population structure

Maintain multiple populations:

```text
CHAMPIONS    — currently trusted for live capital
CHALLENGERS  — passed robust testing, tiny or shadow allocation
RESEARCH     — actively being evaluated
HIBERNATING  — historically useful but current regime mismatch
RETIRED      — failed or superseded; lineage retained
QUARANTINED  — suspicious/invalid/bug-related results
```

## 14.5 Fitness

Do not rank strategies by raw return alone.

Construct regime-aware fitness using metrics such as:

- net return;
- expected log growth;
- max drawdown;
- downside deviation;
- win rate;
- payoff ratio;
- profit factor;
- calibration quality;
- turnover and fee efficiency;
- slippage sensitivity;
- tail loss;
- consistency across walk-forward folds;
- robustness to parameter perturbation;
- performance across neighboring assets;
- sample size;
- live-vs-backtest degradation;
- compute cost per unit return;
- capital capacity.

A simple configurable composite can begin as:

```text
fitness =
    0.28 * normalized_net_return
  + 0.18 * normalized_log_growth
  + 0.12 * robustness
  + 0.10 * regime_consistency
  + 0.10 * calibration_quality
  + 0.08 * cost_efficiency
  + 0.07 * liquidity_capacity
  + 0.07 * live_shadow_consistency
  - drawdown_penalty
  - tail_risk_penalty
  - overfit_penalty
```

Do not freeze these weights permanently. FORGE may optimize the fitness function itself, subject to meta-evaluation.

---

# 15. TESTING PIPELINE FOR EVERY STRATEGY

No meaningful live capital is granted merely because a backtest looks spectacular.

Candidate progression:

```text
IDEA
  ↓
SCHEMA VALIDATION
  ↓
UNIT / INVARIANT TESTS
  ↓
HISTORICAL REPLAY
  ↓
OUT-OF-SAMPLE TEST
  ↓
WALK-FORWARD TEST
  ↓
COST/STRESS TEST
  ↓
MONTE CARLO / RESAMPLING
  ↓
LIVE SHADOW TEST
  ↓
TINY LIVE CHALLENGER
  ↓
CHAMPION / SPECIALIST
```

## 15.1 Backtest realism

Backtests must include:

- actual fee schedule when known;
- bid/ask rather than last price for execution;
- position-size-dependent slippage model;
- order latency assumptions;
- partial fills where relevant;
- stale signal expiration;
- minimum order constraints;
- tick/lot sizes;
- market availability;
- realistic stop execution;
- no lookahead;
- proper time alignment;
- survivorship awareness where relevant.

## 15.2 Walk-forward

Use rolling train/test windows. Do not optimize and score on the same data.

Example:

```text
Train 14d → Test 3d
advance 3d
Train 14d → Test 3d
...
```

Window length should adapt to strategy horizon.

## 15.3 Parameter perturbation

A strategy that only works at exactly `threshold=0.6371` is suspicious.

Test neighborhoods around parameters. Prefer broad plateaus of acceptable performance over sharp isolated maxima.

## 15.4 Monte Carlo / resampling

Randomize:

- trade ordering;
- slippage;
- latency;
- fees within plausible ranges;
- entry delay;
- partial fill behavior;
- regime ordering.

Estimate drawdown and ruin distributions.

## 15.5 Shadow mode

Shadow mode consumes live data and produces exact would-be orders without transmitting them.

Record:

- intended order time;
- intended side/size/type;
- simulated queue/fill;
- actual market evolution;
- expected vs realized hypothetical P&L;
- missed fills;
- adverse selection;
- latency effect.

Shadow results should be first-class fitness evidence.

---

# 16. ONLINE LEARNING — FORGE MUST LEARN WHILE RUNNING

FORGE needs multiple kinds of learning rather than one giant “memory.”

## 16.1 Episodic memory

Store significant episodes:

- unusually profitable trade;
- large loss;
- failed breakout cluster;
- market-data outage;
- fee change;
- new regime transition;
- strategy promotion;
- strategy retirement;
- anomalous slippage;
- compute escalation that changed a decision;
- opportunity missed because of insufficient capital;
- opportunity missed because of latency;
- opportunity that looked attractive but failed validation.

## 16.2 Lesson memory

Convert repeated episodes into structured lessons:

```json
{
  "lesson_id": "lesson_0082",
  "statement": "short-horizon breakout strategies degrade materially when spread percentile > 90 and depth recovery time > 4s",
  "confidence": 0.86,
  "supporting_episode_ids": ["ep_991", "ep_1021", "ep_1077"],
  "contradicting_episode_ids": ["ep_1003"],
  "last_validated_at": "..."
}
```

Lessons can decay if new evidence contradicts them.

## 16.3 Feature-value memory

Track which features matter to which strategy families and regimes.

Do not blindly assume a feature useful for BTC 5-minute momentum is useful for a thin altcoin microstructure strategy.

## 16.4 Mistake taxonomy

Classify failed decisions:

```text
SIGNAL_FALSE_POSITIVE
REGIME_MISCLASSIFIED
SLIPPAGE_UNDERESTIMATED
LIQUIDITY_COLLAPSED
LATE_ENTRY
EARLY_EXIT
LATE_EXIT
POSITION_TOO_LARGE
POSITION_TOO_SMALL
FEE_DRAG
DATA_STALE
EXCHANGE_REJECT
ORDER_NOT_FILLED
CORRELATION_BREAK
TAIL_EVENT
MODEL_OVERFIT
MODEL_DRIFT
UNKNOWN_VARIANCE
```

This taxonomy feeds mutation.

---

# 17. MULTI-AGENT SYSTEM

Do not create “agents” merely to make the architecture sound sophisticated. Each agent must own a clear decision domain.

## 17.1 Forge Orchestrator

Responsibilities:

- coordinate the system;
- schedule research cycles;
- maintain state transitions;
- dispatch tools;
- avoid duplicated work;
- prioritize opportunities;
- ensure no agent bypasses Risk Governor.

## 17.2 Market Scout

Continuously identifies unusual conditions and creates `Opportunity` objects.

Should primarily use deterministic market features and lightweight models. DeepSeek is invoked when interpretation adds value.

## 17.3 Strategy Scientist

DeepSeek-powered research agent responsible for:

- failure analysis;
- new hypothesis generation;
- strategy mutation design;
- new family proposals;
- experiment design;
- interpreting research results.

It does **not** place orders.

## 17.4 Strategy Critic

Attempts to falsify Scientist conclusions.

Questions:

- Is this lookahead?
- Is sample size adequate?
- Are costs realistic?
- Does the edge vanish under parameter perturbation?
- Is it merely correlated with one bull run?
- Does performance survive latency?
- Is the supposed edge actually one extreme outlier?
- Is there a simpler explanation?

Promotions of large-capital strategies should require Critic review.

## 17.5 Allocator

Ranks validated opportunities and assigns capital.

Uses empirically calibrated estimates, not vibes.

## 17.6 Risk Governor

Independent veto authority.

It cannot create profit-seeking orders. It can only:

- reduce size;
- reject;
- delay;
- liquidate under emergency rules;
- disable stale/broken strategies;
- trigger circuit breakers.

This separation is intentional.

## 17.7 Execution Agent

Turns approved `TradeIntent` objects into venue orders.

Responsibilities:

- idempotency;
- venue constraints;
- order type selection;
- fill monitoring;
- cancellation;
- reconciliation;
- exact audit trail.

## 17.8 Compute Governor

Decides whether an analysis job should remain local, call DeepSeek, or burst to Modal.

## 17.9 Accountant

Maintains authoritative ledger and true net P&L.

The Accountant must never rely solely on strategy-reported P&L.

## 17.10 Venue Explorer

Continuously researches legitimate new APIs, markets, x402 services, and economic rails.

It may:

- catalog opportunities;
- verify documentation;
- estimate integration value;
- build/test non-funded adapters in sandbox;
- queue integrations;
- automatically activate data-only integrations when no secret or money movement is required and terms permit it.

It may **not** silently exfiltrate capital to an unknown service or bypass onboarding/compliance controls.

---

# 18. DEEPSEEK TOOL SURFACE

Expose narrow, typed tools. Use JSON schemas and strict validation.

Minimum conceptual tool list:

```text
get_system_health()
get_treasury_state()
get_cost_state()
get_modal_budget_state()
get_market_snapshot(venue, symbols, horizon)
get_feature_snapshot(symbols, features, horizon)
get_regime_state(symbols)
query_strategy(strategy_id)
query_strategy_lineage(strategy_id)
query_strategy_performance(strategy_id, regime, window)
query_recent_failures(filters)
query_missed_opportunities(filters)
create_strategy_candidate(spec, rationale)
validate_strategy_spec(strategy_id)
run_backtest(strategy_id, dataset, assumptions)
run_walk_forward(strategy_id, plan)
run_monte_carlo(strategy_id, plan)
launch_shadow(strategy_id, symbols, duration)
compare_strategies(strategy_ids, metric_set)
propose_promotion(strategy_id, target_tier)
propose_retirement(strategy_id, reason)
request_modal_job(job_type, payload, resource_hint)
get_modal_job(job_id)
rank_opportunities(opportunity_ids)
calculate_position_size(opportunity_id, treasury_state)
propose_trade_intent(opportunity_id, strategy_id, sizing)
explain_trade_intent(intent_id)
query_execution_history(filters)
query_cost_attribution(filters)
search_venue_catalog(query)
propose_new_venue_adapter(spec)
record_lesson(lesson)
```

## Live execution tool separation

Do **not** expose a raw `send_money(address, amount)` tool to DeepSeek.

The live path must be:

```text
DeepSeek/strategy proposes economic intent
→ deterministic allocator sizes it
→ Risk Governor approves/reduces/rejects
→ Execution Gateway maps it to an allowlisted venue action
→ signer/venue adapter executes
```

The LLM never supplies an arbitrary withdrawal destination.

---

# 19. DEEPSEEK SYSTEM PROMPT — RUNTIME SCIENTIST

Create a version-controlled prompt roughly inspired by the following, but improve it where useful:

```text
You are the Strategy Scientist inside FORGE, an autonomous capital growth engine.

FORGE means Find Opportunities, Reinvest, Grow, Evolve.

Your job is not to sound confident. Your job is to discover empirical edge.
Your job is not to trade frequently. Your job is to improve net treasury growth.

Treat every strategy as a falsifiable hypothesis.
Use tools to obtain exact market, cost, performance, and experiment data.
Never invent prices, balances, fills, fees, or backtest results.
Never claim certainty from intuition.

When proposing a strategy or mutation:
1. identify the observed phenomenon;
2. state the causal or statistical hypothesis;
3. identify data/features required;
4. identify likely failure modes;
5. define an experiment that can falsify it;
6. estimate execution sensitivity;
7. compare against the current incumbent;
8. preserve lineage.

When a strategy loses, diagnose before mutating.
A loss may be variance, not failure.
A winning trade may be luck, not edge.

Seek new strategy families when evidence suggests current families are insufficient.
Reuse lessons from prior failures and successful strategies.

You may spend compute when the expected information value justifies the cost.
You are encouraged to request Modal burst compute for parallel research when valuable.

Your output must be structured and actionable through the provided tools.
You cannot bypass the Risk Governor or Execution Gateway.
```

Version this prompt. Track prompt-performance changes exactly like strategy changes.

---
# 20. COINBASE — FIRST LIVE EXECUTION RAIL

Coinbase is the first live venue because the user already has an account and capital can begin there.

FORGE should support two complementary Coinbase paths where appropriate:

1. **Coinbase account / Advanced Trade APIs** for exchange-style market data and order execution.
2. **Coinbase Developer Platform Agentic Wallets / Base onchain capabilities** for autonomous wallet actions, x402 payments, onchain trading, and future machine-economy capabilities.

Do not assume that funds sitting in one Coinbase product are automatically transferable through every API. During integration, inspect the official APIs and determine exactly which balance/account type the configured credentials expose.

## 20.1 Coinbase adapter interface

Implement at least:

```python
class VenueAdapter(Protocol):
    async def connect_market_data(self) -> None: ...
    async def disconnect_market_data(self) -> None: ...
    async def list_markets(self) -> list[Market]: ...
    async def get_market_rules(self, symbol: str) -> MarketRules: ...
    async def get_balances(self) -> list[Balance]: ...
    async def get_open_orders(self) -> list[Order]: ...
    async def get_positions(self) -> list[Position]: ...
    async def quote(self, request: QuoteRequest) -> Quote: ...
    async def submit_order(self, intent: ValidatedTradeIntent) -> OrderAck: ...
    async def cancel_order(self, order_id: str) -> CancelAck: ...
    async def reconcile(self) -> ReconciliationReport: ...
```

Normalize Coinbase-specific response objects immediately at the adapter boundary.

## 20.2 WebSocket market data

Prefer WebSocket streams for live market state. REST is for:

- bootstrapping;
- recovery;
- reconciliation;
- metadata;
- occasional snapshots.

Implement reconnect with exponential backoff + jitter and sequence-state repair where required.

The strategy engine must know when a book has become invalid and require a fresh snapshot before re-enabling trading.

## 20.3 Dynamic market universe

Do not hardcode only BTC/ETH/SOL.

Build a liquidity-aware universe selector that periodically evaluates supported markets using:

- quoted spread;
- 24h volume;
- recent depth;
- minimum order requirements;
- realized volatility;
- fee burden relative to volatility;
- order-book quality;
- data reliability;
- strategy-specific capacity.

FORGE should scan broadly but only trade markets where its model believes execution is economically sensible.

## 20.4 Small-capital reality

The initial $20 makes order minimums and fees extremely important.

The adapter must expose a `FeasibilityCheck` before an opportunity can reach live execution:

```text
Can we place the minimum permitted order?
Can the expected move plausibly exceed round-trip fees?
Does the order size produce meaningful slippage?
Will using this position strand dust?
Is there enough capital left for exit fees / reserve?
```

Do not manufacture trades just to prove the engine is “alive.”

## 20.5 Agentic Wallet integration

Create a separate `AgenticWalletAdapter` behind a capability interface.

Coinbase currently describes Agentic Wallets as infrastructure that can let agents spend, earn, trade, use x402, and enforce session/transaction guardrails while keys remain isolated from the LLM.

Use that architecture where it materially benefits FORGE.

Capabilities should be explicit:

```text
WALLET_BALANCE
TRADE_ON_BASE
PAY_X402
RECEIVE_USDC
SEND_TO_ALLOWLISTED_DESTINATION
EARN / YIELD_CAPABILITY_IF_AUTHORIZED
```

Do not grant generic arbitrary transfer authority to strategy agents.

## 20.6 Key security

- Keep API secrets outside prompts.
- Use provider-supported key restrictions where available.
- Prefer trade-only keys when withdrawals are unnecessary.
- Maintain an explicit withdrawal/transfer allowlist.
- Log every signed action with intent ID and policy decision.
- Never print secret values in logs.

---

# 21. CAPITAL POLICY — THE $20 EXPERIMENT AND AUTOMATIC SCALING

The initial experiment is now:

```text
Initial treasury: $20 USD-equivalent
External capital injection limit for the experiment: $20
```

FORGE should be architected identically whether treasury size is $20, $200, $20,000, or greater. **Do not bake tiny-account assumptions into the architecture.**

Tiny capital changes feasibility and position sizing; it must not constrain the long-term design.

## 21.1 Reinvestment

All realized net profits enter treasury accounting immediately.

Example:

```text
Starting deployable treasury: $20.00
Trade closes net +$1.10
New treasury: $21.10
Next allocator run sees $21.10
```

There is no artificial “profit bucket” that waits for a human to reinvest.

## 21.2 Dynamic reserve

Before total equity reaches $100, use a dynamic reserve target based on capital size, opportunity quality, and ruin risk.

Baseline policy:

```text
Typical reserve: 10–20%
High-quality opportunity: may reduce reserve toward 5–10%
Exceptional empirically validated opportunity: may deploy up to 100% of the initial experimental bankroll if the Risk Governor validates that policy allows it
```

The initial $20 is explicitly experiment capital and may be lost.

When treasury reaches **$100 or more**:

```text
Protected reserve floor = $25
```

That reserve must not be deployed into ordinary strategies. It remains restart/survival capital unless the user changes policy.

Do not interpret “exceptional” as an LLM being enthusiastic. It must be statistically supported.

## 21.3 Confidence-weighted position sizing

Use a position sizing system that considers:

- calibrated probability of success;
- expected payoff distribution;
- loss distribution;
- strategy uncertainty;
- liquidity;
- correlation with existing exposure;
- regime quality;
- sample size;
- recent drift;
- treasury size;
- reserve policy.

For binary-like outcomes, fractional Kelly can be used as one input but never blindly. For continuous returns, use expected log growth or another robust utility formulation.

A conceptual capped Kelly approach:

```text
raw_fraction = kelly_estimate(expected_distribution)
confidence_adjusted = raw_fraction * calibration_factor * regime_match
risk_adjusted = confidence_adjusted * strategy_health
final_fraction = min(risk_adjusted, liquidity_cap, policy_cap)
```

Use fractional Kelly (e.g. 0.1–0.5 Kelly depending evidence) until calibration is exceptional. Full Kelly is too brittle under model error.

## 21.4 Capital competition

Strategies compete for one treasury through **virtual allocations**.

Do not create separate real wallets for each strategy.

Track virtual accounts such as:

```text
Strategy                Virtual allocation    Fitness    Live state
Momentum-A              $4.10                 0.74       ACTIVE
Microstructure-C        $3.25                 0.81       ACTIVE
Breakout-F              $1.20                 0.42       DEMOTED
MeanReversion-B         $0.00                 0.18       HIBERNATING
Research reserve        $X                    —          —
Protected reserve       $Y                    —          LOCKED
```

The actual money remains centrally controlled.

## 21.5 Portfolio concentration

FORGE is allowed to concentrate capital when evidence justifies it, but concentration must be explicit and audited.

Before using >50% of deployable capital in one thesis, require:

- current data healthy;
- strategy live/shadow calibration healthy;
- sufficient sample evidence;
- clear stop/exit plan;
- expected edge after costs;
- no hidden correlated position;
- no critical service degradation;
- no unresolved reconciliation issue;
- Risk Governor approval.

Before using >80%, require additional critic/robustness verification unless latency would destroy the opportunity. In latency-sensitive cases, precompute an “exceptional opportunity” policy so the decision can remain deterministic.

---

# 22. RISK GOVERNOR — HARD SEPARATION FROM PROFIT-SEEKING AGENTS

FORGE is aggressive, but aggression without survival logic is merely uncontrolled variance.

The Risk Governor is not there to make FORGE timid. It is there to keep a mistake in one model from becoming a system-ending bug.

## 22.1 Hard invariants

Implement these as code-level invariants, not prompts:

- no order without an authenticated treasury snapshot;
- no order from stale market data;
- no order without fee and slippage estimate;
- no order below venue minimum;
- no order exceeding actual available balance;
- no duplicate order from retry races;
- no new live position during reconciliation failure;
- no transfer to a destination not explicitly allowed by policy;
- no strategy may edit its own execution history;
- no LLM may bypass risk checks;
- no strategy may modify hard budget limits directly;
- no Modal spend beyond configured monthly budget without changed configuration;
- no local CPU beyond 3-vCPU aggregate policy for runtime services.

## 22.2 Circuit breakers

Implement breakers for:

- repeated exchange rejects;
- websocket integrity failure;
- balance mismatch;
- unexpectedly high slippage;
- fee schedule mismatch;
- rapid drawdown;
- anomalous order frequency;
- duplicate order attempts;
- API authentication errors;
- time synchronization problems;
- persistent P&L reconciliation mismatch;
- inference cost runaway;
- Modal spend anomaly.

Breaker actions:

```text
WARN
REDUCE_SIZE
DISABLE_STRATEGY
DISABLE_VENUE_NEW_ORDERS
CANCEL_OPEN_ORDERS
FLATTEN_WHEN_SAFE
ENTER_OBSERVE_ONLY
```

## 22.3 No leverage by default in Phase 1

Do not use leverage in the initial live $20 validation phase even if a future Coinbase product supports it.

The architecture may model leverage as a future capability, but it must be feature-flagged off initially.

Reason: FORGE must prove actual edge before multiplying exposure.

The user may change this later.

---

# 23. EXECUTION ENGINE

Execution must be deterministic, idempotent, and auditable.

## 23.1 TradeIntent

No agent talks directly to an exchange. It creates a `TradeIntent`.

```python
class TradeIntent(BaseModel):
    intent_id: UUID
    opportunity_id: UUID
    strategy_id: str
    venue: str
    symbol: str
    side: Literal["buy", "sell"]
    requested_notional_usd: Decimal
    max_notional_usd: Decimal
    preferred_order_type: str
    max_slippage_bps: Decimal
    thesis_expiry: datetime
    exit_plan: ExitPlan
    evidence_refs: list[str]
```

Pipeline:

```text
Strategy → Intent
Allocator → Size
Risk Governor → Approve/Reduce/Reject
Execution Validator → Venue rules
Execution Gateway → Place
Reconciler → Verify
Ledger → Journal
```

## 23.2 Idempotency

Every action must have a unique deterministic idempotency key.

Retries must never turn one intended order into two orders.

## 23.3 Reconciliation

Continuously reconcile:

- local order state vs Coinbase;
- local balances vs Coinbase;
- fills vs expected fills;
- P&L vs ledger;
- fees vs recorded fees.

Local state is not authoritative if the venue disagrees.

## 23.4 Order-type intelligence

Execution logic should learn when to prefer:

- market orders;
- limit orders;
- post-only orders;
- cancel/replace;
- patient vs urgent execution.

But it must model opportunity decay. Saving 5 bps in fees is not useful if the opportunity disappears while waiting.

Build an `ExecutionCostModel` that learns realized:

```text
slippage(symbol, side, size, volatility, spread, liquidity, urgency, order_type)
```

This becomes proprietary execution intelligence over time.

---

# 24. COMPUTE GOVERNOR — ECONOMIC INTELLIGENCE ABOUT INTELLIGENCE

FORGE should treat compute as an asset with expected ROI.

## 24.1 Resource tiers

```text
TIER A — local deterministic
  2-vCPU target
  feature math
  streaming
  opportunity filters
  exact accounting

TIER B — local DeepSeek API call
  hypothesis generation
  diagnosis
  structured research

TIER C — Modal warm worker
  quick parallel backtest
  focused parameter test
  short simulation

TIER D — Modal burst
  hundreds/thousands of trials
  broad walk-forward
  Monte Carlo
  strategy tournament
  large feature research

TIER E — exceptional burst
  temporary larger resource request when a high-value opportunity or major research question justifies it
```

## 24.2 Value-of-information decision

Before spending significant compute, estimate:

```text
EVI = Expected Value With Additional Information - Expected Value Without It
```

Run the extra analysis when:

```text
EVI > expected_compute_cost * safety_multiplier
```

The safety multiplier can fall for time-critical/high-value opportunities and rise for speculative research.

## 24.3 Self-funding operating budget

Initial DeepSeek top-up is expected to be approximately **$5**.

Build an `OperatingTreasury` abstraction distinct from trading capital accounting, even if both are funded externally at first.

Track:

```text
DeepSeek budget remaining
Modal budget remaining
paid data/API spend
x402 spend
total operating burn
income allocated back to operations
```

Once FORGE earns enough to support itself, use a configurable profit allocation rule such as:

```text
10% of realized net profit → operating reserve
90% → growth treasury
```

Do not hardwire 10%; make it adaptive based on runway.

If operating runway becomes low, FORGE should reduce low-value research spending before compromising market-data integrity or execution safety.

---

# 25. MODAL IMPLEMENTATION PLAN

Build a dedicated Modal application.

Illustrative code organization:

```python
# modal/app.py
import modal

app = modal.App("forge-research")

base_image = (
    modal.Image.debian_slim()
    .pip_install(
        "numpy",
        "polars",
        "duckdb",
        "pyarrow",
        "pydantic",
    )
)

@app.function(
    image=base_image,
    cpu=0.25,
    memory=256,
    min_containers=1,
    max_containers=1,
    scaledown_window=300,
)
def warm_research_worker(payload: dict) -> dict:
    ...

@app.function(
    image=base_image,
    cpu=2.0,
    memory=2048,
    min_containers=0,
    max_containers=16,
)
def backtest_worker(payload: dict) -> dict:
    ...
```

The exact resource settings should be tuned after benchmarking.

## 25.1 Dynamic overrides

Use Modal's supported runtime resource/autoscaler controls when helpful so FORGE can dynamically choose worker sizes.

Do not deploy one permanently huge worker.

## 25.2 Budget awareness

Integrate Modal billing/usage visibility where supported. If direct billing summary APIs/CLI are available, collect periodic usage metrics.

FORGE must know when it is approaching the monthly allowance.

Modes:

```text
GREEN  < 60% monthly allowance consumed
YELLOW 60–85%
ORANGE 85–95%
RED    >95%
```

In RED mode, new research jobs require unusually high expected value. Critical live-validation jobs may still run if the remaining budget allows them.

## 25.3 No orphan resources

Every Modal invocation must have:

- a timeout;
- retry policy;
- parent job ID;
- cancellation handling;
- result persistence;
- cleanup behavior.

Do not leave accidental persistent containers or volumes consuming budget.

---

# 26. DATABASE AND DATA MODEL

Use SQLite WAL for low-resource transactional state initially.

Suggested tables:

```text
system_state
venue_state
market_metadata
market_quality
strategies
strategy_versions
strategy_lineage_edges
strategy_metrics
strategy_regime_metrics
strategy_mutations
experiments
experiment_runs
shadow_orders
opportunities
trade_intents
risk_decisions
orders
fills
positions
balances
ledger_entries
cost_entries
inference_calls
modal_jobs
lessons
episodes
regime_states
feature_definitions
venue_catalog
integration_candidates
alerts
configuration_history
```

Use migrations from day one.

## 26.1 Append-only audit journal

Maintain a separate append-only JSONL audit stream for critical events:

```text
runtime/audit/YYYY-MM-DD.jsonl
```

Critical events include:

- strategy promotion;
- live enable/disable;
- risk override attempt;
- live order intent;
- risk decision;
- exchange ack;
- fill;
- capital reallocation;
- reserve change;
- credential-state change (never the secret value);
- configuration change;
- kill switch;
- service recovery.

Hash-chain the journal entries if practical so accidental/tampering detection is possible.

## 26.2 Parquet data lake

Partition by:

```text
data/parquet/market/venue=coinbase/symbol=BTC-USD/date=YYYY-MM-DD/
```

Store derived features separately from raw market events when useful.

## 26.3 Retention

Because disk is finite:

- keep all decision-relevant snapshots;
- downsample old tick data;
- compact Parquet periodically;
- keep aggregated bars/features longer;
- never delete audit/ledger history merely for convenience;
- archive older research artifacts if necessary.

---

# 27. REAL-TIME ORCHESTRATION LOOP

FORGE should run multiple asynchronous loops rather than one giant loop.

Example:

```text
market_stream_loop       continuous
feature_loop             event-driven
opportunity_loop         event-driven + periodic sweep
regime_loop              every few seconds/minutes depending horizon
allocator_loop           event-driven
execution_loop           event-driven
reconciliation_loop      frequent
research_trigger_loop    event-driven
strategy_health_loop     periodic
venue_discovery_loop     low-frequency
compute_budget_loop      periodic
accounting_loop          continuous
self_review_loop         hourly/daily
```

## 27.1 Every-second activity does not mean every-second LLM calls

The system can analyze continuously using deterministic code.

DeepSeek should be invoked when reasoning is valuable, not on every market tick.

A good event chain:

```text
100,000 market events
→ deterministic feature engine
→ 400 anomalies
→ 30 opportunity candidates
→ 6 pass minimum EV threshold
→ 2 warrant DeepSeek analysis
→ 1 warrants Modal simulation
→ 1 becomes a trade
```

This is the economically intelligent use of AI.

---

# 28. ALGORITHM FAMILIES TO SEED — NOT TO FREEZE

Opus 5.5 should implement a useful initial primitive/family library so FORGE has something to evolve immediately.

The initial families are starting points, not sacred strategies.

## 28.1 Multi-timescale momentum

Combine:

- short-term acceleration;
- medium-term trend;
- relative volume;
- liquidity quality;
- microstructure confirmation.

Variants should evolve different time horizons and confirmation requirements.

## 28.2 Volatility compression → expansion

Detect low-volatility compression followed by directional expansion.

Research:

- ATR-like compression;
- realized variance percentiles;
- Bollinger-like width as a feature, not a strategy;
- volume burst;
- order-book pressure;
- continuation probability.

## 28.3 Mean reversion with regime veto

Mean reversion is dangerous in trends. Build regime-aware variants that only activate when stationarity/mean stability is plausible.

## 28.4 Microprice pressure

Use order-book imbalance, spread, and microprice to estimate short-horizon movement.

## 28.5 Relative-value residual

Model asset A against basket B, trade residual when divergence is extreme and mean reversion historically survives costs.

## 28.6 Adaptive ensemble

Combine strategy predictions with weights based on recent regime-specific calibrated performance.

Do not let a currently lucky model dominate solely from one streak.

## 28.7 Meta-labeling

A base strategy generates candidate entries. A secondary model estimates whether the candidate is worth taking under current conditions.

This is potentially powerful because it separates signal discovery from trade selection.

## 28.8 Exit-policy evolution

Often the edge is not entry; it is exit.

Evolve:

- fixed target/stop;
- volatility-scaled exits;
- trailing exits;
- time exits;
- signal-decay exits;
- order-flow reversal exits;
- partial exits when capital is larger and venue constraints allow.

## 28.9 Position-sizing evolution

Allow sizing models to compete independently from entry logic.

Examples:

- fixed fraction;
- volatility targeting;
- confidence-weighted;
- fractional Kelly;
- drawdown-aware sizing;
- opportunity-ranked capital allocation.

This creates reusable proprietary modules.

---

# 29. META-ALGORITHMS — ALGORITHMS THAT BUILD ALGORITHMS

This requirement is central.

FORGE must include **meta-algorithms** whose output is not a trade but a better strategy or research plan.

## 29.1 Failure Attribution Engine

Inputs:

- expected trade path;
- actual path;
- market regime;
- execution details;
- slippage;
- feature values;
- comparable historic cases.

Outputs:

```text
failure cause probabilities
candidate fixes
confidence in diagnosis
recommended experiments
```

## 29.2 Mutation Planner

Selects which parts of a genome to mutate based on diagnosed weakness.

Do not mutate everything simultaneously unless doing explicit broad search.

## 29.3 Feature Discovery Engine

Searches for features that improve discrimination on specific failure sets.

Use Modal for broad feature tests.

Require out-of-sample validation to avoid feature mining.

## 29.4 Strategy Crossover Engine

Combines proven components only when their assumptions are compatible.

Example:

```text
Momentum entry from Strategy A
+
regime veto from Strategy B
+
exit model from Strategy C
```

Then test the composite from scratch. Never assume component performance simply adds.

## 29.5 Strategy Resurrection Engine

A retired strategy may become relevant when its historical winning regime returns.

Do not permanently forget profitable specialists.

## 29.6 Opportunity Miss Analyzer

After significant market moves, ask:

```text
Did FORGE detect this?
If not, what feature could have surfaced it?
If detected, why was it rejected?
Was rejection correct given information available at the time?
Could a new strategy have captured it without hindsight leakage?
```

This is one of the best ways to turn market observation into new algorithms.

## 29.7 Portfolio Meta-Allocator

Use online learning / multi-armed-bandit ideas for allocation across strategy specialists.

Consider algorithms such as:

- Thompson sampling with non-stationarity adaptation;
- UCB variants;
- exponentially weighted forecasters;
- Bayesian model averaging;
- contextual bandits where context = regime/features.

Do not blindly choose one. Implement an interface and empirically compare them.

---

# 30. PREVENTING SELF-DECEPTION AND OVERFITTING

A self-evolving trading system will otherwise become an overfitting machine.

Mandatory defenses:

## 30.1 Holdout discipline

Maintain untouched evaluation windows.

Do not repeatedly optimize on the final holdout.

## 30.2 Multiple-testing awareness

If FORGE tests 100,000 strategy mutations, some will look brilliant by chance.

Track the number of hypotheses tested and penalize fragile discoveries.

Consider:

- false discovery rate controls;
- deflated Sharpe concepts;
- probability of backtest overfitting;
- nested validation;
- reality-check style resampling.

Implement appropriate approximations rather than pretending every backtest is independent proof.

## 30.3 Champion decay

Every champion has a “freshness” score.

As market behavior changes without new supporting evidence, confidence decays.

## 30.4 Shadow/live divergence

If live performance is materially worse than shadow/backtest, reduce allocation automatically and investigate.

## 30.5 No hindsight mutation

A mutation created after seeing a specific loss cannot be evaluated only against that same episode.

Test against broad independent data.

---

# 31. CONTINUOUS VENUE AND INCOME DISCOVERY

FORGE must not be permanently limited to one investment type.

Build a `VenueCatalog` and `CapabilityCatalog`.

For every discovered opportunity provider, record:

```text
name
category
jurisdiction/access constraints
official API availability
auth model
market types
fees
minimum capital
settlement speed
withdrawal/funding constraints
rate limits
websocket support
paper/sandbox support
programmatic trading policy
known SDKs
security notes
estimated integration effort
estimated economic potential
status
```

## 31.1 Discovery categories

FORGE may research legitimate opportunities including:

- spot markets;
- prediction markets;
- spreads/relative value;
- staking/yield if authorized;
- liquidity incentives;
- maker rebates;
- API-accessible bounties;
- x402 machine services;
- data/service resale opportunities where terms permit;
- agent-native work marketplaces;
- market-neutral carry;
- future equity/ETF APIs;
- other legal and permitted economic rails.

“Find loopholes” means **find legitimate inefficiencies, pricing discrepancies, incentives, rebates, information delays, structural opportunities, and underexploited permitted mechanisms**.

It does **not** mean bypass authentication, evade rate limits, exploit software vulnerabilities, abuse promotional systems, manipulate markets, or violate platform terms.

## 31.2 Automatic integration boundaries

FORGE may automatically:

- discover public APIs;
- read official documentation;
- build an adapter scaffold;
- run public-data tests;
- create mocked/sandbox integration tests;
- activate a data-only adapter if no credential or money movement is involved and terms permit it.

If a new venue requires credentials, KYC, legal acceptance, account creation, or funding, FORGE should prepare the adapter and clearly flag exactly what is required.

Once the user supplies required credentials and the venue is enabled in policy, routine operations can be autonomous.

---

# 32. DASHBOARD — MAKE FORGE'S INTELLIGENCE VISIBLE

Build a polished but lightweight local web dashboard.

The dashboard is observability, not a manual control requirement.

## 32.1 Home

Show:

```text
FORGE
Find Opportunities · Reinvest · Grow · Evolve

SYSTEM:        AUTONOMOUS / PAPER / LIVE / DEGRADED
TREASURY:      $XX.XX
NET P&L:       +$X.XX (+X.XX%)
REALIZED:      $X.XX
UNREALIZED:    $X.XX
RESERVE:       $X.XX
OPERATING COST $X.XX
TRUE NET:      $X.XX

LOCAL CPU:     1.7 / 3.0 vCPU
MODAL TODAY:   $X.XX
MODAL MONTH:   $X.XX / $30
DEEPSEEK:      $X.XX spend

MARKETS WATCHED: N
OPPORTUNITIES:   N
LIVE POSITIONS:  N
STRATEGIES LIVE: N
CHALLENGERS:     N
RESEARCHING:     N
```

## 32.2 Opportunity feed

For each live candidate:

- venue;
- instrument;
- strategy;
- expected edge;
- calibrated confidence;
- max useful capital;
- fees;
- slippage;
- expiry countdown;
- current status;
- reason rejected/accepted.

## 32.3 Evolution screen

Visualize strategy lineage.

Show:

```text
parent → mutation → challenger → champion
```

Include mutation rationale and performance deltas.

## 32.4 Agent activity

A real-time stream such as:

```text
18:41:02 Market Scout — volatility compression anomaly detected SOL-USD
18:41:02 Opportunity Engine — candidate opp_12881 score 0.71
18:41:03 Scientist — requested focused 30-day replay
18:41:03 Compute Governor — Modal burst approved est. $0.012
18:41:06 Critic — edge unstable under +20ms latency
18:41:06 Allocator — REJECTED
18:41:07 Lesson — latency sensitivity tagged to strategy family
```

## 32.5 Costs

Show P&L gross and net of:

- fees;
- slippage;
- DeepSeek;
- Modal;
- paid APIs.

If the system is gross-profitable but net-unprofitable, the UI should make that painfully obvious.

## 32.6 Safety/control panel

Provide manual controls for emergencies even though routine approvals are zero:

- PAUSE NEW TRADES;
- CANCEL OPEN ORDERS;
- FLATTEN POSITIONS WHEN SAFE;
- OBSERVE ONLY;
- PAPER MODE;
- LIVE MODE guarded by explicit configuration;
- DISABLE VENUE;
- DISABLE STRATEGY;
- KILL FORGE.

These are emergency/operator controls, not normal workflow steps.

---

# 33. OBSERVABILITY

Use structured JSON logging.

Every log should include where relevant:

```text
timestamp
level
service
agent
strategy_id
opportunity_id
intent_id
order_id
venue
symbol
trace_id
```

Metrics:

- websocket uptime;
- message latency;
- stale-data incidents;
- opportunities/sec;
- opportunities passed/rejected;
- strategy population sizes;
- backtest throughput;
- shadow hit rate;
- orders/fills/rejects;
- slippage;
- gross/net P&L;
- drawdown;
- local CPU/memory;
- Modal jobs/cost;
- DeepSeek calls/tokens/cost;
- API errors;
- reconciliation mismatch count.

Alerts should be meaningful, not noisy.

Alert immediately on:

- auth failure;
- unexplained balance mismatch;
- emergency breaker;
- unexpected external transfer attempt;
- persistent market-data corruption;
- repeated execution failure;
- runaway costs;
- live process crash/restart loop.

---
# 34. SECURITY MODEL

FORGE handles real money. Security is part of profitability because one credential compromise can erase every gain.

## 34.1 Threats to explicitly model

- leaked API key;
- leaked wallet credential;
- prompt injection through external content;
- malicious market metadata / malformed payload;
- malicious new-venue documentation;
- dependency compromise;
- accidental transfer to unknown address;
- LLM hallucination;
- race conditions producing duplicate orders;
- compromised dashboard session;
- stale or spoofed market state;
- system clock drift;
- log files containing secrets;
- generated strategy code escaping sandbox;
- another project on the host reading FORGE secrets;
- FORGE accidentally reading another project's secrets.

## 34.2 Prompt-injection containment

Anything fetched from the internet, a market venue, an x402 service, a future bounty/task source, or documentation is **untrusted data**.

DeepSeek must never interpret retrieved content as higher-priority instructions.

Wrap retrieved text in explicit untrusted-data structures and prohibit it from altering:

- system prompt;
- credential policy;
- risk limits;
- transfer allowlists;
- tool permissions;
- compute budget;
- live mode.

## 34.3 Secrets

Recommended local pattern:

```text
/etc/forge/forge.env
```

owned by the FORGE service account and mode `0600`, if host permissions allow it.

If not, use a project-external user-secret path with strict permissions. Never keep secrets in source control.

Modal secrets must be stored in Modal's secret system if remote workers require them. Only provision each remote function the minimum secret set it needs.

## 34.4 Dashboard access

Bind dashboard to localhost by default.

If remote access is required, put it behind an existing secure tunnel/reverse proxy only after verifying that this does not interfere with another project. Require authentication.

Do not expose an unauthenticated “LIVE MODE” control to the internet.

## 34.5 Generated code sandbox

If DeepSeek generates Python for research beyond the Strategy DSL:

- execute it only in an isolated subprocess/container/Modal Sandbox;
- no host filesystem access beyond explicit input directory;
- no live credentials;
- no wallet access;
- no exchange-trading permissions;
- network disabled unless the experiment explicitly needs a safe endpoint;
- timeout;
- memory/CPU limit;
- output size limit.

Only tested primitives incorporated into the reviewed codebase may reach live strategy execution.

---

# 35. RELIABILITY AND RECOVERY

FORGE must recover from normal failures automatically.

## 35.1 Startup recovery

On restart:

1. open database;
2. verify migrations;
3. load configuration;
4. initialize ledger;
5. connect to configured venues;
6. fetch authoritative balances;
7. fetch open orders/positions;
8. reconcile local state;
9. rebuild in-memory books from fresh snapshots;
10. restore strategy state;
11. mark stale opportunities expired;
12. resume research queues;
13. only then enable new live order creation.

## 35.2 Crash consistency

A process crash between order submission and local persistence must not cause duplicate execution.

Use idempotency keys and venue reconciliation.

## 35.3 Database backup

Automate project-local backups of state and critical configuration.

Do not back up secrets into world-readable locations.

Suggested:

```text
backups/YYYY-MM-DD/
  forge-state.sqlite.zst
  audit.jsonl.zst
  config-redacted.json
```

## 35.4 Time

Use UTC internally everywhere.

Persist exchange timestamp and receive timestamp separately.

Monitor clock drift.

---

# 36. LOCAL SERVICE DEPLOYMENT

Prefer systemd if available.

Example conceptual unit:

```ini
[Unit]
Description=FORGE Autonomous Capital Growth Engine
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=forge
WorkingDirectory=/srv/forge
EnvironmentFile=/etc/forge/forge.env
ExecStart=/srv/forge/.venv/bin/python -m forge.main
Restart=always
RestartSec=3
CPUQuota=300%
CPUWeight=50
Nice=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/srv/forge /var/lib/forge /var/log/forge

[Install]
WantedBy=multi-user.target
```

Do not blindly deploy the example paths. Adapt safely to the actual project root and permissions.

If systemd hardening directives conflict with required runtime behavior, adjust minimally and document why.

## 36.1 Normal CPU target

A hard cap alone does not guarantee the 2-vCPU target. Add application-level concurrency limits:

- bounded thread pools;
- `ProcessPoolExecutor(max_workers=2)` locally;
- backpressure on research jobs;
- Modal offloading when queue pressure rises;
- avoid uncontrolled BLAS threading (`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, etc. set appropriately).

Set numerical libraries so they do not silently consume all cores.

Example:

```dotenv
OMP_NUM_THREADS=2
MKL_NUM_THREADS=2
OPENBLAS_NUM_THREADS=2
NUMEXPR_NUM_THREADS=2
```

Benchmark and tune.

---

# 37. DEVELOPMENT MODES

Implement explicit modes.

## MODE 1 — TEST

- fixture market data;
- fake balances;
- no network execution;
- deterministic tests.

## MODE 2 — REPLAY

- historical data;
- deterministic simulated execution;
- no live market actions.

## MODE 3 — SHADOW

- live market data;
- live opportunities;
- would-be trades;
- no real orders.

## MODE 4 — PAPER

- live data;
- persistent simulated account;
- all accounting/allocator/risk logic active;
- no venue orders.

## MODE 5 — LIVE

- real configured venue execution;
- autonomous operation;
- zero routine manual approvals;
- full audit and risk controls.

The mode must be unmistakable in logs and UI.

Live mode should require a deliberate configuration value, not accidental default.

```dotenv
FORGE_LIVE_TRADING=false
```

Do not set it true until integration tests and initial shadow tests pass.

---

# 38. STARTUP CAPITAL AND CONFIGURATION MODEL

Create policy configuration similar to:

```yaml
treasury:
  initial_experiment_capital_usd: 20.0
  external_injection_limit_usd: 20.0
  profit_reinvest: true
  reserve:
    below_100:
      normal_fraction: 0.15
      min_fraction: 0.05
      exceptional_opportunity_can_use_full_experiment_bankroll: true
    at_or_above_100:
      hard_usd_floor: 25.0

risk:
  leverage_enabled: false
  allow_full_bankroll_initial_experiment: true
  require_empirical_confidence_for_concentration: true
  stale_market_ms: <calibrate per stream>
  circuit_breakers_enabled: true

compute:
  local_target_vcpu: 2
  local_max_vcpu: 3
  modal:
    enabled: true
    monthly_budget_usd: 30.0
    preferred_warm_vcpu_equivalent: 0.5
    allow_dynamic_burst: true
  deepseek:
    model: deepseek-flash
    starting_budget_usd: 5.0
    dynamic_effort: true

execution:
  manual_trade_approvals: false
  withdrawals_to_arbitrary_addresses: false
  require_idempotency: true
```

Do not treat this exact YAML as immutable. Build typed configuration and validation.

---

# 39. BUILD ORDER — OPUS 5.5 EXECUTION PLAN

You are Opus 5.5 running inside a fresh Pi CLI terminal. Execute this project methodically.

Do **not** spend the first several hours writing prose while the repository remains empty. Create the project and produce working vertical slices early.

## PHASE 0 — Establish isolation and continuity

1. Perform the minimal host inventory from Section 0.
2. Choose safe FORGE root.
3. Create root directory.
4. Initialize Git.
5. Create `AGENTS.md` containing the isolation and project mission directives.
6. Create `README.md` with purpose and quickstart.
7. Create `ARCHITECTURE.md` and record architectural decisions.
8. Create `.gitignore` immediately.
9. Create `.env.example` only; never create fake secrets.
10. Create the Python environment and deterministic dependency lock.
11. Verify nothing outside FORGE changed.
12. Make initial commit.

**Checkpoint:** print the FORGE root path and explicitly confirm that no unrelated project has been modified.

## PHASE 1 — Skeleton and contracts

Implement:

- settings;
- event types;
- venue protocol;
- strategy genome schema;
- opportunity schema;
- trade intent schema;
- risk-decision schema;
- ledger contracts;
- database migration framework;
- structured logging;
- health endpoint.

Write tests before moving on.

## PHASE 2 — Paper venue vertical slice

Create an entirely functional paper adapter.

Demonstrate:

```text
fixture/live-like ticks
→ feature
→ opportunity
→ strategy signal
→ sizing
→ risk decision
→ paper execution
→ fill
→ ledger
→ dashboard/API
```

This proves architecture before credentials.

## PHASE 3 — Market data engine

Build:

- multi-symbol market fabric;
- order books;
- bars;
- feature engine;
- regime engine;
- Parquet recording;
- replay.

Benchmark CPU use.

## PHASE 4 — Research/evolution system

Build:

- genome compiler;
- initial strategy primitives;
- strategy registry;
- lineage;
- backtester;
- walk-forward;
- Monte Carlo;
- shadow evaluator;
- fitness;
- mutation planner;
- candidate promotion lifecycle.

## PHASE 5 — DeepSeek integration

When key is available:

- implement API client;
- model alias `deepseek-flash`;
- thinking/non-thinking paths;
- tool schemas;
- tool router;
- token/cost ledger;
- Strategy Scientist;
- Critic;
- prompt versioning;
- inference governor.

Until the key exists, use a mock scientist that exercises the tool contracts.

## PHASE 6 — Modal integration

Using the authorized host-level Modal credentials:

- create dedicated FORGE Modal app namespace;
- deploy one small test function;
- validate round trip;
- deploy backtest worker;
- deploy optimizer/simulation worker;
- implement local client;
- implement job ledger;
- implement cost/budget state;
- benchmark warm fractional CPU behavior;
- choose economically sensible warm configuration;
- test automatic scale-up/scale-down.

Do not expose secrets in output.

## PHASE 7 — Coinbase market-data integration

When credentials are not needed for public feeds, integrate immediately if official API supports it.

When credentials are needed, scaffold and test with mocks until supplied.

Implement:

- product discovery;
- market rules;
- WebSocket market data;
- snapshot reconciliation;
- balance reading;
- order state;
- execution behind live feature flag.

## PHASE 8 — Coinbase execution integration

Before first real order:

- test API auth;
- fetch actual balances;
- verify permissions;
- confirm market minimums;
- place no order yet;
- run reconciliation test;
- run dry-run order construction;
- validate risk invariants.

If Coinbase offers a sandbox relevant to the chosen API, use it where practical.

## PHASE 9 — Dashboard

Build the dashboard after the backend's state contracts are stable.

Do not let frontend polish delay the engine.

## PHASE 10 — 24-hour shadow burn-in

Run continuous live market data and shadow decisions.

Targets:

- no crashes;
- no stale-book trades;
- no duplicate intents;
- stable CPU within policy;
- successful reconnects;
- correct ledger;
- research jobs complete and reconcile;
- DeepSeek costs tracked;
- Modal costs tracked;
- strategy mutations actually use prior evidence.

Do not shorten this purely to see a live trade.

## PHASE 11 — Tiny live validation

When the system passes acceptance criteria and the user provides valid credentials/funds:

- enable live mode;
- use the $20 experimental treasury policy;
- allow autonomous trading under code-level risk invariants;
- monitor through the dashboard/logs;
- do not require per-trade approval.

## PHASE 12 — Self-evolution observation

FORGE is not complete because it placed a trade.

Demonstrate at least one full lifecycle:

```text
strategy underperformance detected
→ failure attribution
→ reasoned mutation generated
→ candidate tested
→ challenger result
→ promotion or rejection
→ lineage updated
→ lesson persisted
```

That is a critical acceptance test.

---

# 40. EXACT FIRST-SESSION INSTRUCTIONS TO OPUS 5.5

When receiving this dossier in Pi CLI:

1. Read it completely before performing destructive or broad actions.
2. Restate the isolation boundary in one short paragraph.
3. Perform only minimal host inventory.
4. Create FORGE's isolated root.
5. Create `AGENTS.md` that carries forward all absolute project boundaries so future coding agents inherit them.
6. Build an implementation checklist in `docs/BUILD_STATUS.md`.
7. Begin Phase 0 immediately.
8. Do not ask the user for every implementation detail if a strong engineering default exists.
9. Ask only for information that actually blocks progress, such as a missing credential when the integration reaches the point it is required.
10. Keep the system runnable at the end of every phase.
11. Commit cleanly after meaningful milestones.
12. Never mark something complete without running the relevant tests.

### Permission for engineering judgment

Where this dossier is ambiguous, incomplete, or a newer/better engineering technique exists:

> **Use your highest reasoning and engineering judgment to optimize, advance, evolve, and improve the implementation, provided you preserve the mission, isolation, security boundaries, financial accounting integrity, 2-vCPU normal / 3-vCPU local ceiling, and autonomous nature of FORGE.**

You are explicitly encouraged to improve algorithms, architecture, feature engineering, strategy evaluation, performance, reliability, data structures, research methods, resource usage, and capital-efficiency wherever doing so plausibly increases FORGE's ability to discover sustainable net-positive opportunities.

Do not use “the dossier didn't explicitly say so” as a reason to leave an obviously valuable improvement undone.

But never reinterpret that permission as authority to:

- touch another project;
- bypass provider security;
- violate platform rules;
- exceed explicit external spending limits;
- expose secrets;
- remove auditability;
- disable safety invariants merely to increase short-term return.

---

# 41. DEFINITION OF “AUTONOMOUS”

FORGE is autonomous only if it can complete this loop without human trade approval:

```text
Observe
→ Detect
→ Hypothesize
→ Research
→ Test
→ Compare
→ Allocate
→ Risk-check
→ Execute
→ Monitor
→ Close/Exit
→ Reconcile
→ Account
→ Learn
→ Mutate
→ Reinvest
→ Repeat
```

The system should survive process restarts and resume from durable state.

“Autonomous” does not mean “unbounded.” It means actions happen automatically inside pre-authorized policy boundaries.

---

# 42. DEFINITION OF “RESOURCEFUL”

FORGE must be resourceful.

That means it should continuously ask:

```text
What information do I already have?
What can be computed locally for nearly zero marginal cost?
What additional information could change this decision?
What is that information worth?
Can DeepSeek improve this decision?
Would a Modal burst produce enough additional confidence/value?
Can this job be parallelized?
Can the result be cached/reused?
Can a past experiment answer the question already?
Is there a cheaper equivalent data source?
Is there a more profitable venue for the same underlying edge?
Can this successful component be reused elsewhere?
```

Resourcefulness also means **not spending resources unnecessarily**.

The goal is not to consume the $30 Modal allowance. The goal is to turn available computation into maximum net economic value.

---

# 43. PROPRIETARY ADVANTAGE ROADMAP

FORGE's proprietary advantage should compound in multiple dimensions.

## 43.1 Strategy lineage moat

Every trade and failed experiment makes the strategy graph richer.

## 43.2 Execution-cost model moat

FORGE learns actual slippage and fill behavior specific to its venues and position sizes.

## 43.3 Regime map moat

FORGE learns which strategies work under which market conditions.

## 43.4 Compute-value model moat

FORGE learns which kinds of research deserve DeepSeek or Modal spend.

## 43.5 Opportunity ranking moat

FORGE learns which opportunity features predict realized net return.

## 43.6 Failure-memory moat

FORGE should become progressively harder to fool with the same market pattern twice.

## 43.7 Meta-strategy moat

FORGE learns not only strategies but **how to search for strategies** more efficiently.

Track:

- mutation operators with highest success rate;
- research experiment types with highest information gain;
- feature families that generalize;
- strategy family longevity;
- conditions under which an old strategy should be resurrected.

---

# 44. SELF-REVIEW CYCLES

## Every few minutes / event-driven

- opportunity ranking;
- strategy health;
- capital allocation;
- market-data health.

## Hourly

Generate a machine-readable self-review:

```text
Treasury delta
Gross P&L
True net P&L
Fees/slippage
DeepSeek spend
Modal spend
Best strategy
Worst strategy
New lessons
Missed opportunities
Current regime
Research queue
```

Do not require a human to read it for the system to continue.

## Daily

Deep analysis:

- strategy family contribution;
- regime attribution;
- overfitting indicators;
- live-vs-backtest drift;
- compute ROI;
- opportunity misses;
- new algorithm candidates;
- venue expansion candidates.

Schedule flexible heavy research during DeepSeek off-peak pricing windows where practical, but do not delay time-sensitive opportunities solely to save inference cost.

## Weekly

- prune low-value research artifacts;
- compact Parquet;
- refresh universe;
- evaluate meta-allocator;
- re-evaluate dormant strategies;
- verify backups;
- review spend/runway.

---

# 45. PERFORMANCE AND LATENCY

FORGE is not intended to beat colocated HFT firms at microseconds.

Do not architect around impossible latency assumptions.

Focus on edges whose half-life is compatible with:

- Internet WebSocket latency;
- Coinbase API latency;
- a 2-vCPU local core;
- DeepSeek when needed;
- Modal only when opportunity lifetime permits.

Fast path must not call DeepSeek synchronously if waiting would destroy the edge.

Architecture should support:

```text
FAST PATH
market event
→ local features
→ already-validated strategy
→ deterministic risk
→ execution
```

and:

```text
RESEARCH PATH
market anomaly
→ DeepSeek hypothesis
→ Modal tests
→ strategy promotion
→ future fast-path execution
```

This separation is essential.

---

# 46. TEST SUITE REQUIREMENTS

## Unit tests

- feature calculations;
- sizing;
- reserve logic;
- risk limits;
- genome parsing;
- DSL compilation;
- fee calculations;
- slippage model;
- P&L;
- inference cost calculations;
- Modal budget calculations.

## Property tests

Examples:

- position size can never exceed policy cap;
- reserve never goes negative;
- duplicate intent cannot create duplicate order;
- a stale book can never create approved live intent;
- a strategy cannot mutate immutable history;
- true net P&L equals ledger sum within numeric tolerance.

## Integration tests

- market stream reconnect;
- venue adapter normalization;
- SQLite crash/reopen;
- Modal round trip;
- DeepSeek tool-call round trip;
- dashboard WebSocket;
- reconciliation.

## Replay tests

Take captured market event sequences and ensure deterministic strategy behavior for the same version/configuration.

## Chaos tests

Inject:

- lost websocket;
- delayed messages;
- duplicate messages;
- out-of-order events;
- API 429;
- API 500;
- timeout after order submission;
- local process kill;
- database temporary lock;
- DeepSeek unavailable;
- Modal unavailable.

FORGE must degrade safely.

---

# 47. ACCEPTANCE TESTS — SYSTEM IS NOT “DONE” UNTIL THESE PASS

## Isolation

- [ ] FORGE exists in its own root.
- [ ] Git status outside FORGE is unchanged by the build.
- [ ] No other project dependency/env/database is reused.
- [ ] Service names and ports are unique.
- [ ] Secret files are project-specific or approved user-level provider config.

## Resource limits

- [ ] Normal local load fits approximately 2 vCPUs.
- [ ] Runtime hard local ceiling is 3 vCPUs.
- [ ] Heavy research is capable of Modal offload.
- [ ] Modal workers scale down after work.
- [ ] Monthly Modal budget state is tracked.

## Market data

- [ ] Coinbase market feed runs continuously.
- [ ] reconnect works;
- [ ] stale data disables live decisions;
- [ ] order books are consistent;
- [ ] event timestamps are recorded.

## Strategies

- [ ] at least 5 seed strategy families exist;
- [ ] every strategy has a genome;
- [ ] lineage persists;
- [ ] mutation rationale persists;
- [ ] regime-specific metrics exist;
- [ ] retired strategies remain queryable.

## Research

- [ ] replay works;
- [ ] walk-forward works;
- [ ] shadow mode works;
- [ ] Modal backtest works;
- [ ] DeepSeek can request tools;
- [ ] DeepSeek cannot bypass execution/risk tools;
- [ ] generated candidate is tested before promotion.

## Treasury

- [ ] starting policy supports $20 experiment;
- [ ] profits automatically increase available equity;
- [ ] reserve rules work;
- [ ] $25 reserve activates at $100+;
- [ ] P&L includes operational costs.

## Execution

- [ ] duplicate order protection tested;
- [ ] venue constraints validated;
- [ ] fills reconcile;
- [ ] API errors do not corrupt local state;
- [ ] live mode defaults off.

## Evolution

Demonstrate:

- [ ] a strategy degrades;
- [ ] FORGE detects degradation;
- [ ] Scientist diagnoses it;
- [ ] mutation rationale is generated;
- [ ] new genome is created;
- [ ] candidate is backtested;
- [ ] candidate is shadow tested;
- [ ] candidate is promoted or rejected from evidence;
- [ ] lineage graph reflects the result;
- [ ] lesson memory is updated.

## Autonomy

- [ ] system can run overnight without intervention;
- [ ] research continues without a terminal attached;
- [ ] processes recover after restart;
- [ ] no routine human trade confirmation exists in live flow;
- [ ] dashboard accurately shows what FORGE is doing.

---

# 48. FIRST LIVE-EXPERIMENT PROTOCOL

Do not interpret the user's aggressiveness as permission to skip validation.

When ready:

## Step 1
Confirm actual accessible Coinbase balance and instrument availability.

## Step 2
Confirm exact fee/minimum-order constraints for the account/market being used.

## Step 3
Run 24 hours of shadow mode unless a shorter period has already produced adequate sample data and all acceptance tests pass. Prefer the full burn-in.

## Step 4
Enable live mode with the configured $20 maximum initial external capital.

## Step 5
Allow FORGE to allocate automatically.

## Step 6
Observe the engine, but do not require human approval per trade.

## Step 7
Evaluate **true net P&L**, not account-value screenshots alone.

Success for the first experiment is not defined as “must double overnight.”

Success is:

1. FORGE operated autonomously;
2. it preserved accounting integrity;
3. it correctly distinguished good and bad opportunities;
4. it learned from results;
5. it evolved strategies;
6. any profit was genuine after costs;
7. the system became more intelligent from experience.

The aspirational growth milestone remains:

```text
$20 → $40 → larger treasury
```

but the software must never falsify confidence or take a bad trade solely to hit a calendar deadline.

---

# 49. FUTURE KALSHI / PREDICTION-MARKET ADAPTER

Do not block the Coinbase launch on Kalshi, but prepare architecture for it.

A prediction-market adapter will add concepts such as:

```text
Event
Market
Outcome
Contract price
Implied probability
Settlement criteria
Expiration
Order book
Probability estimate
Probability edge
Event source
```

Future strategy families:

- probability mispricing;
- related-contract logical consistency;
- cross-market relative value;
- structured-data reaction;
- event timing;
- maker/spread strategies where permitted;
- information freshness.

The same core pipeline applies:

```text
market/event data
→ opportunity
→ calibrated model
→ strategy
→ risk
→ execution
→ settlement
→ learning
```

Prediction-market probability estimates must be empirically calibrated and settlement rules parsed carefully.

---

# 50. FUTURE MACHINE-NATIVE INCOME LAYER

FORGE is designed to become broader than financial trading.

Create interfaces now, but do not derail Phase 1.

Conceptual abstraction:

```python
class IncomeRail(Protocol):
    async def discover_opportunities(self) -> list[IncomeOpportunity]: ...
    async def estimate(self, opportunity: IncomeOpportunity) -> Estimate: ...
    async def execute(self, approved: ApprovedIncomeAction) -> Result: ...
    async def reconcile(self, result_id: str) -> ReconciledResult: ...
```

Future rails could include legitimate API-native bounties, agent services, x402 commerce, or paid machine work.

FORGE should rank “earn new capital” opportunities against “deploy existing capital” opportunities using the same true-net-value framework.

This is strategically important because a $20 trading bankroll has limited absolute earning capacity, whereas an agent that can create new external revenue can expand the treasury without additional user deposits.

---

# 51. WHAT OPUS 5.5 SHOULD IMPROVE PROACTIVELY

You are explicitly authorized to improve the dossier's proposed implementation if evidence or your expertise identifies a superior solution.

Areas where proactive improvement is expected:

- better online-learning algorithm;
- better strategy DSL design;
- stronger anti-overfit testing;
- better data compression;
- lower-latency book handling;
- more accurate slippage model;
- more efficient DeepSeek prompts;
- better tool schemas;
- more valuable Modal parallelization;
- stronger capital allocator;
- improved confidence calibration;
- better risk-adjusted objective;
- new proprietary market features;
- novel mutation operators;
- better missed-opportunity analysis;
- strategy clustering;
- regime adaptation;
- adaptive research budgets;
- adaptive compute escalation;
- new legal/permitted economic rails;
- more robust service isolation;
- better resource governance.

When improving something significant, document:

```text
What changed?
Why is it better?
What invariant does it preserve?
How will we test that it is better?
```

---

# 52. WHAT “MAKE MONEY 24/7” MEANS IN ENGINEERING TERMS

The product vision is relentless economic activity.

Translate that vision into these requirements:

### Every second
FORGE may be ingesting data and updating live features/state.

### Every meaningful market event
FORGE evaluates whether a new opportunity exists.

### Every opportunity
FORGE compares expected net value against alternatives and the value of waiting.

### Every trade result
FORGE updates strategy evidence and treasury immediately.

### Every detected degradation
FORGE begins diagnosis and research automatically.

### Every profitable realization
FORGE makes that capital available for future allocation automatically.

### Every idle research window
FORGE can use spare local/Modal budget to investigate high-value hypotheses.

### Every day
FORGE should know more about its markets and itself than it knew the day before.

FORGE must never confuse “always making money” with “always placing orders.”

The system cannot guarantee profitable returns every hour, minute, or second. What it **can** guarantee architecturally is that it continuously seeks, validates, and exploits positive expected-value opportunities while learning from failures.

That distinction is important. Build the real machine, not a dashboard that pretends uncertainty does not exist.

---

# 53. OPUS 5.5 QUALITY BAR

Treat this as production-grade financial automation even though the initial bankroll is only $20.

Why? Because if FORGE works, the bankroll may no longer be $20.

Therefore:

- typed interfaces;
- deterministic tests;
- durable state;
- migrations;
- audit trail;
- secrets discipline;
- recovery logic;
- strong error handling;
- no silent failures;
- no magic global state;
- no unbounded queues;
- no unbounded concurrency;
- no “TODO later” in money-critical paths;
- no fake performance metrics;
- no claimed strategy edge without data.

The initial capital is tiny. The architecture must not be.

---

# 54. DELIVERABLES

At the end of the initial build, FORGE should include:

1. isolated repository and runtime;
2. `AGENTS.md` with immutable project boundaries;
3. architecture documentation;
4. typed configuration;
5. market fabric;
6. Coinbase adapter;
7. paper adapter;
8. feature engine;
9. regime engine;
10. opportunity engine;
11. strategy DSL/genome;
12. seed strategy families;
13. strategy registry and lineage graph;
14. backtester;
15. replay engine;
16. walk-forward engine;
17. Monte Carlo/stress layer;
18. shadow-trading engine;
19. DeepSeek client;
20. DeepSeek tool router;
21. Strategy Scientist;
22. Strategy Critic;
23. capital allocator;
24. Risk Governor;
25. execution gateway;
26. ledger/accounting;
27. inference cost tracking;
28. Modal integration;
29. Modal budget tracking;
30. Compute Governor;
31. opportunity/venue discovery scaffolding;
32. dashboard;
33. health/metrics/alerts;
34. backup/recovery scripts;
35. service deployment;
36. comprehensive tests;
37. paper/shadow/live modes;
38. full self-evolution demonstration.

---

# 55. SOURCE-OF-TRUTH DOCUMENTS TO CREATE INSIDE THE REPO

Create and maintain:

## `AGENTS.md`
Short, forceful rules for every future coding agent:

- FORGE mission;
- DO NOT TOUCH OTHER PROJECTS;
- project root boundary;
- 2-vCPU target / 3-vCPU max;
- Modal authorized;
- secrets rules;
- live-money critical paths;
- tests required.

## `ARCHITECTURE.md`
Current actual architecture, not aspirational architecture.

## `STRATEGY_SPEC.md`
Exact Strategy Genome/DSL schema and lifecycle.

## `OPERATIONS.md`
How to run, stop, inspect, backup, restore, and recover FORGE.

## `SECURITY.md`
Threat model, keys, boundaries, provider permissions.

## `docs/BUILD_STATUS.md`
Checklist with only evidence-backed completion marks.

## `docs/DECISIONS.md`
Architecture Decision Records or concise decision log.

## `docs/LIVE_READINESS.md`
Every requirement before live capital can be activated.

---

# 56. RECOMMENDED INITIAL TECHNOLOGY STACK

Use this unless a clearly better low-resource alternative emerges:

```text
Language/runtime:       Python 3.12+
Async:                  asyncio + uvloop
HTTP/API:               FastAPI
Schemas:                Pydantic v2
HTTP client:            httpx/aiohttp as appropriate
WebSockets:             websockets/aiohttp/provider SDK
Analytics:              Polars + NumPy
Research SQL:           DuckDB
Transactional state:    SQLite WAL
Historical data:        Parquet
Testing:                pytest + hypothesis
Lint/type:               Ruff + Pyright/mypy
Packaging:              uv / locked pyproject
Dashboard:              React + TypeScript + Vite, static build
Remote compute:         Modal Python SDK
LLM:                    DeepSeek V4.1 Flash (`deepseek-flash`)
Process manager:        systemd
Metrics:                lightweight internal metrics first; Prometheus-compatible endpoint optional
```

Avoid adding Redis, Kafka, Kubernetes, Postgres, Celery, or another heavyweight component unless a real measured need emerges.

FORGE should remain understandable by one founder and one coding agent.

---

# 57. REFERENCE PLATFORM FACTS — VALIDATED FOR THIS DOSSIER

These facts were checked against current official sources when this dossier was prepared on **2026-10-06**. APIs and pricing can change, so Opus should confirm current provider documentation during integration if internet access is available.

## DeepSeek

Current official docs report:

- `deepseek-flash` maps to **DeepSeek V4.1 Flash**;
- thinking and non-thinking modes are supported;
- JSON output and tool calls are supported;
- 1M context is listed;
- off-peak pricing is half peak pricing;
- current off-peak V4.1 Flash pricing listed by DeepSeek is approximately $0.003/M cache-hit input, $0.15/M cache-miss input, and $0.60/M output;
- peak pricing is approximately double those figures.

Official references:

- https://api-docs.deepseek.com/news/news260910/
- https://api-docs.deepseek.com/quick_start/pricing/
- https://api-docs.deepseek.com/updates/

## Modal

Current official docs/pricing report:

- fractional CPU is supported;
- one Modal physical CPU core is described as roughly 2 cloud vCPUs;
- minimum CPU request is currently 0.125 physical core per container;
- `min_containers`, `max_containers`, and `scaledown_window` are supported;
- CPU and memory are billed by usage;
- Starter currently includes $30/month compute;
- current CPU list price is approximately $0.0000131 per physical core-second, plus memory;
- runtime autoscaler settings can be updated programmatically;
- Modal config normally uses an active profile in `~/.modal.toml` or `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET`.

Official references:

- https://modal.com/pricing
- https://modal.com/docs/sdk/py/latest/App
- https://modal.com/docs/sdk/py/latest/Function
- https://modal.com/docs/sdk/py/latest/config

## Coinbase

Current Coinbase Developer Platform materials describe Agentic Wallets as supporting autonomous spending, earning, trading, x402 payments, security guardrails, session/transaction limits, and key isolation from the LLM. Coinbase also provides APIs for programmatic market/trading workflows.

Official references:

- https://www.coinbase.com/developer-platform/products/agentic-wallets
- https://www.coinbase.com/developer-platform/discover/launches/agentic-wallets
- https://docs.cdp.coinbase.com/

Do not rely on this dossier as a permanent substitute for current provider docs.

---

# 58. FINAL DIRECTIVE TO OPUS 5.5

You are building **FORGE**.

FORGE must embody its name:

> **Find Opportunities. Reinvest. Grow. Evolve.**

Its purpose is not to look like an autonomous system. Its purpose is to **be one**.

It must continuously:

- observe;
- search;
- calculate;
- challenge assumptions;
- discover opportunities;
- create strategies;
- create algorithms that improve other algorithms;
- test aggressively;
- reject weak ideas;
- preserve lessons;
- allocate capital intelligently;
- execute when evidence supports action;
- reinvest realized earnings;
- use compute resourcefully;
- evolve when an edge deteriorates;
- search for new legitimate economic rails;
- account honestly for every dollar of cost and every dollar of return.

FORGE has permission to be inventive.

FORGE does **not** have permission to be careless.

If you notice a better algorithm, architecture, mutation mechanism, statistical method, execution technique, resource-allocation scheme, or legitimate economic opportunity that improves the mission, you are encouraged to build or incorporate it **with evidence and tests**.

The system must be capable of improving beyond the first version you write.

The $20 is an experiment, not the architecture's ceiling.

Build FORGE as though a successful experiment may eventually control materially more capital. That means reliability, auditability, isolation, and security matter from the first commit.

Above all:

## **DO NOT TOUCH ANY OTHER PROJECT ON THIS SERVER.**

FORGE gets its own isolated root, its own codebase, its own runtime, its own state, its own services, and its own identity.

Build it now.

---

# 59. IMMEDIATE BOOTSTRAP CHECKLIST

Opus 5.5: begin with this list now.

```text
[ ] Read full dossier
[ ] State project-isolation boundary
[ ] Run minimal host inventory only
[ ] Choose clean isolated FORGE root
[ ] Initialize Git
[ ] Create AGENTS.md
[ ] Create .gitignore
[ ] Create pyproject and locked environment
[ ] Create .env.example
[ ] Create docs/BUILD_STATUS.md
[ ] Create src/forge skeleton
[ ] Create tests skeleton
[ ] Create SQLite migration baseline
[ ] Implement event/contracts layer
[ ] Implement paper venue adapter
[ ] Implement one end-to-end paper-trade vertical slice
[ ] Run tests
[ ] Record actual CPU/memory footprint
[ ] Commit
[ ] Continue through build phases without touching another project
```

**End of FORGE Master Build Dossier.**
