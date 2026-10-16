# Session journal — Hermes DeepSeek → Alibaba Token Plan Qwen3.8-Max migration

- **Agent:** Kilo (lead executive engineer), command center → remote /srv/forge.
- **Session:** 20261009T213224Z
- **Authorized scope (founder, this session):** Move ALL Hermes agents (officers + Luke/ops + eng) off DeepSeek onto Alibaba Cloud Model Studio **Token Plan / qwen3.8-max**; assign extra-high (xhigh) reasoning to decision-makers and medium to high-frequency monitors; keep the whole team always-on to attack the STALE/402-starvation failure. Read-only rehydration already completed earlier this session.
- **Boundary:** FORGE only (/srv/forge). Other projects untouched. No LIVE trading, no transfers, no credential changes beyond adding the Token Plan key to Hermes .env files.

## Key research findings (verified)
1. Alibaba **Token Plan** officially supports **Hermes Agent** as a client (dedicated integration page + `bl config agent --agent hermes`). Founder's `o1_...` key is an *agent-scoped* credential; `bl` decodes it to the Token Plan `sk-sp-` key. sha256 of decoded key == command-center stored key (same subscription).
2. Token Plan OpenAI-compatible endpoint `https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1` verified live: qwen3.8-max returns real `reasoning_content`; `reasoning_effort: xhigh` and `medium` both accepted (docs: high/max→xhigh). Context 1,000,000; reasoning_caps lists xhigh/high/medium/low/minimal.
3. Hermes ships a native `alibaba-token-plan` provider profile (env ALIBABA_TOKEN_PLAN_API_KEY). Forge config convention uses named providers + key_env in .env → follow that (secret stays out of config.yaml).
4. **Compliance line:** Token Plan permits coding/agent TOOLS (Hermes) but PROHIBITS application-backend direct API calls. Therefore the **Forge internal Python brain (forge.service, direct httpx) stays on DeepSeek** — repointing it would violate terms AND break its balance-based admission. Only Hermes officers/Luke/eng move to Token Plan.
5. Officers previously routed through the budget proxy (custom:forge-budgeted → /api/agent/inference/v1 → DeepSeek) which emitted HTTP 402 admission-denied and starved them STALE. Direct Token Plan (paid Credits) removes that wall.

## Plan
- Add ALIBABA_TOKEN_PLAN_API_KEY to hermes/ops/eng .env (stdin, never printed).
- Add named provider `alibaba-token-plan` (transport chat_completions, key_env, qwen3.8-max ctx 1M) to each config.yaml; set model.provider/default + cron.model/model_provider to it; global agent.reasoning_effort xhigh + reasoning_overrides qwen3.8-max: xhigh.
- Per-job jobs.json reasoning_effort: xhigh for governor, alpha-inventor, adversary, critic, architect, daily-report(Luke); medium for doctor, scout, rail-hunter, prediction, execution, treasury, intelligence (frequent monitors — preserve Credits so team never goes STALE).
- Restart forge-hermes/ops/eng; verify a live officer wake hits qwen3.8-max with thinking + correct effort.
- Update CURRENT_STATE/CHANGELOG. Follow-up: cost attribution now in Hermes/Alibaba console, not Forge brain ledger (ties to FQ2).

## Rollback
Restore $BK/*.bak (config.yaml, .env, jobs.json) and restart the three services. forge-budgeted/deepseek providers left defined but unused.

## Checkpoint — IMPLEMENTED + VERIFIED (2026-10-09 ~22:00 UTC)
- IMPLEMENTED: 3 config.yaml switched to provider `qwen-token-plan` (key_env ALIBABA_TOKEN_PLAN_API_KEY in .env, 0600); cron jobs effort xhigh/medium per policy; hermes.mode=subscription; agent_api.py subscription_allowance patch (backup beside it, py_compile OK); services restarted, all 4 active.
- VERIFIED: /api/agent/allow → mode=subscription, wake=true (was wake=false denied_budget_or_critical); live `hermes chat` on hermes/ops/eng homes returns via qwen3.8-max; inference_calls shows qwen3.8-max rows for governor/doctor/ops with large tool-loop contexts, no errors; scheduler runs continue (doctor woke on schedule).
- OBSERVED GAP (not blocking): inference_calls.effort empty for qwen rows — usage reported via hermes-forge plugin hook lacks effort field; wire-level effort confirmed accepted earlier via direct API probe (reasoning_content present with xhigh). Attribution fix queued under FQ2.
- Direct-triggered governor run (9953d052) still executing at checkpoint — xhigh deep work is slower than Flash; will close on its own. Natural scheduler runs unaffected.
- NEXT ACTION: monitor next 2–3 scheduled officer cycles for durable role_reports; then return to FQ0/P0 ledger work per WORK_QUEUE.

## Checkpoint 2 — Constitution C2 + RATE-THEN-SCALE (2026-10-09 ~22:35 UTC)
- IMPLEMENTED: constitution.py (C1→C2, new §8), roles.py COMMON_FACTS, genome.py world_state/_velocity_headline, 13 boot prompts, 13 live cron prompts, ops SOUL.md. All compile-verified; forge.service restarted; services active.
- VERIFIED: C2 + doctrine import clean; 13/13 cron prompts contain RATE-THEN-SCALE; live velocity KV exposes regime=BOOTSTRAP, deployable=10.27, capital_utilization=0.0 to briefs.
- Design rationale: Constitution/COMMON_FACTS are the only prompt layers that prompt-evolution cannot mutate (FORBIDDEN_PATTERNS + server-side render) — doctrine placed there is permanent. Deterministic scaling machinery (regime engine, bankroll ladder, velocity caps ∝ D) already existed and now matches the agents' cognition of it.
- NEXT ACTION (top economic lever): deploy loop — proven `coinbase.stable_peg_mm` must open and hold positions continuously in PAPER (capital_utilization 0.0% is the binding FLOW constraint); then measure trustworthy $/h via FQ0/P0 ledger work.

## Checkpoint 3 — prompt-engineering forensic pass (2026-10-09 ~23:40 UTC)
- Trigger: founder flagged Mira's generic-AI persona. Forensic scan across boot prompts + genome (roles.py) + plugin + hook.
- IMPLEMENTED: (a) added prediction(Nolan)+intelligence(Mira) genomes [were absent]; (b) reframed architect genome Rowan→fintech income-infra CTO (was prompt-evolution, colliding with Mira); (c) Mira boot persona finance-contoured; (d) fixed brief double-truncation (dispatch _fit_json 30k→brief-exempt + 120k; plugin 24k→200k); (e) pre_llm hook now forces first-turn get_role_brief pull; (f) COMMON_FACTS alias map corrected; (g) directives_for capped to top-12 distinct. All compile-verified; forge+3 gateways restarted.
- VERIFIED: 13/13 roles return full structured C2 briefs (25–35KB), no truncation, live capital/regime/world-state present; governor@v1 now len=29776 with all keys (was truncated blob).
- Persona-contour audit result: Cyrus/Quinn/Vale/Ada/Tess/Reid/Ellis/Sloane/Casey/Luke were already finance-framed; Mira was generic-AI (fixed); Rowan genome was mis-scoped (fixed); Nolan had no genome (added). No remaining generic-tech persona in the officer layer.
- NEXT ACTION: unchanged — deploy loop (capital_utilization 0.0%) + FQ0/P0 ledger truth; then observe next officer cycles for durable genome-bound role_reports.

## Checkpoint 4 — FOUNDER-ORDERED PAUSE (2026-10-10 03:25 UTC)
- All 13 cron jobs paused (hermes cron pause; state=paused verified in jobs.json). forge-hermes/ops/eng stopped; no hermes processes; zero inference calls since 03:24:00Z (post-shutdown window verified over 75s). reset-failed applied (SIGTERM exit cosmetics).
- forge.service ACTIVE by design: deterministic only, zero tokens, preserves PAPER desk. No trading settings touched.
- SESSION STATE AT PAUSE: overnight Qwen upgrades deployed+verified (C2, 13/13 genomes, brief delivery fixed, wake gate fixed). In-flight governor xhigh session completed during shutdown (harmless).
- RESUME (founder instruction expected in the morning): systemctl start forge-hermes forge-ops forge-eng → hermes cron resume ×13 → verify scheduled + wake=true → continue FQ0/deploy-loop work.

## Checkpoint 5 — Founder morning directives: schedule + milestone ladder + finance-contour (2026-10-10 ~15:15 UTC)
- RESUME: gateways started, 13 jobs resumed (state=scheduled), Qwen verified across 13 agents, zero DeepSeek leakage.
- IMPLEMENTED: gate v2 (business-hours = Alibaba off-peak 14:00–24:00 UTC; 24/7 earner crew after hours; equities 24/5 discipline); Constitution C3 (§9 milestone ladder+lock-in, §10 secret-sauce); COMMON_FACTS + 13 boot + 13 cron prompts carry doctrine; Luke SOUL.md + ops@v2 genome (never-paused, team power switch, financial-advisor identity, roster fix); Nolan prediction@v3 + Kalshi playbook; 15-agent finance audit.
- VERIFIED: C3/ladder/sauce/business-hours/eq-24/5 render in all sampled live briefs; ops@v2 renders (31KB, all upgrades); 16 genome-bound reports/45min; gate sim shows deep-work SKIP outside window, crew WAKE.
- TEAM SELF-SURFACED (real forensics): phantom deployed_usd survives restart (ledger corruption); peg_mm telemetry reset fills 38→0 mid-flight; USDT-USD mark frozen 12h (+7.2% PnL overstatement); Vale RISK_GATE FREEZE (pegmaker inventory 10.44× cap, one-sided bid=null). This is the deploy-loop blocker → FQ0.
- NEXT ACTION: FQ0 ledger truth (phantom deployed_usd + peg telemetry persistence) so stable_peg_mm clears freeze and deploys; then trustworthy $/h toward $0.25 rung. Founder may move to LIVE this evening/tomorrow IF ≥$0.25/h proven on reconciled ledger + founder auth.


## Checkpoint 6 — inference tiering + capital engine unblocked + crown jewel (2026-10-10 ~22:50 UTC)
- RESEARCH: Alibaba Token Plan docs confirm qwen3.8-max AND qwen3.8-flash both enabled on our key, both
  with the 60% night discount 22:00-08:00 UTC+8 (=10:00-20:00 ET, founder's Florida business hours).
  Hermes is an officially supported Token Plan client (coding/agent tool scope) — compliant.
- BENCHMARKED before deciding: max prod avg 89.3s/max 2178.8s; max@high and max@xhigh TIMEOUT >420s;
  max@medium 273s. flash prod avg 35.7s; flash@medium 31.2s with 1744 reasoning tokens; flash@high and
  flash@xhigh TIMEOUT >400s. Conclusion: reasoning DEPTH was never the bottleneck, LATENCY was.
- IMPLEMENTED: Flash registered on all 3 homes; 12 officers + Luca on Flash@medium; Quinn alone on
  Max@medium; schedules staggered for the concurrency cap; Luca rename across 21 files (functional ids
  preserved); founder floor Flash>=medium enforced.
- ROOT CAUSES FIXED: treasury() read the real wallet instead of the paper book (deployable $0.00);
  income_block() ignored scope+expiry (crown jewel locked out of the frontier).
- HYGIENE: idempotent directive/objective emit + backlog collapse (17,486->1,018->277 OPEN; 153->6
  objectives); milestone-stall escalator added; paper scoreboard added with documented fee semantics;
  fixed a circular dependency I had introduced (util 28.95 -> clamped, deployable passed in).
- CROWN JEWEL: stable_triangle analysed, capacity-scanned, locked in as protected what_is_working with
  owner + mechanism + scaling math + a mechanism-class mandate for invention in COMMON_FACTS.
- VERIFIED: 0 errors/tracebacks across all restarts; ledger BALANCED; deepseek leakage 0; inference
  errors 0; 18 durable role_reports/60m across 9 roles; Luca 35s; crown jewel #1 marginal lever.
- NEXT ACTION: raise deployed notional per cycle and lam on the crown jewel; measure the rate toward the
  $0.25 rung; then bring the founder the evidence for micro-LIVE authorisation.


## Checkpoint 7 — Forge-Jev + funnel + inference economy + Luca power switch (2026-10-11 ~03:55 UTC)
- INPUT: founder uploaded the savip Grok-Bot desk guide (two threads) to the paste board and ordered it
  RESEARCHED, cross-referenced against Forge, and improved on — not copied, and without Grok bots.
- VERIFIED EXTERNALLY before acting: typesafe.ai (System One Models, typed decisions + calibrated
  confidence, $42/B-tok ≈ the quoted $0.042/Mtok, 70-500ms); koala73/worldmonitor (88.2k stars, AGPL-3.0,
  self-hostable, MCP); Kalshi + Polymarket public APIs both live; our Token Plan key serves BOTH
  qwen3.8-max AND qwen3.8-flash (qwen-flash/qwen-plus/qwen3-max do NOT exist on it).
- DISCOVERED BEFORE BUILDING: Forge already had the hardest part — `research/calibration.py`
  CalibrationEngine (PAV isotonic, source-weighted, skeptical prior) with 4,072 realized points, plus
  `calibration_points`, `agent_predictions`, `crossrail_calibration` (46,713 rows) and `sw_calibration`
  (43,352). So we manufacture calibration instead of renting it; the judge reuses that engine.
- BUILT: src/forge/judge/ (primitives, questions, calibrator, funnel, checks, judge, salary, schema,
  thresholds, doctrine, event_verdict, __init__), 5 judge tables, 6 officer tools, an hourly economy loop,
  per-role doctrine rendered into every brief, and a zero-inference overnight harness on a 2h timer.
- DECISION that changed the architecture: the judge is NOT a backend LLM pump. Token Plan prohibits
  non-interactive backend calls, so the officer answers inside its own interactive run — cheaper,
  compliant, and the judgement lands in that officer's track record.
- ROOT-CAUSED AND FIXED: three dead wake paths (Popen+sudo under NoNewPrivileges, returning True while
  doing nothing) — every historical FORCE_WAKE was false. Replaced with a queued+reconciled protocol.
- VERIFIED: 68/68 tests; all 5 tools live through the agent API; officer ask→commit returns ACT with
  size_factor 0.4 and calibrated 0.74; power switch pause/resume/status/wake end-to-end with actor
  attribution and 4/4 concurrency; shadow funnel writing real rows; harness exit 0 via systemd;
  4/4 services active; 0 tracebacks; 0 DeepSeek leakage.
- SELF-CAUGHT DEFECTS: 11 itemised in CHANGELOG, incl. 2 caught pre-apply, 1 production poisoning cleaned
  with a prior snapshot, and 1 misleading metric I had just written.
- NEXT ACTION: read the accumulated overnight reports; promote the funnel from shadow to enforcing once
  agreement holds over more decided candidates; raise deployed notional per cycle and unblock the pinned
  USDT-USD book; Nolan targets beating market Brier to reopen the event rail.


## Checkpoint 8 — overnight verification + bots research + salary fix (2026-10-11 ~14:35 UTC)
- VERIFIED overnight: business-hours gate correct (2,089 crew calls, 0 deep-work); 2,152 calls / 88.5M
  tokens at $0 cash (flat plan); earners ran all night (+$0.0428, 37 RTs); 0 errors; ledger BALANCED.
- FIXED (own defect): salary.py charged fabricated DeepSeek-fallback cost_usd as seat salary under a flat
  plan -> 7 false CRITICALs that would throttle income-seeking seats at LIVE. Now honest: metered-only cash,
  quota for subscription, overhead only if priced, never CRITICAL without a cost basis. 0 CRITICAL after.
- RESEARCHED Hermes bots: Bot Mode = desktop UI over profiles (not for headless server; adds processes).
  The right mechanism is delegate_task subagents (10 concurrent, depth 1) — ALREADY ENABLED for officers
  but unused because no prompt tells them to. Doctrine change queued, not an install.
- VERSION: v0.21.5 installed; v0.21.6 available (4 security fixes, 2,100-PR rollup, no curated notes).
  Update = deliberate founder decision with tested rollback. NOT done today.
- LOCATED (not built): deployed=$0 because bridge_stable_shadow_to_paper() only writes a KV PnL book,
  never posts ledger positions, and only runs when an officer calls it. NEXT BUILD: deterministic bridge
  that posts real paper positions so utilization/deployed become true.
- 68/68 tests pass; 0 tracebacks across restarts.


## Checkpoint 9 — ledger bridge live + λ correction + basis guard (2026-10-11 ~15:25 UTC)
- BUILT: treasury/ledger_bridge.py + critical 60s deterministic loop. All 1,570 proven round-trips posted
  to the paper ledger. Reconciled EXACTLY (diff -0.0), identity BALANCED, paper realized -$1.61 -> +$6.50,
  cash $23.55 -> $25.92, 59 ASSET accounts net to zero. Idempotent twice; no position rows (would
  double-count the scoreboard); pegmaker untouched.
- CORRECTED MY OWN MORNING PROJECTION: λ is 1.50/h now, not 20.2/h (that was the stale 96h average inflated
  by phantom over-sizing). Honest rate 0.006692%/$/h => $0.25/h needs ~$4,000 deployed, not ~$380. A ~9x
  overstatement, corrected on the record rather than left standing.
- FIXED: capital_hours_utilization added (instantaneous snapshot reads 0.0 for a 2s-hold earner while 620.3
  capital-hours were genuinely deployed). Honestly reported: 0.0696% of available capital-hours in 24h.
- FIXED: impossible-basis guard (20bp tolerance) — USDT-USD carried 122.2bp of embedded fee vs ~5bp legit,
  pinning the book at cap so it could not quote. Recognizes stranded residue as a realized loss, flattens,
  warns, audits. Self-healed to 0.3bp before firing; book verified healthy and able to unwind.
- REJECTED ON STATISTICS: the settlement-window "edge" (t=0.57, win rate 15.8%, z=-11.89). Not built.
  Building on it would be evidence laundering.
- VERIFIED: 68/68 tests, 4/4 services, 0 tracebacks, bridge reconciled, spot bleed contained (111 closes
  in 24h but only 1 of last 12 hours had any), no open positions, equity gate holding on the weekend.
- HONEST CONCLUSION FOR THE FOUNDER: the firm now provably earns in paper (~$0.0428 overnight at $0 cash),
  and the money is in the ledger rather than asserted. But the rate is ~$0.0017/h on a $26 bank. The
  binding constraint is CAPITAL and the number of independent proven edges — not prompts, not effort, not
  agent count. Cutting min_edge or thinning evidence to flatter the number is forbidden.
- NEXT ACTION: raise deployed notional per cycle as capital grows; Quinn to invent in the structural class
  (identity/carry/fee-asymmetry) with Ada's evidence bar; do not lower any threshold to chase λ.


## Checkpoint 10 — ledger bridge live + arbitrage rail built + advice/evidence consistency (2026-10-11 ~16:20 UTC)
- BUILT ledger_bridge.py as a critical 60s deterministic loop: 1,571 round-trips bridged, reconciled
  EXACTLY (diff -0.0), identity BALANCED, paper realized -$1.61 -> +$6.50, 59 ASSET accounts net to zero.
  No position rows (would double-count the scoreboard); pegmaker untouched; idempotent twice over.
- CAPITAL NOW DEPLOYED: 4 open positions, $11.85 working, utilization 0.0 -> 0.4573.
- FIXED the utilization metric: added capital_hours_utilization (620.3 capital-hours deployed while the
  instantaneous snapshot read 0.0 and looked like "nothing working").
- BUILT cross-bookmaker arbitrage (intel/arb.py) — the crown jewel's identity edge class applied to 24/7
  sports. 30/30 detector + 21/21 settlement tests. $100 stake -> $105 guaranteed payout either way.
  Wired as a priority edge class above directional value.
- FIXED 2 safety defects before they poisoned evidence: side="both" would have settled an arb as LOST
  (fabricating a loss on a guaranteed-profit position); sort crashed on p_hat=None.
- FIXED dishonest blocker reporting: odds API 401s on 9 sports/tick while arb_status said READY (in-memory
  flag lost per instance, also re-triggering the request storm). Now persisted, honest, backed off 30m,
  self-healing on key replacement.
- FIXED advice contradicting evidence: kalshi.MODEL_RAW was ranked the #1 lever while the event rail was
  BENCHED at NEGATIVE_EDGE. Benched streams now filtered out and disclosed with their reopen condition.
- REJECTED an edge on statistics: settlement-window "model beats consensus" (n=49,607) is t=0.57, win rate
  15.8%, z=-11.89 — chance, not edge. Not built. Recorded as investigated-and-rejected.
- FIXED 3 harness self-defects it surfaced itself: workforce section blanked by a bare-float sqlite param;
  then a NameError from out-of-scope `now`; then arb status reporting this process's environment instead of
  the firm's state.
- UNLOCKED delegate_task (already enabled, never used): doctrine + per-role assignments; treasury/governor/
  execution explicitly told NOT to fan out. All 13 briefs verified carrying protocol+seat+delegation.
- SELF-INFLICTED BREAKAGE caught by its own assertion: doctrine.py written before the assert fired, leaving
  an undefined name that would have silently stripped the judge protocol from all 13 briefs (render() guards
  it by design). Caught by rendering all seats, not by compiling.
- VERIFIED: 119/119 tests, 6/6 units, 0 tracebacks, ledger BALANCED, bridge reconciled, 9 agents live,
  159 calls/30m, 0 errors, 0 DeepSeek leakage, 149 judge verdicts, 754 funnel evaluations, 404 reports/24h.
- HONEST STATUS by the founder's four categories: CRYPTO earning and recorded; STOCKS research-only (214
  observe rows, 0 trades, rail CANDIDATE); SPORTS ARB built+proven but blocked on a rejected API key;
  KALSHI EVENTS benched on measured negative edge.
- NEXT ACTION: founder replaces the the-odds-api key (unlocks a proven 24/7 rail, no code change);
  equities need a validated strategy + eligibility confirmation; λ is 1.5/h not 20.2/h so $0.25/h needs
  ~$4,000 deployed OR more independent proven edges at a similar rate.


## Checkpoint 11 — fee truth audit + $50 bankroll + spot-bleed stop (2026-10-11 ~20:10 UTC)
- FOUNDER CHALLENGE: "are fees real or assumed? platforms offer free/reduced fees; Alpaca is $0 commission;
  Coinbase/Kalshi have subscriptions." Audited every fee to its source.
- VERDICT: earners use REAL probed fees (order-preview); SPOT used hardcoded assumed 0.005/0.009 because the
  CDP signer was never configured so the real tier probe never ran. Founder was RIGHT that a fee was assumed.
- SELF-CORRECTIONS: (1) removed an unverified "0.60% published Intro" number I had drafted — could not confirm
  it publicly, so refused to invent it; (2) spot is NOT over-charged (1.3864% RT ≈ taker) — it is fee-TOXIC
  because its EDGE is negative, a different and true diagnosis.
- Coinbase One verified to EXCLUDE Advanced Trade (our path) -> does not reduce our fees. Alpaca $0 commission
  confirmed, SEC/TAF on sells real. Kalshi 0.07·C·P(1−P) verified. Stablecoin pairs have a separate lower
  schedule (why stables pay ~0.005% vs spot more) — verified from help.coinbase.com.
- $50 PAPER BANKROLL deposited via idempotent ledger.deposit; equity $50.00, identity BALANCED.
- FOUND: the $50 bought 0 extra deployable — crossing $50 HWM latched RESERVE and withheld $25. Made reserve
  book-aware: paper/shadow reserve=0 (no ruin to survive), LIVE keeps full $25 protection. Deployable now $50.01.
- STOPPED THE SPOT BLEED: floor was max(2,…), so 2 losing spot probes always stayed open. Below the rung the
  floor is now 0. Spot was the ONLY net-negative rail (−$1.74 realized + $3.28 fees vs stables +$2.375).
- VERIFIED 119/119 tests, 0 tracebacks, ledger BALANCED, deployable $50.01, bridge reconciled 1,588 rows.
- HONEST: $0.25/h on $50 = 12%/day; proven edge gives ~$0.03/h at best. Team cost ~$0.04–0.13/h. The firm does
  NOT yet cover its salary. Path: full $50 now working on proven earners + replace the odds-api key to light the
  proven arb rail + Quinn invents more structural edges. No min_edge cutting.


## Checkpoint 12 — edge discovery infrastructure + triangular arb rejected on real data (2026-10-12 ~00:20 UTC)
- BUILT: scripts/edges/tri_scan.py (248 evaluations, 122 live books) and scripts/edges/edge_scanner.py
  (6 edge classes) + forge-edges.timer (20 min, zero inference, systemd exit 0 verified).
- DERIVED THE SELECTION CRITERION: identity + FREE LEG (or gap > all legs' fees). stable_triangle has a free
  USD<->USDC convert leg -> 5bp hurdle -> 1,481/1,481 wins. Three-leg crypto triangles -> 75-180bp hurdle vs
  +8.01bp max observed gap -> 0 profitable. Triangular arbitrage on Coinbase crypto is REJECTED on evidence.
- WITHDREW MY OWN ODDS-API RECOMMENDATION: the "$100->$105 guaranteed" was synthetic test data proving the
  MATH, not evidence of the MARKET. Quota math: 40 credits/scan x 96 scans/day = 115,200/mo for 24/7; free
  tier = 500 credits = 3 HOURS/month; 24/7 needs $119/mo vs a $50 bankroll. Lay-side arb needs Betfair,
  unavailable to US customers. Do not buy the key.
- FIRST SCANNER RESULTS ($0.00 inference, 33s, 150/150 books): Class A measured the proven pair (USDT gap
  -1.752bp, $1.4M/$2.6M depth); Class C found 12 instruments viable at mid fee (AWE-USD 99.3bp maker margin)
  BUT illiquid and pre-adverse-selection — flagged, not claimed; Class E coarse-tick structural advantage
  (ADA-ETH 100.5bp); Class D cross-venue BTC gap -0.59bp (unexecutable at our capital); Class B dead.
- SELF-CAUGHT DEFECTS: Class F reported BTC-USD as 836,201,550 bp from peg (base-OR-quote filter) — fixed to
  require both sides dollar-pegged; Class A measured 0 rows because the want-list excluded USDT-USDC — fixed
  with priority fetching; JSON truncation broke its own output parsing — fixed.
- PAUSED at founder request 00:09Z (outside discount window). Zero-inference work continues overnight:
  edge scanner every 20 min, evidence harness every 2h, 24/7 earner crew. Deep-work roles gated to window.
- NEXT ACTION (on founder return at 10am ET): read accumulated scans; test whether Class C maker margin is
  PERSISTENT across ~30 overnight scans; if yes, build the shadow adverse-selection measurement — the missing
  number that decides whether a wide spread is income or a trap. Quinn's mandate: classes with a free/rebated
  leg only (C and E qualify; B and D do not).
