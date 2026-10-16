# Imagine Forge — forensic takeover passover

**Prepared:** 2026-10-09 16:02 UTC  
**Scope:** Read-only operational and economic investigation, completed one-hour PAPER observation, and continuity documentation on the command center and the dedicated Forge host.  
**Production root:** `/srv/forge` on `forge` (`forgeadmin@104.237.131.109`).  
**Changes in this pass:** continuity documents only. No Forge application code, prompts, credentials, portfolio settings, strategy controls, or live-money settings were changed. No tests were run.

## 1. Executive finding

Forge is an always-on autonomous research and trading platform with working services, scheduled Hermes roles, multiple paper and shadow rails, and a substantial strategy archive. It is **not currently demonstrated to be a self-funding income generator**. The evidence collected in this observation shows zero settled LIVE income, no new main-book PAPER positions, no promotions from the new trial records, and a negative internally reported 24-hour net estimate. The reported NAV and cost accounting are not independently reconciled, so that estimate must not be presented as audited account performance.

The founder reports that Forge has not exceeded **$0.10/hour** historically. Treat this as founder-reported history until reconciled account data establishes the exact series. The first economic milestone is **at least $0.50/hour of aggregate TRUE NET**, with the ambitious primary target **at least $1.00/hour**, consistently pursued across the combined portfolio: crypto, equities, event and prediction markets, sports, Kalshi, and any other eligible rail. These are economic objectives, not evidence that the system currently earns them and not a reason to force trades.

The one-hour run did what it was designed to do: observe the running PAPER ecosystem across rails without changing it or sending live orders. It recorded 158 new strategy records, but 157 distinct DNA hashes produced only 240 research rows over 103 genomes and **zero validation passes, promotions, or sealed exams**. That is evidence of activity and a failed conversion from candidate generation to validated opportunity, not income. Hash diversity is not strategy quality or independent evidence.

The next takeover should repair the truth and outcome chain before increasing inference spend or candidate volume: reconcile real net economics, prevent false paper closes, make each Hermes run produce an attributable durable result, repair stale or unauthenticated feeds, and admit only falsifiable, venue-specific experiments with realistic execution costs. In parallel, agents should aggressively pursue new proprietary mechanisms and keep a bounded forward-paper pipeline moving. Optimism means fast, accountable action; it does not permit invented profits, confidence unsupported by evidence, or bypassing deterministic financial controls.

## 2. Founder objective and operating doctrine

### Economic mandate

1. **First milestone:** sustained aggregate net earnings of at least $0.50/hour.
2. **Primary ambition:** meet and exceed $1.00/hour across all combined portfolios, consistently, with the system operating and seeking opportunities around the clock where the venue and market are available.
3. **Current truth:** the founder says prior performance never reached $0.10/hour. This observation measured $0 of settled live income; the internal reported 24-hour true-net estimate was approximately **−$0.126/hour**, with disputed NAV and unreconciled costs.
4. **Paper-first:** all strategies and portfolios, including stocks, are to use fake/paper money while the $0.50/hour milestone is being established. Paper gains are never reported as earned cash. Any transition to live execution must pass the governing readiness, reconciliation, authorization, and risk gates; a paper target alone is not proof of live readiness.
5. **Not a SaaS objective:** Forge is intended to earn income for Northstar Imagine and help fund its ventures, not to become a customer-facing SaaS product at this stage.

The target is demanding relative to the currently reported capital. $0.50/hour is $4,380/year and $1/hour is $8,760/year. If the displayed $28.27 NAV were accurate, those simple annual amounts would equal roughly 15,493% and 30,987% of that capital. The NAV is disputed, and these ratios are arithmetic context, not return forecasts. At hypothetical net annual yields of 5% and 10%, the corresponding capital requirements would be $87,600/$43,800 for $0.50/hour and $175,200/$87,600 for $1/hour. Those are scenarios only; they do not establish that such yields are achievable or that those funds exist.

### How the next agent should act

- Keep forward motion: when one rail is blocked, state the exact blocker, give it an owner and repair step, and continue independent work on other usable rails. Do not let blocked work disappear into repeated status reports.
- Invent and test genuinely new, custom algorithms tied to a specific market mechanism, not merely new labels or hash variants. Require a written hypothesis, source and venue, regime, baseline, fee/fill model, capital-hour requirement, falsification condition, sample plan, and maximum paper loss before admission.
- Run baseline comparisons, holdout/forward paper tests, and independent review. A candidate should progress through evidence gates; it should not be promoted because an agent is confident or the archive is large.
- Keep continuous analysis and useful paper trials running across eligible rails, with bounded concurrency and explicit resource budgets. Do not optimize for a fixed CPU percentage. The target server is 4 vCPU / 8 GB RAM; recent observations were around 3–14% CPU and 3.3 GiB available RAM. Use spare capacity for useful experiments, not random churn.
- Make inference earn its place: link paid calls to a question, artifact, decision changed, experiment and eventual outcome. Deterministic monitoring and data checks should not need expensive reasoning calls. Scale spending as measured marginal value and available capital scale.
- Treat each rejected candidate, failed forecast and loss as a recorded learning result with evidence and a changed next action. Do not endlessly rediscover the same failure.
- Never state a strategy “works,” a rail is ready, or income is earned without the relevant independent and settled evidence. Report misses and then the recovery action plainly.

## 3. Investigation scope, evidence standard, and completed observation

Inspection was performed on the dedicated `forge` host under `/srv/forge`, not by running Forge locally on the command center. The target continuity instructions and system map were read; relevant Forge-only service state, Hermes schedule registry, role reports, financial snapshots, trial output and logs were inspected. Secret values and credential contents were not copied into this handoff. Existing target Git modifications and untracked files were preserved.

Evidence classes in this report:

- **Observed:** directly present in a timestamped systemd state, persisted record, run artifact, or log.
- **Founder-reported:** supplied by the owner, not independently reconciled here.
- **Intended:** role/service contract or documented design, not proof of current completion.
- **Inference:** likely explanation or recommendation requiring follow-up evidence.

### One-hour cross-portfolio PAPER observation

Run `20261009T150017Z`, on the target under `var/research/paper_trial_1h/20261009T150017Z/`. The run record and `final.json` are the primary evidence. It was configured as `PAPER_ONLY`, from **2026-10-09 15:00:17 to 16:00:17 UTC**, 13 samples, five-minute sampling. It observed existing bounded engines and did not create live orders, transfer capital, or alter strategy/runtime settings. The recorder completed with systemd `Result=success`; no claim of an early exit is correct. Transient `is-active` readings were initially over-interpreted, then corrected by checking the final artifact and service result.

Coverage included Coinbase crypto research and paper state, Kalshi shadow/live-gate state, Alpaca broker paper, Alpaca local forward paper, and the sports paper desk/feed health.

| Measure | End-of-window observation | Meaning / limitation |
|---|---:|---|
| New strategy records | 158 | Record creation, not executed trades |
| Distinct DNA among new records | 157 | Hash diversity does not establish independent economic ideas |
| Research trial rows | 240 over 103 genomes | Includes repeated/evolving evaluations; not 240 profitable trades |
| Validation passes / promotions / sealed exams | 0 / 0 / 0 | No candidate cleared the observed promotion chain |
| `research_experiments` | empty | No durable cross-rail experiment record was present in this field |
| New main-book paper positions | 0 | No new position was opened in the main paper book during the window |
| Shadow trades | 4, reported net $0.00 | Shadow only; not settled income or a main-book trade |
| Live positions / Kalshi live orders | 0 / 0 | No live deployment observed |
| Settled live income | $0.00 | No earned income during this observation |
| Internal 24-hour true-net estimate | −$3.02594524, or −$0.126081/hour | Internal reporting only; account/cost reconciliation is unresolved |
| Displayed NAV | $28.27 | Disputed and not independently reconciled |
| `paper_edges_found` | 44 | Signal count, not fills, settled profit, or independent edges |

Other rail details:

- The existing crypto/main PAPER history showed 56 closed positions with lifetime grouped net of about **−$2.212455**. This is historical book data, not the one-hour result.
- Alpaca broker paper showed one existing QQQ-USD position with approximately $9.99 cost in a $50 Forge training bankroll; `live_eligible=false`. The broker’s roughly $100,000 toy paper balance is not Forge capital. The position had one paper session and the separate paper report showed a small closed net of about −$0.005, subject to its configured assumed fee model.
- Alpaca local forward-paper trials were READY but had zero sessions/trades and no earnings; the displayed data freshness was `2026-10-08T04:00:00Z`. Those modeled next-open trials are not broker fills.
- The sports desk had 12 open and 16 void paper bets, $0 P&L, zero placements and zero settlements in the observed snapshot. Logs repeatedly showed HTTP 401 responses from score endpoints. The feed must be repaired or the rail visibly quarantined.
- Kalshi remained shadow/paper-gated with zero live orders. Signal counts or crossrail quotes did not demonstrate executable fills.
- An artifact called `trial.8h` was still `RUNNING`, but its observed start/end timestamps span roughly 24 hours. It is not evidence of a completed eight-hour run or a confirmed overnight live run.
- The earlier four-hour observation requested at 14:11 UTC was stopped at 14:59:58 when the requested duration changed. It produced ten samples and an interruption record, not a completed four-hour outcome.

The one-hour observation is not a statistical proof about strategy expectancy. It demonstrates that substantial candidate activity can coexist with no accepted strategy, no new main paper position, and no live earnings.

## 4. How the system and the agents are meant to work

### The deterministic Forge runtime

`forge.service` is the core Python runtime. At startup it seeds the strategy catalog/arena, discovers instruments and data, initializes treasury and execution, loads or recomputes bars, starts a one-worker process pool, registers its loops with the supervisor, and then starts the watchdog. Runtime loops cover market streams/feed health, execution, treasury, history/universe backfill, improvement and arena review, counterfactual analysis, analyst/surface/crossrail/Kalshi work, allocation and profit velocity, equity paper, strategy factory/PaperLab/evidence board/regime work, PositionVigil, officer dispatch, sports paper, economics, earnings escalation/push, results enforcement, workflow progression, opportunity memory and settlement windows.

`Supervisor` checks loop heartbeat/silence and restarts loops that stall or exit using backoff. Its 15-second watchdog interval and per-loop `max_silence_s` thresholds are health/restart controls; they are not necessarily each job’s useful-work cadence. The main execution loop ticks internally around every two seconds. PositionVigil was changed in an earlier explicitly authorized intervention to check the main Forge book every five seconds; that setting does not change the separate Alpaca paper timer, which has been observed at 15 seconds during market sessions / 60 seconds while closed. Do not imply that the 5-second check covers every portfolio.

The money path is designed to be: **founder intent → allocation → deterministic RiskGovernor → validator → idempotent gateway → venue → reconciliation → ledger**. Hermes and other LLM roles propose through constrained tools; they do not hold trading keys, set destinations, override the risk governor, or authorize live orders. Preserve the immutable source-of-truth order and the global STOPPED/live gates in `/srv/forge/AGENTS.md`.

### Services and how work starts

Observed service topology on the target:

| Unit / trigger | Function and activation | What “active/ok” proves |
|---|---|---|
| `forge.service` | Long-running runtime; systemd starts the process, which starts supervised loops and watchdog | Process/loop activity only; not positive P&L |
| `forge-hermes.service` | Separate Hermes economic gateway, running as `forge-hermes`; reads its own scheduled role registry | Service is up; not proof every role produced useful output |
| Hermes internal cron jobs | `/srv/forge/runtime/hermes/home/cron/jobs.json`; scheduler dispatches each enabled prompt at its interval | `last_status=ok` means dispatch/scheduler success in inspected rows, not verified result or income |
| `forge-ops.service` | Private, owner-only Telegram control plane / Luke, running as `forge-ops` | Process is up; fresh Telegram delivery and closed-loop task proof were not verified |
| `forge-eng.service` | Sandboxed coding worker as `forge-eng`; service contract says it does not deploy | Worker availability; deployment is a separate controlled path |
| `forge-deployer.timer` / service | Checks deployment queue every two minutes; one-shot deployer | Timer wake is not a deployed feature until a receipt and runtime observation exist |
| `forge-guardian.timer` | Forge-only guard check every 60 seconds | Guard ran; it does not establish strategy profitability |
| `forge-continuity.timer` | Exports a current runtime continuity snapshot every 15 minutes | Snapshot exists; does not automatically create complete Hermes journals |
| `forge-alpaca-paper.timer` | Alpaca broker-paper lifecycle every 15 minutes | Paper management ran; not LIVE trading or income |
| `forge-alpaca-train.timer` | Alpaca curriculum/training three times daily | Training task ran; not a future profitable edge |
| `forge-equity-forward.timer` | Local forward-paper equity trials hourly | Simulator tick ran; not necessarily a fresh market session or fill |
| `forge-paper-trial-1h.service` | Read-only one-hour observation, five-minute sampling | Completed the requested observation successfully; did not create strategies or place orders |

At inspection, `forge.service`, `forge-hermes.service`, `forge-ops.service`, and `forge-eng.service` were running. The one-hour trial unit was inactive after successful completion, as expected. Always re-check these on rehydration because this is a point-in-time state.

### Hermes officer schedule and roles

The inspected service-user cron registry had 13 enabled roles. All were marked `reasoning_effort=high`, provider/model overrides were null (they inherit the service’s global model configuration), and `last_status` was `ok`. Intervals were: Governor, Alpha Inventor, Adversary, Critic, Scout, Execution and Treasury every 15 minutes; Doctor and Prediction every 30 minutes; Rail Hunter every 120 minutes; Architect and Intelligence every 180 minutes; Daily Report at 12:00 UTC. The scheduled registry lives in the Hermes service-user context; a bare CLI run under a different user/home can show a different history and must not be used to conclude that service crons are absent.

The intended role contracts and the most recent role evidence inspected are:

| Role | Intended job | Forensic state / material limitation |
|---|---|---|
| **Tess — Scout** | Find fresh market anomalies/opportunities and hand Quinn a sourced packet | Most recent inspected report was stale (around 00:47 UTC), and its $28.27 NAV basis was described as phantom/untrusted. Current afternoon cron `ok` rows did not link a fresh durable report. |
| **Quinn — Alpha Inventor** | Propose falsifiable, genuinely distinct custom strategies | Stale report (around 00:44 UTC) described a stable strategy set evaluated on a spot-only 60-symbol universe, excluding fee-viable stable pairs, with zero holdout trades. |
| **Reid — Execution** | Determine fill, fee, latency, liquidity and capacity realism | Stale report (around 00:42 UTC) lacked bid/queue evidence and reported zero true round trips. |
| **Ada — Critic** | Independently challenge claims and gate evidence | Stale report (around 00:46 UTC) said no sleeve met its `P(net>0) >= .90` criterion; it cited conflicting sample counts (350 versus 3), showing evidence lineage/counts need repair. |
| **Vale — Adversary** | Generate concrete counterexamples, tail-risk and correlation stress | No fresh role artifact was verified in the current observation. A generic caution is not a substitute for falsification evidence. |
| **Cyrus — Governor** | Rank use of shared capital by marginal risk-adjusted net value | Report around 00:57 UTC said $0 marginal new trading capital, zero executable rails and a stable-triangle idea tied to one contaminated calibration stream. No executable live round trips. |
| **Ellis — Treasury** | Reconcile cash, reserves, expenses, book truth and P&L | Report around 00:58 UTC was red-zone: no new fundable destination; NAV and P&L sources disagreed. |
| **Nolan — Prediction** | Analyze event-contract rules, probabilities, funding and settlement | Report around 00:56 UTC said Kalshi was non-executable/empty-market; other rail-readiness signals conflict. Require current venue and account evidence. |
| **Mira — Intelligence** | Improve prompt/model selection, inference attribution and research efficiency | Report around 00:45 UTC noted the Earnings Escalator directive emitter was outside the genome registry and could emit structurally impossible orders. Model cost attribution remains incomplete. |
| **Casey — Doctor** | Diagnose and repair system/data/account health | Report around 00:49 UTC gave health 86/100 and carried an old 45-second PositionVigil issue; the main-book interval was changed to 5 seconds earlier, but this does not prove all book checks are fixed. |
| **Rowan — Architect** | Design scalable, implementable engineering and evidence systems | Last inspected output (around October 8 10:00 UTC) had a 10/8 prompt variant rejected by a role-only gate. No fresh design artifact was tied to the current cron rows. |
| **Sloane — Rail Hunter** | Find new eligible earning rails and document API/economics/capacity | Last inspected output (around October 8 10:00 UTC) had a role/callsign mismatch (“Tess”), raising identity mapping and routing concerns. |
| **Luke — Ops / Founder interface** | Telegram reporting, natural-language delegation, progress and authorized closure | Service is active, but inspected records showed open work and missed-fire wake conditions; current end-to-end Telegram delivery proof was not collected. |

The scheduled `forge-daily-report` is a Hermes cron. Luke’s Telegram operations service is separate. Runtime ID/callsign mappings in `TEAM_ECONOMICS.md` and persisted reports do not always agree; verify the actual prompt, role identity, tool scope and output ID for every role rather than trusting a label.

### What agents appeared to be doing at the time

The scheduler was waking enabled prompts and marking dispatches `ok`. Forge’s deterministic loops were running and the strategy/research stores were changing. The one-hour record confirms candidate generation and evaluations. However, durable role reports and `agent_results` were stale relative to those wakes; around 6,654 directives were open versus 298 done and 343 cancelled in the inspected snapshot; several officers were in `HOLD_OPEN_COOLDOWN`, and `results_enforcer` logged `MISSED_FIRE_WAKE` for core roles. No model call was recorded after approximately 00:58 UTC despite the later cron status rows, and recent durable role artifacts were around 00:10–00:58. That gap needs a current re-check, but it demonstrates why `ok` cannot be equated with useful work.

Inference spend was concentrated: the prior-24-hour inspected call set contained 301 DeepSeek Flash records, approximately 4.776M input tokens (3.118M cached) and 1.116M output tokens; local recorded cost was about $0.619. One reconstruction using official off-peak rates was about $0.928 and an illustrative Haiku 5.5 reconstruction about $0.755 assuming prompts under 100K. The local ledger did not reconcile to the reconstruction (roughly $0.309 difference). 174 calls were attributed to Governor at about $0.437 local cost. Effort metadata was missing on 246 records. These are bounded database observations, not provider invoice totals or independently fetched account billing. Reconcile the same exact call IDs and UTC window to the provider before making a spend claim.

## 5. Why thousands of strategies have not produced the target

The records demonstrate candidate volume, not value. A DNA hash proves only that a serialized candidate differed. Many candidates may share the same mechanism, use the wrong venue/universe, reuse a contaminated or correlated data stream, have no independent holdout, or assume fills and costs that are not attainable. The one-hour sample makes the conversion gap concrete: new records and trial rows were produced, but no pass/promotion/sealed exam followed.

Confirmed or strongly evidenced blockers:

1. **Financial outcome truth is not reconciled.** Displayed NAV and reported net figures conflict; provider cost totals also differ from the local call ledger. Without a canonical net value by book and clock window, agents cannot reliably know what earned money.
2. **Research output is not durably joined to outcomes.** The experiment registry was empty in the trial snapshot, while role cron status could be `ok` without a fresh report/artifact. Research activity is difficult to attribute to an owner, decision, paper execution and resulting net outcome.
3. **Candidate generation is not the binding success measure.** The observed records produced zero promotions. Population caps and retired history are not themselves an earning engine. Retirement should preserve reusable lessons but not consume unbounded active evaluation.
4. **Some evidence is contaminated or mismatched.** Prior team reports identified stable-signal calibration issues, venue/universe mismatch, conflicting sample counts, and incomplete fee/fill proof. These are reasons to reject those claims until repaired.
5. **Execution and settlement evidence is thin.** There were no new main paper positions during the hour, zero true round trips in the cited execution report, and no settled live gains. Signals, quotes and paper edges are not filled positions.
6. **Rail readiness is inconsistent.** Sports repeatedly returned HTTP 401; Kalshi readiness reports disagreed; Alpaca forward data was stale and had no forward sessions. A broken rail should be repaired or quarantined, not counted as active opportunity.
7. **False PAPER close is a P0 accounting defect.** The GTC-USD case has a rejected exit (`NO_MARKET_DATA`) followed by generic paper reap/force-close behavior despite no exit price. The ledger has the original buy debit but no valid sale proceeds. This is an inventory/ledger inconsistency, not a valid fill, profit, or realized loss. It must be reconciled before trusting paper result or any promotion gate.
8. **Work is accumulating without closure.** Open directives greatly outnumber completed work, with missed-fire wake/cooldown events. A team that repeatedly analyzes the same unresolved issue can consume inference without producing a changed experiment or repair.
9. **CPU utilization is not an economic objective.** Recent sampled CPU was far below 70%, while RAM had about 3.3 GiB available. Forcing 70% CPU would create no edge and risks more low-quality candidate churn. Increase useful parallel evaluation only after each work unit has evidence, a cap, and an outcome.

The old retired-strategy archive is primarily disk-backed: earlier inspection found roughly 594 MB SQLite plus 82 MB JSON. Those files are not automatically resident in RAM in full. Keep history queryable and compressed/retained by policy, but make memory use explicit and avoid mass-loading retired rows. Historical archived counts do not mean that many strategies are simultaneously being tested.

## 6. Model choice and inference economics (as of this handoff)

This is a dated comparison, not a provider guarantee. The target was configured for DeepSeek Flash with high reasoning in the inspected workforce path; no model or credential was changed in this pass.

- Anthropic’s newest Haiku at the time was **Claude Haiku 5.5**, API ID `claude-haiku-5-5`, released October 7, 2026. “75% cheaper” was a comparison to Haiku 4.5, not to Forge’s DeepSeek bill. Official listed rates below 100K input tokens were $0.10/M input, $0.50/M output, $0.01/M cache read; over 100K, $0.50/M input and $2.50/M output. High effort is supported explicitly; the model defaults to medium effort. Use the current official [model page](https://platform.claude.com/docs/en/models/haiku-5-5/overview), [effort documentation](https://platform.claude.com/docs/en/build-with-claude/effort), and [release announcement](https://www.anthropic.com/claude-haiku-5-5) for current details.
- DeepSeek’s September 10 release note says V4.1 Flash is available and that requests to `deepseek-v4-pro` route to V4.1 Flash at Flash prices until V4.1-Pro launches. The separate pricing page still listed V4 Pro 0813, creating an alias/documentation ambiguity. Forge’s inspected setting was Flash/high, so do not claim it was receiving distinct V4.1-Pro weights. See [DeepSeek’s release note](https://api-docs.deepseek.com/news/news260910/), [official pricing](https://api-docs.deepseek.com/quick_start/pricing/), and [thinking-mode guide](https://api-docs.deepseek.com/guides/thinking_mode/).
- Anthropic’s release benchmarks show Haiku 5.5 ahead of GPT-6 Luna on selected reported evaluations, but results are vendor-selected and do not prove superior performance on Forge’s trading, execution, coding or risk tasks. No direct same-task Haiku 5.5 versus DeepSeek Flash evaluation was run here.
- Applying listed prices to the same observed token mix gives only an illustrative comparison: about $0.928 for DeepSeek off-peak versus about $0.755 for Haiku if all prompts fit under 100K and the tokenization/cache assumptions match. That is roughly 19% lower, not 75%. Haiku’s cache-read price differs, long-context pricing is higher, and different token counts, latency, retries, or reasoning behavior can erase the apparent saving. Forge’s local $0.619 call ledger does not reconcile to that calculation.
- Provider reliability cannot be ranked from this snapshot. Haiku had been released two days earlier; provider incident windows and public availability percentages are not comparable enough to support a reliability winner. See the provider [Anthropic status](https://status.claude.com/) and [DeepSeek status](https://status.deepseek.com/) pages for dated provider evidence.

Recommendation: do not switch the whole team based on a headline or benchmark. First restore call-level cost/outcome attribution. Then run a bounded paired evaluation on identical fixed tasks with explicit high effort: tool/schema success, decision quality, useful durable artifacts, downstream paper result, latency, retries and actual cost. Keep separate deterministic tasks out of LLM workloads. Only adopt a new default after Forge-specific evidence supports it and rollback is ready.

Alpaca training caveat: official paper trading omits or simplifies market impact, queue position, latency/slippage and some fees, and can simulate fills beyond displayed NBBO size ([paper-trading limitations](https://docs.alpaca.markets/us/docs/paper-trading)). Its 24/5 session expands eligible hours but is not 24/7 and does not make equities trade around the clock ([24/5 API docs](https://docs.alpaca.markets/us/docs/245-trading-for-trading-api)). Commission-free trading can still have pass-through fees ([disclosures](https://alpaca.markets/disclosures)). A 24/7 portfolio objective therefore requires a mix of actually available rails and truthful market-hour coverage.

## 7. Recommended takeover sequence

These are proposed actions for the next implementation session; this handoff does not claim they are deployed. The next agent should pursue them aggressively in dependency order and continue independent work where a dependency blocks one rail.

### P0 — make “net” and “closed” true

1. Reconcile each real wallet/account, paper book, shadow book, external deposit/withdrawal, unsettled fill, fee, data bill, inference bill and compute bill into one sourced ledger. Show LIVE realized net separately from PAPER and forecast. Keep UNKNOWN explicit where reconciliation fails.
2. Repair the GTC-USD false-close path. A rejected order or missing market price must not create a close or proceeds. Reconcile quantity, order, fill and inventory without inventing a fill; document any explicit write-off.
3. Recompute 1h, 24h and 7d earnings from reconciled records with coverage, worst period, drawdown, open risk, pending settlements and cost completeness. Keep the founder’s <$0.10/hour history labelled as reported pending reconciliation.

### P1 — make the team produce a traceable result

4. Every Hermes dispatch must create a receipt containing run ID, actual role/prompt identity, model/provider/effort, token counts/cost, question, evidence version, artifact/report ID, decision or experiment created, owner, deadline, next wake, and later outcome. Missing output is FAILED/BLOCKED, never successful work merely because dispatch succeeded.
5. Close or cancel aged open directives with evidence and deduplicate by objective/evidence version. Resolve `MISSED_FIRE_WAKE`, `HOLD_OPEN_COOLDOWN`, role/callsign drift and scheduler-to-report linkage. Keep work running on independent rails while one task waits.
6. Replace claims-only role grades with contribution classes (EARNED, VALIDATED, LEARNED, IMPLEMENTED, UNPRODUCTIVE) and prevent multiple roles from claiming the same income. Only settled/reconciled LIVE net counts as EARNED.

### P2 — establish a bespoke, bounded strategy factory

7. Create one cross-portfolio experiment schema. Each experiment declares mechanism, venue, source, freshness, hypothesis, regime, baseline, signal horizon, fee/fill/latency model, correlation cluster, capital-hours, risk/loss stop, sample size, holdout, cost ceiling, cutoff and outcome ID.
8. Separate candidate discovery from independent evaluation and sealed validation. Novelty means a materially different causal/mechanical hypothesis, not merely a unique DNA serialization. Require a valid source and minimum economic plausibility before using scarce paid inference or parallel paper slots.
9. Run concurrent but bounded challengers across available rails; compare every challenger to simple baselines and incumbents. Automatically retain, mutate, pause or retire using preregistered evidence. Preserve failed lessons in disk-backed history; do not let retirement count masquerade as active tests.
10. Treat a research result as useful only when it changes a decision, produces an independently testable mechanism, or prevents a measured loss. Route each survivor to forward PAPER with realistic venue economics. Continue proposing new algorithms at a steady cadence without exploding the population.

### P3 — fix rails, allocate scarce capital, then scale

11. Repair the sports score authentication/configuration or quarantine it. For each rail, publish current permissions, funding, hours, market/source freshness, executable universe, costs, fill/settlement path and kill conditions. Reconcile competing Kalshi readiness messages. Require fresh Alpaca data before counting sessions.
12. Use an allocator that accounts for shared capital, margin, correlation, settlement lockup, liquidity, marginal net value and reserve. Scale paper allocation only after independently observed forward evidence and robustness; scale real capital only under existing explicit live policy and owner authorization.
13. Establish a controlled paper-to-live promotion standard: multiple independent forward periods, lower-confidence-bound/net expectancy after all attributable costs, realistic fill and stress testing, reconciliation, operational health, rollback/kill path, and explicit authorized live settings. The $0.50/hour paper milestone is a necessary founder milestone, not by itself proof that live trading is safe or profitable.

### P4 — intelligence and compute earn their spend

14. Attribute each model and Modal dollar to an experiment/decision and report cost per validated learning and per settled net dollar. Keep the Modal cap and launch only a named, bounded experiment with expected value, stop condition and receipt.
15. Use deterministic code for routine scheduling, data freshness, policy checks, accounting, health and risk. Use high reasoning when it can change a consequential decision, devise a genuinely new mechanism, or resolve ambiguity worth its cost. Coalesce duplicate team analysis around shared evidence packets.
16. Use spare CPU for admitted valid tests, data processing, and independent replication. Do not force a 70% CPU target or use idle compute to manufacture strategy counts.

## 8. Continuity and rehydration procedure

The command center is the SSH administration workstation only. Forge production and source changes belong on the dedicated host in `/srv/forge`. The provisioned SSH key stays at its documented local path; do not copy or print its private contents, and never place API credentials in continuity documents.

On takeover:

1. Read `/srv/forge/AGENTS.md` and the continuity `README.md`, then `FOUNDER_INTENT.md`, `CURRENT_STATE.md`, `WORK_QUEUE.md`, `KNOWN_ISSUES.md`, `SYSTEM_MAP.md`, `LUKE_CONTRACT.md`, the latest report and session journal.
2. Reconfirm hostname, root, target Git status, service state, mode/live flags, ledger, source freshness, role registry and evidence window. Preserve target dirty/untracked work. Do not use the command-center historical checkout as a deployment source.
3. Before implementation, create a unique session journal with a file/behavior scope, baseline and planned evidence. Keep implementation, test, deploy, runtime observation and financial reconciliation as separate states. Do not mark done because a note exists or a timer ran.
4. For financial statements, cite the exact paper/live book and UTC window. Reconcile cash flows, fees, fills and external costs. Treat report/status fields as hypotheses until corroborated. Never call simulated gains earnings.
5. At each meaningful checkpoint, update the session, `CURRENT_STATE.md`, `WORK_QUEUE.md` and append-only `CHANGELOG.md`. Leave a precise next action, owner, evidence required and blockers with recovery actions.
6. Luke’s Telegram tools are private and authorization constrained. Use only explicitly authorized external actions; a coding/continuity note does not grant transfer, live-order or messaging authority.

## 9. Known evidence gaps and confidence

**High confidence:** target/host boundary; service/process topology at observation time; exact one-hour interval and final summary; zero new main-paper positions, zero live positions/orders, zero settled live income in the observation; zero observed validation/promotion/sealed pass; sports feed HTTP 401; trial-only simulated status.

**Moderate confidence:** role intent and cron cadence from service registry and team contract; open-work and stale-report counts from database snapshots; recorded call/token counts and local cost. These are point-in-time database values and need current refresh.

**Low / unresolved:** true account NAV, provider-invoiced inference cost, actual compute bill attribution, historical hourly net, live rail readiness, current independent strategy expectancy, exact reasons every role wake lacked a new artifact, and whether the stale-data/401 conditions have since cleared.

No claim in this document proves positive future returns, safe live readiness, or that Forge is at maximum potential. The practical finding is that it has substantial machinery and ambition but the validated strategy-to-settlement-to-net loop is not closing reliably. The next agent’s job is to close that loop while actively inventing and testing economically credible new mechanisms.

## 10. Source artifacts

- Target one-hour run: `/srv/forge/var/research/paper_trial_1h/20261009T150017Z/run.json`, `snapshots.jsonl`, and `final.json`.
- Target Hermes registry: `/srv/forge/runtime/hermes/home/cron/jobs.json` (service-user context; do not expose its environment or secrets).
- Team contract and queue: `/srv/forge/docs/continuity/TEAM_ECONOMICS.md`, `WORK_QUEUE.md`, `KNOWN_ISSUES.md`.
- Architecture and rehydration: `/srv/forge/docs/continuity/SYSTEM_MAP.md`, `REHYDRATE.md`, and `/srv/forge/AGENTS.md`.
- Alpaca official docs: [paper trading](https://docs.alpaca.markets/us/docs/paper-trading), [24/5 trading](https://docs.alpaca.markets/us/docs/245-trading-for-trading-api), [disclosures](https://alpaca.markets/disclosures).
- Model documentation: official Anthropic and DeepSeek links in §6.

---

**Passover instruction:** Rehydrate from the live target, verify what changed since this dated report, then take the highest-value open item and move it to reviewable evidence. Keep the $0.50/hour first milestone and $1/hour whole-portfolio ambition visible in every economic decision. Pursue them boldly; report the truth without dilution.
