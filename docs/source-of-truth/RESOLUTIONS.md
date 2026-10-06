# FORGE Source-of-Truth Resolutions (3-pass reconciliation of DOSSIER + DIRECTIVE)

Authoritative documents (both verbatim, read-only, sha256-pinned):
- **DOSSIER**: `FORGE_MASTER_BUILD_DOSSIER.md` (paste batch-20261006T224609Z-dcc34d, 4,416 lines)
- **DIRECTIVE**: `FORGE_AUTONOMOUS_BUILD_DIRECTIVE.md` (paste batch-20261006T225951Z-b67cda, 2,447 lines). It is the operator's answer to my open questions and is newer.

**Precedence:** where the two documents conflict, the **DIRECTIVE wins**, except that the *stricter* safety rule always wins where one is a safety or isolation rule. Everything else in both documents applies. This file is a navigation aid; the verbatim documents remain the authority.
Lookup: `scripts/dossier.sh section 21` (dossier) · `scripts/dossier.sh -d section 18` (directive).

## Operator answers to my 4 open questions
| Q | Answer | Source |
|---|---|---|
| Project root | **`/srv/forge` approved** | DIR §0, §2, §48 |
| `forge` service account | **Create it if it can be done safely; least privilege** | DIR §0, §48 P0 |
| Continuity system | **FORGE keeps its own continuity system; never write into another project's** | DIR §0, §47 |
| Dashboard exposure | **Private/local during build. No shared reverse-proxy changes. Operator supplies a domain later → secure, authenticated, installable mobile-first PWA** | DIR §28, §30, §52 |
| Shared infra needs | Don't do them automatically. Record them in `docs/OPERATOR_ACTIONS.md` and continue | DIR §0 |

## Conflicts resolved
| # | Topic | DOSSIER | DIRECTIVE | Resolution |
|---|---|---|---|---|
| 1 | Pre-live validation | Fixed 24h shadow burn-in (§39 P10, §48) | **Automated readiness gate instead of a fixed waiting period**; don't skip validation (§18, §42) | Automated readiness gate made of both lists combined (DIR §42 + DOS §47 essentials). Shadow evidence must reach statistical minimums, not a clock. |
| 2 | Modes | TEST/REPLAY/SHADOW/PAPER/LIVE (§37) | MOCK/REPLAY/SHADOW/LIVE/STOPPED (§43) | Modes: `MOCK`, `REPLAY`, `SHADOW`, `PAPER`, `LIVE`. Plus a global trading state `STOPPED` (emergency stop) that overrides every mode. LIVE needs explicit config. |
| 3 | Database | SQLite WAL + DuckDB/Parquet; avoid Postgres w/o measured need (§7, §56) | Postgres preferred **if safely available as a FORGE-only instance**; SQLite OK for bootstrap; migrations must scale (§26) | No Postgres server on host (client only) and installing one is a host package change → **SQLite WAL now**, portable SQL migrations, DB access behind a repository layer. Dedicated Postgres goes in OPERATOR_ACTIONS as an optional upgrade. |
| 4 | Reserve below $100 | Exceptional → up to 100% of initial bankroll (§21.2) | **Generally preserve ~5–20%**; no fake 100%-certain state; stricter as treasury grows (§6) | Stricter rule wins: reserve fraction is dynamic in [5%, 20%] below $100. Exceptional opportunities can lower it toward 5%, never to 0. Exit-fee buffer is always on top. At ≥ $100: $25 hard floor (sticky) plus a fraction that grows with treasury size. |
| 5 | Operating-cost share of profit | ~10% adaptive (§24.3) | 5–15% configurable (§24) | Default 10%, bounded to [5%, 15%], adapted to runway. Booked as accounting partitions (Trading / Protected / Compute / Inference reserves), with no on-chain moves. |
| 6 | Dashboard | React+TS+Vite static (§7, §56) | **Mobile-first installable PWA**, dark mode, WS/SSE, STOP ALL TRADING button (§28, §29) | PWA served by the FORGE backend on localhost; lightweight build. |
| 7 | Endpoints | health endpoint | `/health`, `/ready`, `/metrics` (§31) | All three. |
| 8 | Emergency stop | Control panel (§32.6) | `STOP ALL TRADING` atomic + `forge stop-all` CLI + `scripts/stop-all.sh`; resume needs deliberate authenticated action (§29) | Implement exactly as DIR §29. |
| 9 | Docs set | DOS §55 list | DIR §47 list (+CURRENT_STATE, CREDENTIALS_REQUIRED, OPERATOR_ACTIONS, RISK_POLICY, STRATEGY_EVOLUTION, MODAL_POLICY, DEPLOYMENT, INCIDENTS) | Maintain both sets combined. |
| 10 | Phase order | Paper slice before market data (§39) | Coinbase market data in Phase 2 (§48); first milestone = live data → features → opps → replay/shadow → econ → DeepSeek → Modal → dashboard (§50) | Core → Coinbase **public** market data early (no creds needed; API reachable) → features/regimes → opportunities → genomes → replay/shadow → treasury/risk/exec (paper) → evolution → DeepSeek → Modal → API/PWA → readiness gate. |
| 11 | Env var names | `COINBASE_CDP_API_KEY_ID/SECRET`, `COINBASE_ADVANCED_*` | `COINBASE_API_KEY/SECRET`, `COINBASE_WALLET_SECRET`, `MODAL_TOKEN_*` | "Names may change; keep namespaced & documented" (DIR §3). Use the CDP names that match the current Coinbase SDK and document them in CREDENTIALS_REQUIRED. |
| 12 | `modal/` dir | in tree | in tree | Renamed to **`modal_apps/`**: a top-level `modal/` package shadows the `modal` SDK on sys.path. Logged in DECISIONS (DIR §46 allows improvements). |
| 13 | Exploration budget | discovery pool must not dominate (§14.2) | explicit exploration budget for compute & capital (§37) | Explicit configurable exploration fractions for research compute and capital. |
| 14 | Compute decision | Tiers A–E, EVI rule (§24) | `ComputeAllocator` LOCAL_NORMAL / LOCAL_SURGE / MODAL_BURST + IntelligenceROI (§4, §22) | ComputeAllocator emits the DIR states. The EVI/IntelligenceROI rule drives it. Inference levels L0–L4 kept. |
| 15 | Missed opportunities | §29.6 | §34: record **every rejected** opportunity and score its outcome later | Every rejected opportunity is persisted and scored afterwards (counterfactual P&L). |

## Unchanged hard constraints (both documents)
Isolation (no other project, no broad scans) · 2 vCPU normal / 3 vCPU ceiling · Modal ≤ $30/mo, warm only if measured worth it · DeepSeek `deepseek-flash`, ~$5 start, tracked · $20 experiment, scale-agnostic architecture · $25 reserve at ≥ $100 · no leverage by default · deterministic Risk Governor the LLM cannot override · LLM never holds keys or supplies destinations · idempotent execution, reconciliation, audit trail · true net P&L after every cost · strategies are evolvable genomes with lineage; failures are preserved · no generated code in live without validation · zero routine trade approvals once LIVE is explicitly enabled.

## Host facts (minimal inventory, 2026-10-06)
12 cores / 23 GiB RAM (~15 GiB avail) / 127 GB free · Python 3.14.4 · Node 22 / npm 9 · no `uv`, no `modal` CLI on PATH · psql client only, no Postgres server · passwordless sudo · systemd (system + user) · NTP synced · Coinbase public API reachable (200) · DeepSeek API reachable (401 w/o key) · ports in use include 3400, 5174, 6060, 7431, 768x, 8300, 8781–8790, 18080, 2024x → FORGE uses **127.0.0.1:8470**.
