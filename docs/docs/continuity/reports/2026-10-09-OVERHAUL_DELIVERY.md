# Imagine Forge: takeover and intelligence overhaul

Recorded 2026-10-09 UTC. Scope: dedicated Forge server, `/srv/forge`. Other command-center projects were not modified. The earlier requested Pi configuration is complete independently: Pi 1.1.0, DeepSeek V4 Pro/high by default, verified by a real response and lowercase `pi` launch.

## Independent judgment

Forge is not yet self-sufficient, profitable, or at its maximum useful potential. The immediate problem was that research output, paper estimates, wallet changes and income were being confused while paid work lacked enforceable economic accountability. Extra enthusiasm or larger models cannot establish a tradable edge. The overhaul makes spending bounded, results visible, and selected paper experiments automatic. It does not demonstrate a profitable investment strategy.

The combined target remains at least $1/hour, with $0.50/hour as the progress floor. $1/hour means $24/day or $720 over 30 days **after Forge operating costs**. Against the observed $28.27 real treasury, that is approximately 85% of capital each day; present evidence does not support that return. Performance should be judged by rolling realized net, hourly coverage, drawdown, independent evidence and capacity. No system can guarantee a profitable outcome in every hour.

## Observed financial position

At approximately 01:17 UTC, the canonical last-24-hour endpoint reported:

| Metric | Observed amount / state |
|---|---|
| Settled LIVE investment income | $0 |
| Recorded/estimated inference cost | $0.644908 |
| Recorded/estimated compute cost | $8.221923 |
| Net after those Forge operating costs | **−$8.866831** |
| Real Coinbase treasury visibility | $28.27 |
| Kalshi funding at inspection | $0 |
| Alpaca research bankroll | $50 simulated; broker toy equity ignored |
| Modal month estimate | Approximately $25.54 of the $30 cap |
| Shared DeepSeek provider balance at inspection | Approximately $0.13 |
| Independent broker reconciliation | UNKNOWN / still required |
| Trading authority | PAPER, global RUNNING; LIVE flag false |

Costs are usage/resource estimates, not reconciled provider invoices. The historical inference estimate includes paid source usage missing from the old operating ledger without rewriting old ledger entries. Wallet movement, deposits, unrealized changes and simulated returns do not qualify as income. The balance is shared: it cannot be attributed exclusively to Forge.

The provider balance and already-incurred spending currently fail the autonomous inference admission budget. A real request to the new gateway was correctly rejected with HTTP 402 before paid inference. The normal source-usage response path was verified with mocked provider HTTP, including streaming transport. Deterministic local market monitoring and research continue without LLM calls. The separate owner/engineering profiles still use their existing direct provider configuration and are not all governed by this workforce gateway.

## What was implemented and deployed

1. **Common economic truth.** Treasury/performance/profit velocity use settled live outcomes less all recorded Forge operating costs. Paper capital and paper results are separate. Real account visibility remains available in PAPER mode. Paper positions no longer reduce real cash. Missing independent reconciliation is explicit.
2. **Durable paid-work admission.** Atomic reservations prevent concurrent overspending; failed requests with unknown charges retain their bound. Fresh provider balance is required. No-income operation preserves a seven-day inference runway. Verified positive live net and cost coverage can increase throughput and reinvest a bounded share. Deposits and paper profits do not unlock it. Reservations use peak pricing across time windows.
3. **Hermes workforce gateway.** Research/ops workforce calls use the authenticated local DeepSeek proxy, with per-role source usage and duplicate usage reporting suppressed. Flash/high remains the economical routine model; Pro/high is available for justified deeper work. Paid fallback providers and unmetered external compute do not bypass admission.
4. **Modal experiment discipline.** Paid jobs require a current explicit experiment, decision, evidence version, worst-case cost and abort condition. The $30 monthly cap remains. Launches reserve cost before dispatch; failures remain accountable. Artifacts and consumption receipts are retained. Identical in-run DNA evaluations are cached. Generic cadence, urgency or a low-income alert cannot launch another paid burst.
5. **Evidence and workflow integrity.** Contaminated strategy claims remain ineligible even after a timer expires. Workflow advance validates owner, stage and payload before mutation, transactionally. Self-reported forecast deltas no longer become measured earnings. Reports and diagnostic prose cannot earn an EARNER classification. Risk JSON serialization is repaired; workforce counts use actual reports and overlapping wake policies are coalesced.
6. **Results for Luke and the team.** Authenticated research/results, economic and capability endpoints expose calls by role, validation receipts, paid jobs, outstanding reservations, artifacts, current trials and blockers. Role contracts specify actionable hypotheses, owners, deadlines, cost limits, falsification and measured outcomes. Continuity exports run every 15 minutes.
7. **Alpaca training.** Official documentation is recorded in the curriculum. Explicit paper hosts, stable client order IDs, legal quantities/types and global trading authority are checked. Direct LIVE submission remains unavailable until full deterministic execution integration. Blind SPY drills were removed. Historical research uses completed recent daily bars with next-open execution and costs. The corrected recent-data example produced three hypothetical trades and about +$0.359637, with **zero earned cash** and insufficient independent evidence. This is a changed data window, not an algorithm improvement or profit proof.
8. **Automatic equity research-to-trial loop.** The hourly `forge-equity-forward.timer` runs a persistent local simulation with no inference tokens. Two $10 trial slots share the capped $50 research bankroll. Initial mechanisms are relative momentum and dip reversion; trend following is the next available mechanism. New registration excludes all historical bars through its registration date. Signals use prior completed sessions; modeled entry/exit uses next-session opens, a five-session hold, 20bps round-trip cost, a close-triggered stop and trial/shared loss stops. At 20 future sessions, positive net above the equal-capital buy-and-hold baseline with at least three closed trades retains the mechanism for another future block; failed or insufficient trials rotate automatically. It does not need a human to trigger the next paper hypothesis. STOPPED/unknown authority blocks progression and new registration effects; paused dates are not backfilled as active trials. These are local forward simulations, **not actual Alpaca broker fills**. Gaps can exceed the simulated stop budget. No automatic LIVE promotion exists.
9. **Kalshi authority.** The separate live path now requires Forge LIVE mode, the explicit live flag and explicit Kalshi enablement. PAPER or SHADOW cannot submit through that path. Existing paper prediction observation and settlement loops remain separate.

## Where research's results are visible

- Luke's `ops_research_results` and `/api/v1/research/results` show costs, artifacts, decisions and current forward trials.
- `/srv/forge/var/alpaca_forward_trials.json`: complete persistent trial contracts, modeled trades, net results, review history and automatic next hypothesis.
- `/srv/forge/var/alpaca_research.json`: latest historical curriculum evidence and limitations.
- `/srv/forge/var/research/modal/`: paid job artifacts; `compute_jobs`, `research_trials` and `spend_reservations` preserve structured accountability.
- `/srv/forge/docs/continuity/runtime/latest.json`: scheduled metadata snapshot; full engineering details are in the session journals, reports and deployment receipt.

Previous-day observations included thousands of candidate receipts and hundreds of validation passes, but only three promoted candidate receipts and no established live income. Candidate counts, validation passes and promotion are separate from earnings. The latest local cycle evaluated 2,626 genomes and returned 12 candidates; its receipt says forward evidence is pending. These numbers expose research throughput; they do not justify further spending by themselves.

## Team assessment and operating contract

The detailed role-by-role assessment is `2026-10-09-TEAM_ANALYSIS.md` in the continuity reports. The team should operate as one economic pipeline:

Tess finds a fresh feasible anomaly → Quinn defines an executable falsifiable mechanism → Ada independently validates it → Vale identifies concrete failure conditions → Cyrus selects within shared exposure and capital constraints → Reid preserves the edge through orders and exits → Ellis reconciles actual results → Luke reports closure and assigns the next action. Nolan owns prediction calibration and settlement evidence. Doctor, Architect, Intelligence, Rail Hunter and engineering should unlock specific decisions or repairs and supply acceptance receipts.

These changes improve incentives through measurable contracts, not claims that prompting makes agents money-motivated. Research has useful intermediate outcomes—learning, repair, validation, rejection—but only settled reconciled real net can demonstrate self-funding. Persistent deterministic checks handle routine 24/7 monitoring; costly reasoning wakes only when evidence or an actionable decision changes.

## Verification

- Full isolated remote suite: **128 passed**, one warning. Includes atomic concurrent reservations, uncertain charges, peak cost bounds, real/paper accounting, role/stage validation, contamination, risk serialization, Alpaca constraints, global-stop handling, HTTP auth/JSON/SSE and automatic future-trial retention/rotation/idempotency.
- Production health, risk, performance, workforce, capabilities and research/results endpoints returned HTTP 200.
- Production forward service ran successfully twice; two future-only trials registered, no historical fills created, no earned dollars claimed. This is startup verification, not a completed forward trial.
- Forge, Hermes, ops, engineering, guardian/deployer timers, continuity timer and forward timer were active after deployment. Training service completed successfully. No LIVE order, transfer, funding action or Telegram message was initiated.
- Deployment guarded current file hashes and preserved original files plus an online database backup. Existing dirty prompts/Alpaca work were retained. No broad git reset, staging or commit was performed.

## Remaining work and priorities

1. **Observe actual future outcomes.** The new trial loop needs future market sessions; the trading engine needs 24-hour and seven-day acceptance observations. Automatically rotating a fixed library is not unrestricted invention of arbitrary algorithms. New mechanisms must become typed executable strategies with independent tests; free-form reports cannot autoexecute code.
2. **Complete Alpaca broker-paper integration.** Build an isolated broker-paper adapter using Forge's deterministic risk, order, exit, partial-fill and reconciliation lifecycle before brokerage execution or LIVE readiness. Current trial fills are modeled daily-bar fills, not measured execution quality.
3. **Reconcile external truth.** Provider invoices, independently sourced venue cash/fills/settlements and historical attribution remain incomplete. Readiness must remain unavailable where these facts are unknown.
4. **Improve mechanism quality.** Triangle/conservation assumptions need corrected complete-leg fees, executable price and fill evidence before rehabilitation. Contaminated memory cannot become clean merely with age. Kalshi needs independently calibrated event clusters, current per-market fees and verified settlement timing. Odds API authentication is still a known blocker.
5. **Extend automatic experimentation.** The equity loop is a bounded mechanism library; existing crypto evolution and prediction simulations run separately. A unified typed experiment registry across all portfolios, automatic evidence-driven new-mechanism generation and an admitted Modal proposal/approval tool are still needed. Expensive retries must be justified by new information, not merely losing money.
6. **Finish economic allocation and ops closure.** Shared portfolio correlation, cash locks, settlement timing, marginal net per capital-hour and capacity need measured evidence. Historical workflow backlogs need provenance review and concrete closure. Workflow advance is protected; concurrent workflow creation and wake-after-commit deserve further hardening. The current workforce grade remains THEATER_RISK rather than a fabricated improvement.
7. **Scale from evidence.** Budgets already scale from verified real net/cost coverage. Increase capacity and models only where independent results support the incremental expense; keep the owner's $30 Modal envelope. Paper profit and newly deposited capital are not evidence of profitable intelligence.

## Continuity and rollback

Say: **“Go rehydrate on `/srv/forge/docs/continuity/REHYDRATE.md`, then read CURRENT_STATE, WORK_QUEUE, the latest session and deployment receipt.”**

Original source backups and the deployment receipt are under `/srv/forge/.engineering/20261009-overhaul/`. The staged rollback script checks current hashes, restores code/configuration and preserves new financial rows and the additive migration. Before a rollback of the automatic equity addition, disable `forge-equity-forward.timer` and stop its service; its systemd units require explicit removal or restoration. Never roll back the entire database over newer fills. Reverting the overhaul also reintroduces the diagnosed accounting and spending defects, so prefer narrow fixes.
