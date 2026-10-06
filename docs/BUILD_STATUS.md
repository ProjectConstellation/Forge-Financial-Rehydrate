# BUILD STATUS (evidence-backed only)
| Area | Status | Evidence |
|---|---|---|
| Isolation / root / service user / secrets file | DONE | /srv/forge, user forge, /etc/forge/forge.env 0640 |
| Source-of-truth anchor + lookup tool | DONE | scripts/dossier.sh verify |
| Credentials (DeepSeek, Modal, Coinbase) | VERIFIED | live API checks 2026-10-06 (docs/CREDENTIALS_REQUIRED.md) |
| Config / bus / DB+migrations / audit / ledger | DONE | pytest tests/unit (ledger property test, audit tamper test) |
| Coinbase REST + JWT + adapter | WORKING (live read-only) | live check: perms, fees, products, balances, candles |
| Coinbase WS + L2 book + quality | WORKING (live) | 30s live session, 0 gaps, books valid |
| Features / regime / genome / backtest / evolution | IN PROGRESS | — |
| Treasury / risk / execution / paper venue | TODO | — |
| DeepSeek brain / attribution ledger | TODO | — |
| Modal compute | TODO | — |
| API / PWA / emergency stop | TODO | — |
| Readiness gate / systemd / burn-in | TODO | — |
