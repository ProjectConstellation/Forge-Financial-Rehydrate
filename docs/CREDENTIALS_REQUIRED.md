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
