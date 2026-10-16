# Four-hour PAPER trial — start record and strategy-count interpretation

**Run ID:** `20261009T141137Z`  
**Window:** 2026-10-09 14:11:37 UTC through 18:11:37 UTC.  
**Status at start:** evidence recorder active as `forge-paper-trial-4h.service`; five-minute snapshots in `/srv/forge/var/research/paper_trial_4h/20261009T141137Z/`. The runner writes `final.json` and `final.md` after four hours. It samples, but does not alter, the existing paper loops.

## What the strategy counts actually mean

- **240 EXPERIMENTAL**: unique DNA genomes in Forge's current experimental population, which is at the configured 240-strategy cap. They are research candidates; this does not mean 240 have active paper positions or positive results.
- **62 SHADOW**: unique DNA strategies observing current market data and accumulating forward evidence. These are hypothetical/simulated decisions in the current PAPER mode, not real-money orders.
- **12 CHALLENGER**: unique DNA candidates that passed earlier validation and are competing for promotion. Despite the registry's generic state description, the server is in PAPER mode; these do not have permission to place live capital.
- **48,052 RETIRED** at run start: retained historical records, not running strategies. Most were unique DNA, but this archive is large and should not be interpreted as a live portfolio.
- At run start, exactly **12** fresh research-trial rows had been recorded since the launch point, with **0** passing validation, **0** promoted and **0** sealed. These must not be called earnings or forward trade wins.

**Correction logged 2026-10-09 14:19 UTC:** an earlier SQL window filter mixed ISO `T` timestamps with SQLite `datetime()` space timestamps. The quoted 2,262 records / 2,110 hashes were effectively a UTC-day count, not the prior four hours. Corrected at 14:19: 2,274 records / 2,122 DNA since UTC midnight; about 670 records / 644 distinct DNA in the rolling four hours. In the rolling four hours, the adjudicated research ledger contained about 984 rows / 442 unique genome IDs, with zero passing validation and zero promoted. Do not repeat the erroneous four-hour count. Reasons and implications are analyzed in `reports/2026-10-09-STRATEGY-CAPACITY-AUDIT.md`. The active population cap prevents a larger live candidate bench, while persistent lifetime turnover remains a concern.

## Paper-only safeguards and run coverage

- Forge systemd service explicitly sets `FORGE_MODE=PAPER`; Coinbase strategy fills are recorded in `book='paper'`. At run start, no LIVE-book strategy position rows were present.
- Alpaca broker service uses `AlpacaClient(paper=True)`, reports `ALPACA_BROKER_PAPER`, `authority=RUNNING`, `live_eligible=false`, and a `PAPER_ONLY` $50 simulated bankroll. The existing simulated QQQ position is managed by the paper adapter and reconciles cleanly; it is not the broker's $100,000 demo equity.
- Kalshi live path explicitly reported `Forge PAPER/SHADOW or LIVE authorization disabled`, and the `kalshi_live_orders` table was empty at start. Kalshi shadow signals continue to be observed.
- Run recorder covers Coinbase paper strategy/research, Kalshi shadow, Alpaca paper broker and local equity forward trials, plus sports paper status. It does not open trades or increase simulated risk.
- Sports desk's latest snapshot found 44 candidate edges, 12 open virtual bets and no new placements/settlements due its open-position cap. The Forge journal also showed HTTP 401 for sports score/odds requests. Keep this lane in the report as feed-blocked/degraded unless fresh successful responses and settlements are observed; don't accept its stale cached candidates as validated tests.
- Local Alpaca forward simulator has relative-momentum and dip-reversion trials; they had zero completed sessions and last completed daily bars dated 2026-10-08, expected while the Oct 9 market session was open. The live broker-paper runner currently tests one relative-momentum QQQ hypothesis while managing an open simulated position. The four-hour run may end without enough stock-market sessions to judge these hypotheses; record that as insufficient duration/data, not a win or loss.

## Run protocol and interpretation

The existing 24/7 Forge research/execution/evidence loops remain in control. This trial adds read-only five-minute sampling and a four-hour stop for the evidence window, not a shutdown or reset of Forge. Do not force a trade to fill a quota. Record new distinct candidates, validation/promotion counts, forward shadow decisions, fills, settlements, net simulated outcomes after costs, exposure, data freshness and errors by rail. Report any market-closed/no-signal interval plainly. Paper P&L is not income; actual income remains based only on independently reconciled LIVE settlement.

At finish, analyze the run against its start snapshot. Review at least the incumbents/SHADOW/CHALLENGER groups, unique candidate DNA, evidence and rail feed status. Next build should cap admission/turnover, rank challengers against the current deployed incumbent, keep the strongest incumbent running, and retain concise failed-hypothesis evidence rather than equating archive size with learning.
