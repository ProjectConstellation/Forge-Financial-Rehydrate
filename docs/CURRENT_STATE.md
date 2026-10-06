# CURRENT STATE (update at every milestone) — last: 2026-10-06
Read first: AGENTS.md → docs/source-of-truth/OPERATOR_POLICY.md (OP-001..006) → RESOLUTIONS.md → docs/EDGE_AND_INTELLIGENCE_PLAN.md → BUILD_STATUS.md

## Environment
- Root `/srv/forge` (NorthStarImagine:forge, 2750). Service user `forge` (uid 991). Secrets `/etc/forge/forge.env` (root:forge 0640), backup `/etc/forge/backup/`.
- Python 3.14 venv `.venv` via project-local uv (`.tools/uv`, cache `.cache/uv`, `UV_PROJECT_ENVIRONMENT=.venv`). Lock: `uv.lock`. aarch64 host.
- Dev state dir `.devvar/`; prod state `var/` (forge-owned). API port 127.0.0.1:8470.
- Run things needing secrets as: `sudo -u forge bash -c 'set -a; . /etc/forge/forge.env; set +a; ...'`
- Modal: token "FORGE", workspace projectconstellation, environment `forge`.

## Verified live facts
- Coinbase personal Advanced Trade key: view+trade, no transfer; Intro tier maker 0.50% / taker 0.90%; USD 28.27; 919 spot products (804 online USD/USDC), $1 min.
- WS: ticker/market_trades/heartbeats public; level2 (`l2_data`) + candles require JWT; one subscription per channel, spaced 0.25s.
  market_trades `side` = MAKER side (aggressor = opposite; verified 84–90% vs book).
- REST JWT `uri` must exclude query string. Coinbase de-dups client_order_id.
- DeepSeek: deepseek-flash (V4.1 Flash) + deepseek-v4-pro; effort low/high/max; prices in config (OP-004); balance read via /user/balance.

## Code that exists (src/forge)
config.py · core/{clock,ids,bus} · persistence/{db, migrations/0001_init.sql} · audit/journal.py · ledger/ledger.py ·
domain/{market,trading} · venues/{base, coinbase/{auth,rest,ws,adapter}} · market_data/{orderbook,quality,bars,history}
Tests: tests/unit/{test_ledger,test_audit}.py (pass).

## Next (in order)
features engine → regime → genome/DSL + seeds → backtester/triple-barrier/meta-label/calibration/stats → fabric+universe (live) →
opportunity scanner → treasury/sizing → risk governor (OP-004 thresholds) → execution gateway + paper venue → shadow population →
evolution arena + metabolism → brain (DeepSeek client, tools, router, attribution ledger, prompts) → Modal app + compute allocator →
API + PWA + STOP ALL TRADING → readiness gate → systemd → burn-in.
