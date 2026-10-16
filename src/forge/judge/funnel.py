"""The cost-ordered funnel: facts kill before judgements, and each rung kills harder than the last.

THE CORE DISCIPLINE (and the fix for "53k candidates/hour, $0 income"): a candidate that a free
arithmetic comparison can reject must NEVER reach a paid judgement. Rungs are ordered by cost:

    R0 free arithmetic   no network, no model   — kills hundreds
    R1 fact kill         cheap reads (ledger/on-chain/venue facts) — kills tens
    R2 structural        identity/carry/basis checks — still free of judgement
    R3 judge             typed judgement seats, answered by an OFFICER's own Qwen call (no extra inference)
    R4 pick              one choice over survivors

R0-R2 are pure Python and cost nothing. R3-R4 are answered inside an officer's interactive session,
so the funnel never triggers a standalone model call — that keeps it compliant with the Token Plan
(no backend batch calls) AND keeps inference frugal.

Every rejection is logged with the rung and the check that fired. Two health metrics fall out, both
from the reference desk and both correct:
  * rejections/day  — under ~10 means the filter is misconfigured, not that the market is quiet.
  * per-rung kill-rate — a rung that kills nothing is paying for itself with nothing.

Benching is on the CHECK, not the candidate, with a reason-specific TTL: a structural fact that will
never change (no identity, unkeyed rail, fee-negative) benches for ~forever; a condition that matures
inside the hour (too young, volume too low) benches briefly so we do not miss the setup ripening.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from forge.judge.thresholds import FUNNEL, BENCH_MINUTES, DEFAULT_BENCH_MINUTES


@dataclass
class Candidate:
    """One thing the funnel is deciding about. `facts` are numbers already fetched (no network here)."""
    id: str
    rail: str
    family: str = ""
    facts: dict[str, Any] = field(default_factory=dict)
    # filled as it descends
    rung_reached: int = -1
    killed_by: str | None = None
    killed_at_rung: int | None = None


@dataclass
class FunnelResult:
    survivors: list[Candidate]
    killed: list[tuple[Candidate, str, int]]      # (candidate, check, rung)
    bench_set: list[tuple[str, str, float]]        # (id, reason, until_ts)
    stats: dict[str, Any]


# A check returns None to pass, or a short reason string to kill. Checks are pure: facts in, verdict out.
Check = Callable[[Candidate], "str | None"]


class Funnel:
    """Deterministic, zero-inference candidate funnel with cost-ordered rungs and reason-benched rejects."""

    def __init__(self, db: Any, *, r0: list[Check] = (), r1: list[Check] = (), r2: list[Check] = ()) -> None:
        self.db = db
        self.rungs: dict[int, list[Check]] = {0: list(r0), 1: list(r1), 2: list(r2)}

    # ---------------- bench ----------------
    def _benched(self, cid: str) -> bool:
        try:
            until = self.db.scalar("SELECT until FROM funnel_bench WHERE id=?", (cid,))
            return bool(until and float(until) > time.time())
        except Exception:
            return False

    def _sit(self, cid: str, reason: str, *, persist: bool = True) -> float:
        mins = BENCH_MINUTES.get(reason, DEFAULT_BENCH_MINUTES)
        until = time.time() + mins * 60
        if not persist:
            return until          # replay/backtest mode: compute the TTL, never touch production state
        try:
            self.db.execute(
                "INSERT INTO funnel_bench(id, reason, until) VALUES(?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET reason=excluded.reason, until=excluded.until",
                (cid, reason, until))
        except Exception:
            pass
        return until

    # ---------------- run ----------------
    def run(self, candidates: list[Candidate], *, max_per_rung: bool = True,
            bench_persist: bool = True) -> FunnelResult:
        """Descend candidates through R0..R2. R3/R4 are officer-judged downstream (not called here).

        Deterministic rungs only. This method makes NO model call and touches NO paid API by design;
        any network reads a check needs must already be in `candidate.facts`.

        bench_persist=False makes the run PURE: it reports what WOULD be benched and for how long
        without writing to funnel_bench or reading production benches. Replay and backtest harnesses
        must use it — a replay that mutates production state poisons the live filter. (Caught in
        review: the first harness run wrote 4,000 real opportunity ids into funnel_bench as
        `fee_negative` for 69 days, which would have blocked genuine candidates for two months.)
        """
        alive: list[Candidate] = []
        killed: list[tuple[Candidate, str, int]] = []
        bench_set: list[tuple[str, str, float]] = []
        rung_counts = {r: {"in": 0, "killed": 0} for r in (0, 1, 2)}

        for c in candidates:
            if bench_persist and self._benched(c.id):
                killed.append((c, "benched", -1))
                continue
            alive.append(c)

        for rung in (0, 1, 2):
            checks = self.rungs.get(rung) or []
            cap = FUNNEL.get(f"r{rung}_free_arithmetic" if rung == 0 else
                             f"r{rung}_fact_kill" if rung == 1 else "r2_structural", {}).get("max_pass")
            nxt: list[Candidate] = []
            for c in alive:
                rung_counts[rung]["in"] += 1
                verdict = None
                for chk in checks:
                    try:
                        verdict = chk(c)
                    except Exception as e:                 # a broken check must not silently pass
                        verdict = f"check_error:{type(e).__name__}"
                    if verdict:
                        break
                if verdict:
                    c.killed_by, c.killed_at_rung = verdict, rung
                    rung_counts[rung]["killed"] += 1
                    killed.append((c, verdict, rung))
                    bench_set.append((c.id, verdict, self._sit(c.id, verdict, persist=bench_persist)))
                    if bench_persist:
                        # Log the reject so funnel_health's rejections/day is a real number. Only in
                        # production runs — a pure replay (bench_persist=False) must not write history.
                        try:
                            self.db.insert("funnel_rejects", {
                                "ts": time.time(), "candidate_id": c.id, "rail": c.rail,
                                "family": c.family, "rung": rung, "reason": verdict})
                        except Exception:
                            pass
                else:
                    c.rung_reached = rung
                    nxt.append(c)
            alive = nxt
            if max_per_rung and cap is not None and len(alive) > cap:
                # Deterministic priority: keep the candidates with the highest measured edge-per-dollar
                # so the scarce downstream judgement slots go to the best, not the first.
                alive.sort(key=lambda c: float(c.facts.get("edge_per_dollar_h") or 0.0), reverse=True)
                for c in alive[cap:]:
                    c.killed_by, c.killed_at_rung = "rung_budget", rung
                    killed.append((c, "rung_budget", rung))
                    bench_set.append((c.id, "rung_budget",
                                      self._sit(c.id, "momentum_spent", persist=bench_persist)))
                alive = alive[:cap]

        stats = {
            "in": len(candidates), "survivors": len(alive), "killed": len(killed),
            "rung_kill_rate": {r: (round(rc["killed"] / rc["in"], 3) if rc["in"] else None)
                               for r, rc in rung_counts.items()},
            "rung_in": {r: rc["in"] for r, rc in rung_counts.items()},
            "ts": time.time(),
        }
        return FunnelResult(alive, killed, bench_set, stats)

    # ---------------- health ----------------
    def daily_rejection_count(self, since_ts: float) -> int:
        try:
            return int(self.db.scalar(
                "SELECT COUNT(*) FROM funnel_rejects WHERE ts>=?", (since_ts,)) or 0)
        except Exception:
            return 0

    def health(self) -> dict[str, Any]:
        """The desk's own filter-health check. Under ~10 rejections/day => filter misconfigured."""
        now = time.time()
        rej24 = self.daily_rejection_count(now - 86400)
        return {
            "rejections_24h": rej24,
            "filter_misconfigured": rej24 < 10,
            "note": ("under 10 rejections/day means the filter is misconfigured, not that the market "
                     "is quiet — widen the universe or loosen R0" if rej24 < 10 else "healthy"),
            "benched_now": self._benched_count(),
        }

    def _benched_count(self) -> int:
        try:
            return int(self.db.scalar("SELECT COUNT(*) FROM funnel_bench WHERE until>?", (time.time(),)) or 0)
        except Exception:
            return 0
