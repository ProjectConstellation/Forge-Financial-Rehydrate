# Forge equities and event-market curriculum

Verified 2026-10-09 UTC. Research instructions; permission to trade remains the deterministic money path. Refresh provider documentation and account capabilities before changing eligibility or fees.

## Alpaca: account and session literacy

Start with account, assets, clock, calendar, open orders and positions. The brokerage's paper equity is simulation capacity, not Forge's bankroll. Use canonical treasury truth to choose the configured training tier. Unknown treasury is a missing signal; no profitable tier unlock is inferred. Account buying power can include margin: Forge uses no leverage. Check account blocks, instrument tradability, fractional permission, applicable cash/day-trade constraints and settlement. A submitted order consumes buying power even while resting.

Commission-free trading eligibility does not eliminate spread, slippage, regulatory charges, data fees or losses. Consult actual account statements and the current fee schedule rather than copying an old fee constant. Securities proceeds may remain unsettled until T+1; settlement availability and withdrawability differ from displayed cash.

Sources: [Trading account](https://docs.alpaca.markets/us/docs/account-plans), [Margin restrictions](https://docs.alpaca.markets/us/docs/margin-and-short-selling), [Commission eligibility](https://alpaca.markets/learn/start-paper-trading), [Settlement](https://alpaca.markets/support/why-do-i-get-an-error-of-insufficient-balance-when-my-cash-balance-holds-the-requested-amount).

Regular equities session is normally 09:30–16:00 America/New_York on trading days; calendar handles holidays/early closes. Extended eligible sessions include premarket 04:00–09:30, postmarket 16:00–20:00 and overnight 20:00–04:00 across the supported Sunday-to-Friday week. Eligibility depends on asset and account. Query asset attributes including overnight eligibility and halts; regular `clock.is_open=false` is insufficient to determine extended eligibility. Limit/day is Forge's initial training restriction. GTC/overnight/fractional expansion requires explicit capability verification; do not assume the regular session order matrix applies everywhere. Keep UTC storage and timezone-aware scheduling for daylight saving time.

Sources: [Orders](https://docs.alpaca.markets/us/docs/orders-at-alpaca), [24/5 eligibility](https://docs.alpaca.markets/us/docs/245-trading), [Assets](https://docs.alpaca.markets/us/reference/get-v2-assets-1).

## Alpaca: measured drills

1. **Ellis/Cyrus:** distinguish $100k broker paper capacity, training bankroll, real treasury and committed capital. Reject negative/NaN sizes and orders exceeding total open exposure including resting buys.
2. **Reid:** define stable decision/order ID, timeout/cancel policy, partial-fill handling, protective exit and reconciliation before any order. An order acknowledgement is not a fill. A paper fill is not real revenue.
3. **Tess/Quinn:** preregister the fixed relative-momentum hypothesis and next-open/five-session exit timing. Record data dates, feed and cost assumption. Do not repeatedly tune on the forward partition. Compare a market benchmark and cash. Extend later to residual/event hypotheses only with independent evidence.
4. **Ada:** examine historical simulation limitations and missing evidence. Queue effects, latency, impact and real execution can differ from paper. Thin samples do not establish a reliable edge or support scaling.
5. **Vale:** test stale quote, unexpected margin, cross-portfolio concentration, closed session, full bankroll, absent exit and unavailable settlement scenarios. Give concrete acceptance conditions.

The local curriculum emits `var/alpaca_research.json`, a training brief and lesson receipts. The initial evaluator is research-only and reports hypothetical return separately from zero earned cash. Existing blind SPY buys are blocked pending a full deterministic paper adapter. Monitor free data entitlement; a data error must not silently trigger a paid subscription.

Source: [Paper simulation limitations](https://docs.alpaca.markets/us/docs/paper-trading).

## Kalshi: executable event intelligence

Kalshi trading is generally 24/7, with scheduled Thursday 03:00–05:00 Eastern maintenance. Query actual exchange/market status before action. Contract closing time, resolution and cash settlement are separate events; money can remain tied up after close. Learn exact official outcome criteria and index/basis for each market. Group correlated observations by underlying, expiry and direction; ten similar bets are not ten independent proofs.

Sources: [Hours](https://help.kalshi.com/en/articles/13823807-what-are-trading-hours), [Market resolution](https://help.kalshi.com/en/articles/13823821-market-faqs), [Payout timeline](https://help.kalshi.com/en/articles/13823825-timeline-and-payout).

Account keys, eligible products, available funding, exchange state, authenticated order interface, per-market fee schedule and readiness gate are separate capabilities. Successful public research does not prove private trading permission. Market-specific fees and possible maker fees must be checked. A resting order does not prove execution. Compare calibrated prediction probabilities with executable prices after fees, fill probability, uncertainty and capital lockup. No perpetuals/leverage are introduced by this curriculum.

Source: [Fees](https://help.kalshi.com/en/articles/13823805-fees).

Demo credentials are separate from production. Demo prices/behavior are not reliable proof of real executable edge. Use the documented demo endpoint with mock funds for protocol learning. Authenticated API rate limits use independent read/write token budgets; query account limits and endpoint costs, and apply bounded backoff. Avoid polling every market repeatedly when cached state and incremental updates suffice.

Sources: [Demo API](https://docs.kalshi.com/getting_started/demo_env), [Rate limits](https://docs.kalshi.com/getting_started/rate_limits).

## Graduation and next work

A role passes a lesson through evidence-bearing artifacts and successful deterministic checks, not a claim that it has been trained. Learning means a changed decision or reproducible capability. Strategy validation requires independent forward outcomes, costs, drawdowns, capacity, correlation and settlement proof. Live graduation additionally requires founder authorization, funded account, deterministic gateway integration, global-state preservation and reconciled fills. Funding alone does not make a rail live-ready.
