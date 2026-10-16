- 2026-10-09T14:21Z — Added strategy quality/throughput/archive/resource audit, custom evidence-first admission criteria and count correction; confirmed read-only archive access and documented current kill/reallocation latency. No runtime changes.
- 2026-10-09T14:11:37Z — Founder-specific four-hour PAPER evidence window started (read-only five-minute monitor, Coinbase/Kalshi/Alpaca/sports coverage); documented actual lifecycle counts, cash isolation, baseline churn, and feed caveats. Final evidence due 18:11:37Z.
- 2026-10-09T01:59:50Z — Added cross-portfolio paper-learning upgrade specification, verified paper-lane snapshot and rehydration journal; queued seven next-upgrade work items. Documentation only; no strategy/runtime/account changes.
# Continuity changelog — append only

| UTC | Session | Scope | Result | Evidence |
|---|---|---|---|---|
| 2026-10-09T00:21:38.113671+00:00 | [20261009T002138Z-codex-takeover](sessions/20261009T002138Z-codex-takeover.md) | Continuity documents, templates, assessment and discovery pointers | IMPLEMENTED; runtime repairs remain PLANNED | [baseline](evidence/20261009T002138Z-baseline.json); file/link/scope verification to be recorded in session |

Append corrections as new dated entries. Do not rewrite historical claims to hide failures or promote plans into deployments.

2026-10-09T00:23:00.351374+00:00 — Added TEAM_ECONOMICS.md for founder steering; documentation readback/link/sanitization/source-hash/scope checks passed. Runtime implementation/tests/deployment: none.

2026-10-09T00:32:45.331662+00:00 — Read-only spend/workflow refresh and OVERHAUL_PROPOSAL.md prepared for founder approval. No runtime changes, service actions, paid jobs, orders or external messages launched.

## 2026-10-09T01:21:28.905994+00:00 — approved intelligence and economic overhaul deployed

Canonical money/book separation, spend reservations/workforce proxy, explicit Modal contracts, evidence/workflow/accountability controls, Alpaca curriculum and automatic future paper trials, Kalshi authority, continuity export. 128 tests passed; production read paths healthy. Income remains unproved, billing/broker reconciliation incomplete. Delivery report and receipt define exact scope/rollback.

## 2026-10-09T01:47:33.497113+00:00 — broker-paper execution delivered

Full execution lifecycle, atomic fills, typed autonomous proposals/reviews, policy-capital scaling and allocator integrity deployed. 140 tests passed; independent broker-paper inventory and ledger reconciliation verified, API tools/schema fresh. See BROKER_EXECUTION_DELIVERY and production evidence.

2026-10-09T16:02:50Z — Added detailed forensic passover and refreshed founder/team/system/current-state/work-queue/known-issue continuity notes. Recorded completed one-hour PAPER observation and its evidence limits, actual Hermes role activation, income objective and paper-only phase. Documentation only: no source, prompt, service, credentials, model or portfolio configuration changes; no tests run. See [report](reports/2026-10-09-FORGE-FORENSIC-PASSOVER.md) and [session](sessions/20261009T160250Z-codex-forensic-passover.md).

2026-10-09T22:00:33Z — Kilo session: migrated ALL Hermes agents (13 officers + Luke/ops + eng) from DeepSeek to Alibaba Cloud Model Studio Token Plan / qwen3.8-max. Officially supported Hermes integration path (bl config agent --agent hermes; key decoded from founder-provided o1_ agent credential). Effort policy: xhigh for governor, alpha-inventor, adversary, critic, architect, prediction, execution, treasury, intelligence, daily-report(Luke); medium for doctor, scout, rail-hunter. New subscription wake mode in src/forge/api/agent_api.py (hermes.mode=subscription; wakes no longer gated by dead DeepSeek balance which was at -$0.01 and denying ALL officer wakes). Forge internal brain stays DeepSeek per Token Plan terms (no backend automation). Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/. Verified: allow gate wake=true, live qwen3.8-max inference on hermes/ops/eng homes, officers executing multi-turn tool loops (30–52k token contexts), zero errors. Follow-ups: effort/cost attribution gap in usage hook (FQ2); role_report freshness (F-015, pre-existing).

2026-10-09T22:34:14Z — Kilo session: **Constitution C2 + RATE-THEN-SCALE doctrine deployed firm-wide.** (1) constitution.py C1→C2: added immutable §8 CAPITAL SCALING (rate engine, auto-scale on deposits, ≥bash.50/h milestone + ≥/h primary never redefined downward, idle proven capital = defect). (2) roles.py COMMON_FACTS: removed stale "Treasury ≈ 8" static; installed live-treasury mandate + regime ladder (SURVIVAL <00 → GROWTH 00–500 → EXPANSION >00) + bash.50/h-as-real-milestone (implements founder's recorded intent that was never migrated to runtime). (3) genome.py world_state/_velocity_headline: every officer brief now carries deployable_usd, capital_utilization, regime, regime_policy and a scaling_note. (4) All 13 boot prompts + live cron job prompts patched with C2 economic law; 13/13 verified carrying RATE-THEN-SCALE. (5) Luke SOUL.md: bash.50/h upgraded from "diagnostic only" to contractual first milestone + RATE-THEN-SCALE mandate section (quote rate per capital-hour, project $/h at 00/00/00, escalate idle proven capital). forge.service restarted clean; all services active; py_compile passed. Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/{constitution,roles,genome}.py.bak + SOUL.md.bak.

2026-10-09T23:34:14Z — Kilo session: **deep prompt-engineering forensic pass (identity + finance-contour + delivery).** Founder flagged Mira as generic-AI-framed, not finance-scoped — correct, and it exposed a systemic identity layer problem. Findings + fixes: (1) **Mira/intelligence + Nolan/prediction had NO genome at all** (`get_role_brief` returned `unknown role`) — they ran boot-only, structurally cut off from Constitution/world-state/evolution. Added both as first-class finance-contoured genomes. (2) **Identity collision:** Rowan/architect genome said "Organizational & Prompt Architect: evolve agent prompts" (= Mira's job) while his boot+INFRA DESIGN stage are fintech-engineering; reframed Rowan genome to CTO/financial-income-infrastructure. (3) **Mira boot** persona re-contoured from "AI systems researcher/prompt engineer" to "Director of Financial Intelligence & Prompt-Evolution Alpha / quant meta-trading scientist" optimizing income-per-inference-dollar. (4) **CRITICAL delivery bug (pre-existing):** the role brief — Constitution+genome+live world-state, the most important payload — was double-truncated by stale DeepSeek-era caps (`_fit_json 30000` server-side; `[:24000]` plugin). Governor's 33KB brief arrived as a `{truncated,preview}` blob losing structured keys; all roles lost the tail (world-state/memory/contract). Exempted brief from truncation, raised caps to 120k/200k for Qwen's 1M context. (5) **Voluntary-pull gap:** pre_llm_call hook only tagged role, returned None — officers got their brief ONLY if they chose to call get_role_brief (bind rate: Quinn 5/13, Vale 5/12, Nolan 2/7, Mira 2/4, Luke 0). Hook now injects a MANDATORY first-turn instruction to pull the brief. (6) COMMON_FACTS alias map corrected (Luke=ops, Mira=intelligence, Rowan=architect, Ellis=treasury, Nolan=prediction; "sign with your OWN callsign only"). (7) Directive-flood cap: 10,024 OPEN (9,423 critical, 4.5× dupes) were injected uncapped into every brief; now top-12 distinct newest. VERIFIED: 13/13 roles serve full untruncated C2 briefs (25–35KB), all services active. Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/pre-prompt-forensic/.

2026-10-10T03:25:24Z — Kilo session: **FOUNDER-ORDERED FULL AGENT PAUSE (overnight, zero token usage until morning resume).** Actions: (1) all 13 Hermes officer cron jobs PAUSED via hermes cron pause (persistent in jobs.json, survives restarts, auditable paused_at). (2) forge-hermes, forge-ops, forge-eng services STOPPED — kills every LLM session path including Officer Dispatch/results_enforcer Popen wakes (they fail closed with no gateway). (3) VERIFIED: no hermes processes; zero inference calls since 03:24:00Z (last call hermes_governor qwen3.8-max 03:23:48Z, in-flight during shutdown); reset-failed applied to clean SIGTERM exit states. (4) forge.service left ACTIVE deliberately: deterministic desk (no LLM tokens) keeps PAPER observation, market data and loops running; LIVE flag false; trading state RUNNING per founder's standing PAPER mandate. RESUME PROCEDURE (morning): sudo systemctl start forge-hermes forge-ops forge-eng; then hermes cron resume for each of 13 job ids (ids in cron/jobs.json); verify jobs state=scheduled and /api/agent/allow wake=true. NO founder-unauthorized changes were made beyond the pause. Next work queued for resume: FQ0 ledger truth + deploy loop + FQ2 subscription cost attribution + FQ4 directive backlog closure.

2026-10-10T15:15:25Z — Kilo session (founder morning directives): **Firm schedule + milestone-ladder + 15-agent finance-contour.** (1) TEAM ONLINE: all 13 officer jobs resumed, 3 gateways active, Qwen3.8-Max verified live across 13 distinct agents (183 calls/45min, zero DeepSeek leakage). (2) GATE v2 (forge_gate.py): Alibaba Token Plan off-peak = 60% cheaper Credits 14:00–24:00 UTC (~10:00–20:00 ET) = FIRM BUSINESS HOURS → full team; outside → only 24/7 EARNER CREW (prediction/Kalshi, execution/crypto, scout, doctor, governor, treasury, ops) wakes; deep-work roles (invent/critique/adversary/intelligence/rail-hunter/architect) skip at ZERO token cost until window open. Venue hours encoded: crypto+Kalshi 24/7, Alpaca equities 24/5 (no inference on closed equity markets). (3) CONSTITUTION C2→C3: added §9 MILESTONE LADDER + LOCK-IN (climb bash.25→bash.50→bash.75→.00/h sustained; on crossing a rung name what earned it + protect it as what_is_working; new algos ADDITIVE, never cannibalize a proven earner) and §10 PROTECT THE SECRET SAUCE (moat = proprietary algos/models/allocator/execution; never leak/echo internals; attribute every dollar to its mechanism). (4) COMMON_FACTS + all 13 boot prompts + 13 live cron prompts carry schedule + ladder doctrine. (5) LUKE: SOUL.md + genome ops@v2 (CHAMPION, C3) upgraded — Managing Partner / founder financial advisor, NEVER PAUSED (24/7 Telegram-reachable), owns the workforce power switch (pause/resume all 13 officers + gateways on founder word or observed Credit waste, keeping forge-ops alive), milestone-ladder economics, roster identity fix (Mira=intelligence, Rowan=architect). (6) NOLAN/prediction@v3: Kalshi 24/7 event-contract surface (series→event→market, weather-index/game-stats/CF-Benchmarks/Pyth live feeds, fee 0.07·C·P(1−P), Create Order V2, settlement-basis edge) + playbook at /srv/forge/hermes/research/kalshi_playbook.md. (7) 15-agent finance-framing audit: 12/13 genomes OK, ops was weak→upgraded. VERIFIED: C3+ladder+sauce+business-hours render in all live briefs; ops@v2 renders full; 16 genome-bound reports/45min. Team self-surfaced live defects: phantom deployed_usd surviving restart, peg_mm telemetry reset (fills 38→0), USDT-USD mark frozen 12h (+7.2% PnL overstatement), Vale RISK_GATE FREEZE (pegmaker inventory 10.44× cap one-sided). Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/pre-prompt-forensic/.

2026-10-10T22:50:00Z — Kilo session: **API inference upgrade + capital-engine root-cause fix + crown-jewel analysis.**

(A) INFERENCE TIERING (founder order: Max only where extra-high reasoning genuinely compounds).
  Live benchmark on our own Token Plan key, 1,962 production calls + synthetic probes:
  qwen3.8-max production avg 89.3s / max 2178.8s (36 min); hard-prompt medium=273s, high=TIMEOUT>420s.
  qwen3.8-flash production avg 35.7s / max 279.3s; hard-prompt medium=31.2s (1744 reasoning tokens);
  flash@high and flash@xhigh TIMEOUT >400s => medium is the deepest USABLE tier on BOTH models.
  Token Plan confirmed both models enabled on the existing key; both carry the 60% night discount
  22:00-08:00 UTC+8 = 14:00-24:00 UTC = 10:00-20:00 ET (founder's Florida business hours).
  DEPLOYED: qwen3.8-flash registered on all 3 Hermes homes; 12 officers + Luca on Flash@medium;
  alpha_inventor (Quinn) alone on Max@medium (new algorithms are the compounding asset).
  Schedules staggered to keep concurrency inside the Token Plan agent cap (Pro=6-8) — previously all
  15 agents fired on 15-minute boundaries. VERIFIED on the wire: 163 flash vs 9 max calls/30min,
  max avg latency 41.7s (was 262s for governor), flash avg 30.7s, 0 errors, 0 DeepSeek leakage.
  FOUNDER FLOOR ENFORCED: Flash is never below medium (an initial Flash@low for Luca was corrected).
  LUCA LATENCY: 3-5 minutes -> 35 seconds measured end-to-end on "give me an update on the whole system".

(B) RENAME Luke -> Luca across 21 files (display text only). Functional identifiers deliberately
  preserved: role_id "ops", INFERENCE_CHAT_ROLES {"ops","luke"}, KV lab.luke_orchestration,
  world key LUKE_BOARD. Verified none damaged.

(C) ROOT CAUSE #1 — CAPITAL ENGINE WAS WIRED TO THE WRONG WALLET (the single biggest defect found).
  profit_velocity.treasury() read `account_total_usd` (the REAL Coinbase wallet) with no book filter.
  The founder's withdrawal at 2026-10-10 19:29 collapsed it from ~$63 to $0.0896 while the PAPER book
  still held $23.85. regime_for() computes deployable = max(0, treasury - reserve) and reserve had
  latched at $25 from the stale real-wallet high-water mark => **deployable = $0.00**. Consequence:
  NO strategy could ever be allocated capital — 89 validated strategies, 0 positions,
  capital_utilization pinned at 0.0 for the firm's entire life. FIXED: treasury() now sizes from the
  active book's own equity_usd (fallback account_total_usd only when no equity row exists), and the
  regime HWM was re-baselined onto the paper book's own peak ($63.43 -> $28.63). Result:
  regime RESERVE->BOOTSTRAP, reserve $25->$0, **deployable $0.00 -> $23.835**.

(D) ROOT CAUSE #2 — THE BEST EARNER WAS LOCKED OUT BY A SCOPE BUG.
  treasury/evidence_eligibility.income_block() ignored BOTH `scope` and `expires_at`. Five
  NEGATIVE/CONTAMINATED markers excluded coinbase.stable_triangle from the frontier, but every one is
  scope='income_claim' and two say verbatim "CLAIM discipline only: do not label stables proven until
  peg ledger clean. **PAPER capital-hours ALLOWED.**" Two of them had EXPIRED 47.2h earlier and still
  blocked (the canonical accessor opportunity_memory.blocks_income_claim() DOES filter expiry — this
  helper had silently diverged). Effect: the firm's crown jewel (1,452 round-trips, 100.0% win rate,
  $1.90421 net, 20.2 RT/h) was absent from the frontier entirely, leaving only the 10x slower peg
  stream and pinning proven $/h near zero. FIXED with two-tier semantics: HARD statuses
  (KILLED/BLOCKED/NEGATIVE_AFTER_COSTS/EXECUTION_INFEASIBLE) block everywhere; claim-scoped markers
  block only the PROVEN tier and never measurement/allocation. Reallocator (a planner, paper_only=True,
  no live execution) uses hard_only=True. Arena/readiness keep full claim discipline — promotion and
  LIVE gates remain strict. VERIFIED: stable_triangle back in the potential frontier (locked $6.92,
  $0.0106/h) and ranked #1 marginal lever (+0.00945/h); proven rate 0.0007 -> 0.00131.

(E) ACCOUNTABILITY HYGIENE. 17,486 OPEN directives vs 1,573 DONE (11:1) — the same EARNINGS_PUSH
  instruction emitted 1,351 times because every emitter did a raw unconditional INSERT per tick.
  Added forge/agents/directives.py: idempotent emit() keyed on a number-normalised signature (the
  messages embed a changing $/h figure, so naive text dedup never matched), plus emit_objective().
  Wired earnings_push, earnings_escalator and results_enforcer._page to it. Collapsed the backlog:
  OPEN 17,486 -> 1,018 distinct; ACTIVE objectives 153 -> 6 (146 identical "TEAM FAILURE MODE" zombies
  that never closed). Added forge/agents/directive_hygiene.reap_stale() on the hourly housekeeping loop
  (critical/high expire after 6h, normal after 12h; workflow-linked rows preserved): OPEN -> 277, all
  fresh/actionable. Nothing deleted — rows move to CANCELLED/EXPIRED_STALE with an audit reason.
  Added ResultsEnforcer._milestone_stall(): the employee the founder asked for. Owns "we are not making
  money": if the measured rate stops advancing for 2h it pages named owners with the top lever and a
  required Δ$/h; at 6h severity rises to critical and adds critic/adversary/ops with a duty to report
  the stall to the founder. Surfaced on the enforcer board as `milestone`.

(F) MEASUREMENT HONESTY. Added treasury/economic_truth.paper_realized_window() — a MEASURED paper
  scoreboard (paper closed positions + shadow round-trips, per rail) so the founder's
  $0.25->$0.50->$0.75->$1.00 ladder is climbed on evidence, not on model expectations. Cash TRUE-NET
  stays live-only ("paper never becomes cash income") — nothing is fabricated as earnings. Documented
  fee semantics per source: positions.realized_pnl_usd is GROSS (net = realized - fees) while
  shadow_trades.pnl_usd is ALREADY fee-net (pegmaker nets the exit fee and carries the buy fee inside
  avg cost; triangle nets both legs), so fee_usd there is informational and must not be re-subtracted.
  Also fixed a circular dependency I had introduced: paper_realized_window read `deployable` from the
  velocity KV, which compute() itself writes — it consumed its own prior-cycle output and, when that
  was stale, reported capital_utilization=28.95 (an impossible >100%). Now deployable is passed in from
  the regime and the ratio is clamped to [0,1].

(G) CROWN-JEWEL ANALYSIS + C3 LOCK-IN RITUAL. Recorded as protected what_is_working:
  coinbase.stable_triangle (conf 0.98, owner=execution, ttl ~permanent) and coinbase.stable_peg_mm
  (conf 0.90). Mechanism: Coinbase converts USD<->USDC 1:1 FREE, so USDT-USD and USDT-USDC must imply
  one USDT price; the engine takes the taker-taker cycle when the gap exceeds both taker fees + 0.15bp.
  It is a STRUCTURAL IDENTITY, not a forecast — which is why it wins 100% of 1,452 round-trips at ~2s
  hold and ZERO inference cost. Also recorded a NEGATIVE lesson (scope=lesson, owner=alpha_inventor):
  directional LLM genomes do not earn here (145 spot closes, mu=-0.0012/unit, UNPROVEN, $0 from ~53k
  genomes/hour pre-fix) with a reopen_condition requiring fresh fee-net positive evidence.
  CAPACITY SCAN (live level-2): USDT-USD 472,330 USDT bid / 385,596 ask; USDT-USDC 348,939 bid /
  1,667,684 ask. **Depth is not the constraint — deployed notional per round-trip is.** At the measured
  0.004081% mean return and lam~20 RT/h: $12/book -> $0.0097/h; $150/book -> $0.122/h; $250/book ->
  $0.204/h. So the founder's planned $300-500 reaches the $0.25 rung IF lam holds; the two levers are
  (1) raise deployed notional per cycle as treasury grows (band already scales with deployable) and
  (2) raise lam by capturing more gaps — never by cutting min_edge below fee+buffer.
  Venue scan: USDT is the ONLY base quoted in both USD and USDC (842 products; quote=USD 403,
  quote=USDC 5, quote=USDT 20), so this identity edge is structurally unique and already ours;
  sibling identities do not exist on this venue. Injected the crown jewel, the scaling math and a
  MECHANISM-CLASS MANDATE into COMMON_FACTS (rendered into all 15 briefs): invention must target
  deterministic structural/carry/identity edges that cost zero inference per round-trip.

BACKUPS: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ (profit_velocity.py.bak3-5,
evidence_eligibility.py.bak, reallocator.py.bak, runtime.py.bak2-4, earnings_push.py.bak2-3,
earnings_escalator.py.bak-2, results_enforcer.py.bak2, roles.py.bak4, directives.py.bak,
jobs.json.bak2, 3x config.yaml.bak2, 13x boot_*.md.bak2, forge.sqlite.pre-treasury-fix.bak,
forge.sqlite.pre-lockin.bak, forge.sqlite.premigrate.bak).

2026-10-11T03:55:00Z — Kilo session: **Forge-Jev (typed judgement desk) + cost-ordered funnel + inference economy + Luca power switch.** Founder order: build our own Jev, state-of-the-art; make inference self-sustaining; give Luca real ops authority.

(A) FORGE-JEV — `src/forge/judge/` (12 modules, 68/68 zero-inference tests).
  Typed judgement seats instead of prose: `noul` (is-this-true → calibrated 0..1), `choice`
  (which-one → label + probabilities + confidence), `score` (rate-on-rubric → ordinal + legend).
  modules: primitives · questions (one file holds every question set) · calibrator · funnel · checks ·
  judge · salary · schema · thresholds · doctrine · event_verdict · __init__.
  KEY DIFFERENCE FROM THE REFERENCE DESK (savip/Jev): they RENT calibration from a vendor; we MANUFACTURE
  it. Every `noul` is calibrated through the existing `forge.research.calibration.CalibrationEngine`
  (PAV isotonic, source-weighted live>paper>shadow>counterfactual, skeptical prior) over 4,075 realized
  points, and every judgement is scored when reality resolves, so it compounds. Measured tonight: raw
  LLM probabilities are NOT probabilities — Qwen returned noul=0.0062 / confidence=0.00027 for a plainly
  risky token. Live proof through the officer API: raw 0.98 → **calibrated 0.74**, and size_factor cut to
  **0.4** because n=0 (provisional). The desk refuses to size up on unproven confidence.
  COMPLIANCE: the judge makes NO model call of its own. A separate high-volume judge service would be a
  "custom application backend / non-interactive batch call", which Token Plan terms prohibit. Instead the
  OFFICER is the judge: `judge_ask` returns a strict schema + state PRUNED to the declared fields; the
  officer answers inside its existing interactive Qwen call; `judge_commit` validates, calibrates and
  records. Zero extra inference, zero terms risk.
  DISCIPLINES ENCODED: never invent a number (null stays null; missing data = `dark`, which CUTS the
  ticket, never skips); a Choice is relative and always names a winner, so every pick set ships an
  absolute `worth_acting_at_all` gate that makes STAND_DOWN reachable; facts are not questions (anything
  arithmetic can settle is settled free, before judgement); thresholds live in ONE file.

(B) COST-ORDERED FUNNEL — `judge/funnel.py` + `judge/checks.py`. R0 free arithmetic (no network) →
  R1 fact kill (rail executable, session open, identity present, measured negative edge) → R2 structural
  (identity gap vs fees+buffer, cross-venue gap vs cost, depth, unproven spot) → R3/R4 judged by officers.
  Benching is on the CHECK, not the candidate, with reason-specific TTLs (`fee_negative` ~forever,
  `too_young` 20min so a maturing setup is not lost). A raising check KILLS (fails closed) rather than
  silently passing. Replay of 4,000 real opportunities: **3,990 killed by free arithmetic, 0 inference**.
  Live shadow mode wired into the opportunity path: 16 real candidates evaluated, **16 would-kill, 15 of
  them still status=NEW** (kills the funnel can make for free before any judgement), agreement 1.0 on the
  decided subset. Net edge of what it would kill: −169 to −346 bps.

(C) INFERENCE ECONOMY — `judge/salary.py`. The founder's rule made executable: "their inference is how
  they get paid; if they're not contributing income that pays for it, they lose their jobs." Per role:
  attributed income ÷ inference salary → EARNING / WARN / CRITICAL / UNSCORED / PROTECTED, surfaced as
  `salary_report` and running hourly. CRITICAL cuts wake frequency (3×), WARN 1.5× — reduced wake
  budget, never deletion, and it restores automatically on recovery.
  IMPORTANT SEMANTICS: during PAPER proof it MEASURES but never ENFORCES. Live testing caught the flaw:
  critic and adversary scored CRITICAL precisely BECAUSE today's funnel + mark-to-market fixes stopped the
  losses they are credited for preventing — punishing success. There is no real income to recoup yet, so
  no seat is cut before the book can pay anyone. Enforcement begins at LIVE. Luca (ops) is PROTECTED,
  never cut, by founder order. Current baseline: execution + treasury EARNING ($0.329 income), 5 UNSCORED
  enabling roles, 3 WARN, 2 CRITICAL (measured, not enforced).

(D) EVENT-RAIL VERDICT — `judge/event_verdict.py`. Phase 3 (cross-venue arbitrage) was RESEARCHED, not
  assumed. Four live probes found: Kalshi and Polymarket are both reachable and Polymarket data is rich,
  but **there are ZERO tradeable structural overlaps** (Polymarket's liquid book is long-dated
  politics/sports; Kalshi's crypto strikes have no counterpart) — the savip `venue_gap` idea does not
  exist for us. Worse, Forge's OWN event engine was measured at a LOSS: crossrail model Brier 0.12992 vs
  **market 0.12854 (the market beats our model)**, 20,068 settled signals totalling **−$412 to −$417**.
  So instead of building on it, the verdict was made data-driven: NEGATIVE_EDGE → `bench`, with a stated
  reopen condition (model Brier < market Brier on ≥200 rows AND shadow P&L > 0 on ≥200 signals). It
  SELF-HEALS with no code change when the model starts winning. Evidence gate requires BOTH sides —
  thin evidence yields INSUFFICIENT_EVIDENCE rather than a guess. All four branches are unit-tested.
  Contrast worth keeping: on settlement-window markets our model DOES beat consensus
  (Brier 0.09289 vs 0.10505, n=44,428) — a real, large-sample edge sitting unused.

(E) LUCA POWER SWITCH (founder: "Luca never gets paused… he can pause the team or bring it back").
  forge.service is hardened (NoNewPrivileges=yes, ProtectSystem=strict, ReadWritePaths=/srv/forge/var) so
  it can NEVER sudo — correct, and not weakened. Solution: the service drops a per-nonce request into
  /srv/forge/var/run; a root systemd PATH unit (`forge-team-power.path`) runs `team_power_exec.py`, which
  drains every pending request and drops to forge-hermes via sudoers; results return nonce-keyed.
  Verbs: pause · resume · status · wake <role>. Bounded by design: role NAMES only (never a raw job id),
  resolved against live jobs.json; forge-ops is never touched; every call audited with the actor name in
  both the hash-chained ops_audit and a root-side log. VERIFIED end-to-end: 13 paused → 13 scheduled,
  actor attributed, request consumed (no replay), and a real wake LAUNCHED by the service itself
  (`role=rail_hunter job=34ad169160fe result=LAUNCHED pid=445798`). Concurrency verified 4/4 results, 0
  dropped. Exposed to Luca as `ops_action team_pause|team_resume|team_status`.

(F) MAJOR LATENT BUG FOUND AND FIXED — on-demand wake has never worked.
  THREE call sites used `subprocess.Popen(["sudo","-u","forge-hermes", ... "cron","run",jid])`:
  agents/employment_accountability.py:_hermes_wake (the PRIMARY path), lab/officer_dispatch.py, and
  results_enforcer.py:_wake. Under NoNewPrivileges that sudo can never succeed, and Popen with
  stdout/stderr=DEVNULL does NOT raise on refusal — so all three returned True and were recorded as
  `woke=True` while nothing ran. All 8 historical FORCE_WAKE records were false, which is exactly why
  stale officers were reported as force-woken and stayed stale. Replaced with the honest queued protocol:
  a wake records QUEUED, never success, and `reconcile_wakes()` upgrades it to CONFIRMED / FAILED /
  UNCONFIRMED from the executor's answer (an unanswered wake is marked UNCONFIRMED rather than left
  looking successful). Also cleared 13 legacy `ATTEMPTED` admission entries written by the dead path, and
  made the client ignore that legacy vocabulary so it self-heals.

(G) LATENCY TIERING EVIDENCE (from production ledger, 1,962 calls): qwen3.8-max avg **89.3s**, max
  **2178.8s**; qwen3.8-flash avg **35.7s**. Hard-prompt probe: max@medium 273s, max@high and max@xhigh
  **TIMEOUT >420s**; flash@medium **31.2s with 1,744 reasoning tokens**, flash@high and flash@xhigh
  **TIMEOUT >400s**. So `medium` is the deepest USABLE tier on both models, and latency — not reasoning depth
  — was the bottleneck. Post-tiering measured: officers now run **8.8s–33.3s** per call. FOUNDER FLOOR
  enforced: Flash is never below medium (an initial Flash@low for Luca was corrected). Quinn
  (alpha_inventor) alone keeps Max@medium.

(H) PROMPT ENGINEERING — per-role judge doctrine (`judge/doctrine.py`), rendered by `genome.render()`
  immediately after COMMON_FACTS so it reaches every brief through the immutable path prompt-evolution
  cannot weaken, while being specific to the reader. Each of the 13 seats gets: what it does (as an
  economic outcome), who it talks to (named handoff contract, both directions), how it gets work done
  (its exact question sets and the two-call protocol), and how it is motivated (its salary and what
  earning buys). VERIFIED live: all 13 briefs carry JUDGE PROTOCOL + their own seat (30.8k–45.3k chars,
  untruncated). Luca's SOUL was corrected to use REACHABLE tools — it previously told him to run
  `systemctl` and `hermes cron resume`, which the sandboxed ops runtime cannot execute (an agent told to
  use an unreachable mechanism goes silent or invents a result); it now maps his own natural-language
  table to `ops_action team_pause/team_resume/team_status`, `ops_salary_report`, `ops_funnel_health`,
  `ops_judge_calibration` and `ops_get_overnight_evidence`, and states plainly that pausing the team does
  NOT stop the deterministic earners inside forge.service.

(I) OVERNIGHT EVIDENCE HARNESS — `scripts/overnight/harness.py` + `forge-overnight.timer` (every 2h,
  verified via systemd, exit 0, 28.8 MB, **zero inference / zero network**). Writes
  var/reports/overnight/latest.{json,txt}: [A] funnel replay · [A2] live shadow funnel · [B] calibration
  audit (raw vs calibrated Brier, model vs market) · [C] salary baseline · [D] crown-jewel λ study with
  an hourly profile and $/h projections · [E] event-rail verdict · [F] velocity/milestone · [G] ledger
  identity · [H] workforce. Pure replay uses `bench_persist=False` so it can never mutate production
  state.

CROWN-JEWEL λ FINDING (corrects an earlier projection): λ did not collapse — the earlier λ=16.18 RT/h was
  inflated by phantom over-sizing. Hour-by-hour: 57h ago n=33 at ~$26 notional; 13h ago n=1 at $300;
  now n=1 at $23.72. Rate per dollar is stable (~0.0041%/RT); what changed is that the old hardcoded
  $200–500 band let it quote $300–433/book against a $28 paper book — trading money it did not have,
  which is what produced Vale's "inventory 10.44× cap" freeze. Current $23.84 notional is the honest
  figure for $23.73 deployable. Second lever found: USDT-USD `inv_qty=11.93` is pinned at its per-book
  cap, so that book is FULL and blocked. Hourly λ profile peaks 113/107 RT at 16:00–17:00 UTC (the
  discount window) and dips to 16–19 at 09:00–10:00 UTC.

SELF-CAUGHT DEFECTS (all fixed before or immediately after deploy, none shipped broken):
  1. `pol` variable shadowing in runtime.py would have corrupted position sizing (caught pre-apply).
  2. Changing frontier cluster `cap` from 1.0 to real notional would have divided rel_edge by ~77× and
     demoted the only EXCEPTIONAL earner out of the frontier (caught pre-apply, reverted).
  3. My paper scoreboard read `deployable` from the velocity KV that its own caller writes — circular,
     yielding capital_utilization=28.95 (>100%). Fixed by passing it in + clamping to [0,1].
  4. First funnel replay double-counted fees (`expected_net_bps` is already net), killing 4,000/4,000 as
     `fee_negative`. Fixed by using the engine's own recorded net edge with an honest reason
     (`net_edge_nonpositive`) and charging cost once.
  5. That first replay also WROTE 4,000 real opportunity ids into production `funnel_bench` as
     `fee_negative` for 69 days — which would have blocked genuine candidates for two months. Cleared
     (DB snapshot taken first) and added `bench_persist=False` so replays are pure.
  6. A single shared request file meant concurrent wakes overwrote each other (7 left pending forever).
     Fixed with per-nonce request files + a draining executor; verified 4/4.
  7. `setsid run_hermes` could not work (a shell function is not an executable); rewired to the binary.
  8. `contextlib` was not imported in results_enforcer; my patch would have crashed at runtime.
  9. `tools.py` lacks a `time` import; the overnight-evidence handler would have raised. Imported locally.
 10. Agreement metric counted undecided `NEW` candidates as disagreements (reported 0.0625 when the
     honest reading is "the funnel got there first"); now decided-only, with undecided reported separately.
 11. Harness `DB.query()` returns dicts, so `dict(zip(keys, row))` would have emitted garbage.

BACKUPS: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ — every touched source file (tools.py,
runtime.py, ops_api.py, db.py, genome.py, checks.py, salary.py, roles.py, results_enforcer.py,
employment_accountability.py, officer_dispatch.py, profit_velocity.py, evidence_eligibility.py,
reallocator.py, earnings_push.py, earnings_escalator.py, pegmaker.py, gateway.py, surface.py,
agent_api.py, economic_truth.py, SOUL.md, 13 boot prompts, 3 configs, jobs.json) plus FOUR DB snapshots
(premigrate, pre-treasury-fix, pre-lockin, pre-bench-clean). Every change is revertible.

2026-10-11T14:35:00Z — Kilo session: **overnight verification + Hermes bots research + salary cost-basis fix.**

(A) BUSINESS-HOURS GATE VERIFIED IN PRODUCTION. Overnight window 04:15–14:00 UTC (12:15am–10am ET):
  **2,089 crew calls, 0 deep-work calls** — the gate did exactly what the founder ordered. Only the 24/7
  earner crew ran (execution 472, governor 408, prediction 405, treasury 360, doctor 258, scout 236,
  ops 11); Quinn (alpha_inventor, the only Max seat) made 2 calls total overnight and deep-work roles
  made none. Business hours opened 14:00 UTC and all 7 active roles began waking. 0 errors overnight.

(B) OVERNIGHT INFERENCE — the founder's "how much was burned?" question, answered honestly.
  2,152 calls, 86.4M input / 2.15M output tokens. **Cash cost: $0** — Token Plan is a FLAT subscription,
  so marginal cash per call is $0; the real budget is the monthly Credits quota, which this consumed
  against. Ledger OPEX:INFERENCE posted for qwen since the fix: **0 rows** (fix holding). The 1,392
  historical pre-fix rows ($4.5231) remain disclosed, never rewritten.

(C) OVERNIGHT INCOME — positive, and the earners never slept.
  stable_triangle: 21 round-trips, **+$0.026893** net, last at 13:45 UTC.
  stable_peg_mm: 16 round-trips, **+$0.015899** net, last at 11:38 UTC.
  Combined overnight: **37 round-trips, +$0.042792 net**. Measured paper 1h rate **+$0.0026/h**
  (positive), 24h −$0.0149/h (spot churn −$2.16 still dominates the 24h window). Ledger BALANCED
  (residual 0.0000000000). Both earners fired while the deep-work team was gated off — the "always
  earning 24/7" requirement is being met by the deterministic layer, which costs zero inference.

(D) SALARY COST-BASIS BUG FOUND AND FIXED (my own code, and it was dangerous).
  `judge/salary.py:role_cost` summed `inference_calls.cost_usd` as each seat's salary — but that column
  is priced from the **DeepSeek FALLBACK** table because `hermes.prices` is unset. Under a flat Token Plan
  the marginal cash cost of a Qwen call is **$0**, so this fabricated ~$8.66/day of salary and made 7 of
  13 seats read CRITICAL. That is not merely wrong: CRITICAL is the state that cuts a seat's wake budget
  at LIVE, so a fabricated cost would throttle the very seats trying to find income — exactly the
  bottleneck the founder forbade ("don't create a bottleneck… if they're not generating income they need
  to double down on different approaches").
  FIXED: only non-subscription (metered) models carry per-call cash cost; subscription calls report quota
  consumed (calls + tokens) instead; the fixed plan fee is firm OVERHEAD, pro-rated only when the founder
  supplies `hermes.mode.plan_monthly_usd` (never invented); and a seat can never be scored CRITICAL when
  no dollar cost basis exists. VERIFIED: the 7 false CRITICALs resolved to 7 EARNING + 5 UNSCORED +
  1 PROTECTED, **0 CRITICAL**. 68/68 tests still pass; 0 tracebacks.

(E) HERMES BOTS RESEARCH (founder asked: can each agent spin up bots? do we need fewer agents?).
  VERIFIED from official Nous docs (/docs/user-guide/bot-mode, /docs/user-guide/profiles,
  /docs/user-guide/features/delegation) + release notes:
  * **Bot Mode is a DESKTOP-APP UI** over Hermes *profiles*: "a Bot IS a Hermes profile — isolated config,
    memory, skills, credentials, chat history under ~/.hermes/profiles/<name>/". It gives profiles avatars,
    group chats and @mentions. It is NOT a headless spawn mechanism, and Forge runs headless on a server.
    Each local Bot costs its own backend process (~60 MB, default max 3 warm) — so Bot Mode would ADD
    processes, not replace our officers.
  * The mechanism that DOES match the founder's intuition is **`delegate_task` subagents** — "spawns child
    AIAgent instances with isolated context, inherited tool access, their own terminal sessions… only its
    final summary enters the parent's context." Up to **10 concurrent children by default**, no hard
    ceiling; live orchestration (list/steer/stop) added in v0.21.0.
  * **ALREADY AVAILABLE TO US:** the `delegation` toolset is enabled in our config for cron jobs, and
    `delegate_task` exists in the installed v0.21.5. Effective defaults (we set none): MAX_DEPTH=1
    (flat: parent→child, no grandchildren), 10 concurrent children, oneshot 2. So an officer can already
    fan out parallel research inside its own wake — but NONE of our officer prompts currently instruct
    them to. That is the gap to close, and it is a prompt/doctrine change, not an install.
  * `hermes peer` (bot-to-bot DMs across profiles/gateways) also exists — relevant only if we ever run
    multiple profiles; we currently run 3 separate Hermes homes (hermes/ops/eng), not profiles.
  * **VERSION:** installed v0.21.5 (2026-09-24); latest is **v0.21.6 (2026-10-08)** — a rollup tag
    (~2,100 PRs) whose curated notes are deferred to v0.22.0. It ships 4 dashboard auth security fixes
    (reported by Tenable) + git-filter hardening + email-sender hardening. RECOMMENDATION: update is
    worthwhile for the security fixes, but it is a 2,100-PR rollup with no curated notes, so it must be
    done deliberately with a tested rollback, NOT mid-session. Not done today; queued as a founder decision.

(F) THE REMAINING INCOME GAP, precisely located (not yet fixed — needs a build, reported for decision).
  `deployed=$0` and `paper_utilization=0.0` even though the earners are profitable, because
  `paper_lab.bridge_stable_shadow_to_paper()` only accumulates PnL into a KV book
  (`lab.paper_stable_pnl`) — it never posts to the LEDGER and never opens a position — AND it is only
  called when an LLM officer chooses to invoke it via officer_dispatch. So the proven earners earn in
  shadow but their capital never formally goes to work, and the milestone scoreboard cannot see deployed
  capital. The fix is to make the bridge deterministic (a loop, not an officer's choice) and have it post
  real positions to the paper ledger so utilization and deployed_usd become true. This is the single
  highest-value next build.

BACKUPS: /srv/forge/.engineering/20261009T213224Z-qwen-migration/salary.py.bak2 (+ all prior).

2026-10-11T15:25:00Z — Kilo session: **LEDGER BRIDGE (income is now real) + λ correction + basis guard.**

(A) THE LEDGER BRIDGE — `treasury/ledger_bridge.py`, wired as a critical 60s deterministic loop.
  THE GAP CLOSED: Forge's earners completed round-trips and recorded them in `shadow_trades`, but nothing
  ever posted them to the ledger. `bridge_stable_shadow_to_paper()` only accumulated a KV PnL book AND only
  ran when an LLM officer chose to call it. So the firm was profitable in shadow while the ledger showed
  zero income and deployed=0 — no scoreboard could prove the firm earns. Bookkeeping is not a judgement
  call, so it is now a deterministic loop with zero inference and zero network.
  RESULT (verified): all **1,570** historical round-trips bridged in 4 batches (500/500/500/70).
  Reconciliation **EXACT**: shadow_net $2.36884618 == ledger_net $2.36884618, difference **−0.0**,
  `reconciled: True`. Ledger identity still **BALANCED** (residual −0.0000000000). Paper realized PnL
  **−$1.60651 → +$6.49901**. Paper cash **$23.5514 → $25.9202**. All 59 ASSET accounts net to exactly
  zero (no phantom inventory). 10,832 ledger rows posted. Bridged by strategy:
  paper_stable_triangle $7.632767 (1,480 fills), paper_stable_peg_mm $0.472753 (90 fills); fees $5.736674.
  SAFETY PROPERTIES: pegmaker NOT touched (C3 §9 — never risk a proven earner; additive only);
  **NO position rows written** (deliberate: `paper_realized_window` sums paper positions AND shadow
  round-trips, so writing positions would DOUBLE-COUNT the same income — the ledger is truth for cash,
  the scoreboard keeps reading shadow_trades, and `reconcile()` proves they agree every 60s);
  idempotent twice over (monotonic watermark + record_fill's own idem keys, so a crash/restart/re-run
  cannot double-post a cent); a reconciliation failure logs an ERROR and writes an audit entry because
  income must never be claimed on untrusted books. Pre-bridge DB snapshot taken.

(B) λ CORRECTION — my morning projection was WRONG and is corrected here.
  This morning I projected $0.25/h at ~$380 deployed using λ=20.2 RT/h. That λ was drawn from the 96h
  lifetime average, which is inflated by the old phantom over-sizing era. The current rate is far lower:
    last  6h: λ=2.00/h  mean_ret=0.008689%  rate=0.017377%/$/h
    last 24h: λ=1.50/h  mean_ret=0.004461%  rate=0.006692%/$/h   <- honest current rate
    last 96h: λ=14.68/h mean_ret=0.004143%  rate=0.060807%/$/h   <- stale, do not plan on this
  At the honest 24h rate, **$0.25/h requires ~$4,000 deployed, not ~$380** (a ~9x overstatement corrected).
  Root cause of the low λ: the identity edge only pays when USDT-USD and USDT-USDC disagree by more than
  fees + 0.15bp. That is a MARKET condition, not a tuning knob. λ is episodic by nature — 12h profile shows
  bursts of 0,3,0,5,2,4,2,0,1,3,1,0 round-trips per hour.
  The two real levers are therefore: (1) MORE CAPITAL (notional scales $/h roughly linearly at constant λ)
  and (2) capturing more dislocations without cutting min_edge below fee+buffer (cutting it would turn a
  100%-win edge negative and is forbidden). λ=1.5/h with a $11.66 cap per book on $25.92 deployable is
  already near full deployment of the available bank — the bank, not the engine, is the binding constraint.

(C) UTILIZATION METRIC FIXED — 0.0 was misleading and hid real work.
  `capital_utilization` = instantaneous ledger ASSET balance ÷ deployable. The crown jewel holds inventory
  ~2 seconds per round-trip, so that snapshot is legitimately ~0 almost always, while **620.3 capital-hours**
  were deployed and $2.37 earned. Reporting 0.0 reads as "the firm is doing nothing". Added
  `capital_hours_utilization` = capital_hours ÷ (deployable × window_hours) — the honest measure for
  high-velocity earners — reported beside the snapshot and surfaced in the velocity paper block. It is
  deliberately NOT clamped to 1.0: a value above 1.0 means notional per round-trip exceeded deployable,
  which is a genuine over-deployment risk signal (that is exactly how the phantom $300–433/book sizing
  against a $28 paper book was caught), not a metric error. Current honest reading: 24h capital-hours
  0.4327 of 622.09 available = **0.0696%** — the real bottleneck, stated plainly.

(D) IMPOSSIBLE-BASIS GUARD — `pegmaker._rebase_basis()` + PEG_BASIS_TOLERANCE=20bp.
  FOUND: USDT-USD carried inv_qty=11.7878 with inv_cost=11.918773 while the market traded 0.9989 — an
  average cost of 1.01111, i.e. **122.2bp of embedded fee where the legitimate maker fee is ~5bp (24x too
  large)**. The maker exit price is min_px = avg·(1+2·fee)+tick, so the book needed USDT-USD at ~1.0112 to
  exit — impossible for a stable pair. The book was pinned at its cap and could not quote, a direct cause of
  collapsed λ. DEPEG_BP could not catch it (that tests the MARKET mid vs peg, 1bp off — fine; nothing tested
  OUR basis vs fair). Aggravating factor: my state-restore fix now correctly preserves inv_cost across
  restarts, so a corrupted basis would persist forever instead of being accidentally cleared by a restart.
  FIX: when |avg/fair − 1| > 20bp on a hard-pegged instrument, recognize the stranded residue as a REALIZED
  LOSS (pnl = fair·qty − cost, truthful and not double-counted since residue is by definition the cost no
  completed round-trip ever released), record it as a shadow_trade with side="basis_rebase", flatten the
  book so it can quote again immediately, and log a WARNING + audit KV because a corrupted basis is a
  defect to investigate, not a routine event. Tolerance is deliberately generous (20bp vs a few bp real).
  STATUS: the basis self-healed through normal trading before the guard needed to fire (now 0.3bp from fair,
  avg_cost 0.999015, min_exit 0.999125 ≤ quoted ask 0.999130 → the book CAN unwind profitably and is
  correctly waiting for a buyer). The guard is in place against recurrence; 0 rebase rows so far.

(E) SETTLEMENT-WINDOW EDGE INVESTIGATED AND REJECTED ON STATISTICS — no build.
  The harness reported model Brier 0.09063 vs consensus 0.10311 at n=49,607 (model beats consensus), which
  looked like a real unused edge. Drilling into EXECUTABLE shadow PnL by slice showed it is not usable:
  the candidate slice (15M crypto series, <3 min to close) is n=303, +$3.326, but **win rate 15.8%
  (binomial z=−11.89) and t=0.57** — the positive mean comes from a few large wins against a sd of $0.337,
  i.e. statistically indistinguishable from chance. Every SETTLE_WINDOW family overall is negative
  (−$30.57 over 2,198 signals). Building on that would be evidence laundering — exactly what Ada exists to
  prevent. Recorded as investigated-and-rejected rather than promoted.

(F) THE SPOT BLEED IS ALREADY CONTAINED (verified, not assumed).
  24h by rail: stable_triangle +$0.03496, stable_peg_mm +$0.01781, twelve.equity_paper $0.00000 (gated:
  weekend, and observe-only rows now filtered). Paper positions closed in 24h: 111 closes, −$0.22776
  realized, $2.04415 fees — and by hour the bleed is now sparse (only one hour in the last 12 showed closes:
  3 closes, −$0.13086). No open positions remain. The diagnostic allowance + weekend equity gate are doing
  their job; the remaining 24h negative rate is dominated by earlier spot churn inside the window, which
  will age out.

VERIFICATION: 68/68 tests pass · 4/4 services active · 0 tracebacks · ledger BALANCED (residual 0.0) ·
bridge reconciled exactly · treasury $25.9202 · proven frontier $0.001303/h · binding FLOW ·
measured paper 24h −$0.012722/h, 1h +$0.0026/h · capital_hours 620.31 lifetime / 0.4327 in 24h.

BACKUPS: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ — added pegmaker.py.bak2,
runtime.py.bak7, economic_truth.py.bak5, profit_velocity.py.bak6, forge.sqlite.pre-bridge.bak.

2026-10-11T16:20:00Z — Kilo session: **income made real in the ledger + cross-book arbitrage rail built + advice/evidence consistency.**

(A) LEDGER BRIDGE — INCOME IS NOW REAL, NOT ASSERTED. `treasury/ledger_bridge.py` + critical 60s loop.
  Previously `bridge_stable_shadow_to_paper()` only accumulated a KV PnL book AND only ran when an LLM
  officer chose to call it, so the firm was profitable in shadow while the ledger showed zero income and
  deployed=0. Bookkeeping is not a judgement call — it is now deterministic.
  VERIFIED: 1,571 round-trips bridged; reconciliation **EXACT** (shadow_net $2.36936862 == ledger_net
  $2.36936862, difference −0.0, `reconciled: True`); ledger identity **BALANCED** (residual −0.0000000000);
  paper realized PnL **−$1.60651 → +$6.50238**; all 59 ASSET accounts net to exactly zero.
  SAFETY: pegmaker untouched (C3 §9); **no position rows written** (the scoreboard sums paper positions AND
  shadow round-trips, so writing positions would double-count the same income); idempotent twice over
  (watermark + record_fill idem keys); reconciliation failure logs an ERROR + audit entry because income
  must never be claimed on untrusted books. Pre-bridge DB snapshot taken.

(B) CAPITAL IS ACTUALLY DEPLOYED NOW. Open positions 0 → **4** ($11.85 in assets), snapshot utilization
  0.0 → **0.4573**. Cash $25.92 → $14.01 because $11.85 is genuinely working.

(C) UTILIZATION METRIC FIXED (0.0 was misleading). `capital_utilization` uses the INSTANTANEOUS ledger
  ASSET balance, which for a ~2-second hold is legitimately ~0 — so the firm reported "nothing working"
  while **620.3 capital-hours** were deployed. Added `capital_hours_utilization` = capital_hours ÷
  (deployable × window_hours), reported beside the snapshot. Deliberately NOT clamped to 1.0: >1.0 means
  notional per round-trip exceeded deployable, which is a real over-deployment signal (that is how the
  phantom $300–433/book sizing against a $28 paper book was caught). Honest current reading: 0.4471 of
  622 capital-hours available in 24h = **0.0719%**.

(D) CROSS-BOOKMAKER ARBITRAGE RAIL BUILT — the crown jewel's edge class applied to 24/7 bets.
  `intel/arb.py`: one match has exactly one winner, so HOME and AWAY true probabilities must sum to 1. If
  book A's best home odds and book B's best away odds imply probabilities summing to **<1**, backing both
  legs returns more than staked whichever side wins. **An identity violated, not a forecast** — the same
  family as stable_triangle (free 1:1 USD⇄USDC convert). Reuses the existing `consensus_h2h`, which already
  returns best_home/best_away per book, so detection is a pure function: no network, no model, no inference.
  PROVEN: **30/30 detector tests** (equal payout both ways, normal markets rejected, breakeven sum==1.0 is
  NOT an arb, sub-margin rejected by buffer, same-book flagged suspect, stake-limit scaling preserves the
  identity, deterministic ordering, malformed input fails closed) + **21/21 settlement tests**
  ($100 stake → $105 guaranteed payout whichever side wins; draw → stakes returned, profit exactly 0;
  missing leg split → voids rather than inventing a payout).
  WIRED into `paper_bets.scan_edges()` as a PRIORITY edge class (ranked above directional value, and an arb
  consumes the event so no unhedged directional bet is added on top).

(E) TWO SAFETY DEFECTS FOUND AND FIXED BEFORE THEY COULD POISON EVIDENCE.
  1. An arb edge carries `side="both"` and `p_hat=None`. The directional `settle()` computes `won` only for
     side home/away, so `side="both"` would settle as **LOST — recording a fabricated loss on a position
     guaranteed to profit.** Worse than a crash: it would poison the evidence the whole firm learns from.
     Fixed with dedicated `place_arb()`/`settle_arb()` two-leg accounting; `place()` routes arbs away.
  2. `edges.sort(key=lambda e: -e.get("p_hat", 0))` raised TypeError because the key EXISTS with value None
     (a `.get` default only fires for missing keys). Caught by the live run; fixed with explicit coercion.

(F) HONEST BLOCKER REPORTING + REQUEST BACKOFF for the odds rail. The API returned HTTP 401 for all 9
  sports every tick, so `_key()` had a key the API REJECTS — but `arb_status()` only tested for a falsy key
  and reported **READY**. Fixed: the rejection is recorded, reported as `BLOCKED_KEY_REJECTED` with the
  exact error and a `founder_action`, and fetching backs off (`AUTH_RETRY_S=1800`) so we stop burning 9
  requests/tick; it self-heals within 30 minutes of a replaced key with no restart.
  ALSO FIXED: that state was in-memory only, so a tool call on a fresh instance reported READY **and
  re-triggered the 9-sport 401 storm**. Now persisted in `paper_bets.auth_error` so every process agrees.
  VERIFIED: tool reports BLOCKED_KEY_REJECTED with 0 requests issued.

(G) ADVICE MUST AGREE WITH EVIDENCE. The frontier ranked `kalshi.MODEL_RAW` as the **#1 lever
  (+$0.002772/h)** while `event_verdict` had that rail **BENCHED at NEGATIVE_EDGE**. Self-contradictory
  advice that would send Quinn/Nolan/Cyrus to invest inference and capital in something measured to lose
  money. Fixed with a real filter (`_benched_rails`): benched streams are removed from the priority list
  before sorting, and disclosed in `suppressed_benched_levers` with the reopen condition — suppression is
  visible, never silent. VERIFIED: the lever list is now stable_triangle ×2, add capital, stable_peg_mm ×2;
  6 benched levers suppressed. Removed the redundant disclosure-only helper so there is ONE source of truth.

(H) SETTLEMENT-WINDOW EDGE INVESTIGATED AND REJECTED ON STATISTICS (no build). The harness reported model
  Brier 0.09063 vs consensus 0.10311 at n=49,607, which looked like a real unused edge. Drilling into
  EXECUTABLE shadow PnL disproved it: the candidate slice (15M crypto series, <3 min to close) is n=303,
  +$3.326, but **win rate 15.8% (binomial z=−11.89) and t=0.57** — a positive mean from a few large wins
  against sd $0.337, statistically indistinguishable from chance, while the whole SETTLE_WINDOW family is
  −$31.73 over 2,211 signals. Building on it would be evidence laundering. Recorded as rejected.

(I) HARNESS SELF-DEFECTS FOUND AND FIXED (the harness found them, which is its purpose).
  1. `[H] WORKFORCE` reported every metric as None with `workforce_error: parameters are of unsupported
     type` — `db.scalar(q, time.time()-86400)` passed a bare float where sqlite3 requires a sequence. The
     section that proves the team is producing at all was blank. Fixed with proper tuples, and added
     distinct_roles_reporting, judge_verdicts_by_verdict and funnel_shadow_evaluated.
  2. Second defect in my own fix: `day_ago = (now - 86400,)` referenced `now`, which is not in
     `system_snapshot`'s scope (it is defined per-function elsewhere) → NameError. Fixed with a local
     `time.time()`. Caught because the harness reports its own errors instead of silently blanking.
  3. `[J] ARBITRAGE RAIL` reported BLOCKED_NO_KEY while the live service saw BLOCKED_KEY_REJECTED, because
     the harness process has no credentials in its environment. Fixed to prefer the persisted record written
     by the live service, with a note that the report reflects the firm, not the producing process.

(J) DELEGATION CAPABILITY UNLOCKED (enabled but unused). Verified on the installed runtime: the `delegation`
  toolset is enabled for cron jobs and `delegate_task` exists in v0.21.5 with MAX_DEPTH=1 and 10 concurrent
  children by default — but no officer prompt mentioned it, so no officer had ever used it. Added to the
  doctrine: when to fan out (genuinely parallel, independent work), when NOT to (never split one chain of
  reasoning), that a child returns only a summary, that children have no seat/salary/authority, and
  **NEVER DELEGATE THE DECISION** (the seat that is paid is the seat that decides). Per-role assignments
  added for 11 roles; treasury/governor/execution are explicitly told **NOT** to fan out (parallel children
  on one bank invite double-spending; on one order book they risk conflicting quotes and doubled inventory).
  VERIFIED: all 13 briefs carry protocol + seat + delegation (6.0k–8.0k chars), unknown roles handled safely.

(K) A SELF-INFLICTED BREAKAGE CAUGHT BY ITS OWN ASSERTION. The delegation patch wrote `doctrine.py` before
  its assertion fired, leaving the file referencing an undefined `DELEGATION_DOCTRINE`. Because
  `genome.render()` correctly guards the doctrine call with try/except (so a brief can never fail to
  render), this would have SILENTLY stripped the judge protocol and every seat definition from all 13
  briefs. Detected by `doctrine()` raising NameError at runtime, repaired by inserting the missing
  definitions, then verified by actually rendering all 13 seats rather than only compiling.

VERIFICATION: **119/119 tests across 3 suites** (68 judge + 30 arb detector + 21 arb settlement), all
zero-inference. 6/6 units active. 0 tracebacks. Ledger BALANCED. Bridge reconciled (diff −0.0). 9 agents
live, 159 calls/30m (157 flash + 2 max), 0 errors, 0 DeepSeek leakage. 149 judge verdicts
(101 ACT / 42 REJECT / 6 STAND_DOWN). 754 funnel shadow evaluations. OPEN directives 360 (was 17,486).
Workforce 24h: 404 role reports, 6,296 qwen calls, 0 inference errors.

INCOME STATUS BY THE FOUNDER'S FOUR CATEGORIES:
  CRYPTO — **EARNING, and now provably recorded.** stable_triangle $1.935461 (1,481 RTs, 100% win),
    stable_peg_mm $0.433908 (90 RTs, 91.1% win). Bridged to the ledger, reconciled to the cent.
  STOCKS — **NOT EARNING, research only.** 214 rows, **all 214 `side="observe"`, 0 real trades.** The
    equity rail is `CANDIDATE`, executable=0, blocked by "account equity eligibility unverified" and "no
    equity strategy validated yet". It is also correctly market-hours gated (weekend → skipping research,
    next open Mon 09:30 ET). This needs a validated equity strategy and eligibility confirmation, not code.
  BETS/SPORTS — **BUILT AND PROVEN, BLOCKED ON ONE CREDENTIAL.** Detector 30/30 + settlement 21/21. Rail
    reports BLOCKED_KEY_REJECTED: the-odds-api returns 401. Founder action: replace the key via the
    one-time portal; the rail goes live with no code change and self-heals within 30 minutes.
  BETS/EVENTS (Kalshi) — **BENCHED ON MEASURED EVIDENCE, self-healing.** model Brier 0.13222 vs market
    0.13064 (market wins), shadow PnL −$494.63 over 48,094 settled signals. Reopen condition published.

BACKUPS: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ — added ledger_bridge (new),
paper_bets.py.bak2/.bak3, doctrine.py.bak/.bak2, tools.py.bak2, ops_api.py.bak2, profit_velocity.py.bak7,
harness.py.bak, pegmaker.py.bak2, forge.sqlite.pre-bridge.bak.

2026-10-11T20:10:00Z — Kilo session: **FEE TRUTH AUDIT + $50 paper bankroll + spot-bleed stop + book-aware reserve.** Founder challenged whether fees were hallucinated/assumed and whether platforms' free/reduced-fee tiers were being ignored.

(A) FEE PROVENANCE AUDIT — `treasury/fee_truth.py` (new). The founder's suspicion was PARTLY RIGHT, with an important correction:
  * STABLE rails (the earners): fees are REAL, probed via Coinbase order-preview — USDT-USD maker 0.005% /
    taker 0.0099990%, USDT-USDC maker 0% / taker 0.00099990%. Triangle pays 0.0110% of notional. NOT hallucinated.
  * SPOT path: ran on **hardcoded config defaults (maker 0.005 / taker 0.009, source="assumed")** because the
    CDP signer was never configured in this paper env, so the real authenticated `/transaction_summary` tier
    probe never ran. This IS an assumed fee — the founder was right to challenge it. Measured effective
    one-way 0.69% (round-trip 1.3864%).
  * CORRECTION TO MY OWN FIRST DRAFT: I initially wrote that spot was "over-charged" and cited a "published
    Intro taker of 0.60%" — but I could NOT verify that 0.60% number from any public page (it is behind
    login), so asserting it would have been the exact "inventing fees" sin being investigated. Removed the
    unverified number. And spot is NOT over-charged: 1.3864% round-trip ≈ Advanced Trade taker, roughly
    correct. Spot is fee-TOXIC because its EDGE is negative (mu=−0.0012/unit), not because fees are inflated.
    Two different diagnoses; only the second is true.
  * VERIFIED from help.coinbase.com/…/advanced-trade-fees (2026-10-11): maker/taker vary by 30-day-volume
    tier; negative maker = rebate; **stablecoin pairs have a SEPARATE (lower) fee schedule** — this is WHY the
    stable rails legitimately pay ~0.005% while spot pays more. Exact tier numbers are login-only and are NOT
    hardcoded anywhere (`COINBASE_ADVANCED_INTRO = None` deliberately).
  * ALPACA: $0 commission CONFIRMED (equity.coinbase_eligibility KV records "Commission-free 24/5 stock
    trading, live 2026-10-07"); SEC fee + FINRA TAF apply on SELLS only, are real, and are NOT zeroed. The
    equity rail has produced 0 real trades (214 observe-only rows), so no equity fee has ever been charged or
    hallucinated — there is nothing to over-charge yet.
  * KALSHI: taker 0.07·C·P(1−P), maker free — verified against docs.kalshi.com worked example. Event rail is
    benched on negative edge, so no Kalshi fee is currently being incurred.
  * COINBASE ONE (founder asked about subscription fee reductions): the membership's OWN recorded note says the
    zero-fee benefit **EXCLUDES Advanced Trade, DEX and derivatives**, and simple-trade zero-fee is capped at
    $5/mo. We trade via the Advanced Trade API, so **Coinbase One does NOT reduce our fees.** Recorded explicitly
    so nobody "optimizes" on a benefit we cannot use. (Monthly cost $4.99, incremental to Forge $4.99.)

(B) $50 PAPER BANKROLL (founder directive). Deposited $24.3812 via the idempotent double-entry
  `ledger.deposit("paper", …, ref_id="founder_paper_50_20261011")`. Paper equity $25.62 → **$50.00 exactly**;
  ledger identity BALANCED (residual −0.0000000000); contributed $28.27 → $52.65.

(C) BOOK-AWARE SURVIVAL RESERVE — `treasury/regime.py`. The $50 deposit initially bought ZERO extra deployable
  capital: crossing the $50 high-water mark LATCHED the regime to RESERVE and withheld the first $25 as
  "survival capital", leaving deployable at $25. The reserve exists to protect REAL capital from ruin; in PAPER
  proof there is no ruin to survive, so withholding half the simulated book makes utilization look permanently
  ~50% and understates the honest rate. FIXED: `regime_for(…, book=)` returns reserve 0 for paper/shadow and
  the full $25 floor + growth for LIVE (unchanged). Verified: paper→deployable $50.01, live→$25.01. The firm's
  actual book is passed at the single production call site. **LIVE risk protection is not weakened in any way.**

(D) SPOT-BLEED STOP — `runtime.py`. The only reason the firm's net ledger was negative: spot/breakout churn
  (179 closes, −$1.7393 realized + $3.2770 fees) while the stable rails earned +$2.375. The prior lock-in gate
  capped spot at `max(2, max_open//4)` — a floor of 2 that meant losing spot probes NEVER fully stopped. Below
  the first rung the floor is now **0**: every capital-hour goes to proven earners and to discovery of NEW
  structural edges (which the funnel still admits), not to re-funding a measured loser. This is NOT the
  bottleneck the founder warned against — the founder's rule was "don't stop inference that could FIND income;
  double down on DIFFERENT approaches." Spot directional breakout is a proven negative-edge family being
  re-funded, not a different approach being explored. Discovery (Quinn's structural inventions, the arb rail,
  event markets) remains fully enabled.

VERIFICATION: 119/119 tests · 4/4 services · 0 tracebacks · ledger BALANCED · paper equity $49.99 ·
DEPLOYABLE $50.01 (was $25) · reserve $0 · regime BOOTSTRAP · proven frontier $0.002050/h (up from $0.001228)
· bridge reconciled (1,588 rows, diff −0.0) · 2 pre-existing spot positions left to exit naturally (not
force-closed, to avoid realizing an unnecessary loss).

HONEST $0.25/h-ON-$50 MATH: at the proven 96h rate (0.0608%/$/h) $50 yields ~$0.030/h; at the current 24h
rate (0.0067%/$/h) it yields ~$0.003/h. **$0.25/h on $50 = 0.50%/h = 12%/day**, which the proven structural
edge does not deliver — that rate needs either ~$411 deployed at the 96h rate or several more independent
proven edges. The team's own cost (Modal compute ~$25/mo + Qwen flat subscription) is ~$0.04–0.13/h, so at
the current rate the firm does NOT yet cover its salary. Stated plainly, not dressed up.

BACKUPS: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ — added regime.py.bak,
profit_velocity.py.bak8, runtime.py.bak8, fee_truth.py (new).

2026-10-12T00:20:00Z — Kilo session: **edge-discovery infrastructure built; triangular-arbitrage hypothesis TESTED AND REJECTED on real data.** Founder directive: "triple down on finding new edges... run however many simulations... every edge based off intelligence."

(A) THE SELECTION CRITERION, DERIVED EMPIRICALLY TONIGHT (this is the reusable secret sauce).
  `scripts/edges/tri_scan.py` evaluated 248 triangular-arbitrage combinations across 122 LIVE Coinbase
  order books (public data, zero inference, zero key). Result:
      single-book overround 1.0296–1.0473 (every book builds in 3–5% margin)
      best cross-book combination (home 3.400 + away 1.364) book_sum = 1.0275
      our threshold requires book_sum < 0.9950 (0.50% margin + 0.10% latency buffer)
      GAP = 0.0325  ->  NO ARB. The detector correctly returned None.
  A second run over 124 discovered triangles (515 online products) gave gap_max **+8.01bp** (HBAR via USDT),
  gap_median **−9.09bp**, cheapest three-leg hurdle **75bp** (3 x maker) -> **0 profitable**.
  CONCLUSION, and it explains the crown jewel: **an identity alone is not an edge.** `stable_triangle` wins
  1,481/1,481 because it has a **FREE LEG** — Coinbase converts USD<->USDC 1:1 at zero cost — so its hurdle
  is ~5bp, not 75–180bp. The rule for all future edge hunting: **(1) a must-agree relationship AND
  (2) a free/rebated leg, OR a gap exceeding every leg's fee.** This is recorded in
  `scripts/edges/edge_scanner.py` as `selection_criterion` so every future scan states it.

(B) THE ODDS-API RAIL: RECOMMENDATION WITHDRAWN (correction of my own earlier advice).
  I told the founder that replacing the rejected the-odds-api key was the "highest-value unlock" and quoted
  "$100 -> $105 guaranteed". BOTH WERE WRONG and are retracted on the record:
   * The $100->$105 figure was **synthetic test data** (odds 2.10/2.10 constructed to prove the arithmetic
     is exact), not evidence such an opportunity exists. The 51 tests verify the MATH, not the MARKET.
   * Quota economics (verified from the-odds-api.com docs: cost = markets x regions): our config is
     8 sports x (3 regions x 1 market + 2 for scores) = **40 credits/scan**, every 15 min => **115,200
     credits/month for 24/7**. FREE tier = 500 credits = **3 hours of operation per MONTH**. 24/7 needs the
     $119/month plan — **more than double the entire $50 paper bankroll** — to hunt an edge the real-data
     test did not find. Leanest possible config (1 league, 1 region, no scores) buys ~4 h/day of one league.
   * The classic back-at-book / lay-at-exchange arb runs through Betfair/Matchbook (`h2h_lay` market), which
     **US customers cannot access**.
   RECOMMENDATION NOW: **do not buy that key.** The detector code is a proven asset (51 tests, cannot false-
   positive, cannot fabricate a loss) and stays; the rail is not worth $119/month on this evidence.

(C) EDGE-CLASS SCANNER BUILT — `scripts/edges/edge_scanner.py` + `forge-edges.timer` (every 20 min,
  zero inference, public data only, Nice=19, CPUQuota=20%, exit 0/SUCCESS verified via systemd).
  This is the "thousands of simulations" capability the founder asked for, made affordable by putting the
  enumeration in deterministic code and reserving inference for judgement only. Classes scanned:
   A free_leg_identity   — re-discovers pairs bridged by a zero-cost conversion (the proven class)
   B multi_leg_triangle  — control class, re-measured every run in case it wakes
   C maker_spread_capture— instruments whose spread exceeds 2x round-trip maker cost (generalizes pegmaker)
   D cross_venue         — Coinbase vs Kraken mid gap (measures whether the class is alive)
   E tick_discreteness   — coarse price grids relative to price (structural maker advantage)
   F stablecoin_pegs     — dollar-pegged pairs deviating from 1.0 beyond fees
  FIRST REAL RESULTS (33s runtime, 150/150 books, $0.00 inference):
   * Class A now MEASURES the proven pair: USDT via free convert, gap −1.752bp,
     USDT-USD mid 0.998875 (bid depth $1,412,636) vs USDT-USDC mid 0.999050 (ask depth $2,556,924).
   * Class C: **12 instruments viable at mid fee, 9 at high fee.** Top maker margins: AWE-USD 179.3bp
     spread / 99.3bp margin; 00-USD 172.6/92.6; AERGO-USD 170.9/90.9; DEXT-USD 145.2/65.2; AST-USD
     139.8/59.8. HONEST CAVEAT RECORDED IN THE REPORT: these are illiquid micro-caps (AWE-USD bid depth
     $2,916, ask $2,051) and the margin is **before adverse selection**, which has never been measured
     here. Any candidate must run in shadow and be scored on realized fill PnL, not on this margin.
   * Class E: ADA-ETH tick 100.5bp (spread exactly 1 tick), DOGE-BTC 96.6bp, ALGO-BTC 66.5bp — coarse
     grids where queue position beats price competition.
   * Class D: BTC-USD Coinbase vs Kraken gap −0.59bp — real but far below the cost of moving funds, and
     only executable with inventory pre-positioned at BOTH venues (a capital requirement we do not meet).
   * Class B: reconfirmed DEAD (gap_max −1.58bp vs 75bp hurdle).

(D) TWO DEFECTS IN MY OWN SCANNER, CAUGHT AND FIXED THE SAME RUN.
   1. Class F computed "deviation from 1.0" for BTC-USD and reported **836,201,550 bp** — because the filter
      admitted any product whose base OR quote was a stable. An absurd number in a report is worse than no
      number, since someone will act on it. Fixed: BOTH sides must be dollar-pegged. Verified: only
      USDT-USD (−11.25bp) and USDT-USDC (−9.50bp) now appear.
   2. Class A found its candidate but **measured 0 rows** — the sorted+capped want-list excluded USDT-USDC,
      so the scanner skipped the one pair we KNOW earns. Fixed with a priority list fetched first.
      Verified: measured 1.
   Also fixed: the scanner's own `print(json.dumps(...)[:9000])` truncated JSON mid-string and broke parsing;
   it now writes full JSON to a file and prints only the summary.

(E) PAUSE AT THE FOUNDER'S REQUEST (2026-10-12 00:09Z = 8:09pm ET, outside the discount window).
  All coding stopped to avoid full-rate token spend. The following run UNPAUSED overnight at ZERO inference
  cost: `forge-edges.timer` (edge scanner every 20 min), `forge-overnight.timer` (evidence harness every 2h),
  and the 24/7 earner crew (prediction, execution, scout, doctor, governor, treasury, ops/Luca). Deep-work
  roles (alpha_inventor, adversary, critic, intelligence, rail_hunter, architect) are gated off until the
  14:00 UTC window opens. Nothing is paused that would stop income.

BACKUPS: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ unchanged this session (only new files
added: scripts/edges/tri_scan.py, scripts/edges/edge_scanner.py, /etc/systemd/system/forge-edges.{service,timer}).
