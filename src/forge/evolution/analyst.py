"""Live Strategy Analyst — real-time judgment of every deployed algorithm (operator directive: never stop improving).

Every 60 s, for each PRODUCTION / CHALLENGER / SHADOW strategy:
  • live performance: realized net (closed), open P&L marked to live prices, trade count, win rate;
  • expectation: what its validation evidence predicted (holdout mean / win rate);
  • decay detection: one-sided CUSUM on (actual − expected) per-trade returns (catches drift in a few trades,
    not after a disaster); a single loss is NOT a failure — variance is modeled;
  • verdict: THRIVING · ON_TRACK · WARMING_UP · DRIFTING · FAILING.
Actions (autonomous):
  FAILING  → cut: demote to SHADOW (capital withdrawn) + DeepSeek targeted REBUILD (successor genomes with lineage)
  DRIFTING → reduce: flagged; DeepSeek diagnosis queued; evidence-weighted sizing already shrinks its capital
  THRIVING → amplify: DeepSeek designs upgraded challengers that must beat the incumbent (incumbent keeps earning)
All verdicts are persisted, narrated on the live feed, and shown on the founder portal.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from typing import Any

from forge.strategies.registry import State

log = logging.getLogger("forge.analyst")


def cusum_negative(returns: list[float], expected: float, slack: float, threshold: float) -> tuple[float, bool]:
    """One-sided lower CUSUM: accumulates shortfall vs expectation beyond `slack`; alarm when it exceeds `threshold`."""
    s = 0.0
    for r in returns:
        s = max(0.0, s + (expected - r) - slack)
    return s, s > threshold


class StrategyAnalyst:
    def __init__(self, forge: Any, period_s: float = 60.0) -> None:
        self.f = forge
        self.period = period_s
        self.last_action: dict[str, float] = {}

    def _analyze(self, sid: str, state: State, family: str) -> dict[str, Any]:
        db, book = self.f.db, self.f.book if self.f.book in ("live", "paper") else "paper"
        closed = db.query("SELECT realized_pnl_usd, fees_usd, cost_usd, closed_at FROM positions WHERE strategy_id = ? AND book = ? "
                          "AND status='CLOSED' AND CAST(cost_usd AS REAL) > 0 ORDER BY closed_at", (sid, book))
        rets = [(float(r["realized_pnl_usd"]) - float(r["fees_usd"])) / float(r["cost_usd"]) for r in closed]
        realized = sum(float(r["realized_pnl_usd"]) - float(r["fees_usd"]) for r in closed)
        marks = self.f.market.marks()
        open_pnl, open_n = 0.0, 0
        for p in db.query("SELECT symbol, qty, cost_usd FROM positions WHERE strategy_id = ? AND book = ? AND status != 'CLOSED'", (sid, book)):
            px = marks.get(p["symbol"])
            if px and float(p["qty"]) > 0:
                open_pnl += float(p["qty"]) * px - float(p["cost_usd"])
                open_n += 1
        hold = self.f.reg.latest_metrics(sid, "holdout") or {}
        fwd = self.f.reg.latest_metrics(sid, "forward") or {}
        exp_mean = float(hold.get("mean_net") or 0.0) * 0.5          # learned haircut prior: expect half of backtest
        exp_std = float(hold.get("std") or 0.03) or 0.03
        n = len(rets)
        cus, alarm = cusum_negative(rets, exp_mean, slack=0.25 * exp_std, threshold=2.5 * exp_std)
        win = sum(r > 0 for r in rets) / n if n else None
        mean = sum(rets) / n if n else None
        if n < 3:
            verdict = "WARMING_UP"
        elif alarm and (mean or 0) < 0:
            verdict = "FAILING"
        elif alarm or (mean is not None and mean < exp_mean - exp_std / math.sqrt(n)):
            verdict = "DRIFTING"
        elif mean is not None and mean >= exp_mean and realized > 0:
            verdict = "THRIVING"
        else:
            verdict = "ON_TRACK"
        return {"id": sid, "family": family, "state": state.value, "verdict": verdict, "trades": n, "open": open_n,
                "realized_usd": realized, "open_pnl_usd": open_pnl, "live_total_usd": realized + open_pnl,
                "win_rate": win, "mean_net": mean, "expected_mean": exp_mean, "cusum": cus,
                "forward_n": fwd.get("n", 0), "forward_mean": fwd.get("mean_net"), "holdout_n": hold.get("n")}

    async def tick(self) -> list[dict[str, Any]]:
        reports = []
        for g, st, _ in self.f.reg.list((State.PRODUCTION, State.CHALLENGER, State.SHADOW)):
            rep = self._analyze(g.id, st, g.family)
            reports.append(rep)
            await self._act(g, st, rep)
        reports.sort(key=lambda r: -r["live_total_usd"])
        self.f.db.kv_set("analyst.report", {"ts": time.time(), "strategies": reports})
        self.f.workers["analyst"] = {"what": f"judging {len(reports)} live algorithms vs their evidence (CUSUM decay watch)",
                                     "count": 1, "since": time.time(), "where": "real-time"}
        return reports

    async def _act(self, g: Any, st: State, rep: dict[str, Any]) -> None:
        now = time.time()
        key = f"{g.id}:{rep['verdict']}"
        if now - self.last_action.get(key, 0) < 3600:
            return
        brain = self.f.brain
        if rep["verdict"] == "FAILING":
            self.last_action[key] = now
            if st in (State.PRODUCTION, State.CHALLENGER):
                self.f.reg.transition(g.id, State.SHADOW, "Analyst: FAILING (CUSUM decay vs evidence) → capital withdrawn, rebuild",
                                      evidence=rep)
            await self.f.say("Strategy Analyst", f"CUT {g.family} {g.id[:18]}: {rep['trades']} trades, mean {rep['mean_net']:+.2%} vs "
                                                 f"expected {rep['expected_mean']:+.2%} (CUSUM alarm) → capital withdrawn; DeepSeek rebuilding it",
                             level="warn", strategy=g.id)
            succ = self._successor(g)
            if succ:
                self.f.reg.transition(succ, State.CHALLENGER, f"Succession: replaces {g.id} (best ready challenger on the bench)")
                self.f.reg.add_lineage(g.id, succ, "OUTPERFORMED_BY", {"by": "analyst succession"})
                await self.f.say("Strategy Analyst", f"SUCCESSION: {succ[:18]} promoted to CHALLENGER — capital keeps working while "
                                                     f"{g.id[:18]} is rebuilt", strategy=succ)
            if brain is not None:
                asyncio.create_task(brain.rebuild(g.id, rep, critical=st in (State.PRODUCTION, State.CHALLENGER) and self.f.book == "live"))
        elif rep["verdict"] == "DRIFTING":
            self.last_action[key] = now
            await self.f.say("Strategy Analyst", f"DRIFT {g.family} {g.id[:18]}: mean {rep['mean_net']:+.2%} vs expected "
                                                 f"{rep['expected_mean']:+.2%} — sizing shrinks automatically; diagnosis queued", strategy=g.id)
            if brain is not None:
                asyncio.create_task(brain.rebuild(g.id, rep, critical=False, mode="repair"))
        elif rep["verdict"] == "THRIVING":
            self.last_action[key] = now
            await self.f.say("Strategy Analyst", f"THRIVING {g.family} {g.id[:18]}: live {rep['live_total_usd']:+.4f} USD over "
                                                 f"{rep['trades']} trades — incumbent keeps earning; DeepSeek designing upgraded challengers",
                             strategy=g.id)
            if brain is not None:
                asyncio.create_task(brain.rebuild(g.id, rep, critical=False, mode="amplify"))

    def _successor(self, g: Any) -> str | None:
        """Best bench strategy (SHADOW) with positive live-forward evidence, same family preferred."""
        best, best_score = None, 0.0
        for c, st, _ in self.f.reg.list((State.SHADOW,)):
            if c.id == g.id:
                continue
            ev = self.f.arena.evidence(c.id)
            fwd = self.f.reg.latest_metrics(c.id, "forward") or {}
            if ev is None or ev.p_edge < 0.75 or (fwd.get("mean_net") or 0) <= 0:
                continue
            score = ev.p_edge + (0.1 if c.family == g.family else 0.0) + min(0.2, (fwd.get("n") or 0) / 50)
            if score > best_score:
                best, best_score = c.id, score
        return best

    async def run(self) -> None:
        while not self.f.stop_event.is_set():
            self.f.sup.beat("analyst")
            try:
                await self.tick()
            except Exception:
                log.exception("analyst tick failed")
            await asyncio.sleep(self.period)


def report(db: Any) -> dict[str, Any]:
    return db.kv_get("analyst.report") or {"ts": None, "strategies": []}


__all__ = ["StrategyAnalyst", "report", "json"]
