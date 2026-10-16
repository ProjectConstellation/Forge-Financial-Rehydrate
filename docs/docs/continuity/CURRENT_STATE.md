# Latest checkpoint — EDGE DISCOVERY: criterion derived, triangular arb rejected on real data, scanner live

2026-10-12T00:20Z — Founder directive: triple down on finding NEW proprietary edges, run thousands of
simulations, every edge based on intelligence. The infrastructure for that is now built and running, and the
first hypothesis has been tested against real market data and **rejected on evidence** — which is more useful
than another unverified idea.

**THE SELECTION CRITERION (derived empirically tonight, now the standing rule for edge hunting).**
An identity alone is NOT an edge. `stable_triangle` wins 1,481/1,481 because it has a **FREE LEG** — Coinbase
converts USD<->USDC 1:1 at zero cost — giving it a ~5bp capture hurdle. A three-leg crypto triangle pays all
three legs: hurdle 75bp (maker) to 180bp (taker). Scanned across **122 live order books and 248 combinations**:
max observed gap **+8.01bp** (HBAR via USDT), median **−9.09bp**, **0 profitable**. Every single book builds
in 3–5% overround (1.0296–1.0473). The rule: **(1) a must-agree relationship AND (2) a free/rebated leg, or a
gap exceeding every leg's fee.** Recorded in the scanner so every future run states it.

**MY ODDS-API RECOMMENDATION IS WITHDRAWN — corrected on the record.** I told the founder that replacing the
rejected the-odds-api key was the highest-value unlock and quoted "$100 -> $105 guaranteed". Both were wrong:
that figure was **synthetic test data** (odds 2.10/2.10 constructed to prove the arithmetic is exact), not
evidence such an opportunity exists — the 51 tests verify the MATH, not the MARKET. And the quota economics
(verified from the vendor's docs: cost = markets x regions) are **40 credits/scan every 15 min = 115,200
credits/month for 24/7**. The FREE tier is 500 credits = **3 hours per month**; 24/7 needs the **$119/month**
plan, more than double the entire $50 paper bankroll, to hunt an edge the real-data test did not find. The
classic lay-side arb runs through Betfair/Matchbook, which **US customers cannot access**. **Do not buy that
key.** The detector stays — it is proven and cannot false-positive — but the rail is not worth its data cost.

**EDGE-CLASS SCANNER LIVE.** `scripts/edges/edge_scanner.py` + `forge-edges.timer` (every 20 min, **zero
inference**, public data, Nice=19, CPUQuota=20%, verified exit 0 via systemd). This is the "thousands of
simulations" capability made affordable: enumeration lives in deterministic code, inference is reserved for
judgement. Six classes scanned — A free-leg identity, B multi-leg triangle (control), C maker-spread capture,
D cross-venue, E tick discreteness, F stablecoin pegs.

**FIRST REAL RESULTS (33s, 150/150 books, $0.00 inference):**
- **Class A (the proven class) now measured:** USDT via the free convert, gap −1.752bp; USDT-USD mid
  0.998875 with **$1,412,636 bid depth**, USDT-USDC mid 0.999050 with **$2,556,924 ask depth**. Depth is
  genuinely abundant — the constraint is gap frequency (λ≈1.5/h), not size.
- **Class C — the most promising new lead:** 12 instruments viable at mid fee, 9 at high fee. Top maker
  margins: AWE-USD 179.3bp spread / **99.3bp margin**; 00-USD 172.6/92.6; AERGO-USD 170.9/90.9;
  DEXT-USD 145.2/65.2; AST-USD 139.8/59.8; A8-USD 130.9/50.9. **HONEST CAVEAT (recorded in the report):**
  these are illiquid micro-caps (AWE-USD bid depth $2,916, ask $2,051) and the margin is **BEFORE adverse
  selection**, which has never been measured on this desk. Any candidate must run in shadow and be scored on
  realized fill PnL, not on this margin. This is the same class as the pegmaker, generalized beyond stables.
- **Class E:** ADA-ETH tick = 100.5bp with spread exactly 1 tick; DOGE-BTC 96.6bp; ALGO-BTC 66.5bp — coarse
  grids where queue position beats price competition, an advantage that does not decay with volume.
- **Class D:** BTC-USD Coinbase vs Kraken gap **−0.59bp** — real but far below the cost of moving funds, and
  executable only with inventory pre-positioned at BOTH venues (a capital requirement we do not meet at $50).
- **Class B:** reconfirmed DEAD (gap_max −1.58bp vs 75bp hurdle). Re-measured every run in case it wakes.

**TWO DEFECTS IN MY OWN SCANNER, CAUGHT AND FIXED THE SAME RUN.** (1) Class F computed "deviation from 1.0"
for BTC-USD and reported **836,201,550 bp**, because the filter admitted any product whose base OR quote was
a stable — an absurd number in a report is worse than none, since someone will act on it. Fixed: both sides
must be dollar-pegged; verified only USDT-USD (−11.25bp) and USDT-USDC (−9.50bp) appear. (2) Class A found its
candidate but measured 0 rows, because the sorted+capped want-list excluded USDT-USDC — the scanner skipped
the one pair we KNOW earns. Fixed with a priority list fetched first; verified measured=1. Also fixed the
scanner truncating its own JSON mid-string.

**PAUSED AT THE FOUNDER'S REQUEST** (00:09Z = 8:09pm ET, outside the discount window) to avoid full-rate
token spend. Still running overnight at **zero inference cost**: `forge-edges.timer` (edge scanner, 20 min),
`forge-overnight.timer` (evidence harness, 2h), and the 24/7 earner crew (prediction, execution, scout,
doctor, governor, treasury, Luca). Deep-work roles stay gated until the 14:00 UTC window opens. **Nothing
that generates income is paused.**

**RESUME PLAN (founder returns 10am ET = 14:00 UTC, and only when he returns):**
1. Read the accumulated edge scans (`/srv/forge/var/reports/edges/`) — ~30 more scans will have run overnight.
   The key question: is Class C's maker margin persistent across scans, or was one snapshot lucky?
2. If persistent, build the **shadow adverse-selection measurement** for Class C candidates — the missing
   number that decides whether a 99bp spread margin is real income or a trap. This is the highest-value next
   build and it costs zero inference.
3. Quinn's mandate is now precise: invent in classes with a **free or rebated leg**. Class C (maker rebate
   economics) and Class E (tick discreteness) both qualify; Class B and D do not.
4. The crown jewel's λ is the binding constraint on existing income; USDT-USD inventory sits at its per-book
   cap, so unblocking inventory rotation is a free λ lever.

Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/. New files this session:
`scripts/edges/tri_scan.py`, `scripts/edges/edge_scanner.py`, `/etc/systemd/system/forge-edges.{service,timer}`.

---

# Latest checkpoint — fee truth audited, $50 paper bankroll live, spot bleed stopped

2026-10-11T20:10Z — The founder asked three pointed questions (does everything work / does it earn / if not
why) and challenged whether fees were assumed or hallucinated and whether platform free/reduced-fee tiers were
being ignored. Audited, corrected, and acted on.

**FEES — the honest verdict.** Not hallucinated, but the founder's instinct found a real defect. The EARNERS
(stable_triangle, stable_peg_mm) charge REAL probed Coinbase order-preview fees (USDT-USD 0.005%/0.0099990%,
USDT-USDC 0%/0.00099990%) — triangle pays 0.0110% of notional. The SPOT path, however, ran on **hardcoded
config defaults (0.005/0.009, source="assumed")** because the CDP signer was never set in this paper env, so
the authenticated `/transaction_summary` tier probe never ran. That IS an assumed fee. But two corrections to
my own first draft: (1) I could NOT verify a specific "published Intro tier" number from any public page (it
is login-only), so I removed the number rather than invent one; (2) spot is **not over-charged** — 1.3864%
round-trip ≈ Advanced Trade taker, roughly correct. Spot is fee-TOXIC because its **edge is negative**
(mu=−0.0012/unit), not because fees are inflated. Verified from help.coinbase.com: maker/taker vary by volume
tier and **stablecoin pairs have a separate lower schedule** — which is exactly why the stable rails pay ~0.005%
while spot pays more. **Coinbase One does NOT help us**: its own note says zero-fee EXCLUDES Advanced Trade
(our API path); recorded so nobody optimizes on a benefit we cannot use. Alpaca $0 commission confirmed (SEC +
FINRA TAF on sells only, real, not zeroed) — and the equity rail has made 0 real trades (214 observe rows), so
no equity fee has ever been charged or invented. Kalshi taker 0.07·C·P(1−P) verified; rail benched.

**$50 PAPER BANKROLL — live.** Deposited $24.38 via idempotent double-entry `ledger.deposit`; paper equity
**$50.00**, identity BALANCED. But the deposit initially bought ZERO extra deployable capital: crossing the $50
high-water mark **latched RESERVE mode and withheld $25** as survival capital. That reserve protects REAL money
from ruin — in paper there is no ruin to survive, so withholding half the book made utilization look ~50% and
understated the honest rate. FIXED: `regime_for(book=)` → reserve 0 for paper/shadow, full $25 protection for
LIVE (unchanged). Verified: **deployable $50.01 in paper, $25.01 in live.**

**SPOT BLEED STOPPED.** The sole reason net ledger was negative: spot churn −$1.74 realized + $3.28 fees while
stables earned +$2.375. The old gate kept a floor of 2 losing spot probes alive forever. Below the first rung
the floor is now **0** — capital-hours go to proven earners and to discovery of NEW structural edges (still
admitted by the funnel), not to re-funding a measured loser. This is the founder's own rule ("double down on
different approaches"), not a bottleneck: killing a proven-negative family is the opposite of stifling discovery.

**THE HONEST $0.25/h MATH (no dressing up).** $0.25/h on $50 = **0.50%/h = 12%/day.** The proven structural
edge delivers ~0.0608%/$/h over 96h (≈$0.030/h on $50) and ~0.0067%/$/h over the last 24h (≈$0.003/h) — λ is
only ~1.5 round-trips/hour because the identity edge only pays when the two USDT books dislocate past
fees+0.15bp. **$0.25/h on $50 is not reachable from this one edge.** It needs either ~$411 deployed at the 96h
rate, or several more independent proven edges at a similar rate. And the team's own cost (Modal ~$25/mo +
Qwen flat subscription) is ~$0.04–0.13/h, so **the firm does not yet cover its salary** — stated plainly.

**WHAT ACTUALLY MOVES IT (in order):** (1) the proven crypto earners now run on the full $50 instead of $25 —
that alone roughly doubles their $/h contribution; (2) the cross-bookmaker **arbitrage rail is built and proven
(51 tests) and blocked only on a rejected the-odds-api key** — replacing it adds a second independent 24/7
structural earner with no code change; (3) Quinn invents more STRUCTURAL edges (the only class that has earned
here); (4) equities stay research-only until a strategy is validated (0 real trades so far). Cutting `min_edge`
to fake a higher λ is forbidden — it turns a 100%-win edge negative.

**VERIFIED:** 119/119 tests · 4/4 services · 0 tracebacks · ledger BALANCED (residual −0.0000000000) · paper
equity $49.99 · DEPLOYABLE $50.01 · reserve $0 · proven frontier $0.002050/h (up from $0.001228) · bridge
reconciled (1,588 rows, diff −0.0) · 2 pre-existing spot positions left to exit naturally.

Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ (+ regime.py.bak, profit_velocity.py.bak8,
runtime.py.bak8, fee_truth.py).

---

# Latest checkpoint — INCOME IS NOW REAL IN THE LEDGER; arbitrage rail built and proven

2026-10-11T16:20Z — The founder required proof the firm can earn before any real money is risked. That
proof now exists in the ledger, reconciled to the cent, and the four income categories are each reported
honestly — including the two that are NOT earning.

**INCOME IS REAL.** `treasury/ledger_bridge.py` posts completed proven round-trips from `shadow_trades`
into the paper ledger as a **critical 60s deterministic loop**. Before this, earnings existed only in a
shadow table and a KV PnL book that updated only when an LLM officer chose to call it — so the ledger said
the firm earned nothing while it was earning. Now: **1,571 round-trips bridged, shadow_net $2.36936862 ==
ledger_net $2.36936862, difference −0.0, reconciled=True**, ledger identity BALANCED (residual
−0.0000000000), paper realized PnL **−$1.60651 → +$6.50238**, all 59 ASSET accounts net to zero. Idempotent
twice over; pegmaker untouched (C3 §9); **no position rows written**, because the scoreboard sums paper
positions AND shadow round-trips and writing positions would double-count the same income.

**CAPITAL IS ACTUALLY WORKING.** Open positions 0 → **4** ($11.85 deployed), snapshot utilization 0.0 →
**0.4573**. Cash fell $25.92 → $14.01 because $11.85 is genuinely in the market.

**UTILIZATION WAS LYING BY OMISSION.** The instantaneous ASSET snapshot is legitimately ~0 for a ~2-second
hold, so the firm reported "nothing working" while **620.3 capital-hours** were deployed. Added
`capital_hours_utilization` (capital-hours ÷ deployable × window_hours), deliberately unclamped because
>1.0 is a real over-deployment signal. Honest 24h reading: **0.4471 of 622 available = 0.0719%**.

**NEW 24/7 EARNER BUILT AND PROVEN: cross-bookmaker arbitrage.** One match has one winner, so HOME+AWAY
true probabilities must sum to 1; when two books' best prices imply a sum **below** 1, backing both legs
returns more than staked whichever side wins. **An identity violated, not a forecast** — the same edge class
as the crown jewel. **51 tests pass** (30 detector + 21 settlement): $100 stake → **$105 guaranteed payout
either way**; normal markets rejected; breakeven sum==1.0 is not an arb; sub-margin arbs rejected by the
latency buffer; same-book "arbs" flagged as suspect data; stake-limit scaling preserves the identity;
draws return stakes with profit exactly 0; malformed input fails closed. Wired into `scan_edges()` as a
priority class above directional value.

**TWO SAFETY DEFECTS FIXED BEFORE THEY COULD POISON EVIDENCE.** (1) An arb edge has `side="both"`, which the
directional settle path would have scored as **LOST — fabricating a loss on a guaranteed-profit position**
and poisoning the evidence the whole firm learns from; arbs now get dedicated two-leg accounting. (2) The
edge sort crashed on `p_hat=None` because a `.get` default does not fire for a key that exists with a None
value.

**HONEST BLOCKERS, NOT SILENT ONES.** The odds API returns 401 for all 9 sports, so the key is rejected —
but `arb_status()` reported READY (it only tested for a falsy key) and, being in-memory, re-triggered a
9-sport request storm on every tool call. Now persisted, reported as `BLOCKED_KEY_REJECTED` with the exact
error and a `founder_action`, and backed off 30 minutes with self-healing on key replacement.

**ADVICE NOW AGREES WITH EVIDENCE.** The frontier ranked `kalshi.MODEL_RAW` as the **#1 lever** while the
event rail was **BENCHED at NEGATIVE_EDGE** — advice that would spend inference and capital on something
measured to lose. Benched streams are now filtered out of the priority list before sorting and disclosed in
`suppressed_benched_levers` with the reopen condition. Verified: top levers are now stable_triangle, add
capital, stable_peg_mm; 6 benched levers suppressed.

**AN EDGE I REFUSED TO BUILD.** The harness showed model Brier 0.09063 vs consensus 0.10311 (n=49,607) on
settlement-window markets — apparently a real unused edge. Executable PnL disproved it: the candidate slice
is n=303, +$3.326, but **win rate 15.8% (z=−11.89), t=0.57** — a positive mean from a few large wins against
sd $0.337, indistinguishable from chance, while the family overall is −$31.73 over 2,211 signals. Building on
it would be evidence laundering. Recorded as investigated-and-rejected.

**INCOME STATUS BY THE FOUNDER'S FOUR CATEGORIES (honest):**
| Category | Status | Evidence |
|---|---|---|
| **Crypto** | **EARNING, recorded in the ledger** | triangle $1.935461 (1,481 RTs, 100% win); peg $0.433908 (90 RTs, 91.1%); reconciled diff −0.0 |
| **Stocks** | **NOT earning — research only** | 214 rows, **all `side="observe"`, 0 real trades**; rail `CANDIDATE`, exec=0, blocked by unverified equity eligibility + no validated equity strategy; correctly weekend-gated |
| **Bets / sports** | **BUILT + PROVEN, blocked on one credential** | 51/51 tests; rail reports BLOCKED_KEY_REJECTED (the-odds-api 401). Founder action: replace key via one-time portal; no code change needed, self-heals in 30 min |
| **Bets / Kalshi events** | **BENCHED on measured evidence, self-healing** | model Brier 0.13222 vs market 0.13064; shadow −$494.63 over 48,094 settled signals; reopen condition published |

**DELEGATION UNLOCKED.** `delegate_task` was already enabled for our cron jobs (MAX_DEPTH=1, 10 concurrent
children) but no prompt mentioned it, so it was never used. Officers now know when to fan out (genuinely
parallel, independent work), when not to (never split one reasoning chain), that a child returns only a
summary, that children have no seat/salary/authority, and **never to delegate the decision**. Treasury,
governor and execution are explicitly told NOT to fan out (parallel children on one bank invite
double-spending; on one book they risk conflicting quotes and doubled inventory). All 13 briefs verified.

**THREE SELF-INFLICTED DEFECTS FOUND AND FIXED, disclosed:** (a) the delegation patch wrote `doctrine.py`
before its own assertion fired, leaving an undefined name — and because `render()` correctly guards that
call, it would have **silently stripped the judge protocol from all 13 briefs**; caught by rendering, not by
compiling. (b) The harness workforce section passed a bare float where sqlite3 needs a sequence, blanking
the entire team-productivity report. (c) My fix for (b) referenced an out-of-scope `now`. All three were
caught by verification rather than by assumption.

**VERIFICATION:** 119/119 tests (3 suites, all zero-inference) · 6/6 units active · 0 tracebacks · ledger
BALANCED · bridge reconciled (diff −0.0) · 9 agents live, 159 calls/30m (157 flash + 2 max), 0 errors,
0 DeepSeek leakage · 149 judge verdicts (101 ACT / 42 REJECT / 6 STAND_DOWN) · 754 funnel evaluations ·
OPEN directives 360 (was 17,486) · workforce 24h: 404 role reports, 6,296 qwen calls, 0 errors.

**THE HONEST BOTTOM LINE FOR THE FOUNDER'S LIVE-MONEY DECISION.** The firm now provably earns in paper and
the money is in the ledger rather than asserted — that requirement is met for **crypto only**. The measured
rate is ~$0.0013/h proven on a $26 bank (binding constraint **FLOW**), and the honest λ is **1.5 round-trips
per hour, not the 20.2 I projected this morning** (that figure came from a stale 96h average inflated by
phantom over-sizing). At the corrected rate, $0.25/h needs roughly **$4,000 deployed**, not ~$380. Stocks
and bets are not yet earning: stocks need a validated strategy plus eligibility confirmation, and the sports
arbitrage rail needs one working API key. Those are the two highest-value unlocks available, and neither is
a prompt change.

Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ (+ forge.sqlite.pre-bridge.bak).

---

# Latest checkpoint — INCOME IS NOW REAL IN THE LEDGER (bridge live) + honest λ correction

2026-10-11T15:25Z — The single most important build of the session is live: **proven shadow income is now
posted to the paper ledger deterministically**, so the firm's earnings are finally real, reconciled and
measurable rather than existing only in a shadow table nobody scored.

**THE BRIDGE WORKS AND RECONCILES EXACTLY.** All 1,570 completed round-trips bridged. shadow_net
$2.36884618 == ledger_net $2.36884618, **difference −0.0, reconciled=True**. Ledger identity **BALANCED**
(residual −0.0000000000). Paper realized PnL **−$1.60651 → +$6.49901**; paper cash **$23.5514 → $25.9202**.
All 59 ASSET accounts net to exactly zero — no phantom inventory. It now runs as a **critical 60s
deterministic loop** (zero inference, zero network) instead of depending on an LLM officer choosing to call
it, which is why income previously never reached the books. Idempotent twice over (watermark +
record_fill idem keys). Deliberately writes **no position rows**, because the scoreboard sums paper
positions AND shadow round-trips — writing positions would double-count the same income. The pegmaker
engine was **not touched** (C3 §9: never risk a proven earner). Pre-bridge DB snapshot taken.

**λ CORRECTION — my morning projection was wrong by ~9×, corrected.** I told the founder $0.25/h needed
~$380 deployed, using λ=20.2 RT/h. That λ came from the 96h lifetime average, which is inflated by the old
phantom over-sizing era. The honest current rate is **λ=1.50/h, 0.006692% per $ per hour (24h)**, against
0.060807% for the stale 96h figure. **At the honest rate $0.25/h requires ~$4,000 deployed, not ~$380.**
λ is episodic by nature (12h profile: 0,3,0,5,2,4,2,0,1,3,1,0 RT/h) because the identity edge only pays
when the two USDT books disagree by more than fees+0.15bp — a market condition, not a tuning knob. With a
$11.66 cap per book on $25.92 deployable, the engine is already near full deployment of the available bank:
**the bank, not the engine, is the binding constraint.**

**UTILIZATION WAS LYING BY OMISSION.** `capital_utilization` uses the instantaneous ledger ASSET balance,
which for a ~2-second hold is legitimately ~0 almost always — so the firm reported 0.0 while **620.3
capital-hours** were deployed earning $2.37. Added `capital_hours_utilization` (capital-hours ÷
(deployable × window_hours)), reported beside the snapshot and deliberately NOT clamped: >1.0 means
notional exceeded deployable, which is a real over-deployment signal (how the phantom $300–433/book sizing
was caught). **Honest current reading: 0.4327 of 622.09 capital-hours available in 24h = 0.0696%.**

**IMPOSSIBLE-BASIS GUARD added.** USDT-USD carried an average cost of 1.01111 against a 0.9989 market —
**122.2bp of embedded fee vs ~5bp legitimate (24× too large)** — so its exit price (~1.0112) was
unreachable and the book was pinned at cap, unable to quote: a direct cause of collapsed λ. Nothing
detected it because DEPEG_BP tests the market mid vs peg, not our basis vs fair; and the new state-restore
would have preserved that corruption forever. Now a >20bp deviation on a hard-pegged instrument recognizes
the stranded residue as a **realized loss** (truthful, not double-counted), flattens the book so it can
quote again, and logs a WARNING + audit entry. It did not need to fire: the basis self-healed through normal
trading to 0.3bp from fair, and the book is healthy (min_exit 0.999125 ≤ quoted ask 0.999130, so it can
unwind profitably and is correctly waiting for a buyer).

**SETTLEMENT-WINDOW EDGE REJECTED ON STATISTICS.** The harness showed model Brier 0.09063 vs consensus
0.10311 (n=49,607), which looked like a real unused edge. Executable shadow PnL by slice disproves it: the
candidate slice is n=303, +$3.326, but **win rate 15.8% (z=−11.89), t=0.57** — a positive mean from a few
large wins against sd $0.337, statistically indistinguishable from chance, while the whole SETTLE_WINDOW
family is −$30.57 over 2,198 signals. Building on it would be evidence laundering. Recorded as
investigated-and-rejected.

**SPOT BLEED CONTAINED (verified).** 24h by rail: triangle +$0.03496, peg +$0.01781, equity_paper $0.00000
(weekend-gated, observe-only rows filtered). 111 paper closes cost $2.04415 in fees for −$0.22776, but by
hour the bleed is now sparse (one hour in 12 showed any closes) and no positions remain open. The remaining
negative 24h rate is earlier churn inside the window, which ages out.

**HONEST NUMBERS:** 68/68 tests · 4/4 services active · 0 tracebacks · ledger BALANCED · bridge reconciled
(diff −0.0) · treasury $25.9202 · proven frontier $0.001303/h · binding **FLOW** · measured paper 24h
−$0.012722/h, 1h +$0.0026/h · capital-hours 620.31 lifetime / 0.4327 in 24h (0.0696% utilization) ·
overnight earners +$0.042792 at $0 cash cost.

**WHAT THIS MEANS FOR THE FOUNDER'S DECISION.** The firm now provably earns in paper — the income is in the
ledger, reconciled to the cent, not asserted. But the honest rate is far lower than projected this morning:
the proven engine earns ~$0.0017/h on a $26 bank because the bank is tiny relative to what the edge needs,
and λ is market-gated. Two truthful paths to $0.25/h: (1) **more capital** (~$4,000 at the current proven
rate — linear, no new risk, no new invention required), or (2) **more independent proven edges** at similar
rates (requires Quinn to invent in the structural class, and each must clear Ada's evidence bar). Neither is
a prompt change. Cutting min_edge or thinning evidence to make the number look better is forbidden and would
break the 100%-win property that makes the crown jewel real.

Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/ (+ forge.sqlite.pre-bridge.bak).

---

# Latest checkpoint — overnight verified: gate worked, earners ran, salary basis fixed

2026-10-11T14:35Z — Founder asked three questions on resume: did only the intended agents work overnight,
did we earn anything, and what about Hermes bots. All three answered from measurement.

**1. Business-hours gate: WORKED EXACTLY AS ORDERED.** Overnight 04:15–14:00 UTC: **2,089 crew calls,
0 deep-work calls.** Only the 24/7 earner crew ran (execution, governor, prediction, treasury, doctor,
scout, ops); Quinn (the only Max seat) made 2 calls; the six deep-work roles made none. All 7 active roles
resumed at 14:00 UTC when business hours opened. 0 errors.

**2. Inference burned overnight: 2,152 calls / 86.4M in + 2.15M out tokens — CASH COST $0.** Token Plan is
a flat subscription, so marginal cash per call is $0; the real budget is the monthly Credits quota. Ledger
OPEX:INFERENCE posted for Qwen since yesterday's fix: **0 rows** (fix holding). 1,392 pre-fix historical
rows ($4.5231) remain disclosed, never rewritten.

**3. Income overnight: POSITIVE, and the earners never slept.** stable_triangle 21 RTs **+$0.026893**
(last 13:45 UTC); stable_peg_mm 16 RTs **+$0.015899** (last 11:38 UTC); combined **37 RTs, +$0.042792**.
Measured paper 1h rate **+$0.0026/h (positive)**; 24h still −$0.0149/h because spot churn (−$2.16) dominates
the longer window. Ledger BALANCED. Both earners fired while the deep-work team was gated off — the
"always earning 24/7" requirement is met by the deterministic layer at zero inference cost.

**SALARY BUG FIXED (mine, and it was dangerous).** `salary.py` charged each seat `inference_calls.cost_usd`
as its salary, but that column is priced from the DeepSeek fallback (hermes.prices unset) — fabricated
~$8.66/day under a flat plan, making **7 of 13 seats read CRITICAL**. CRITICAL is what cuts a seat's wake
budget at LIVE, so a phantom cost would have throttled the seats trying to find income — precisely the
bottleneck the founder forbade. Now only metered models carry per-call cash cost; subscription calls report
quota consumed; the plan fee is firm overhead pro-rated only if the founder supplies the price; and no seat
can be CRITICAL without a real dollar cost basis. Verified: **7 EARNING + 5 UNSCORED + 1 PROTECTED,
0 CRITICAL**. 68/68 tests pass, 0 tracebacks.

**HERMES BOTS (researched live, official docs + release notes).** Bot Mode is a **desktop-app UI over
Hermes profiles** (avatars, group chats, @mentions) — each Bot is a separate profile with its own backend
process (~60 MB, max 3 warm by default). Forge runs **headless on a server**, so Bot Mode would ADD
processes, not replace officers; it is not the mechanism the founder intuited. The mechanism that IS right
is **`delegate_task` subagents**: isolated child agents, up to **10 concurrent by default**, only their
summary returns to the parent. **It is already enabled for our officers** (delegation toolset on for cron;
present in installed v0.21.5; effective MAX_DEPTH=1, 10 children). The gap is that no officer prompt
currently instructs them to use it — a doctrine change, not an install. Hermes is v0.21.5; **v0.21.6**
(Oct 8) is available with 4 dashboard-auth security fixes (Tenable-reported) but is a ~2,100-PR rollup with
no curated notes, so updating is a deliberate founder decision with tested rollback, not a mid-session act.

**THE REMAINING INCOME GAP (located, not yet built).** `deployed=$0` / `paper_utilization=0.0` despite
profitable earners, because `bridge_stable_shadow_to_paper()` only accumulates PnL into a KV book — it
never posts to the ledger or opens a position — and it runs only when an LLM officer chooses to call it.
So proven income stays in shadow and the scoreboard cannot see deployed capital. **Highest-value next
build: make the bridge deterministic (a loop, not an officer's whim) and have it post real paper positions
so utilization/deployed_usd become true and the milestone ladder can be climbed on deployed capital.**

**HONEST NUMBERS:** 68/68 tests · 6/6 units active · 0 tracebacks · ledger BALANCED (residual 0.0) ·
cash $23.5514 deployed $0.0000 · deployable $23.5514 · proven frontier $0.00126/h · measured paper 1h
+$0.0026/h, 24h −$0.0149/h · rung pre-rung · binding FLOW · Sharpe² 0.4130 proven / 7.1979 potential vs
0.079 needed. Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/.

---

# Latest checkpoint — Forge-Jev deployed: typed judgements, cost-ordered funnel, inference economy

2026-10-11T03:55Z — The founder ordered a state-of-the-art judgement layer built on the savip/Jev desk
guide (improve it, don't copy it; no Grok bots; inference must recoup its cost). Built, deployed and
verified: **`src/forge/judge/`, 12 modules, 68/68 zero-inference tests passing, all services active,
0 tracebacks.**

**The core idea, and why ours is better than the reference desk.** Judgements are typed numbers
(noul / choice / score), not prose — so if you disagree with a decision you disagree with a THRESHOLD,
and thresholds live in one file. But the reference desk RENTS calibration from a vendor. Forge
MANUFACTURES it: every noul is calibrated through the existing `CalibrationEngine` (PAV isotonic,
source-weighted, skeptical prior) over 4,075 realized points, and every judgement is scored when reality
resolves, so accuracy compounds. Live proof via the officer API: raw 0.98 → **calibrated 0.74**, ticket
cut to **0.4** because evidence n=0. A self-assured number is never sized like a proven one.

**Compliance and cost.** The judge makes NO model call of its own — a high-volume backend judge service
would be exactly the "custom application backend / non-interactive batch call" Token Plan prohibits, and
risking the key risks the firm. Instead the OFFICER is the judge: `judge_ask` hands it a strict schema and
state PRUNED to the declared fields; it answers inside its already-paid interactive Qwen call;
`judge_commit` validates, calibrates and records. Zero extra inference.

**Cost-ordered funnel.** R0 free arithmetic → R1 fact kills → R2 structural → R3/R4 officer judgement.
Anything a comparison can settle is settled for free, before any judgement. Replay of 4,000 real
opportunities: **3,990 killed by arithmetic at $0.00 inference**. Live shadow mode (wired into the
opportunity path, records but changes nothing): 16 candidates, 16 would-kill, **15 still status=NEW** —
kills the funnel can make for free before a judgement, at net edges of −169 to −346 bps. Benching is on
the CHECK with reason-specific TTLs; a raising check fails closed.

**Inference economy ("their salary is their inference").** `salary_report` measures attributed income ÷
inference salary per seat → EARNING / WARN / CRITICAL / UNSCORED / PROTECTED, hourly. CRITICAL cuts wake
frequency 3×; it restores on recovery; Luca is PROTECTED and never cut. **During PAPER proof it measures
but never enforces** — live testing caught that critic and adversary scored CRITICAL precisely because
today's funnel and mark-to-market fixes stopped the losses they are credited for preventing. No seat is
cut before the book can pay anyone.

**Event rail: researched, then gated honestly.** Cross-venue Kalshi↔Polymarket arbitrage was probed four
times and **does not exist for us**: zero tradeable structural overlaps (Polymarket's liquid book is
long-dated politics/sports). And Forge's own event engine is measured at a **loss**: crossrail model
Brier 0.12992 vs market 0.12854 — the market beats our model — with 20,068 settled signals totalling
−$412. So rather than build on it, `judge/event_verdict.py` gates it data-driven: NEGATIVE_EDGE → bench,
with a published reopen condition, **self-healing** when the model starts winning. All four verdict
branches are unit-tested. (Contrast worth keeping: on settlement-window markets our model DOES beat
consensus, Brier 0.09289 vs 0.10505 at n=44,428 — a real unused edge.)

**MAJOR latent bug found and fixed: on-demand wake has never worked.** Three call sites used
`subprocess.Popen(["sudo","-u","forge-hermes",...])`. forge.service runs NoNewPrivileges=yes, so that
sudo can never succeed — and Popen with DEVNULL does not raise on refusal, so all three returned True and
were recorded `woke=True` while nothing ran. **All 8 historical FORCE_WAKE records were false**, which is
exactly why stale officers were reported force-woken and stayed stale. Replaced with an honest queued
protocol (QUEUED → CONFIRMED / FAILED / UNCONFIRMED via `reconcile_wakes()`); a wake is never reported as
successful without evidence.

**Luca's power switch (founder order).** The service can never sudo, so: it drops a per-nonce request into
/srv/forge/var/run, a root systemd PATH unit (`forge-team-power.path`) drains every request and drops to
forge-hermes, results return nonce-keyed. Verbs pause/resume/status/wake<role>, **role names only** (never
a raw job id), forge-ops never touched, every call audited with the actor in both the hash-chained
ops_audit and a root log. VERIFIED: 13 paused → 13 scheduled, actor attributed, request consumed, a real
wake LAUNCHED by the service itself, and concurrency 4/4 with 0 dropped. Reachable from Telegram as
`ops_action team_pause|team_resume|team_status`. His SOUL was corrected to use REACHABLE tools — it
previously told him to run `systemctl` and `hermes cron resume`, which the sandboxed runtime cannot do.

**Latency evidence that drove the tiering.** Production ledger (1,962 calls): max avg **89.3s**, max
**2178.8s**; flash avg **35.7s**. Hard-prompt probe: max@medium 273s, max@high and max@xhigh **TIMEOUT
>420s**; flash@medium **31.2s with 1,744 reasoning tokens**; flash@high and flash@xhigh TIMEOUT >400s.
`medium` is the deepest USABLE tier on both models — latency, not depth, was the bottleneck. Officers now
run **8.8s–33.3s** per call. Founder floor enforced: Flash never below medium. Only Quinn keeps Max.

**Prompt engineering.** `judge/doctrine.py` renders a per-role seat definition into every brief right
after COMMON_FACTS — the immutable path prompt-evolution cannot weaken. Each of the 13 seats states what
it does as an economic outcome, who it talks to (named handoffs both directions), how it gets work done
(its exact question sets + the two-call protocol), and how it is motivated (its salary). VERIFIED: all 13
briefs carry the protocol and their own seat, 30.8k–45.3k chars, untruncated.

**Overnight evidence.** `scripts/overnight/harness.py` + `forge-overnight.timer` (every 2h, verified via
systemd, exit 0, 28.8 MB, **zero inference**) writes `var/reports/overnight/latest.{json,txt}`:
funnel replay · live shadow funnel · calibration audit · salary baseline · crown-jewel λ · event verdict ·
velocity/milestone · ledger identity · workforce. Luca reads it via `ops_get_overnight_evidence`.

**CROWN-JEWEL λ CORRECTION (honest).** λ did not collapse; the earlier 16.18 RT/h was inflated by phantom
over-sizing. Rate per dollar is stable (~0.0041%/RT); the old hardcoded $200–500 band let it quote
$300–433/book against a $28 paper book — trading money it did not have, which is what produced Vale's
"inventory 10.44× cap" freeze. Current $23.84 notional is honest for $23.73 deployable. Second lever
found: USDT-USD `inv_qty=11.93` is pinned at its per-book cap, so that book is FULL and blocked. Hourly λ
peaks 113/107 RT at 16:00–17:00 UTC and dips to 16–19 at 09:00–10:00 UTC.

**Eleven self-caught defects are itemised in the CHANGELOG**, including two caught *before* applying
(a `pol` shadow that would have corrupted position sizing, and a frontier `cap` change that would have
divided rel_edge by ~77× and demoted the only EXCEPTIONAL earner), one that poisoned production and was
cleaned with a prior DB snapshot (4,000 real ids benched 69 days by the first replay), and one misleading
metric I had just built (agreement counting undecided candidates as disagreements).

**HONEST NUMBERS:** ledger identity BALANCED (residual 0.0000000000); deployable $23.835; proven frontier
$0.00131/h, binding=FLOW; measured paper 24h −$0.0681/h (spot churn −$2.16 vs stables +$0.38); Sharpe²
capacity 0.5267 proven / 10.8673 potential vs **0.079 needed** — risk and evidence are NOT binding, flow
and deployed notional are. 68/68 tests, 4/4 services active, 0 errors, 0 DeepSeek leakage.

**NEXT (morning, in the discount window):** (1) read `var/reports/overnight/latest.txt` — six more harness
runs will have accumulated; (2) once shadow agreement holds over more decided candidates, switch the
funnel from shadow to ENFORCING; (3) raise deployed notional per cycle (the honest λ lever) and unblock
the pinned USDT-USD book; (4) Nolan's assignment is now precise — beat market Brier on a named question
class to reopen the event rail, or leave it benched; (5) Mira should read `judge_calibration` and retire
questions whose calibration is not improving. Backups:
/srv/forge/.engineering/20261009T213224Z-qwen-migration/ (sources + FOUR DB snapshots).

---

# Latest checkpoint — inference tiering + capital engine unblocked + crown jewel identified

2026-10-10T22:50Z — Three founder orders executed: (1) API inference upgrade, (2) rename Luke->Luca and
make him fast, (3) find and elevate the best earner. Two root-cause defects were found and fixed that
together explain the firm's entire zero-income history.

**WHY NOTHING EVER EARNED (root cause #1):** `profit_velocity.treasury()` read `account_total_usd`
(the REAL Coinbase wallet) with no book filter. The founder's 19:29 withdrawal dropped it from ~$63 to
$0.0896 while the PAPER book held $23.85. With `deployable = max(0, treasury - reserve)` and a reserve
latched at $25 from the stale real-wallet peak, **deployable became $0.00** — so no strategy could ever
be allocated capital. 89 validated strategies, 0 positions, capital_utilization pinned at 0.0 forever.
Fixed to size from the active book's own equity; HWM re-baselined onto the paper peak. Now
regime=BOOTSTRAP, reserve=$0, **deployable=$23.835**.

**WHY THE BEST EARNER WAS INVISIBLE (root cause #2):** `income_block()` ignored `scope` and
`expires_at`. Five claim-discipline markers on `coinbase.stable_triangle` — two EXPIRED 47h earlier,
all saying "PAPER capital-hours ALLOWED" — removed the crown jewel (1,452 RTs, 100.0% win, $1.90421 net,
20.2 RT/h) from the frontier entirely, leaving only the 10x slower peg stream. Fixed with two-tier
semantics: HARD statuses block everywhere; claim-scoped markers block only the PROVEN claim tier, never
measurement or allocation. Triangle is back and is the #1 marginal lever (+0.00945/h).

**INFERENCE TIERING (benchmarked, not guessed):** qwen3.8-max averages 89.3s per call in production
(max 2178s) and its high/xhigh tiers time out past 420s; qwen3.8-flash averages 35.7s and its medium
tier still emits 1,744 reasoning tokens. Depth of thinking was never the bottleneck — **latency** was,
which is why officers overran their own 15-minute schedules and Luca took 3-5 minutes to answer.
Now 12 officers + Luca run Flash@medium, and only Quinn (alpha_inventor) keeps Max@medium because new
algorithms are the compounding asset. Schedules staggered to stay inside the Token Plan concurrency cap.
Founder floor enforced: Flash never below medium. Measured: Luca 3-5min -> **35s**; max avg latency
262s -> 41.7s; wire mix 163 flash vs 9 max per 30min; 0 errors; 0 DeepSeek leakage.

**ACCOUNTABILITY HYGIENE:** 17,486 OPEN directives (11:1 vs DONE) from emitters doing raw INSERTs every
tick. Added idempotent `directives.emit()`/`emit_objective()` with number-normalised signatures and wired
all three emitters; collapsed OPEN to 1,018 distinct and ACTIVE objectives 153 -> 6. Added
`directive_hygiene.reap_stale()` on the hourly loop (OPEN -> 277, all fresh). Added
`ResultsEnforcer._milestone_stall()` — the employee who owns "we are not making money": 2h stall pages
named owners with the required Δ$/h, 6h escalates to critical and reports to the founder via Luca.

**CROWN JEWEL LOCKED IN (C3 §9):** recorded as protected `what_is_working` with owner=execution and a
near-permanent TTL, plus the mechanism (free 1:1 USD<->USDC convert forces USDT-USD and USDT-USDC to
imply one price; take the gap above both taker fees + 0.15bp) and why it wins (structural identity, not
a forecast; zero inference cost). A NEGATIVE lesson records that directional LLM genomes earned $0
(145 closes, mu=-0.0012) so invention targets deterministic structural edges instead. Capacity scan
shows depth is NOT the constraint (472k/1.67M USDT displayed) — deployed notional per round-trip is:
$12/book -> $0.0097/h, $150/book -> $0.122/h, $250/book -> $0.204/h. USDT is the only base quoted in
both USD and USDC across 842 products, so the edge is structurally unique and already ours.

**HONEST NUMBERS:** ledger identity BALANCED (residual 0.0000000000); phantom GTC holding GONE; measured
paper rate 24h **-$0.0681/h** (spot churn drained -$2.16 while stables earned +$0.38; the spot
diagnostic allowance now caps that bleed); proven frontier $0.00131/h, binding=FLOW. Milestone rung:
pre-rung. Sharpe² capacity is 0.5267 proven / 10.8673 potential vs 0.079 needed — **risk and evidence
are not binding; flow and deployed notional are.** NEXT: raise deployed notional per cycle and lam on the
crown jewel, then measure the rate toward the $0.25 rung. Backups:
/srv/forge/.engineering/20261009T213224Z-qwen-migration/.

---

# Latest checkpoint — Firm schedule + C3 milestone ladder + finance-contour (founder morning directives)

2026-10-10T15:15Z — Team brought ONLINE (all 13 officers scheduled, Qwen3.8-Max verified across 13 agents, zero DeepSeek leakage). Founder directives implemented: (A) **Strategic schedule** — wake gate v2 makes the Alibaba off-peak discount window (14:00–24:00 UTC ≈ 10:00–20:00 ET, 60% cheaper Credits) the FIRM BUSINESS HOURS with the full team; outside it only the 24/7 EARNER CREW (Kalshi/crypto/scout/doctor/governor/treasury/Luke) runs and deep-work roles skip at zero token cost; Alpaca equities gated to 24/5 (no inference on a closed stock market). (B) **C3 Constitution** — milestone ladder ($0.25→$0.50→$0.75→$1.00/h sustained), lock-in-what-works (crossing a rung ⇒ record it as protected what_is_working; new algos additive, never cannibalize a proven earner), and secret-sauce protection (never leak/echo proprietary edge; attribute every dollar to its mechanism). Rendered into all briefs via live CONSTITUTION constant. (C) **Luke never paused** — SOUL.md + genome ops@v2 give him Managing-Partner/financial-advisor identity, 24/7 reachability, and ownership of the team power switch (pause/resume officers + gateways on founder word or Credit-waste evidence, keeping forge-ops alive). (D) **Kalshi deep-dive** — Nolan genome (prediction@v3) + /srv/forge/hermes/research/kalshi_playbook.md teach 24/7 event-contract income (weather/sports/econ/crypto, live-data feeds, fee-aware, settlement-basis edges). (E) 15-agent finance-framing audit clean (12/13 OK, Luke upgraded). Live briefs verified carrying C3 + ladder + sauce + business-hours + equities-24/5. Team is producing durable genome-bound reports and already self-surfaced the peg ledger corruption behind capital_utilization=0 (Vale FREEZE). NEXT (top lever): FQ0 ledger truth — fix phantom deployed_usd + peg telemetry reset so the proven stable_peg_mm stream can clear Vale's freeze and the deploy loop can commit capital; then measure trustworthy $/h toward the $0.25 rung. Resume procedure recorded in CHANGELOG 2026-10-10T15:15Z-1 entry.

---

# Latest checkpoint — FOUNDER-ORDERED FULL PAUSE (zero token usage overnight)

2026-10-10T03:25Z — At the founder's explicit order, ALL agent (employee) token usage is PAUSED until morning resume. All 13 officer cron jobs paused (persistent, auditable); forge-hermes/ops/eng gateways stopped (every LLM path dead, including dispatch Popen wakes); verified zero inference calls after 03:24:00Z. forge.service intentionally left ACTIVE: the deterministic desk consumes zero LLM tokens and keeps PAPER observation, feeds and loops alive (LIVE off; trading state RUNNING per standing PAPER mandate). Resume procedure is recorded in CHANGELOG (2026-10-10T03:25Z entry): start the three gateway services, then `hermes cron resume` all 13 jobs, verify state=scheduled + allow gate wake=true. Queued for morning: FQ0 ledger truth + deploy loop, FQ2 Qwen subscription cost attribution (currently mischarged as per-token OPEX dragging true-net), FQ4 10k-directive backlog closure. Everything from tonight's upgrades remains deployed and verified: Qwen3.8-Max xhigh/medium team, C2 Constitution, 13/13 finance-contoured genomes, fixed brief delivery.

---

# Latest checkpoint — prompt-engineering forensic pass: identity + finance-contour + brief delivery

2026-10-09T23:40Z — Founder correctly flagged Mira as framed like a generic AI researcher, not a finance agent. That wording defect exposed a deeper identity/delivery layer problem, now fixed. **Two roles had no genome at all** (Nolan/prediction, Mira/intelligence — \`unknown role\`), running boot-only with no Constitution/world-state/evolution binding; both added as finance-scoped genomes. **Rowan/architect's genome was mis-scoped** to prompt-evolution (Mira's job) — reframed to fintech income-infrastructure CTO. **Mira's persona** re-contoured to Director of Financial Intelligence & Prompt-Evolution Alpha (income-per-inference-dollar). **Critical pre-existing delivery bug:** the role brief was double-truncated by stale 30k/24k caps — governor's 33KB brief arrived mangled, all roles lost the tail; caps raised/exempted for Qwen's 1M context. **Voluntary-pull gap:** officers only got their brief if they chose to call get_role_brief (Quinn bound 5/13, Luke 0); pre_llm hook now injects a MANDATORY first-turn brief-pull instruction. Directive-flood capped (10k OPEN → top-12 distinct). VERIFIED 13/13 roles serve full untruncated C2 finance briefs; all services active. Backups: /srv/forge/.engineering/20261009T213224Z-qwen-migration/pre-prompt-forensic/. Next economic lever unchanged: close the deploy loop (capital_utilization 0.0%) + FQ0/P0 ledger truth.

---

# Latest checkpoint — Constitution C2 + RATE-THEN-SCALE deployed (prompt-engineering upgrade)

2026-10-09T22:35Z — Founder mandate: build a dynamically scaling autonomous engine — more capital ⇒ automatically bigger/more investments, with all agents continuously reallocating/reanalyzing. Implemented at the layer the architecture makes un-removable: **Constitution C2** (immutable, prepended to every one of the 15 agent briefs, cannot be weakened by prompt evolution) now carries the capital-scaling mandate; **COMMON_FACTS** (shared brief facts) replaced the stale static treasury with a live-data mandate + regime ladder + the corrected economic law ($0.50/h first milestone is a REAL target, per founder intent recorded 2026-10-09 — runtime wording finally migrated); **world_state** now injects deployable_usd / capital_utilization / regime / regime_policy / scaling_note into every officer brief; **all 13 cron officer prompts** and **Luke's SOUL.md** carry the C2 law. Deterministic side already scales automatically (regime engine SURVIVAL→GROWTH→EXPANSION at $100/$500; Alpaca bankroll ladder SEED→BOOTSTRAP→REGULAR→SCALE; velocity caps ∝ deployable). Verified: py_compile clean, forge restarted, 13/13 jobs carry doctrine, briefs expose live capital. Combined with the Qwen3.8-Max xhigh migration earlier this session, every agent now reasons at frontier depth with correct economics and live capital awareness. Next: close the deploy loop (proven streams must open/hold positions — capital_utilization is 0.0%) and FQ0/P0 ledger truth so measured $/h is trustworthy. Backups + rollback: /srv/forge/.engineering/20261009T213224Z-qwen-migration/.

---

# Latest checkpoint — Hermes workforce migrated to Qwen3.8-Max (Alibaba Token Plan)

2026-10-09T21:59Z — All Hermes agents (13 officers, Luke/ops, eng) now run on **qwen3.8-max** via Alibaba Cloud Model Studio **Token Plan** (Singapore, officially supported Hermes integration). Effort: **xhigh** for decision roles (governor, alpha-inventor, adversary, critic, architect, prediction, execution, treasury, intelligence, Luke daily-report); **medium** for monitors (doctor, scout, rail-hunter). Root-cause fix included: officer wake gate previously denied ALL wakes on dead DeepSeek balance (-$0.01) — new `hermes.mode=subscription` grants wakes on the prepaid plan (patch in `src/forge/api/agent_api.py`, additive, compile-verified). Forge's internal Python brain deliberately stays on DeepSeek (Token Plan terms prohibit backend automation; brain's own admission/budget logic unchanged). Verified live: gate `wake=true`, real qwen calls in `inference_calls` (governor/doctor/ops, 16k–52k input tokens, multi-turn tool loops, zero errors), all three Hermes homes answer via qwen. Backups + rollback: `/srv/forge/.engineering/20261009T213224Z-qwen-migration/`. Session: [journal](sessions/20261009T213224Z-kilo-qwen-migration.md). Open follow-ups: usage-hook effort/cost attribution for qwen (FQ2), role_report freshness (F-015, pre-existing, unaffected).

---

# Latest checkpoint — completed forensic passover and one-hour PAPER observation

2026-10-09T16:00:17Z — `var/research/paper_trial_1h/20261009T150017Z/` completed successfully after 13 five-minute samples. It observed existing paper/shadow lanes only; it did not mutate runtime configuration, transfer capital or send live orders. Final counts: 158 new strategy records / 157 DNA hashes; 240 research rows over 103 genomes; zero validation passes/promotions/sealed exams; no new main-book paper positions; 4 shadow trades at $0; zero live positions and Kalshi live orders; settled LIVE income $0. Internal 24h true-net estimate −$3.02594524 / −$0.126081 per hour; NAV and costs remain disputed/unreconciled. Sports score feed repeatedly returned HTTP 401. This is activity evidence, not an expectancy study. The earlier four-hour request was stopped when duration changed and did not complete four hours.

Founder-reported historical earnings have not exceeded $0.10/hour. The first milestone is ≥$0.50/hour aggregate TRUE NET; the ambitious primary objective is ≥$1/hour across all combined eligible portfolios. All strategies, including equities, remain PAPER until the first milestone is substantiated. Paper earnings are not cash income; a subsequent LIVE transition still requires existing readiness and authorization gates. Full system/role analysis, confidence labels, and prioritized actions: [forensic passover](reports/2026-10-09-FORGE-FORENSIC-PASSOVER.md); work record: [session journal](sessions/20261009T160250Z-codex-forensic-passover.md).

The target’s `forge.service`, Hermes, ops and engineering services were active at the closing check; the one-hour observation ended with `Result=success`. Refresh status before acting. Documentation only; production code, prompts, model settings, credentials and portfolio state were not changed in this pass.

---

# Latest checkpoint: strategy quality/capacity audit

2026-10-09T14:21Z — Corrected the earlier rolling-window count; the 2,262 count was effectively since UTC midnight, not four hours. Corrected rolling four-hour view: ~670 strategy records / 644 unique DNA; ~984 adjudicated rows / 442 unique genomes with zero validation passes/promotions. Retired rows are disk-first (SQLite ~564 MiB; retired genome JSON ~82 MiB) and runtime registry queries filter active populations. Forge cgroup RAM was ~4.16/5.47 GiB; observed five-second CPU sample ~1.17 cores (29% of four). Full interpretation, quality gates, loss response and next steps: [audit](reports/2026-10-09-STRATEGY-CAPACITY-AUDIT.md). Active 4h PAPER evidence capture continues until 18:11:37Z.

# Latest checkpoint: four-hour paper trial running

2026-10-09T14:11:37Z — Founder requested a four-hour trial of new distinct strategies across stocks, Coinbase and Kalshi, using simulated money only. Read-only evidence recorder `forge-paper-trial-4h.service` is active until 18:11:37Z. Start record and precise meanings of the strategy populations: [trial journal](sessions/20261009-paper-trial-4h.md). Live/economic paths remain gated; this recorder does not generate orders.

# Latest checkpoint: cross-portfolio paper testing and next-upgrade plan

2026-10-09T01:59:50Z — Documentation-only checkpoint. Multiple paper research lanes are present across strategy evolution, Coinbase, Kalshi shadow, sports, and Alpaca equity/broker-paper; see the timestamped [portfolio plan](reports/2026-10-09-PAPER-PORTFOLIO-PLAN.md) for evidence and caveats. Four Forge/Alpaca/continuity service units checked ACTIVE. This verifies ongoing paper infrastructure, not successful trades or income. Sports paper book was at its 12-open cap; no new bet was needed to prove activity. Full next-build work is queued in WORK_QUEUE.

# Latest checkpoint: broker-paper execution delivered

2026-10-09T01:47:33.497113+00:00 — [current delivery](reports/2026-10-09-BROKER_EXECUTION_DELIVERY.md). 140 tests passed; independent paper broker inventory/ledger reconciliation passed; new agent experiment tools present and broker service active. PAPER authority retained. Earlier initial-account-reconciliation and incomplete-adapter notes below are timestamped historical scope; broker-paper integration is now implemented. No production fill or LIVE income is claimed by startup verification.

# Current state — approved overhaul deployed

Updated: 2026-10-09T01:21:28.905994+00:00.

## Scope
Production `/srv/forge` on the dedicated Imagine Forge server. Owner approved the intelligence/economic overhaul, training, continuity and automatic paper experimentation. No LIVE activation, funding, transfers, new subscriptions or Telegram messages were authorized or performed. Preserve pre-existing dirty changes; original head remains `7b6fca7cd9975fea2e5227d3591550e673f0cc10`.

## Rehydrate first
Read [delivery report](reports/2026-10-09-OVERHAUL_DELIVERY.md), [team analysis](reports/2026-10-09-TEAM_ANALYSIS.md), [active session](sessions/20261009-approved-overhaul.md), WORK_QUEUE and baseline/production evidence. Runtime snapshots are observations, not permanent values.

## Deployed
- Common settled LIVE net less all Forge costs; real/paper capital separated; independent reconciliation remains UNKNOWN.
- Durable inference/compute admission, metered workforce gateway, guarded explicit Modal experiments, evidence contamination exclusion, transactional workflow advance, repaired risk JSON/counts, action/outcome role contracts.
- Pro high available for justified deep work; Flash high routine workforce. PI on command center separately defaults to V4 Pro/high.
- Official Alpaca curriculum, legal order/global-state checks, corrected recent completed-bar query, blind trade drill removed.
- Automatic hourly local forward paper experiments: $50 fixed simulated bankroll, two $10 slots, future-only observations, cost/exit/loss rules, retain/rotate after review. These are local modeled fills, not broker fills or income. Existing crypto/prediction loops continue independently.
- Separate Kalshi LIVE path now requires global LIVE mode and authorization. PAPER cannot submit real orders through it.
- Continuity export every 15 minutes and Luke research/results tool/API.

## Last observations (~01:17 UTC)
PAPER / global RUNNING / LIVE false. Real treasury $28.27; Kalshi funding $0; independent account reconciliation UNKNOWN. Last-24h settled live income $0, inference $0.644908, estimated compute $8.221923, net −$8.866831. Provider shared balance about $0.13 and autonomous inference admission rejected new paid work with HTTP 402. Modal month approximately $25.54/$30. Deterministic work continues. Re-read current values before reporting.

New Alpaca trials registered October 9 with zero completed future sessions and zero earnings. Corrected historical curriculum: three modeled trades, +$0.359637, insufficient independent evidence. No production forward profitability has been established. Workforce grade remains THEATER_RISK.

## Verification and receipts
128 isolated tests passed, one warning. Production health/risk/performance/research/capabilities/workforce returned 200; forward service completed twice without backfilling historical trades. Forge/Hermes/ops/engineering, deployer/guardian, continuity and forward timers active. Receipt `/srv/forge/.engineering/20261009-overhaul/deployment.json`; backups beside it. Additive migration 0018 present. Production evidence `evidence/2026-10-09-overhaul-production.json`.

## Next work
Observe 24h/7d outcomes; broker-paper adapter/exits/reconciliation now deployed and verified at startup; independent venue/provider billing reconciliation; typed unified experiment registry and independently tested new mechanisms; explicit admitted Modal proposal tool; fix contaminated triangle fee/fill economics; finish shared portfolio allocator and historical workflow closure/provenance. The automatic equity loop rotates a fixed library and is not an arbitrary autonomous algorithm coder.

Rollback must preserve newer financial rows and migration. Disable the new forward timer/service before reverting its module; restore/remove its systemd units explicitly. Do not restore an old whole database over new fills. Original governing precedence and owner STOPPED remain authoritative.
