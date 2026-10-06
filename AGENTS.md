# AGENTS.md — FORGE (read before doing anything)

**FORGE = Find Opportunities · Reinvest · Grow · Evolve** — an autonomous capital growth engine.

## Sources of truth (in `docs/source-of-truth/`)
0. `OPERATOR_POLICY.md` — operator overrides recorded during the build (**highest precedence**; e.g. OP-001 treasury = full account balance).
1. `FORGE_AUTONOMOUS_BUILD_DIRECTIVE.md` — the operator's directive; newer; **wins conflicts** (`scripts/dossier.sh -d ...`).
2. `FORGE_MASTER_BUILD_DOSSIER.md` — the full blueprint (`scripts/dossier.sh ...`).
3. `RESOLUTIONS.md` — how the two are reconciled. `DOSSIER_DIGEST.md` — reading notes (its Pass-3 open questions are answered in RESOLUTIONS).
- `scripts/dossier.sh verify` · `[-d] toc` · `[-d] section <n>` · `[-d] grep <regex>`
- **If unsure, drifting, or about to touch money, secrets, or the live path: re-read the governing section verbatim first.**
- Never edit the source documents. Departures go in `docs/DECISIONS.md` (what/why/benefit/risk/rollback).
- Session continuity: read `docs/CURRENT_STATE.md` and `docs/BUILD_STATUS.md` first.

## ABSOLUTE BOUNDARY — DO NOT TOUCH ANY OTHER PROJECT
- Root: **`/srv/forge`**. Work only here (plus `/etc/forge`, the `forge` service account, and FORGE-namespaced systemd units / Modal apps).
- Never read, scan, import, reuse, restart, or modify anything of another project (Imagine Compass, `/srv/northstar/projects/*`, etc.).
- No `find /`, `grep -R /`, or recursive scans outside `/srv/forge`. No edits to shared reverse proxy, firewall, shared packages or services → record in `docs/OPERATOR_ACTIONS.md`.
- FORGE-only: port **127.0.0.1:8470**, service names `forge*`, own venv/DB/logs/cache, Modal apps `forge-*`, own continuity docs.

## Non-negotiables
- Local CPU 2 vCPU normal, **3 vCPU hard ceiling**. Heavy work → Modal (≤ $30/mo, tracked; warm only if measured worth it).
- Secrets never in git, logs, browser, or LLM prompts. `.env.example` = names only. Never invent/harvest credentials.
- Live trading off by default; LIVE only via explicit config + automated readiness gate. Global `STOPPED` state overrides everything.
- Money path only: intent → allocator → deterministic RiskGovernor → validator → gateway (idempotent) → reconciler → ledger. LLM proposes via tools only; no keys, no destinations, no leverage.
- True net P&L after every cost (fees, spread, slippage, DeepSeek, Modal, data). No fake metrics, no claimed edge without data.
- Don't mark anything done in `docs/BUILD_STATUS.md` without running the tests that prove it.
