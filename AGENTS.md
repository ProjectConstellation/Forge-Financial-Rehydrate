# AGENTS.md — FORGE (read before doing anything)

**FORGE = Find Opportunities · Reinvest · Grow · Evolve** — an autonomous capital growth engine.

## Single source of truth
`docs/source-of-truth/FORGE_MASTER_BUILD_DOSSIER.md` (read-only, sha256-pinned) is the **only authority** for this project.
- Verify: `scripts/dossier.sh verify` · Index: `scripts/dossier.sh toc`
- Read a section verbatim: `scripts/dossier.sh section <n>` · Search: `scripts/dossier.sh grep <pattern>`
- `docs/source-of-truth/DOSSIER_DIGEST.md` is a navigation aid only; the dossier wins any conflict.
- **If unsure, drifting, or about to touch money/secrets/live path: re-read the governing section verbatim first.**
- Never edit the dossier. If it seems wrong, record it in `docs/DECISIONS.md` and ask the user.

## ABSOLUTE BOUNDARY — DO NOT TOUCH ANY OTHER PROJECT (§0)
- Project root: **`/srv/forge`**. Work only inside it, plus explicitly approved user-level provider config (e.g. `~/.modal.toml` via `modal token info`).
- Do not read, scan, import, reuse, restart, or modify anything belonging to another project (incl. Imagine Compass, `/srv/northstar/projects/*`).
- No `find /`, `grep -R /`, or recursive scans outside `/srv/forge`. No global packages/firewall/shell changes without approval.
- FORGE's own ports, service names (`forge-*`), venv, DB, logs, caches, Modal apps (`forge-*`).

## Non-negotiables
- Local CPU: 2 vCPU normal, **3 vCPU hard ceiling**. Heavy work → Modal (budget $30/mo, tracked, never exceeded).
- Secrets never in git, logs, or LLM prompts. `.env.example` holds names only. Never invent or harvest credentials.
- `FORGE_LIVE_TRADING=false` by default. Live only after acceptance tests + 24h shadow burn-in (§39, §48).
- Live path only: intent → allocator → Risk Governor → validator → gateway → reconciler → ledger. No LLM bypass, no arbitrary transfers, no leverage (§18, §22, §23).
- True net P&L includes every cost (§2.6). No fake metrics; no claimed edge without data.
- Never mark anything done in `docs/BUILD_STATUS.md` without running the relevant tests (§40).
