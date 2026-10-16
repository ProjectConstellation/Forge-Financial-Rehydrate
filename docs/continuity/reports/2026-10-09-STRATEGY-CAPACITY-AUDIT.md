# Strategy quality, throughput, archive and resource audit

Observed: 2026-10-09 14:21 UTC. Production Forge only. No strategy, trading, memory, or service configuration changed for this audit. The user-requested PAPER observation window `20261009T141137Z` remains active through 18:11:37 UTC.

## Corrected strategy-throughput counts

An earlier continuity paragraph said “2,262 strategy records in the prior four hours.” That was wrong: its SQLite filter compared ISO timestamps containing `T` with SQLite's `datetime()` strings containing a space, so the count was effectively for the current UTC date. At 14:19 UTC the corrected values were **2,274 records / 2,122 distinct DNA since UTC midnight**, and **about 670 records / 644 DNA in the rolling four-hour window**. This correction is recorded explicitly; do not repeat the 2,262 number as a four-hour count.

A different, more useful measure is the research-trial ledger: at about 14:21 UTC, the rolling four-hour window held **984 adjudicated trial rows across 442 unique genome IDs**, with **0 passed and 0 promoted**. The average holdout count among rows with a count was about 13; common rejection reasons included holdout sample size below 30, zero holdout trades, weak alpha versus market drift, nonpositive selection mean, and robustness/fold checks. Many rows are the same genome evaluated across intervals; rows are not independent strategies. Around 451 unique genome IDs were observed in a nearby query; timestamps naturally shifted as the rolling window advanced.

The four-hour live observation window had, at its first completed sample (14:16:44 UTC), **9 newly registered strategies (9 unique DNA) and 24 research-trial rows (24 unique genome IDs); 0 had passed or been promoted; no new Coinbase paper positions had opened**. It had fresh Kalshi shadow signals and one Alpaca broker-paper position already open before the run. Continue measuring; these early counts do not describe the full trial.

## What is being evaluated, and what is actually running

At the 14:18–14:21 read, the strategy registry contained:

| Population | Count | Meaning in this PAPER runtime |
|---|---:|---|
| EXPERIMENTAL | 240 | Unique candidate genomes at the configured active research-population cap; not 240 positions or 240 strategies independently trading |
| SHADOW | 62 | Forward-scored on fresh market data where available; hypothetical paper evidence, not LIVE capital |
| CHALLENGER | 12 | Candidates that passed some prior validation and compete for a simulated allocation; Forge's global mode is PAPER |
| RETIRED | 48,059 | Historical genomes/evidence; not active; lifetime archive, not current test capacity |

In the Coinbase evolution path, one bounded local search worker runs a sequential evolutionary batch per interval (the search code has a time budget and evaluates candidate genomes sequentially; top finalists are then adjudicated). The separate forward reviewer was producing repeated metrics for **74 distinct SHADOW/CHALLENGER/PRODUCTION strategies** during the rolling four hours (8,806 metric rows), not 8,806 separate realized trades. At the observation snapshot, no core Coinbase PAPER position was open. The equity broker-paper engine was managing one QQQ simulated position; its local forward simulator had two ready hypotheses with zero completed sessions and the Oct 8 last completed daily bar (expected while the Oct 9 market session was still open; the local simulator advances only on completed daily bars). Kalshi produced shadow signals, while live order insertion remained blocked in PAPER mode. Sports odds/scoring requests were returning HTTP 401 and its 12 open paper bets could not be treated as fresh resolved evidence.

The algorithm is not purely random: selection, holdout, robustness, fold consistency, a sealed exam, and diversity gates exist. However, generation uses stochastic mutation/crossover and diversification; many outputs are archived despite no gate passes. Research trial rows are not being converted into returns or income. Therefore the current bottleneck is not a shortage of strategy records. It is the economic hypothesis, relevant data/sample, executable edge and economics after cost, plus conversion of qualifying forward evidence into a useful PAPER allocation. LIVE algorithmic trading remains disabled, so these simulations cannot themselves generate customer/exchange income.

## Retired archive and memory

The SQLite database measured **about 564 MiB on disk** (about 5 MiB WAL). Raw `genome` JSON for retired rows measured about **82 MiB**; this is a component, not the full database. Registry call-site review found runtime consumers enumerate explicit active populations; no unfiltered `reg.list()` call was found. Thus 48,059 retired rows are not all deserialized into one in-memory Python population. SQLite page cache, filesystem cache and individual queries can still use RAM, but record count alone does not imply that 48k genomes occupy RAM.

At the same read, Forge's cgroup used **about 4.16 GiB of a 5.47 GiB cap**, with a 4.52 GiB prior peak; main process RSS was about 1.20 GiB. The four-vCPU host had about 2.7 GiB available system memory. A five-second cgroup sample was about **1.17 CPU cores, 29% of total four-vCPU capacity**. Forge is capped at 3 CPU cores. The trial recorder itself used under 20 MiB and is read-only.

Do not VACUUM, rewrite/compress the live SQLite database, or migrate all archive rows during the active PAPER observation: SQLite is a live WAL database and the run needs a stable baseline. A future lossless cold archive can keep an indexed active SQL table plus a compact ID/hash/lineage/verdict index and checksummed zstd JSONL shards of complete retired evidence; expose a bounded lookup/read API usable by Luke and coding agents. First measure storage growth and verify backups/restore and lookup parity. The present 82 MiB of retired genome JSON does not justify a risky live rewrite by itself.

## Founder-directed strategy admission criteria for next upgrade

1. **Require an economic thesis before mutation/admission.** Each proposed strategy must name one rail, market/universe, inefficiency/event, causal signal, entry/exit and holding horizon, forecast, market/session assumptions, data source and freshness, fee/slippage/fill/settlement model, and a falsifiable kill condition. Tie it to a diagnosed weakness or an independently observed opportunity. A parameter/feature mutation without a changed, reviewable thesis is not a new strategy for allocation.
2. **Novelty check before expensive inference/backtests.** Deduplicate by exact DNA and by economic hypothesis plus near-equivalent features/parameters/market; record why a rejected/failed idea differs before retrying it. Candidate generation should be guided by which gate failed (e.g. no fills → improve signal frequency/data coverage; fee failure → execution economics; regime failure → conditional model), not spray mutations. Start with a small bounded funnel, and only retain full strategy rows for qualifying candidates; keep compact trial outcomes for rejected candidates.
3. **Use same-window counterfactuals.** Compare each candidate against (a) no trade/idle cash, (b) a simple rail-specific benchmark, and (c) the incumbent in the same market/regime/time window. Measure net of all explicit fees, spread, slippage, partial fills, queue position and costs; count overlapping signals/events as one correlated evidence cluster.
4. **Chronological validation with multiple-test correction.** Separate training, holdout and sealed data; require a sufficient independent sample and at least two non-overlapping forward windows. Preserve the existing promotion gates unless an audit justifies recalibration. Do not lower the 30-trade holdout threshold merely to produce promotions; use an instrument-appropriate independent-event sample, calibrated confidence, and a written exception only where lower frequency makes that threshold statistically inappropriate.
5. **Small, bounded active challenger bench by rail.** Keep profitable incumbents while evidence supports them; reserve a defined small number of concurrent forward-paper challengers per rail and risk budget. Proposed starting envelope: at most 3 forward challengers per rail and 12 total, plus the incumbents. Historical search candidates stay in the trial ledger until their screen passes. A new candidate displaces a challenger only when it is more novel or has stronger risk-adjusted evidence; it never displaces a sound incumbent from a single noisy win.
6. **Promotion requires executable net advantage.** Require positive conservative lower-bound net expectancy after costs, improvement over both baseline and incumbent, acceptable drawdown/turnover/capacity/correlation, fresh market data, and enough independent forward evidence. Promotion to PAPER is automatic only after these gates; promotion to LIVE is never automatic from PAPER.
7. **Risk and reallocation operate at separate levels.** Enforce immediate instrument/order hard stops and stale-quote guards. Pause/hibernate a strategy when calibrated deterioration criteria are breached, not on one small red tick. Keep protective exits for open positions. Reallocate only reconciled free simulated capital after closing/settling as appropriate; the next best strategy also must pass eligibility and risk gates.
8. **Measure learning, not CPU occupancy.** Track cost/CPU-seconds/memory per adjudicated unique thesis, per validated forward paper fill, and per settled positive net result. Current 0/442 unique research genomes passing in four hours should trigger gate/funnel diagnosis, not a more aggressive spawn rate. Use spare CPU for independent validation and better data only when quality gates, memory headroom and inference/compute budget are healthy.

## CPU target assessment

A fixed 70% of four vCPUs means maintaining about 2.8 CPU cores busy even when markets are closed, feeds fail, no qualified hypothesis exists, or Forge is already near its memory ceiling. That would repeat the activity-without-income failure. Preserve a reserve for execution, reconciliation, OS and other agents. Backtests can use a bounded low-priority budget when there is an evidence-backed queue and memory headroom; tune utilization from useful validated outcomes per dollar/CPU-hour, not a hard idle-time floor. Modal must be admitted per bounded experiment with expected information value and strict cost limit.

## Position/strategy loss response already present (current behavior)

Current protections are partial and thresholded: Position Vigil scans about every 45 seconds, flags a paper position at roughly −4% marked loss or six hours held, and queues an exit/strategy hibernation; Strategy Analyst runs about every 60 seconds and uses CUSUM, requiring at least three closed trades before a failing verdict; Edge Decay runs about every five minutes and requires sequential adverse evidence; Capital Reallocator runs on a slower periodic loop. Alpaca's broker-paper adapter uses the paper venue and a per-trial loss/position cap. This is not “exit at the first negative mark,” nor is reallocation instantaneous. The next upgrade should unify price freshness, position hard stops, strategy expectancy decay and allocation into event-driven gates with per-rail acknowledgements and audit traces. A single losing tick cannot be a reliable forecast; premature exits/churn can destroy net returns. Define immediate action for hard risk or invalidated edge, then model short-term losses with calibrated variance/confidence.

## Next work (do not alter the active trial baseline)

- Finish the 4-hour PAPER evidence window and compare it to the captured baseline; preserve results and configuration version.
- Add objective/hypothesis/near-duplicate admission gates and keep failed-candidate evidence compact; stop filling the active registry with unpromotable random variants.
- Explain the zero-pass gate outcome by interval/family and repair data/sample mismatch; keep strict out-of-sample discipline.
- Add a bounded, rail-specific forward bench and correct the sports 401 / equity stale-data blockers.
- Measure true compute/inference cost per validated unique thesis and per paper outcome; do not target 70% CPU continuously.
- Add the archive export only after tested backup/restore and exact lookup parity; current retired rows are disk-first and not all read into RAM.
- Upgrade position-risk/event-driven redeployment only after documenting exact latency, loss limit, stale-feed fallback, and per-rail failure behavior.
