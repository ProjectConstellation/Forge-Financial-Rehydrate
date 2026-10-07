"""Self-healing at every layer (OP-012) + the SELF-HEALING HEALTH SCORE.

Layers (all concurrent, all isolated — one failing subsystem never takes down unrelated loops):
  1 OPERATIONAL  supervisor restarts crashed/stalled loops (core/supervisor.py); this monitor adds event-loop lag,
                 memory pressure (controlled self-restart under systemd before the OOM killer), DB liveness, provider breakers.
  2 ECONOMIC     Strategy Analyst cut/succession/rebuild (evolution/analyst.py) + bench coverage (tested replacement waiting).
  3 DATA+EXEC    bar-data integrity quarantine + refetch; paper/live wallet-truth reconciliation with automatic state rebuild;
                 per-symbol execution pause on uncertainty; idempotent orders everywhere.
  4 INTELLIGENCE DeepSeek circuit breaker (closed → open → half-open) with queued retry; engine never waits on AI.
Health score: six 0–100 components + overall, persisted and pushed to the founder portal every second.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import math
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

log = logging.getLogger("forge.healing")


@dataclass
class Circuit:
    """Provider circuit breaker: CLOSED (healthy) → OPEN after N consecutive failures → HALF_OPEN after cooldown (one
    trial call) → CLOSED on success / OPEN again (cooldown doubles, capped) on failure."""
    name: str
    threshold: int = 3
    base_cooldown_s: float = 300.0
    max_cooldown_s: float = 3600.0
    failures: int = 0
    state: str = "CLOSED"
    opened_at: float = 0.0
    cooldown_s: float = 300.0
    total_failures: int = 0
    total_success: int = 0
    last_error: str = ""
    history: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cooldown_s = self.base_cooldown_s

    def allow(self) -> bool:
        if self.state == "OPEN" and time.time() - self.opened_at >= self.cooldown_s:
            self.state = "HALF_OPEN"
        return self.state in ("CLOSED", "HALF_OPEN")

    def success(self) -> None:
        self.total_success += 1
        self.failures = 0
        if self.state != "CLOSED":
            self.state, self.cooldown_s = "CLOSED", self.base_cooldown_s

    def failure(self, err: str = "") -> None:
        self.total_failures += 1
        self.failures += 1
        self.last_error = err[:200]
        if self.state == "HALF_OPEN" or self.failures >= self.threshold:
            if self.state == "HALF_OPEN":
                self.cooldown_s = min(self.max_cooldown_s, self.cooldown_s * 2)
            self.state, self.opened_at = "OPEN", time.time()

    def snapshot(self) -> dict[str, Any]:
        return {"name": self.name, "state": self.state, "failures": self.failures, "total_failures": self.total_failures,
                "total_success": self.total_success, "cooldown_s": round(self.cooldown_s), "last_error": self.last_error}


def bar_integrity(series_arrays: dict[str, Any], interval_s: int | None = None, now_s: float | None = None,
                  live_price: float | None = None) -> list[str]:
    """Problems with the latest bars. Genuine violent moves are NOT corruption: a spike is only a bad print if it reverts
    on the next bar and the live market does not corroborate it. Missing candles in thin markets are normal; only a stale
    latest bar counts."""
    import numpy as np
    c, h, lo, ts = (np.asarray(series_arrays[k], dtype=float) for k in ("close", "high", "low", "ts"))
    issues: list[str] = []
    if len(c) < 50:
        return ["insufficient history"]
    tail = slice(-50, None)
    if not np.all(np.isfinite(c[tail])) or np.any(c[tail] <= 0):
        issues.append("non-finite or non-positive prices")
        return issues
    if np.any(h[tail] < lo[tail]):
        issues.append("high < low (contradictory bar)")
    r = np.diff(np.log(np.maximum(c[tail], 1e-12)))
    med = float(np.median(np.abs(r))) or 1e-6
    big = max(0.25, 40 * med)
    for i in range(len(r) - 1):
        if abs(r[i]) > big and np.sign(r[i + 1]) == -np.sign(r[i]) and abs(r[i + 1]) > 0.6 * abs(r[i]):
            issues.append(f"bad print: {r[i]:+.1%} spike reverted next bar ({r[i + 1]:+.1%})")
            break
    if live_price and live_price > 0 and abs(live_price / c[-1] - 1) > max(0.15, 20 * med):
        issues.append(f"bars disagree with live market ({c[-1]:.6g} vs live {live_price:.6g})")
    if interval_s and now_s and now_s - ts[-1] > 4 * interval_s:
        issues.append(f"stale bars (latest {int((now_s - ts[-1]) / interval_s)} intervals old)")
    return issues


class HealthMonitor:
    """Runs every 10 s: measures, heals, scores."""

    def __init__(self, forge: Any) -> None:
        self.f = forge
        self.lag_ms = 0.0
        self.rss_mb = 0.0
        self.db_ok = True
        self.quarantined: dict[str, dict[str, Any]] = {}
        self.paper_rebuilds = 0
        self.last: dict[str, Any] = {}
        self.events: list[str] = []

    # ---------------- measurements ----------------
    async def _loop_lag(self) -> float:
        t = time.perf_counter()
        await asyncio.sleep(0)
        await asyncio.sleep(0.05)
        return max(0.0, (time.perf_counter() - t - 0.05) * 1000)

    def _rss(self) -> float:
        try:
            with open(f"/proc/{os.getpid()}/status") as fh:
                for line in fh:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024
        except OSError:
            pass
        return 0.0

    # ---------------- healing actions ----------------
    async def _heal_memory(self) -> None:
        if self.rss_mb > 1300:                                   # MemoryHigh 1.5G: shed caches first
            gc.collect()
            for eng in self.f.bars.values():
                for st in eng.state.values():
                    if len(st.series) > eng.window:
                        st.series = type(st.series).from_arrays(st.series.interval_s, st.series.arrays(), eng.window + 50)
            await self.f.say("Self-Healing", f"Memory {self.rss_mb:.0f} MB → caches trimmed + GC", level="warn")
        if self._rss() > 1750:                                   # last resort: checkpointed controlled restart (systemd)
            await self.f.say("Self-Healing", "Memory critical → checkpoint + controlled restart (state is in SQLite)", level="error")
            self.f.audit.append("SELF_RESTART", {"reason": "memory", "rss_mb": self.rss_mb})
            os._exit(75)

    def _check_db(self) -> None:
        try:
            self.f.db.scalar("SELECT 1")
            self.db_ok = True
        except Exception as e:
            self.db_ok = False
            log.error("db liveness failed: %s — reopening", e)
            try:
                from forge.persistence.db import Database
                self.f.db = Database(self.f.s.db_path)
            except Exception:
                log.exception("db reopen failed")

    async def _heal_data(self) -> None:
        for interval, eng in self.f.bars.items():
            for sym, st in list(eng.state.items()):
                if len(st.series) < 300:
                    continue
                bbo = self.f.market.get_bbo(sym)
                issues = bar_integrity(st.series.arrays(), interval, time.time(), bbo.mid if bbo else None)
                key = f"{sym}@{interval}"
                if issues and key not in self.quarantined:
                    self.quarantined[key] = {"since": time.time(), "issues": issues}
                    self.f.db.kv_set(f"quarantine.{sym}", {"issues": issues, "interval": interval, "since": time.time()})
                    await self.f.say("Self-Healing", f"DATA QUARANTINE {sym} ({interval // 60}m): {'; '.join(issues)} → trading paused "
                                                     "on this market; refetching authoritative bars", level="warn")
                    eng.state.pop(sym, None)                    # drop corrupted cache; next refresh rebuilds from REST/store
                elif not issues and key in self.quarantined:
                    self.quarantined.pop(key, None)
                    self.f.db.kv_set(f"quarantine.{sym}", None)
                    await self.f.say("Self-Healing", f"{sym} data healed → market re-enabled")

    async def _heal_paper_truth(self) -> None:
        """Paper wallet-truth: ledger vs paper venue; on mismatch rebuild the venue state from the ledger (authoritative)."""
        v = getattr(self.f, "venue", None)
        if self.f.book != "paper" or v is None or not hasattr(v, "balances"):
            return
        if any(o.status.value == "OPEN" for o in v.orders.values()):
            return                                              # holds in flight; compare when quiet
        st = self.f.ledger.state("paper")
        diff = abs(float(v.balances.get("USD", Decimal(0)) - st.cash.get("USD", Decimal(0))))
        if diff > 0.01:
            v.balances = {"USD": st.cash.get("USD", Decimal(0)), **{a: h.qty for (_, a), h in st.holdings.items() if h.qty > 0}}
            v.holds = {}
            self.paper_rebuilds += 1
            await self.f.say("Self-Healing", f"Paper venue drifted ${diff:.4f} from the ledger → state rebuilt from the ledger",
                             level="warn")

    async def _heal_bench(self) -> None:
        """Operating law: a tested replacement strategy should be waiting. If the bench is empty, prioritize research."""
        from forge.strategies.registry import State
        live = self.f.reg.list((State.PRODUCTION, State.CHALLENGER))
        bench = self.f.reg.list((State.SHADOW,))
        if live and not bench:
            q = self.f.db.kv_get("evolution.near_miss", []) or []
            for g, _, _ in live:
                if not any(x["id"] == g.id for x in q):
                    q.insert(0, {"id": g.id, "interval": g.interval_s, "p": 0.99, "n": 0, "reasons": ["bench empty"]})
            self.f.db.kv_set("evolution.near_miss", q[:20])

    # ---------------- scoring ----------------
    def score(self) -> dict[str, Any]:
        f = self.f
        loops = f.sup.snapshot()
        alive = sum(1 for x in loops if x["alive"] and x["silent_s"] <= x["limit_s"]) / max(1, len(loops))
        restarts_recent = sum(x["restarts"] for x in loops)
        system = 100 * alive - min(20, restarts_recent * 2) - (15 if self.lag_ms > 250 else 0) - (15 if self.rss_mb > 1300 else 0) \
            - (30 if not self.db_ok else 0)
        q = f.stream.quality
        age = (time.time_ns() - q.last_message_ns) / 1e9 if q.last_message_ns else 999
        feed = (100 if q.connected and age < 5 else 60 if age < 30 else 0) - min(20, len(self.quarantined) * 5)
        unknown = f.db.scalar("SELECT COUNT(*) FROM orders WHERE status = 'UNKNOWN'") or 0
        execution = 100 - (40 if not f.reconciled_ok else 0) - min(40, unknown * 20) - min(30, len(f.breakers.blocking()) * 15)
        from forge.strategies.registry import State
        validated = len(f.reg.list((State.PRODUCTION, State.CHALLENGER, State.SHADOW)))
        rep = (f.db.kv_get("analyst.report") or {}).get("strategies", [])
        failing = sum(1 for r in rep if r["verdict"] == "FAILING")
        bench = len(f.reg.list((State.SHADOW,)))
        strategy = min(100, 40 + 10 * validated) - 15 * failing - (0 if bench else 20)
        b = getattr(f, "brain", None)
        if b is None:
            ai = 40
        else:
            c = b.circuit
            ai = (100 if c.state == "CLOSED" else 60 if c.state == "HALF_OPEN" else 30) - {"NORMAL": 0, "LEAN": 20, "CRITICAL": 40}.get(b.tier, 0)
        resid = f.ledger.check_balanced(f.book if f.book in ("live", "paper") else "paper")
        t = f.treasury
        eq0 = float(f.day.get("start_equity") or 0)
        dd = (float(t.get("daily_pnl_usd") or 0) / eq0) if eq0 else 0.0
        treasury = 100 - (50 if resid != 0 else 0) - (30 if not f.reconciled_ok else 0) - min(40, max(0.0, -dd) * 400)
        parts = {k: int(max(0, min(100, v))) for k, v in (("system", system), ("feed", feed), ("execution", execution),
                                                          ("strategy", strategy), ("ai", ai), ("treasury", treasury))}
        overall = int(round(0.6 * min(parts.values()) + 0.4 * sum(parts.values()) / len(parts)))
        # organism state: EARNING · LEARNING · HEALING · PREPARING TO EARN BETTER
        open_pos = f.db.scalar("SELECT COUNT(*) FROM positions WHERE book = ? AND status != 'CLOSED'", (f.book,)) or 0
        healing = bool(self.quarantined) or unknown or not f.reconciled_ok or (b is not None and b.circuit.state != "CLOSED") \
            or any(not x["alive"] for x in loops)
        mode = "HEALING" if healing else "EARNING" if open_pos else "LEARNING" if any(
            w.get("count") for k, w in f.workers.items() if k in ("modal", "research", "brain")) else "PREPARING TO EARN BETTER"
        return {"overall": overall, "parts": parts, "organism": mode, "lag_ms": round(self.lag_ms, 1), "rss_mb": round(self.rss_mb),
                "quarantined": list(self.quarantined), "unknown_orders": unknown, "paper_rebuilds": self.paper_rebuilds,
                "bench": bench, "validated": validated, "ai_circuit": b.circuit.snapshot() if b else None,
                "modal_circuit": f.compute.circuit.snapshot() if getattr(f, "compute", None) is not None and hasattr(f.compute, "circuit") else None}

    async def run(self) -> None:
        n = 0
        while not self.f.stop_event.is_set():
            self.f.sup.beat("healing")
            n += 1
            try:
                self.lag_ms = await self._loop_lag()
                self.rss_mb = self._rss()
                self._check_db()
                await self._heal_memory()
                if n % 3 == 0:
                    await self._heal_data()
                    await self._heal_paper_truth()
                    await self._heal_bench()
                self.last = self.score()
                self.f.db.kv_set("health.score", self.last)
            except Exception:
                log.exception("health monitor cycle failed")
            await asyncio.sleep(10)


def isfinite(x: float) -> bool:
    return math.isfinite(x)
