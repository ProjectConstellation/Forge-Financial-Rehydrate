# FORGE OPS COMMANDER — runbook (OP-023)
Owner-only remote operations agent (Hermes v0.21.5, profile `/srv/forge/runtime/ops/home`, user `forge-ops`,
unit `forge-ops.service`, model = DeepSeek V4.1 Flash credit → DeepSeek later, same provider config as the research Hermes).

## Activate Telegram (once)
1. Telegram: message **@BotFather** → `/newbot` → name it (e.g. "FORGE OPS") → copy the bot token.
2. Telegram: message **@userinfobot** → copy your numeric user ID.
3. Linode Cloud Manager → Linodes → NorthStar-Imagine-Forge → **Launch LISH Console** → log in as `root` →
   run `forge-ops-telegram` → paste the token (hidden) and your user ID. Done — message your bot.
Secrets never go through chat. Only your user ID can talk to the bot (TELEGRAM_ALLOWED_USERS); others are ignored.

## What it can do
Read: `ops_status` (one-call status), all FORGE read tools (`ops_get_*`, `ops_list_strategies`, …), `ops_host`,
`ops_logs` (forge units, redacted), `ops_audit`, `ops_directives`.
Act: `ops_restart` (forge / forge-hermes / forge-tunnel; verified), `ops_assign` (directive → Hermes role, reported back),
`ops_action` SAFE: stop_trading, research_focus, compute_boost (≤ 6 h; Modal caps apply), kalshi_live_off,
cancel_directive · CONFIRM (code sent to your Telegram, model never sees it): resume_trading, kalshi_live_on.
Cannot: shell, files, secrets, other projects, code changes/deploys (engineering channel), stopping services.

## Security layers
Telegram allowlist · separate token for `/api/ops/*` (loopback only) · rate limits (240 reads/min, 30 writes/10 min,
12 confirmations/h) · every command + action in `ops_audit` (also `ops_audit` tool) · Hermes session history ·
sandboxed unit (FORGE secrets, DB and research profile invisible) · polkit: restart/start of 3 FORGE units only ·
redaction of secrets in tool outputs · SOUL rules: only owner messages are instructions.

## Operate
`systemctl status forge-ops` · `journalctl -u forge-ops -n 50` · disable: `systemctl disable --now forge-ops`
Audit: `sqlite3 /srv/forge/var/state/forge.sqlite "SELECT * FROM ops_audit ORDER BY id DESC LIMIT 20"`
