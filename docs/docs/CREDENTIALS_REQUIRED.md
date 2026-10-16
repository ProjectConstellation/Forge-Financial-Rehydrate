# Credentials — status
Secrets live ONLY in `/etc/forge/forge.env` (root:forge 0640) with a root-only backup in `/etc/forge/backup/` (0600).
Never in git, logs, browser, or LLM prompts. Operator pasted keys in chat on 2026-10-06 → **rotate after build** (see OPERATOR_ACTIONS).

| Provider | Variables | Status (verified 2026-10-06) |
|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | ✅ `/models` 200; `deepseek-flash` = DeepSeek-V4.1-Flash, 1M ctx, effort low/high/max. Balance $1.93 (operator to top up to ~$5) |
| Modal | `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` | ✅ token "FORGE", workspace `projectconstellation`; FORGE uses Modal **environment `forge`** |
| Coinbase Advanced Trade (personal account) | `COINBASE_CDP_API_KEY_NAME`, `COINBASE_CDP_API_KEY_SECRET` (ECDSA/ES256 PEM, `\n`-escaped) | ✅ key_permissions: view=true, trade=true, **transfer=false**, portfolio Default. Fee tier Intro: maker 0.50% / taker 0.90%. USD 28.27 available |

## Still needed later (not blocking)
| Item | When |
|---|---|
| Coinbase key **with Transfer** + destination allowlist | Only when operator authorizes automated cash-out/transfer (Stage 2). Separate key recommended. |
| Kalshi `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PATH` | When Kalshi adapter is activated |
| Coinbase CDP wallet secret (Agentic Wallet / x402) | When agentic-wallet rail is activated |
| OpenRouter (Jev only) | `OPENROUTER_API_KEY_JEV` | ✅ 2026-10-07; account credit $5. Used ONLY for `typesafe/jev-router` as DeepSeek-outage failover (measured: routes to deepseek-v4.1-flash via Together, 3–8 s, $0.001–0.003/call). |
| TypeSafe (optional) | `TYPESAFE_API_KEY` | Not provided. Needed only for the real System One API (sub-second calibrated triage, ~$0.0001/decision). |

## Kalshi activation (founder — 2026-10-08)

1. Create/login at https://kalshi.com
2. API Keys: https://docs.kalshi.com/getting_started/api_keys — create key, download private key PEM + copy API Key ID
3. SCP PEM to forge host, then: 
4. Fund ~$25 for micro PAPER/LIVE ladder later
5. Keep KALSHI_LIVE=off until PAPER shadow evidence + explicit founder LIVE auth
6. Never paste the private key into chat or Cursor

Coinbase = crypto/stables. Kalshi = event contracts. Both add independent FLOW toward $1/h.

## Kalshi activation (founder)

1. Create/login at https://kalshi.com
2. API Keys docs: https://docs.kalshi.com/getting_started/api_keys — create key, download PEM + copy API Key ID
3. SCP PEM to forge host, then: sudo bash /srv/forge/scripts/install_kalshi_creds.sh <API_KEY_ID> /path/to/key.pem
4. Fund ~$25; keep KALSHI_LIVE=off until PAPER evidence + founder LIVE auth
5. Never paste the private key into chat


## Alpaca PAPER (equities training rail)
1. Sign up: https://app.alpaca.markets/signup — use **Paper Trading** keys only until founder authorizes live.
2. Dashboard → Paper → API Keys → Generate → `APCA_API_KEY_ID` + `APCA_API_SECRET_KEY`
3. Install: `sudo bash /srv/forge/scripts/install_alpaca_paper_creds.sh <KEY_ID> <SECRET>`
4. Keep `ALPACA_LIVE=off`. Paper endpoint: `https://paper-api.alpaca.markets`
