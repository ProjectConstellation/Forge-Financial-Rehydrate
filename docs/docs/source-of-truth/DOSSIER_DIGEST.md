# FORGE Dossier Digest — 3-pass reading notes

> **Subordinate document.** This is a navigation aid, NOT an authority.
> The only authority is `FORGE_MASTER_BUILD_DOSSIER.md` (sha256 `398000d7…05d8f4`).
> If this digest and the dossier ever disagree, **the dossier wins** — fix this digest.
> Look up any § verbatim: `scripts/dossier.sh section <n>`.

Provenance: paste board batch `batch-20261006T224609Z-dcc34d` (uploaded 2026-10-06T22:46:09Z),
121,581 bytes, 4,416 lines. Copied verbatim to this directory, read-only (0444).

---

## PASS 1 — What FORGE is (mission, scope, vocabulary)

- **FORGE = Find Opportunities · Reinvest · Grow · Evolve.** An *Autonomous Capital Growth Engine* — not a single bot, not static strategies, not an LLM deciding buy/sell (§1).
- **Objective:** maximize long-run *true net* treasury growth & compounding velocity while controlling probability of ruin, and keep improving the algorithms (§1).
- **Intellectually active 24/7, not financially hyperactive.** Never force a trade because time passed. Inactivity can be optimal (§1, §20.4, §52).
- Autonomous once creds + live mode enabled; zero routine trade approvals. Humans: creds, policy, onboarding, emergency override (§2.1, §41).
- Market-agnostic: everything behind `VenueAdapter`; Coinbase is first rail, not the boundary (§2.2, §20.1).
- Strategies are **declarative genomes** in a whitelisted DSL, with lineage — never LLM-written code hot-deployed live (§2.3, §12, §13).
- LLM confidence has **zero authority**; confidence = empirical calibration (§2.4).
- Losses → diagnose, preserve lineage, reasoned successors. Never random reset, never delete lineage (§2.5).
- **True Net P&L** subtracts fees, spread, slippage, gas, DeepSeek, Modal, data, x402, other costs (§2.6).
- Cost-*aware*, not cheap: spend when expected benefit > cost (§2.7, §24.2 EVI rule).
- Vocabulary: Opportunity (§11), Genome/DSL (§12), Lineage edges (§13), Populations CHAMPIONS/CHALLENGERS/RESEARCH/HIBERNATING/RETIRED/QUARANTINED (§14.4), TradeIntent (§23.1), Modes TEST/REPLAY/SHADOW/PAPER/LIVE (§37), Inference levels L0–L4 (§6.3), Compute tiers A–E (§24.1), Modal budget GREEN/YELLOW/ORANGE/RED (§25.2).

## PASS 2 — Hard requirements, numbers, order of work

### Hard numbers (verify with `scripts/dossier.sh grep '\$[0-9]'`)
| Item | Value | § |
|---|---|---|
| Initial treasury / external injection cap | **$20 / $20** | 21 |
| Reserve below $100 equity | typical 10–20%, high-quality → 5–10%, exceptional validated → up to 100% of initial bankroll (Risk Governor) | 21.2 |
| Reserve at ≥ $100 | **hard floor $25**, not deployable | 21.2 |
| Concentration gates | >50% one thesis → checklist + RG; >80% → also critic/robustness (or precomputed policy if latency-critical) | 21.5 |
| Kelly | fractional 0.1–0.5, never full | 21.3 |
| Leverage | **OFF** (feature-flagged) | 22.3 |
| Local CPU | **2 vCPU normal / 3 vCPU hard ceiling** (CPUQuota=300%, CPUWeight=50, Nice=5) | 3, 36 |
| Local process pool | `ProcessPoolExecutor(max_workers=2)`, BLAS threads=2 | 36.1 |
| Modal budget | **$30/month**, use fully if ROI-positive, never exceed without config change | 4, 22.1 |
| Modal warm | ~0.25 physical core (~0.5 vCPU) target; 0.125 min; 0 if negative EV | 4.3 |
| Modal states | GREEN <60%, YELLOW 60–85, ORANGE 85–95, RED >95 | 25.2 |
| DeepSeek | model alias `deepseek-flash`, starting budget **$5** | 6, 24.3 |
| Operating profit split | ~10% ops / 90% growth, **adaptive, not hardwired** | 24.3 |
| Live flag | `FORGE_LIVE_TRADING=false` default | 5, 37 |
| Shadow burn-in | **24 h** before live, do not shorten to see a trade | 39 P10, 48 |

### Code-level invariants (§22.1 — never prompts)
No order without authenticated treasury snapshot · no stale-data order · no order w/o fee+slippage estimate · none below venue minimum · none exceeding available balance · no duplicates from retries · no new position during reconciliation failure · no transfer to non-allowlisted destination · strategies can't edit execution history · LLM can't bypass risk · strategies can't modify budgets · no Modal spend over budget · no local CPU over 3 vCPU.

### Live path (§18, §23.1) — the only path to money
`Strategy/DeepSeek proposes intent → deterministic Allocator sizes → Risk Governor approve/reduce/reject → Execution Validator (venue rules) → Execution Gateway (allowlisted action) → Reconciler → Ledger`. No `send_money` tool. LLM never supplies a destination. Risk Governor can only reduce/reject/delay/liquidate (§17.6).

### Fast path vs research path (§45)
Fast: event → local features → already-validated strategy → deterministic risk → execution (no synchronous DeepSeek). Research: anomaly → DeepSeek → Modal → promotion → future fast path.

### Build order (§39) — keep runnable after every phase, commit milestones, never mark done without tests
P0 isolation & continuity → P1 skeleton/contracts (+tests) → P2 paper vertical slice → P3 market data engine (+CPU benchmark) → P4 research/evolution → P5 DeepSeek (mock until key) → P6 Modal → P7 Coinbase market data (public feeds immediately) → P8 Coinbase execution (no order yet; dry-run) → P9 dashboard → P10 24h shadow burn-in → P11 tiny live → P12 self-evolution lifecycle demo.

### Required in-repo docs (§55)
AGENTS.md, ARCHITECTURE.md (actual, not aspirational), STRATEGY_SPEC.md, OPERATIONS.md, SECURITY.md, docs/BUILD_STATUS.md (evidence-backed only), docs/DECISIONS.md, docs/LIVE_READINESS.md.

### "Done" = §47 acceptance checklist + §54 deliverables (38 items). Quality bar §53: no TODOs in money paths, no unbounded queues/concurrency, no fake metrics.

## PASS 3 — Gaps, tensions, and how I'll resolve them

These are my interpretations. Each must be logged in `docs/DECISIONS.md` when acted on; anything marked **ASK** needs the user.

1. **§0 vs. my own first action.** Before reading the dossier I ran `find /` to locate the file. §0 forbids that. It listed file paths only and read nothing. Rule from now on: no broad scans.
2. **Project root.** §0 suggests `~/forge` or `/srv/forge`. Other projects live under `/srv/northstar/projects/`; I chose **`/srv/forge`** to stay outside that shared tree (stronger isolation). The user can move it while the repo is small.
3. **Dedicated `forge` OS user / `/etc/forge/forge.env`** (§0, §34.3, §36): passwordless sudo exists, so this is technically possible. It is a host-level change, but it only adds an isolated identity, so it's low risk → **ASK before creating**.
4. **Server "continuity system."** The user mentioned it. §39 P0 "continuity" means the in-repo AGENTS.md/BUILD_STATUS. Whether FORGE should *report into* the server's continuity system is unspecified → **ASK**. Until then, don't touch it.
5. **Dashboard exposure** (§34.4): localhost by default. A public subdomain would need the shared reverse proxy, which touches shared infra → **ASK first**.
6. **"Up to 100% of the initial experimental bankroll"** (§21.2) vs. §20.4 "enough capital left for exit fees/reserve" vs. config `min_fraction: 0.05` (§38). Resolution: "100%" always means *net of the exit-fee/dust buffer*. The exceptional-opportunity path overrides `min_fraction` only through the Risk Governor's precomputed policy (§21.5). "Initial bankroll" caps a single exceptional deployment at $20 even if the treasury is larger and below $100.
7. **$25 floor hysteresis** (§21.2): it is unclear whether the floor persists if equity falls back below $100. Resolution: **sticky once activated** ("restart/survival capital unless the user changes policy"); configurable.
8. **Equity definition for the $100 trigger**: use *marked-to-market total equity net of estimated exit costs*, so unrealized spikes don't trigger it trivially. Log as a decision.
9. **Operating-reserve split vs. "no profit bucket"** (§24.3 vs. §21.1): every profit is booked to the treasury immediately. The ops allocation is an accounting earmark that activates only once self-supporting and adapts to runway. It is not a manual-reinvest bucket.
10. **Modal warm cost reality:** 0.25 core × ~2.63M s/month × $0.0000131 ≈ **$8.6/mo CPU** plus memory ≈ **~$10/mo**, about ⅓ of the budget. Warm-on-by-default must be justified by measured dispatch latency value (§4.3 allows 0). The Compute Governor decides; start at 0.125 or 0 until benchmarked.
11. **Modal billing visibility** (§25.2): usage APIs may not expose remaining credit. Resolution: a local ComputeLedger estimates from requested resources × duration × list price, and is reconciled with Modal usage data when available. Be conservative: assume the higher estimate.
12. **Repo dir named `modal/`** (§8) would shadow the `modal` Python package on `sys.path`. Rename it to `modal_apps/` (§51 permits improvements; document it).
13. **Python:** the host has 3.14.4; the dossier needs 3.12+. `uv` isn't installed, so install it project-locally or user-locally (not system-wide) and pin the Python version in `.python-version`. Check that wheels exist for polars/duckdb/pyarrow; fall back to a uv-managed 3.12/3.13 if needed.
14. **`modal` CLI not on PATH.** Credentials reportedly exist (§4.2). Install the SDK in FORGE's venv, then verify with `modal token info` only. Never read other projects' env files.
15. **Coinbase small-capital math** (§20.4): retail Advanced Trade taker fees (~0.6%/side at low tiers; verify live) mean a round trip costs about 1.2%. Most short-horizon microstructure edges will fail `FeasibilityCheck` at $20. Maker/post-only (§11.1 G) and longer-horizon moves matter most. Expect long stretches of correct inactivity.
16. **Public market data needs no credentials** → P7 market data can start before Coinbase keys arrive (§39 P7 says integrate immediately).
17. **Provider facts are dated 2026-10-06** (§57). Re-verify the DeepSeek model alias and pricing, Modal pricing and minimums, and Coinbase fees when integrating.
18. **systemd:** user-level systemd works, so a `--user` unit with CPUQuota needs no root. Whether to use a system unit with `User=forge` depends on item 3.
19. **Memory limits** (§3): host has 23 GiB total, ~15 GiB available. Proposed MemoryHigh 1.5 GiB / MemoryMax 2 GiB, to be confirmed after measuring footprint.
20. **Ports:** choose after `ss -ltnp`; bind 127.0.0.1 only; record in DECISIONS.

## Drift self-check (run whenever unsure)
1. `scripts/dossier.sh verify` — is the source intact?
2. Which § governs what I'm doing? `scripts/dossier.sh grep <topic>` → `section <n>`. Re-read it **verbatim**.
3. Am I inside `/srv/forge`? Am I touching anything of another project? (§0) If yes, STOP.
4. Does this action touch money, secrets, or the live path? Then re-read §18, §22, §23, §34.
5. Is the claim I'm about to mark "done" backed by a test run? (§40.12, §55 BUILD_STATUS)
6. Am I adding infrastructure the dossier says to avoid (Redis/Kafka/Postgres/Celery/K8s)? (§56)
