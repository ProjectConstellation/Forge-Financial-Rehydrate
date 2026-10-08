"""Real-time Edge Decay Engine — milking detection (blueprint §33).

Improvements over naive recent-vs-prior means:
- CUSUM on per-trade true-net residuals vs rolling expectation
- explicit state machine HEALTHY→WATCH→WEAKENING→REDUCE→PAUSE→DIAGNOSE→…
- hysteresis + min trades; never pause on a single loss
- actuates: kv actions + ops directives + challenger request
"""
from __future__ import annotations

import json
import logging
import math
import time
from typing import Any

log = logging.getLogger("forge.edge_decay")

ADVERSE_WINDOWS_TO_PAUSE = 3
CUSUM_H = 2.5       # decision threshold (in residual σ units)
CUSUM_K = 0.5       # allowance
MIN_TRADES = 3


def _f(x: Any, d: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else d
    except Exception:
        return d


def cusum_neg(xs: list[float]) -> float:
    """One-sided CUSUM for downward shifts; returns max cumulative sum in σ units."""
    if len(xs) < 3:
        return 0.0
    mu = sum(xs) / len(xs)
    var = sum((x - mu) ** 2 for x in xs) / max(len(xs) - 1, 1)
    sd = math.sqrt(var) if var > 1e-12 else (abs(mu) * 0.5 + 1e-6)
    s, m = 0.0, 0.0
    for x in xs:
        s = max(0.0, s - (x - mu) / sd - CUSUM_K)
        m = max(m, s)
    return m


def classify(cusum: float, recent_m: float, prior_m: float, n: int, adverse: int) -> str:
    if n < MIN_TRADES:
        return "WATCH" if n >= 2 else "HEALTHY"
    if cusum >= CUSUM_H and adverse >= ADVERSE_WINDOWS_TO_PAUSE and recent_m < 0:
        return "PAUSE"
    if cusum >= CUSUM_H and adverse >= 2:
        return "REDUCE"
    if cusum >= CUSUM_H * 0.66 or (prior_m > 0 and recent_m < prior_m * 0.5):
        return "WEAKENING"
    if cusum >= CUSUM_H * 0.33 or (prior_m > 0 and recent_m < prior_m * 0.8):
        return "WATCH"
    return "HEALTHY"


class EdgeDecayMonitor:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def scorecard(self, strategy_id: str) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        open_n = db.scalar(
            "SELECT COUNT(*) FROM positions WHERE strategy_id=? AND status!='CLOSED'", (strategy_id,)) or 0
        closed = db.query(
            "SELECT realized_pnl_usd, fees_usd, opened_at, closed_at FROM positions "
            "WHERE strategy_id=? AND status='CLOSED' ORDER BY closed_at DESC LIMIT 80", (strategy_id,)) or []
        # chronological for CUSUM
        pnls_desc = [_f(r.get("realized_pnl_usd")) - _f(r.get("fees_usd")) for r in closed]
        pnls = list(reversed(pnls_desc))
        fees = sum(_f(r.get("fees_usd")) for r in closed)
        n = len(pnls)
        realized = sum(pnls)
        recent = pnls_desc[:5]
        prior = pnls_desc[5:10]
        recent_m = sum(recent) / len(recent) if recent else 0.0
        prior_m = sum(prior) / len(prior) if prior else 0.0
        csum = cusum_neg(pnls[-30:]) if pnls else 0.0
        # adverse windows: last three non-overlapping pairs
        adverse = 0
        for i in range(0, min(9, len(pnls_desc)), 3):
            w = pnls_desc[i:i + 3]
            if w and sum(w) / len(w) < 0:
                adverse += 1
        state = classify(csum, recent_m, prior_m, n, adverse)
        decay = min(1.0, csum / max(CUSUM_H, 1e-6))
        if prior_m > 0 and recent_m < 0:
            decay = max(decay, 0.7)
        st_row = db.query_one(
            "SELECT population, fitness, status_reason FROM strategies WHERE id=?", (strategy_id,)) or {}
        # rolling $/h
        day_pnl = 0.0
        for r in closed:
            try:
                import datetime as dt
                ca = r.get("closed_at") or ""
                if ca and (now - dt.datetime.fromisoformat(ca.replace("Z", "+00:00")).timestamp()) <= 86400:
                    day_pnl += _f(r.get("realized_pnl_usd")) - _f(r.get("fees_usd"))
            except Exception:
                pass
        return {
            "strategy_id": strategy_id,
            "ts": now,
            "expected_edge": _f(st_row.get("fitness")),
            "realized_edge": recent_m,
            "true_net_pnl": realized,
            "rolling_usd_per_h": round(day_pnl / 24.0, 6),
            "slippage": None,
            "fees": fees,
            "confidence": max(0.0, min(1.0, n / 30.0)),
            "regime": "UNKNOWN",
            "drawdown": min(0.0, min(pnls) if pnls else 0.0),
            "capital_efficiency": (realized) / max(fees + abs(realized) * 0.01, 1e-6),
            "edge_decay_score": round(decay, 4),
            "cusum": round(csum, 4),
            "adverse_windows": adverse,
            "state": state,
            "open_positions": int(open_n),
            "n_closed": n,
            "population": st_row.get("population"),
            "status_reason": st_row.get("status_reason"),
        }

    def actuate(self, card: dict[str, Any]) -> dict[str, Any] | None:
        st = card.get("state")
        if st not in ("WATCH", "WEAKENING", "REDUCE", "PAUSE"):
            return None
        now = time.time()
        action = {
            "ts": now,
            "strategy_id": card["strategy_id"],
            "state": st,
            "edge_decay_score": card["edge_decay_score"],
            "cusum": card.get("cusum"),
            "protocol": "DETECT→VERIFY→REDUCE/PAUSE→DIAGNOSE→REALLOCATE→CHALLENGER→VALIDATE→PROMOTE→MONITOR",
        }
        db = self.f.db
        if st in ("REDUCE", "PAUSE"):
            sid = card["strategy_id"]
            try:
                db.execute(
                    "UPDATE strategies SET status_reason=? WHERE id=?",
                    (f"edge_decay:{st}:cusum={card.get('cusum')}", sid),
                )
            except Exception:
                pass
            # PAPER: actuate immediately — do not wait for human/Hermes to notice
            book = getattr(self.f, "book", "paper")
            try:
                from forge.strategies.registry import State
                cur = self.f.reg.state(sid)
                if book == "paper" and cur in (State.SHADOW, State.CHALLENGER, State.EXPERIMENTAL):
                    if st == "PAUSE":
                        self.f.reg.transition(
                            sid, State.HIBERNATING,
                            f"edge_decay PAUSE: cusum={card.get('cusum')} — drop until challenger beats it",
                        )
                        action["transition"] = "HIBERNATING"
                    elif st == "REDUCE" and cur == State.CHALLENGER:
                        self.f.reg.transition(
                            sid, State.SHADOW,
                            f"edge_decay REDUCE: demote challenger cusum={card.get('cusum')}",
                        )
                        action["transition"] = "SHADOW"
            except Exception as e:
                action["transition_error"] = str(e)[:120]
            try:
                db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, "alpha_inventor",
                     f"CHALLENGER needed: {sid} state={st} decay={card['edge_decay_score']} "
                     f"cusum={card.get('cusum')}. Invent replacement; do not revive milched edge.",
                     "high", "OPEN", "edge_decay"),
                )
                db.execute(
                    "INSERT INTO ops_directives (ts, role, instruction, priority, status, requested_by) VALUES (?,?,?,?,?,?)",
                    (now, "governor",
                     f"REALLOCATE away from {sid} ({st}). Prefer higher marginal-value PAPER rails.",
                     "high", "OPEN", "edge_decay"),
                )
                action["directives"] = True
            except Exception as e:
                action["directive_error"] = str(e)[:120]
        return action

    def evaluate_all(self) -> dict[str, Any]:
        db = self.f.db
        ids = [r["id"] for r in db.query(
            "SELECT id FROM strategies WHERE population IN ('SHADOW','CHALLENGER','PRODUCTION') LIMIT 200")] or []
        cards = [self.scorecard(i) for i in ids]
        actions = []
        for c in cards:
            a = self.actuate(c)
            if a:
                actions.append(a)
        cards.sort(key=lambda c: -c["edge_decay_score"])
        rep = {
            "ts": time.time(),
            "n": len(cards),
            "actions": actions[:30],
            "best": [c for c in sorted(cards, key=lambda x: x.get("rolling_usd_per_h") or 0, reverse=True)[:10]],
            "worst": cards[:10],
            "by_state": {},
        }
        for c in cards:
            rep["by_state"][c["state"]] = rep["by_state"].get(c["state"], 0) + 1
        db.kv_set("edge_decay", rep)
        return rep

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("edge_decay")
            try:
                await asyncio.to_thread(self.evaluate_all)
            except Exception as e:
                log.warning("edge_decay: %s", e, exc_info=True)
            await asyncio.sleep(300)
