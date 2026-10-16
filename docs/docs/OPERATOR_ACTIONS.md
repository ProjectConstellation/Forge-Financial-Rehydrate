# Operator actions (things FORGE must not do automatically)
| # | Action | Why | Status |
|---|---|---|---|
| 1 | **Rotate DeepSeek, Modal and Coinbase keys** after the build; put new values in `/etc/forge/forge.env` via `sudo nano` | Keys were pasted into chat history | OPEN |
| 2 | Top up DeepSeek balance to ~$5 | Balance is $1.93 | OPEN |
| 3 | Optional: create Coinbase portfolio `FORGE` holding exactly the experiment capital, and re-scope the (rotated) key to it | Hard isolation of the $20 experiment from the rest of the account. FORGE already enforces a $20 software cap. | OPTIONAL |
| 4 | Founder portal domain | Operator authorized forge.northstarimagine.com (2026-10-07) | DONE — FORGE's own tunnel `forge` (ca90affe…), service `forge-tunnel` |
| 7 | Optional: Cloudflare Access (Zero Trust, free tier) email one-time-PIN in front of the portal | Second factor for a public portal with a simple password | OPTIONAL |
| 8 | Optional: external uptime monitor (e.g. Better Stack) on https://forge.northstarimagine.com/health | Independent alerting if the server is down | OPTIONAL |
| 5 | Optional: dedicated PostgreSQL instance for FORGE | Host has psql client only; installing a server is a host package change. SQLite WAL in use. | OPTIONAL |
| 6 | Stage-2 cash-out: separate Coinbase key with Transfer + Coinbase address allowlist; register destinations in FORGE policy | Only if automated transfers to operator are wanted | LATER |
