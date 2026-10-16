# FORGE + HERMES: Autonomous Economic Intelligence Dossier
**Date:** 2026-10-07  
**Project:** FORGE — Find Opportunities, Reinvest, Grow, Evolve  
**Purpose:** Integrate Hermes Agent into FORGE as a 24/7 autonomous economic research/orchestration layer, while adding a new cross-rail prediction-market alpha engine inspired by the market structure visible in the viral “$68 → $6,732” trading-bot screenshot.

---

## Executive conclusion

The viral screenshot should **not** be treated as proof that someone turned $68 into $750,000. The claim is not independently verified, and reposts of the same story conflict on basic details. The useful part is not the claimed P&L. The useful part is the **architecture implied by the screenshot**: fast underlying-market data feeding a probability engine that looks for temporarily mispriced short-duration prediction contracts.

FORGE should absorb that idea, but implement it much more rigorously:

1. **Fast deterministic market perception** from Coinbase, CF Benchmarks, Kalshi and other permitted read-only feeds.
2. **Fair-probability models** for short-duration BTC/ETH prediction contracts.
3. **Cross-contract probability-surface consistency checks** to detect stale or mathematically inconsistent pricing.
4. **Cross-rail lead/lag models** to learn which underlying feed tends to move before another venue reprices.
5. **Hermes Agent as the 24/7 economic operating intelligence**: research, monitor, assign work, create reusable skills, keep goals alive, schedule recurring analysis, orchestrate specialists, and continuously improve the system.
6. **DeepSeek as FORGE’s reasoning brain**, with Flash used cheaply and continuously and stronger reasoning models invoked when the economic value of deeper thinking warrants it.
7. **Modal as burst compute**, dynamically used for large backtests, simulations, parameter sweeps, strategy tournaments and probability calibration.
8. **Immutable deterministic execution/risk controls** between every AI agent and real money.

The “secret sauce” is therefore **not Hermes alone** and not a single magic trading algorithm. It is the combination:

> **Hermes autonomy + FORGE strategy evolution + cross-rail probability alpha + deterministic execution + DeepSeek reasoning + Modal scale + empirical self-healing.**

The system must remain economically active 24/7, but that does **not** mean forcing trades 24/7. When no trade has positive expected value after all costs, FORGE should be researching, validating, evolving, calibrating, discovering new rails or preparing for the next edge.

---

# 1. Hermes Agent research verdict

## 1.1 What Hermes Agent is now

As of this dossier, the latest tagged Hermes Agent release located in the official NousResearch repository is **Hermes Agent v0.21.3 (v2026.9.14)**, released September 14, 2026.

Hermes Agent is an open-source autonomous-agent framework from Nous Research. It is model-provider agnostic and can run on a normal Linux server. Its most relevant capabilities for FORGE are:

- persistent profiles with isolated config, API keys, memory, sessions, skills and cron state;
- self-improving skills that can be created and updated from experience;
- durable cron jobs for unattended recurring work;
- session heartbeats and recurring loops;
- persistent `/goal` loops that keep working until completion criteria are met;
- multi-agent delegation and Kanban-style task dispatch;
- Bot Mode, where specialist Hermes profiles each have their own model, memory, skills and routines;
- plugins for custom tools and hooks;
- MCP integration for external tool servers;
- provider routing across multiple model providers;
- terminal, web, code execution and search tools;
- restart-safe scheduler behavior and watchdog patterns.

**Primary sources:**
- Hermes Agent releases: https://github.com/NousResearch/hermes-agent/releases
- Hermes docs: https://hermes-agent.nousresearch.com/docs/
- Profiles: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/profiles.md
- Plugins: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md
- Persistent goals: https://github.com/nousresearch/hermes-agent/blob/main/website/docs/user-guide/features/goals.md
- Cron: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md
- Loops: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/loops.md
- Bot Mode: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/bot-mode.md
- Skills: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/

## 1.2 Why Hermes belongs in FORGE

FORGE already has the pieces of a sophisticated quantitative system: market streaming, feature computation, strategy genomes, evolutionary search, paper/live validation, a deterministic risk governor, Modal compute and DeepSeek strategy design.

What FORGE still benefits from is an **autonomous operating intelligence that lives above those services and keeps the whole economic laboratory moving**.

Hermes is well suited to be that layer because it already knows how to:

- keep a standing objective alive across sessions;
- schedule unattended work;
- maintain procedural skills from experience;
- delegate to specialist agents;
- persist lessons and session history;
- recover from interrupted workflows;
- use multiple models/providers rather than tying the system to one model.

Hermes should **not** replace the fast market loop. It should not sit between a price tick and a time-sensitive order. It should be FORGE’s **Chief Economic Operating Intelligence / Research Director**, not its exchange matching engine.

---

# 2. Strict integration boundary

FORGE’s current isolation rules remain absolute.

Hermes must be installed and configured **only for FORGE**.

Recommended runtime boundary:

```text
/srv/forge/
├── app/
├── services/
├── strategies/
├── data/
├── logs/
├── runtime/
│   └── hermes/
├── plugins/
│   └── hermes-forge/
└── ...
```

Use a dedicated Hermes home such as:

```bash
export HERMES_HOME=/srv/forge/runtime/hermes
```

and configure its terminal working directory to `/srv/forge`.

Hermes profiles are specifically designed to isolate configuration, credentials, memory, sessions, skills and state. The official docs warn not to point two independent agents at the same Hermes home because memory/state writes can contaminate each other. FORGE should therefore use **one distinct Hermes home per long-lived Hermes profile/bot** when multiple bots are deployed.

For maximum separation from the rest of the host, prefer Hermes terminal subprocess home isolation (profile-scoped home) rather than inheriting unrelated host-user state wherever practical.

**Hard rule:** Hermes may not search other project directories, import their state, read their `.env` files, or reuse their credentials.

---

# 3. Hermes’ role inside FORGE

Create a dedicated role:

## **FORGE Economic Governor (Hermes)**

Mission:

> Keep FORGE economically active 24/7 by continuously discovering, validating, improving and orchestrating legitimate income-generating opportunities, while ensuring the deterministic FORGE risk and execution layers remain authoritative over real capital.

Hermes is responsible for:

- opportunity research;
- market-structure research;
- monitoring whether current strategies are degrading;
- generating research tasks for DeepSeek;
- deciding when deeper reasoning is worth its cost;
- launching Modal experiments through FORGE tools;
- comparing candidate strategy families;
- maintaining research and strategy lineage;
- generating/refining reusable FORGE skills;
- discovering new legitimate API-accessible income rails;
- scheduling recurring diagnostics and research;
- creating incidents when system/data/strategy health degrades;
- asking specialist agents to challenge assumptions;
- continuously searching for better ways to turn available capital into more capital.

Hermes **must not**:

- possess raw Coinbase/Kalshi signing secrets in model context;
- bypass the Risk Governor;
- directly rewrite immutable wallet-security controls;
- submit an exchange order except through a deterministic FORGE execution tool that validates policy first;
- trade merely to satisfy an “always earn” slogan;
- treat LLM confidence as financial certainty.

---

# 4. Give Hermes FORGE-native tools, not unrestricted money

Build a project-local Hermes plugin named something like:

```text
hermes-forge
```

Hermes’ plugin system supports custom tools, hooks, commands, skills and structured LLM calls without modifying Hermes core.

Expose a carefully designed tool surface such as:

```text
forge_get_treasury_state()
forge_get_positions()
forge_get_strategy_health()
forge_get_market_regimes()
forge_get_top_opportunities()
forge_get_prediction_surface(asset, expiry)
forge_get_cross_rail_state(asset)
forge_get_execution_cost_estimate(opportunity)
forge_get_system_health()
forge_get_intelligence_budget()

forge_create_research_task(hypothesis, priority)
forge_run_backtest(strategy_genome, dataset)
forge_run_walkforward(strategy_genome)
forge_launch_modal_experiment(spec)
forge_shadow_candidate(strategy_id)
forge_compare_candidates(ids)
forge_request_strategy_mutation(strategy_id, failure_evidence)
forge_archive_strategy(strategy_id, reason)
forge_promote_candidate(strategy_id)

forge_request_trade(opportunity_id, proposed_size, rationale)
forge_request_exit(position_id, rationale)
```

`forge_request_trade()` and `forge_request_exit()` must be **requests**, not raw exchange access. The deterministic FORGE execution service re-checks:

- strategy authorization;
- calibrated probability;
- expected value after fees/slippage;
- wallet state;
- capital regime;
- correlation/exposure;
- market freshness;
- order idempotency;
- account/venue health;
- hard operator limits.

Only then may an order reach an exchange API.

This gives Hermes broad autonomy without giving a language model unlimited signing authority.

---

# 5. 24/7 Hermes operating pattern

Use the right Hermes primitive for the right kind of autonomy.

## 5.1 Durable cron — standing unattended jobs

Use Hermes cron for tasks that must survive terminal restarts and run indefinitely in independent fresh sessions.

Examples:

- every 5 minutes: check FORGE system/market feed health;
- every 15 minutes: review opportunity funnel and rejected opportunities;
- hourly: compare live strategy performance to expected distributions;
- every 2 hours: search for market-structure changes, venue notices, listings and new contracts;
- every 4 hours: run a compact failure-analysis pass on strategies that degraded;
- daily: generate a strategy lineage/economic report;
- weekly: audit fee schedules, venue rules and data/API changes.

When a check can be deterministic, use Hermes’ **script-only / no-agent cron** so it consumes zero LLM tokens.

Only wake an LLM when something economically meaningful changed.

## 5.2 Heartbeats — contextful supervision

Use a Hermes heartbeat for a long-lived Economic Governor session so it periodically revisits FORGE’s current state while retaining the session context.

The heartbeat is not a trading clock. It is a supervisory wakeup.

## 5.3 Persistent goals — deep autonomous research

Use `/goal` for finite but multi-step objectives such as:

- discover whether a new Kalshi contract family can produce positive net expectancy;
- diagnose why a strategy’s live edge decayed;
- design and validate three replacement strategy families;
- reduce inference cost by 25% without reducing economic output.

Attach acceptance gates where possible so a research goal cannot mark itself complete without evidence.

## 5.4 Loops — temporary high-attention periods

Use `/loop` during a live experiment or unusual market condition when FORGE wants repeated context-aware inspection for a limited duration.

Do not run permanent high-frequency LLM loops. They waste tokens and add latency.

---

# 6. Hermes specialist roster

Do not start with a huge expensive swarm. Start with a lean roster and expand only when attribution proves value.

Recommended initial Hermes roles:

## 6.1 FORGE Economic Governor
Primary model: DeepSeek V4.1 Flash by default.  
Role: overall economic orchestration, triage, work scheduling, opportunity review.

## 6.2 Quant Scientist
Default: DeepSeek V4.1 Flash.  
Escalation: DeepSeek V4 Pro/high reasoning for high-value or difficult strategy invention/diagnosis.  
Role: new strategy families, failure diagnosis, probability-model improvements.

## 6.3 Adversarial Critic
Model: economical independent model or second DeepSeek pass with deliberately adversarial prompt.  
Role: attack backtests, identify leakage, overfitting, fee blindness, data-mining artifacts and unjustified confidence.

## 6.4 Market/Income Scout
Model: cheap/fast model, deterministic scripts whenever possible.  
Role: monitor Coinbase products, Kalshi markets, venue announcements, API changes, new legitimate rails and structurally unusual opportunities.

## 6.5 Operations Doctor
Prefer deterministic monitoring; LLM invoked only on anomalies.  
Role: self-healing incidents, stale streams, failed Modal tasks, broken cron, data inconsistency.

Hermes Bot Mode can represent these as separate profiles with isolated memories, models, skills and routines. If multiple persistent bots are used, give each its own profile/home exactly as Hermes documentation recommends.

---

# 7. The prediction-market alpha engine

## 7.1 What the viral screenshot most plausibly points toward

The screenshot visibly references BTC/Polymarket-like trading concepts and appears much more consistent with a short-duration prediction-market system than with a magical general-purpose crypto predictor.

A credible architecture for this strategy family is:

```text
FAST UNDERLYING DATA
        ↓
FAIR PROBABILITY MODEL
        ↓
PREDICTION MARKET PRICE
        ↓
MODEL PROBABILITY - EXECUTABLE MARKET PROBABILITY
        ↓
COST / UNCERTAINTY / LIQUIDITY FILTER
        ↓
TRADE ONLY WHEN NET EDGE IS POSITIVE
```

This type of architecture is reproducible even if the social-media profit claims are not.

FORGE should implement it on **regulated/authorized rails available to the operator**, with Kalshi as the API-first U.S. prediction-market rail.

Coinbase prediction markets are operated by Kalshi, and Coinbase’s own documentation states that U.S. crypto prediction markets settle using the contract’s specified source of truth. BTC/ETH price contracts commonly use the CF Benchmarks Real Time Index (BRTI), based on a 60-second average at settlement.

Sources:
- Coinbase prediction-market introduction: https://help.coinbase.com/en/coinbase/trading-and-funding/prediction-markets/intro
- Coinbase BTC 15-minute example: https://www.coinbase.com/predictions/event/KXBTC15M-26OCT061500
- Kalshi crypto markets: https://help.kalshi.com/en/articles/13823838-crypto-markets
- Kalshi API: https://help.kalshi.com/en/articles/13823854-kalshi-api
- CF Benchmarks API: https://docs.cfbenchmarks.com/api/rest/stats/

---

# 8. Proprietary algorithm family: FORGE Settlement Probability Alpha (FSPA)

For every short-duration contract, estimate:

```text
P_model = probability the contract resolves YES
P_market = executable implied probability from current bid/ask
C_total = fees + spread + slippage + expected adverse selection
U = uncertainty penalty
```

Define:

```text
NET_PROBABILITY_EDGE = P_model - P_market - C_total - U
```

for a YES contract, with the analogous formulation for NO.

FORGE should not use a single probability model. Maintain an ensemble whose components can be evolved and regime-selected.

Candidate inputs:

- distance to strike/target;
- seconds until settlement window;
- current CF Benchmarks RTI/BRTI level;
- rolling RTI slope;
- realized volatility across 15s/1m/5m/15m windows;
- Coinbase spot returns;
- cross-exchange spot returns from permitted public market-data feeds;
- spot dispersion across venues;
- Coinbase L2 order-book imbalance;
- aggressive-buy/sell trade imbalance;
- spread expansion/contraction;
- liquidity withdrawal/replenishment;
- momentum acceleration;
- micro-volatility regime;
- prediction-market odds velocity;
- prediction-market depth imbalance;
- time remaining;
- day/time/maintenance effects;
- learned lead/lag relationships.

Use an ensemble such as:

```text
P_model = w1*P_diffusion
        + w2*P_empirical_regime
        + w3*P_orderflow
        + w4*P_crossrail
        + w5*P_calibrated_ML
```

Weights are regime-dependent and continuously recalibrated.

Hermes’ role is to ask whether new model families or features should be tested. Modal performs large candidate tournaments. Deterministic FORGE code produces the final probability and execution decision.

---

# 9. Proprietary algorithm family: Implied Probability Surface Arbitrage

This is likely more valuable than treating each prediction contract independently.

If multiple threshold contracts exist for the same underlying and expiry, they imply a cumulative distribution:

```text
P(S_T >= K1), P(S_T >= K2), P(S_T >= K3), ...
```

For increasing strikes:

```text
K1 < K2  =>  P(S_T >= K1) >= P(S_T >= K2)
```

Violations suggest incoherent pricing or stale quotes.

Likewise, range probabilities should reconcile approximately with neighboring cumulative strikes.

Build two curves:

```text
MARKET-IMPLIED DISTRIBUTION
vs
FORGE FAIR DISTRIBUTION
```

For every contract calculate:

```text
SURFACE_RESIDUAL = P_forge(K,T) - P_market(K,T)
```

Then run a constrained smoothing/monotonicity pass to identify:

- outright probability mispricing;
- monotonicity violations;
- inconsistent adjacent ranges;
- stale strikes;
- local curvature anomalies;
- contracts whose price is inconsistent with neighboring contracts even if the overall BTC direction is uncertain.

This gives FORGE a route to **relative-value alpha** rather than requiring a heroic directional prediction every time.

---

# 10. Proprietary algorithm family: Cross-Rail Lead/Lag Graph

Do not assume one exchange is always the leader.

Maintain a dynamic graph where nodes are feeds/venues and directed edge weights describe predictive lead/lag strength by regime.

Example nodes:

```text
CF BRTI
Coinbase BTC-USD
Kraken BTC-USD read-only
Binance BTC-USDT read-only (where permitted)
Kalshi BTC contract odds
Coinbase prediction-market displayed odds
```

For each pair `(A,B)`, estimate:

```text
LeadScore(A→B, lag, regime)
```

using rolling cross-correlation, Granger-style tests where statistically appropriate, event-response timing, and actual forward predictive utility.

The model should learn facts such as:

```text
During high-volatility bursts:
Feed A tends to lead prediction odds by ~1.8 s.

During low volatility:
No stable lead exists.
```

FORGE should only trade a lead/lag relationship after it survives walk-forward and live shadow validation.

Hermes continuously asks whether the lead graph has changed and schedules recalibration when evidence says it has.

---

# 11. Proprietary algorithm family: Edge Half-Life Engine

Every discovered edge needs an estimated decay curve.

Define:

```text
Edge(t) = expected remaining net edge after delay t
```

Estimate `t_50`, the time for the edge to lose half its value.

Use it to choose execution urgency:

```text
if t_50 is long and maker fill probability is acceptable:
    prefer patient maker execution
elif t_50 is short and remaining edge > taker cost + safety margin:
    cross immediately
else:
    reject
```

Hermes should not make this millisecond decision. Hermes should supervise the model, analyze systematic execution loss and generate experiments to improve it.

---

# 12. Proprietary algorithm family: Capital Velocity / Opportunity Sequence Optimizer

FORGE should not merely choose the single trade with the largest nominal expected profit.

For each opportunity estimate:

```text
E = expected net return
H = expected capital lock duration
R = calibrated risk penalty
L = liquidity penalty
```

A simple starting score:

```text
GrowthVelocity = E[log(1 + net_return)] / expected_hours_locked
```

Then compare sequences of opportunities rather than isolated bets.

A smaller opportunity that returns capital in 30 minutes may compound faster than a larger opportunity that locks the same capital for four days.

However, do not hard-code short holding periods. A very high-EV longer-duration opportunity may still dominate.

This is the algorithmic expression of:

> **Make capital work hard, return it quickly when economically superior, and reinvest intelligently.**

---

# 13. Hermes as the strategy-evolution conductor

Hermes should manage a permanent challenger pipeline:

```text
OBSERVE
→ FIND ANOMALY
→ FORM HYPOTHESIS
→ CREATE GENOME
→ BACKTEST
→ PURGED/WALK-FORWARD TEST
→ HOLDOUT
→ PARAMETER ROBUSTNESS
→ SHADOW LIVE
→ MICRO-CAPITAL CALIBRATION
→ PROMOTE
→ MONITOR
→ DIAGNOSE
→ MUTATE / HIBERNATE / RETIRE
```

Every strategy must carry lineage:

```text
strategy_id
parents
hypothesis
features
regimes
parameters
cost assumptions
validation evidence
live evidence
confidence calibration
known failure modes
reason for mutation
reason for retirement
```

Hermes creates tasks and hypotheses; FORGE’s validation gates decide what is allowed to touch money.

Use Hermes skills to store **procedural discoveries** such as:

- how to investigate a sudden edge-decay incident;
- how to validate a new Kalshi contract family;
- how to audit a Coinbase fee change;
- how to compare prediction-surface consistency;
- how to diagnose a strategy whose paper/live gap widened.

Do not use Hermes’ small built-in `MEMORY.md` as the primary quantitative memory. Hermes memory is intentionally bounded. FORGE’s database remains the institutional source of truth for experiments, strategy lineage and economic outcomes.

---

# 14. Self-healing with Hermes

Hermes becomes a useful second self-healing layer above FORGE’s existing deterministic supervisors.

## Level 1 — deterministic recovery

No LLM required:

- restart crashed workers;
- reconnect WebSockets;
- rebuild stale books;
- retry transient API errors;
- reconcile open orders;
- detect data gaps;
- pause affected venue execution;
- ensure idempotent order recovery.

## Level 2 — Hermes diagnosis

When repeated recovery fails or performance degrades:

- collect incident evidence;
- assign Operations Doctor task;
- compare with prior incidents via session/skill history;
- propose repair;
- test repair in isolated context;
- apply only if safety gates pass;
- save successful recovery as a reusable skill.

## Level 3 — economic healing

If a strategy fails:

- capital is reduced/removed;
- strongest validated reserve strategy may take over;
- Hermes commissions failure analysis;
- DeepSeek identifies likely mechanism;
- Modal tests targeted mutations;
- successful challenger returns through the normal promotion gates.

The system should therefore heal **software, data, execution and economic logic**.

---

# 15. Intelligence routing: Hermes + DeepSeek + JEV + Modal

The cleanest stack is:

```text
DETERMINISTIC CODE
Fast market ingestion, features, risk, order execution

        ↓

JEV / FAST DECISION MODEL (optional, only if empirically useful)
Typed classification, routing, anomaly score, escalate/pass

        ↓

DEEPSEEK V4.1 FLASH
Cheap continuous reasoning, triage, market interpretation, routine agent work

        ↓ when value of information justifies it

DEEPSEEK V4 PRO / strongest authorized reasoning model
Novel strategy invention, difficult diagnosis, major-opportunity review

        ↓ when parallel computation is useful

MODAL
Mass simulation, replay, optimization, tournaments, Monte Carlo, feature search

        ↑

HERMES
24/7 conductor that decides what research/work needs to happen and keeps the system moving
```

Hermes should implement **Value of Information routing**:

```text
Expected Value of More Intelligence
= expected improvement in decision quality × economic consequence
  - additional inference/compute cost
  - delay cost
```

If positive by a meaningful margin, escalate.

If not, stay cheap or deterministic.

---

# 16. Economic attribution ledger

Every AI/compute action should have an attribution ID.

Record:

```text
intelligence_event_id
model/provider
prompt/task class
cost
latency
opportunity/strategy affected
resulting hypothesis/action
counterfactual baseline
subsequent realized P&L or avoided loss estimate
confidence in attribution
```

Over time FORGE should learn:

- which Hermes tasks create economic value;
- where DeepSeek Pro is worth the premium;
- where Flash is enough;
- where JEV is useful;
- where deterministic code is superior;
- which Modal workloads actually improve live P&L.

Do **not** minimize AI. Optimize its economic ROI.

---

# 17. Hermes 24/7 mission contract

The Economic Governor’s standing mission should read roughly:

> **Your mission is to maximize FORGE’s sustainable true net treasury growth by continuously finding, validating and improving legitimate income opportunities. FORGE must never become strategically stagnant. At all times, keep productive incumbents earning while a parallel research/evolution loop searches for stronger challengers, new market structures, new data advantages, new API-accessible rails and better execution. Never force trades when expected value is negative. When no capital deployment is justified, remain intellectually active: research, test, diagnose, evolve and prepare. Every meaningful lesson must improve FORGE’s future behavior.**

Use Hermes `/goal` for bounded objectives, durable cron for recurring operations and Bot/Kanban workers for parallel research tasks.

---

# 18. Initial launch plan

## Phase A — integrate Hermes without changing live execution

1. Install latest stable Hermes Agent release in a FORGE-controlled environment.
2. Set a dedicated `HERMES_HOME` under `/srv/forge/runtime/`.
3. Configure `terminal.cwd=/srv/forge`.
4. Ensure Hermes cannot browse other server projects.
5. Create the `hermes-forge` plugin with read-only FORGE tools first.
6. Start the Economic Governor on DeepSeek Flash.
7. Add script-only health cron jobs.
8. Add hourly strategy-health review.
9. Verify restart persistence and cron durability.
10. Test self-healing against deliberately killed non-critical workers.

## Phase B — research/experiment authority

Add tools allowing Hermes to:

- create research hypotheses;
- launch Modal experiments;
- create candidate genomes;
- initiate backtests/walk-forward tests;
- shadow candidates;
- request strategy promotion through validation gates.

Hermes still cannot place live orders directly.

## Phase C — prediction-market engine

1. Integrate Kalshi API market discovery/order books/account in sandbox/read-only mode first.
2. Integrate CF Benchmarks settlement/reference data.
3. Build FSPA fair-probability engine.
4. Build implied probability surface engine.
5. Build lead/lag graph.
6. Build edge-half-life estimator.
7. Run continuous paper/shadow trading.
8. Compare against naive market-implied baselines.
9. Require live calibration before risking capital.

## Phase D — gated autonomous execution

When strategy families pass readiness gates, allow Hermes to call `forge_request_trade()`.

The Risk Governor remains the final authority.

Start with minimal capital and dynamically scale only as live calibration improves.

---

# 19. Readiness gates for the new prediction-market engine

Before live capital:

- exact contract settlement source is parsed and verified;
- market data timestamps are synchronized;
- model probability calibration is measured;
- fees/slippage are modeled from executable prices;
- no look-ahead data appears in replay;
- prediction-surface constraints are validated;
- cross-rail lead/lag survives walk-forward testing;
- paper/shadow edge remains positive after all costs;
- strategy is robust to parameter perturbation;
- fill assumptions are realistic;
- settlement/reinvestment timing is included in capital-velocity economics;
- risk governor can stop the strategy independently of Hermes;
- API failure/restart tests pass.

---

# 20. What Hermes should search for continuously

Hermes should maintain an Opportunity Surface Registry and periodically research:

- new Coinbase Advanced markets;
- Coinbase/Kalshi prediction contract families;
- new event categories;
- new settlement/reference sources;
- fee changes;
- maker/taker incentive changes;
- API additions or rate-limit changes;
- new legitimate rewards/yield opportunities;
- onchain/CDP rails if later explicitly authorized;
- novel relative-value relationships between spot and prediction markets;
- structurally linked event contracts;
- data sources that improve hour/day prediction quality;
- new models/providers that reduce intelligence cost or latency.

A newly discovered rail should enter:

```text
DISCOVERED
→ LEGAL/ACCESS CHECK
→ API/AUTOMATION CHECK
→ COST MODEL
→ PAPER TEST
→ VALIDATION
→ SHADOW
→ LIVE CANDIDATE
```

Never browser-bot a platform that does not authorize programmatic trading.

---

# 21. Success metrics

Do not judge success by how many agents are busy or how many strategies are generated.

Primary economic metrics:

```text
TRUE_NET_PNL
TRUE_NET_PNL / CAPITAL_HOUR
LOG_GROWTH_RATE
MAX_DRAWDOWN
PROBABILITY_OF_RUIN
CAPITAL_UTILIZATION
CAPITAL_VELOCITY
ALPHA_AFTER_FEES
PAPER_TO_LIVE_DECAY
INTELLIGENCE_ROI
MODAL_ROI
STRATEGY_REPLACEMENT_GAIN
```

Hermes-specific metrics:

```text
valuable_research_tasks / total_tasks
skills_reused_successfully
incidents_self_healed
opportunities_discovered
strategy_improvements_promoted
avoidable_token_spend
mean_time_to_recovery
```

The Economic Governor should optimize **real account value**, not activity theater.

---

# 22. Important realism rule

FORGE may become a meaningful income engine if it discovers repeatable net edge and scales intelligently. It cannot be truthfully engineered to guarantee doubling, tripling or positive P&L every hour.

The proper mandate is more ambitious and more useful:

> **Continuously maximize the probability and magnitude of sustainable net treasury growth while minimizing ruin, and relentlessly improve the engine’s ability to find and exploit legitimate edge.**

That preserves the aggressive mission without teaching the optimizer to gamble simply because a clock is ticking.

---

# 23. Direct build directive for Opus 5.5

Use the following as the implementation mandate:

> Integrate Hermes Agent into the existing FORGE architecture as a project-isolated, 24/7 Autonomous Economic Governor. Do not rebuild FORGE from scratch and do not put Hermes in latency-critical order execution. FORGE’s deterministic market/risk/execution services remain authoritative.
>
> Install the latest stable Hermes Agent in FORGE’s isolated environment and use a dedicated `HERMES_HOME` under `/srv/forge`. Configure its terminal working directory to `/srv/forge`. It must not inspect or use any other server project.
>
> Build a project-local Hermes plugin exposing structured FORGE tools for treasury state, market state, strategy health, research jobs, Modal experiments, candidate generation, shadow tests and gated trade requests. Never expose exchange private keys or raw signing authority to Hermes or the LLM.
>
> Create an Economic Governor profile using DeepSeek V4.1 Flash by default. Add specialist profiles/workers only where measured economic value justifies their cost. Escalate hard, high-value research to DeepSeek V4 Pro/high reasoning. Use Modal when parallel compute has positive expected value.
>
> Use Hermes durable cron for unattended recurring work, script-only cron whenever no LLM is required, `/goal` for finite multi-step objectives, and Bot/Kanban delegation for parallel research. Build persistent procedural skills from successful investigations and incident recoveries, while keeping quantitative truth in FORGE’s own database.
>
> Add the new FORGE Settlement Probability Alpha strategy family for short-duration prediction markets using exact settlement-source data, especially CF Benchmarks BRTI/RTI where specified. Build fair-probability models, a cross-contract implied probability surface, a cross-rail lead/lag graph and an edge-half-life execution model.
>
> Do not copy the viral social-media profit claim. Copy the useful market-structure concept: fast underlying information may sometimes reveal stale or inconsistent prediction-market probabilities. Prove every edge empirically.
>
> Keep a permanent two-loop system: productive incumbents keep earning while Hermes continuously commissions challengers, new hypotheses and new opportunity rails. Every failure becomes structured evidence; every winner remains an incumbent that challengers must beat.
>
> Implement intelligence attribution so FORGE learns when Hermes, DeepSeek Flash, DeepSeek Pro, JEV and Modal each add economic value. Optimize intelligence; do not merely minimize it.
>
> Add self-healing across operations, data, strategies and intelligence providers. Test recovery by intentionally killing workers, disconnecting feeds, failing inference calls and interrupting Modal jobs.
>
> FORGE must remain economically active 24/7: EARNING, LEARNING, HEALING, DISCOVERING or PREPARING TO EARN BETTER. Never force a negative-EV trade just to appear active.
>
> The governing objective is maximum sustainable true net treasury growth after every fee, spread, slippage, inference and compute expense.

---

# 24. Final strategic view

Hermes improves FORGE most when it is treated as an **economic operating system**, not as the trader itself.

The existing FORGE engine provides the body:

- market feeds;
- strategy genomes;
- validation;
- risk;
- execution;
- accounting;
- capital allocation.

Hermes provides the persistent autonomous executive layer:

- keep the mission alive;
- decide what needs investigation;
- coordinate specialists;
- schedule unattended work;
- turn lessons into reusable skills;
- identify when current assumptions have gone stale;
- continually challenge the system to earn better.

The new prediction-market architecture supplies a potentially higher-capital-velocity strategy family that is structurally different from Coinbase spot momentum.

Together, FORGE becomes less like “a bot” and more like a **self-improving autonomous quantitative research firm compressed into one server**.

That is the architecture worth building.

---

## Source appendix

### Hermes Agent
- Releases: https://github.com/NousResearch/hermes-agent/releases
- Documentation: https://hermes-agent.nousresearch.com/docs/
- Profiles: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/profiles.md
- Plugins: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/plugins.md
- Tools/toolsets: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/toolsets-reference.md
- Persistent goals: https://github.com/nousresearch/hermes-agent/blob/main/website/docs/user-guide/features/goals.md
- Loops: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/loops.md
- Heartbeats: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/heartbeat.md
- Cron: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md
- Bot Mode: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/bot-mode.md
- Skills: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/

### Coinbase / Kalshi / CF Benchmarks
- Coinbase prediction-market introduction: https://help.coinbase.com/en/coinbase/trading-and-funding/prediction-markets/intro
- Coinbase BTC 15-minute contract example: https://www.coinbase.com/predictions/event/KXBTC15M-26OCT061500
- Coinbase prediction payouts/settlement: https://help.coinbase.com/en/coinbase/trading-and-funding/prediction-markets/payouts
- Kalshi crypto markets: https://help.kalshi.com/en/articles/13823838-crypto-markets
- Kalshi API: https://help.kalshi.com/en/articles/13823854-kalshi-api
- CF Benchmarks API: https://docs.cfbenchmarks.com/api/rest/stats/
