"""FORGE PROFIT VELOCITY engine — maximum defensible true-net $/hour across every rail, given capital and evidence.

Every earning stream i is reduced to independent *clusters* (correlated signals — e.g. all Kalshi bets on the same
underlying, expiry and direction — count once). From the last 72 h of evidence (live, shadow or paper):
    λ_i  clusters / hour                      μ_i, σ_i  P&L per cluster at unit size (1 contract per signal / $1 notional)
    c_i  capital per cluster at unit size     T_i       hours that capital is locked (signal → settlement/exit)
    m_i = λ_i μ_i   (hourly mean / unit)      v_i = λ_i (σ_i² + μ_i²)   (hourly variance / unit, compound Poisson)
Sizing y_i (units per cluster) solves, for treasury W, reserve F (regime) and deployable D = W − F:
    max Σ y_i m_i  +  idle-yield on unlocked capital
    s.t.  y_i ≤ liquidity cap · tier concentration cap (share·D / c_i) · fractional Kelly k_tier·D·m_i/v_i
          Σ_venue y_i λ_i c_i T_i ≤ 0.95·D_venue                       (Little's law: capital locked in flight)
          Σ y_i² v_i ≤ (2 D / ln(1/δ)) Σ y_i m_i                         (P(drawdown ≥ D) ≤ δ, drift-diffusion bound)
Mean–variance optimal direction y_i ∝ m_i / v_i, clipped by caps; one scalar bisection finds the frontier. Uncapped,
$/h_max = 2·D·S / ln(1/δ) with S = Σ m_i²/v_i (sum of squared hourly Sharpe ratios) — the precise statement of what has
to grow (deployable capital, edge, independent flow) for the hourly target to be met. The engine evaluates this frontier
for: live-now (executable + gated), proven (LCB edges), potential (posterior means), and for larger treasuries
(scaling curve); differences give the marginal value of capital, of proof and of flow → research priorities.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

from forge.treasury import regime as treg

log = logging.getLogger("forge.velocity")

WINDOW_H = 72.0
MIN_WINDOW_H = 6.0
DELTA = 0.05
UTIL_MAX = 0.95
N0_SHRINK = 5.0
Z90 = 1.2816
OPERATOR_MIN_TARGET = 1.0                     # $/h, operator bar
KALSHI_DEPTH_UNITS = 20.0                     # contracts per signal assumed fillable at the quoted ask (until WS depth)
MEMBERSHIP_USD_PER_H = 4.99 / (30 * 24)       # Coinbase One fee is a FORGE cost
OPUS_FREE_UNTIL = 1791348927.5 + 72 * 3600    # OP-018 credit window


@dataclass
class Stream:
    id: str
    venue: str                     # capital pool: "kalshi" | "coinbase"
    live: bool                     # executable live right now (adapter + credentials + gate)
    binary: bool
    clusters: list[tuple[float, float, float, float]] = field(default_factory=list)   # (ts, pnl, capital, hold_h)
    cap_units: float = 1e9
    note: str = ""

    def stats(self, now: float) -> dict[str, Any]:
        cl = [c for c in self.clusters if c[0] >= now - WINDOW_H * 3600]
        n = len(cl)
        if n == 0:
            return {"n": 0}
        pnl = [c[1] for c in cl]
        cap = sum(c[2] for c in cl) / n
        hold = max(sum(c[3] for c in cl) / n, 1 / 60)
        mu = sum(pnl) / n
        sd = math.sqrt(sum((x - mu) ** 2 for x in pnl) / max(n - 1, 1)) if n > 1 else abs(mu) + 0.25 * cap
        if self.binary:
            sd = max(sd, 0.20 * cap)
        sd = max(sd, 1e-6)
        se = sd / math.sqrt(n)
        hours = max(MIN_WINDOW_H, (now - min(c[0] for c in cl)) / 3600)
        lam = n / hours
        p_pos = 0.5 * (1 + math.erf(mu / se / math.sqrt(2)))
        mu_post = mu * n / (n + N0_SHRINK)
        tier = treg.tier_for(n, p_pos, mu / cap if cap > 0 else 0.0, binary=self.binary, lcb=mu - Z90 * se)
        return {"n": n, "lam": lam, "mu": mu, "mu_post": mu_post, "mu_lcb": mu - Z90 * se, "sd": sd, "cap": cap,
                "hold_h": hold, "p_pos": p_pos, "rel_edge": mu / cap if cap > 0 else 0.0, **tier}


def clusters_from_signals(rows: list[dict[str, Any]]) -> list[tuple[float, float, float, float]]:
    """Kalshi signals → independent clusters keyed by (underlying|ticker, close_ts, side)."""
    g: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for r in rows:
        g.setdefault((r.get("underlying") or r["ticker"], r.get("close_ts"), r["side"]), []).append(r)
    out = []
    for sigs in g.values():
        ts = min(float(s["ts"]) for s in sigs)
        pnl = sum(float(s["pnl"] or 0) for s in sigs)
        capital = sum(float(s["price"] or 0) + float(s["fee"] or 0) for s in sigs)
        end = max(float(s.get("settled_ts") or s.get("close_ts") or s["ts"]) for s in sigs)
        out.append((ts, pnl, capital, max(end - ts, 60.0) / 3600))
    return sorted(out)


def cluster_unit_pnls(rows: list[dict[str, Any]]) -> list[float]:
    """Per-contract P&L of each independent cluster (used by live evidence ladders)."""
    g: dict[tuple[Any, ...], list[float]] = {}
    order: list[tuple[Any, ...]] = []
    for r in rows:
        k = (r.get("underlying") or r["ticker"], r.get("close_ts"), r["side"])
        if k not in g:
            g[k] = []
            order.append(k)
        g[k].append(float(r["pnl"] or 0))
    return [sum(g[k]) / len(g[k]) for k in order]


# ---------------------------------------------------------------------------------------------------- frontier
def frontier(streams: list[tuple[Stream, dict[str, Any]]], W: float, reserve: float, *, edge: str = "mu_post",
             venue_capital: dict[str, float] | None = None, idle_apy: float = 0.0375, delta: float = DELTA,
             require_tier: bool = False, flow_mult: dict[str, float] | None = None) -> dict[str, Any]:
    D = max(0.0, W - reserve)
    L = math.log(1 / delta)
    flow_mult = flow_mult or {}
    act = []
    for s, st in streams:
        if st.get("n", 0) == 0 or (require_tier and not st.get("live_ok")):
            continue
        lam = st["lam"] * flow_mult.get(s.id, 1.0)
        mu = st[edge]
        if mu <= 0:
            continue
        m = lam * mu
        v = lam * (st["sd"] ** 2 + mu ** 2)
        caps = {"liquidity": s.cap_units, "concentration": st["share"] * D / max(st["cap"], 1e-9),
                "kelly": st["kelly"] * D * m / v}
        act.append({"s": s, "st": st, "m": m, "v": v, "lock": lam * st["cap"] * st["hold_h"], "ycap": min(caps.values()),
                    "cap_by": min(caps, key=caps.get)})
    pools = venue_capital if venue_capital is not None else {"*": D}

    def alloc(scale: float) -> list[float]:
        return [min(a["ycap"], scale * a["m"] / a["v"]) for a in act]

    def ok(y: list[float]) -> tuple[bool, str]:
        locks: dict[str, float] = {}
        for a, yi in zip(act, y, strict=True):
            k = a["s"].venue if venue_capital is not None else "*"
            locks[k] = locks.get(k, 0.0) + yi * a["lock"]
        for k, lk in locks.items():
            if lk > UTIL_MAX * pools.get(k, 0.0) + 1e-12:
                return False, "CAPITAL"
        mu_h = sum(yi * a["m"] for a, yi in zip(act, y, strict=True))
        var_h = sum(yi * yi * a["v"] for a, yi in zip(act, y, strict=True))
        if var_h > (2 * D / L) * mu_h + 1e-12:
            return False, "RISK"
        return True, ""

    binding = "EVIDENCE" if not act else "FLOW"
    y = [0.0] * len(act)
    if act:
        lo, hi = 0.0, 1e7
        if ok(alloc(hi))[0]:
            lo = hi
        else:
            for _ in range(80):
                mid = (lo + hi) / 2
                if ok(alloc(mid))[0]:
                    lo = mid
                else:
                    hi = mid
            binding = ok(alloc(hi))[1]
        y = alloc(lo)
    mu_h = sum(yi * a["m"] for a, yi in zip(act, y, strict=True))
    sd_h = math.sqrt(sum(yi * yi * a["v"] for a, yi in zip(act, y, strict=True)))
    locked = sum(yi * a["lock"] for a, yi in zip(act, y, strict=True))
    idle_h = max(0.0, W - locked) * idle_apy / 8760
    per = [{"stream": a["s"].id, "venue": a["s"].venue, "tier": a["st"]["tier"], "units": round(yi, 3),
            "usd_per_h": round(yi * a["m"], 4), "locked_usd": round(yi * a["lock"], 2),
            "capped_by": a["cap_by"] if yi >= a["ycap"] - 1e-9 else binding.lower()} for a, yi in zip(act, y, strict=True)]
    return {"usd_per_h": mu_h + idle_h, "trading_usd_per_h": mu_h, "idle_usd_per_h": idle_h, "sd_per_h": sd_h,
            "locked_usd": locked, "utilization": locked / W if W > 0 else 0.0, "binding": binding,
            "sharpe2_sum": sum(a["m"] ** 2 / a["v"] for a in act), "deployable": D, "streams": per,
            "recycle_h": (sum(yi * a["lock"] for a, yi in zip(act, y, strict=True)) /
                          max(sum(yi * a["lock"] / a["st"]["hold_h"] for a, yi in zip(act, y, strict=True)), 1e-12))
            if locked > 0 else None}


# ---------------------------------------------------------------------------------------------------- engine
class VelocityEngine:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        self.report: dict[str, Any] = {}
        self._last_note = 0.0

    # -------- inputs
    def treasury(self) -> dict[str, float]:
        db = self.f.db
        cb = float(db.scalar("SELECT account_total_usd FROM equity_series ORDER BY ts DESC LIMIT 1") or 0.0)
        kal = (db.kv_get("kalshi.live") or {}).get("balance_usd") or 0.0
        return {"coinbase": cb, "kalshi": float(kal), "total": cb + float(kal)}

    def streams(self, now: float) -> list[Stream]:
        db = self.f.db
        since = now - WINDOW_H * 3600
        out: list[Stream] = []
        kl = getattr(self.f, "kalshi_live", None)
        kal_live = bool(kl is not None and kl.configured)
        kinds = [r["kind"] for r in db.query("SELECT DISTINCT kind FROM crossrail_signals WHERE status='SETTLED' AND ts >= ?",
                                             (since,))]
        for k in kinds:
            rows = db.query("SELECT ts, ticker, underlying, close_ts, side, price, fee, pnl, settled_ts FROM crossrail_signals "
                            "WHERE kind = ? AND status = 'SETTLED' AND ts >= ? ORDER BY ts", (k, since))
            out.append(Stream(f"kalshi.{k}", "kalshi", live=kal_live and k == "TAKE_THRESH", binary=True,
                              clusters=clusters_from_signals(rows), cap_units=KALSHI_DEPTH_UNITS,
                              note="live adapter" if k == "TAKE_THRESH" else "shadow only"))
        for r in db.query("SELECT DISTINCT rail FROM shadow_trades WHERE ts >= ?", (since,)):
            rows = db.query("SELECT ts, pnl_usd, entry * qty AS notional, hold_s FROM shadow_trades WHERE rail = ? AND ts >= ?",
                            (r["rail"], since))
            cl = [(float(x["ts"]), float(x["pnl_usd"] or 0) / float(x["notional"]), 1.0, max(float(x["hold_s"] or 0), 60) / 3600)
                  for x in rows if x["notional"]]
            out.append(Stream(r["rail"], "coinbase", live=False, binary=False, clusters=cl, cap_units=250.0,
                              note="shadow rail (no live executor yet)"))
        rows = db.query("SELECT opened_at, closed_at, cost_usd, realized_pnl_usd, book FROM positions WHERE status = 'CLOSED' "
                        "AND cost_usd > 0")
        cl = []
        for x in rows:
            with contextlib.suppress(Exception):
                t0 = _ts(x["opened_at"])
                t1 = _ts(x["closed_at"])
                if t0 >= since:
                    cl.append((t0, float(x["realized_pnl_usd"] or 0) / float(x["cost_usd"]), 1.0, max(t1 - t0, 60) / 3600))
        live_spot = getattr(self.f, "book", "paper") == "live"
        out.append(Stream("coinbase.spot_strategies", "coinbase", live=live_spot, binary=False, clusters=sorted(cl),
                          cap_units=500.0, note="evolved spot strategies (paper book)"))
        return out

    def realized(self, now: float) -> dict[str, Any]:
        """TRUE NET realized live $/h over 1 h / 4 h / 24 h (live fills + settlements + verified idle rewards − costs)."""
        db = self.f.db
        out: dict[str, Any] = {}
        hist = db.query("SELECT ts, rewards_usdc FROM velocity_history WHERE ts >= ? ORDER BY ts", (now - 24 * 3600 - 900,))
        y = db.kv_get("yield.usdc") or {}
        rewards_now = float(y.get("rewards_usdc") or 0)
        for h in (1, 4, 24):
            t0 = now - h * 3600
            kal = float(db.scalar("SELECT COALESCE(SUM(pnl),0) FROM kalshi_live_orders WHERE status='SETTLED' AND settled_ts >= ?",
                                  (t0,)) or 0)
            spot = float(db.scalar("SELECT COALESCE(SUM(realized_pnl_usd),0) FROM positions WHERE book = 'live' AND "
                                   "status = 'CLOSED' AND closed_at >= ?", (_iso(t0),)) or 0)
            base = next((float(r["rewards_usdc"] or 0) for r in hist if r["ts"] >= t0), rewards_now)
            idle = rewards_now - base
            free_opus = "AND model NOT LIKE '%opus%'" if now < OPUS_FREE_UNTIL else ""
            intel = float(db.scalar(f"SELECT COALESCE(SUM(cost_usd),0) FROM inference_calls WHERE ts >= ? {free_opus}",  # noqa: S608
                                    (_iso(t0),)) or 0)
            net = kal + spot + idle - intel - MEMBERSHIP_USD_PER_H * h
            out[f"{h}h"] = {"usd_per_h": net / h, "net_usd": net, "kalshi": kal, "spot": spot, "idle_yield": idle,
                            "intelligence": -intel, "membership": -MEMBERSHIP_USD_PER_H * h}
        return out

    # -------- compute
    def compute(self) -> dict[str, Any]:
        now = time.time()
        tr = self.treasury()
        reg = treg.current(self.f.db, tr["total"])
        W, F = tr["total"], reg["reserve"]
        streams = self.streams(now)
        with_stats = [(s, s.stats(now)) for s in streams]
        apy = float((self.f.db.kv_get("yield.usdc") or {}).get("realized_apy") or 0.0375)
        frac = {k: (tr[k] / W if W > 0 else 0.0) for k in ("kalshi", "coinbase")}
        venue_now = {k: max(0.0, tr[k] - F * frac[k]) for k in ("kalshi", "coinbase")}
        live = [(s, st) for s, st in with_stats if s.live]
        f_live = frontier(live, W, F, venue_capital=venue_now, idle_apy=apy, require_tier=True)
        f_proven = frontier(with_stats, W, F, edge="mu_lcb", idle_apy=apy, require_tier=True)
        f_potential = frontier(with_stats, W, F, edge="mu_post", idle_apy=apy)
        curve = []
        for w in sorted({round(W, 2), 50.0, 100.0, 250.0, 500.0, 1000.0}):
            if w < W - 1e-9:
                continue
            r = treg.regime_for(w, max(reg["hwm"], w))
            curve.append({"treasury": w, "regime": r["regime"], "reserve": r["reserve"],
                          "proven_usd_per_h": round(frontier(with_stats, w, r["reserve"], edge="mu_lcb", idle_apy=apy,
                                                             require_tier=True)["usd_per_h"], 4),
                          "potential_usd_per_h": round(frontier(with_stats, w, r["reserve"], idle_apy=apy)["usd_per_h"], 4)})
        # marginal values → research / action priorities (anti-stagnation)
        pri = []
        base_pot = f_potential["usd_per_h"]
        pri.append({"action": "add capital (+$10)", "delta_usd_per_h":
                    frontier(with_stats, W + 10, F, idle_apy=apy)["usd_per_h"] - base_pot})
        for s, st in with_stats:
            if st.get("n", 0) == 0:
                continue
            without = frontier([(x, y) for x, y in with_stats if x is not s], W, F, idle_apy=apy)["usd_per_h"]
            pri.append({"action": f"prove + go live: {s.id}", "stream": s.id, "tier": st["tier"],
                        "delta_usd_per_h": base_pot - without})
            pri.append({"action": f"double independent flow (more markets/series): {s.id}", "stream": s.id,
                        "delta_usd_per_h": frontier(with_stats, W, F, idle_apy=apy, flow_mult={s.id: 2.0})["usd_per_h"]
                        - base_pot})
        pri.sort(key=lambda p: -p["delta_usd_per_h"])
        realized = self.realized(now)
        tgt_state = self.f.db.kv_get("velocity.target") or {"value": OPERATOR_MIN_TARGET, "set_ts": now}
        r24 = realized["24h"]["usd_per_h"]
        if r24 >= tgt_state["value"] and now - tgt_state["set_ts"] >= 24 * 3600:
            tgt_state = {"value": round(tgt_state["value"] * 1.25, 4), "set_ts": now, "why": "24h realized ≥ target → ratchet"}
        target = max(OPERATOR_MIN_TARGET, tgt_state["value"], f_proven["usd_per_h"])
        self.f.db.kv_set("velocity.target", {**tgt_state, "effective": target})
        needed_s2 = (target * math.log(1 / DELTA) / (2 * reg["deployable"])) if reg["deployable"] > 0 else None
        diag = []
        if f_live["trading_usd_per_h"] <= 0:
            diag.append("NO LIVE TRADING STREAM YET: only idle yield earns live; proven streams need an executor/credentials/"
                        "gate (see priorities)")
        if f_proven["usd_per_h"] < target:
            diag.append(f"PROVEN FRONTIER ${f_proven['usd_per_h']:.3f}/h < target ${target:.2f}/h — binding: "
                        f"{f_proven['binding']}")
        diag.append(f"to reach ${target:.2f}/h at deployable ${reg['deployable']:.2f}, the combined independent hourly "
                    f"Sharpe² Σ(m²/v) must be ≥ {needed_s2:.3f} (now: proven {f_proven['sharpe2_sum']:.4f}, potential "
                    f"{f_potential['sharpe2_sum']:.4f})" if needed_s2 else "no deployable capital")
        rep = {
            "ts": now, "treasury": tr, "regime": reg, "target_usd_per_h": target, "operator_min_usd_per_h": OPERATOR_MIN_TARGET,
            "realized": realized,
            "profit_velocity": {  # expected true net profit per capital-hour
                "live": f_live["usd_per_h"] / W if W else 0, "proven": f_proven["usd_per_h"] / W if W else 0,
                "potential": f_potential["usd_per_h"] / W if W else 0},
            "expected_usd_per_h": {"live_now": f_live["usd_per_h"], "proven": f_proven["usd_per_h"],
                                   "potential": f_potential["usd_per_h"]},
            "frontier": {"live_now": f_live, "proven": f_proven, "potential": f_potential},
            "capital_utilization": f_live["utilization"], "recycle_h": f_potential["recycle_h"],
            "profit_per_deployed_usd_h": (f_potential["trading_usd_per_h"] / f_potential["locked_usd"])
            if f_potential["locked_usd"] > 0 else None,
            "opportunity_cost_usd_per_h": f_potential["locked_usd"] * apy / 8760,
            "scaling_curve": curve,
            "scaling_headroom": (curve[-1]["potential_usd_per_h"] / max(f_potential["usd_per_h"], 1e-9)) if curve else None,
            "streams": [{"id": s.id, "venue": s.venue, "live": s.live, "note": s.note,
                         **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in st.items()}} for s, st in with_stats],
            "priorities": pri[:12], "diagnosis": diag,
        }
        self.report = rep
        return rep

    async def run(self) -> None:
        while not self.f.stop_event.is_set():
            self.f.sup.beat("velocity")
            try:
                rep = await asyncio.to_thread(self.compute)
                self.f.db.kv_set("velocity", rep)
                last = self.f.db.scalar("SELECT MAX(ts) FROM velocity_history") or 0
                if time.time() - float(last) >= 900:
                    import json
                    self.f.db.insert("velocity_history", {
                        "ts": rep["ts"], "treasury": rep["treasury"]["total"], "realized_1h": rep["realized"]["1h"]["usd_per_h"],
                        "realized_24h": rep["realized"]["24h"]["usd_per_h"], "live_usd_per_h": rep["expected_usd_per_h"]["live_now"],
                        "proven_usd_per_h": rep["expected_usd_per_h"]["proven"],
                        "potential_usd_per_h": rep["expected_usd_per_h"]["potential"], "target": rep["target_usd_per_h"],
                        "rewards_usdc": float((self.f.db.kv_get("yield.usdc") or {}).get("rewards_usdc") or 0),
                        "payload": json.dumps({k: rep[k] for k in ("regime", "diagnosis", "priorities")}, default=str)})
                if time.time() - self._last_note >= 3600:
                    self._last_note = time.time()
                    e = rep["expected_usd_per_h"]
                    await self.f.say("Profit Velocity",
                                     f"realized 1h ${rep['realized']['1h']['usd_per_h']:+.3f}/h · 24h "
                                     f"${rep['realized']['24h']['usd_per_h']:+.3f}/h | expected live ${e['live_now']:.3f}/h · "
                                     f"proven ${e['proven']:.3f}/h · potential ${e['potential']:.3f}/h | target "
                                     f"${rep['target_usd_per_h']:.2f}/h | {rep['regime']['regime']} | top lever: "
                                     f"{rep['priorities'][0]['action'] if rep['priorities'] else '—'}")
            except Exception as e:
                log.warning("velocity: %s", e, exc_info=True)
            await asyncio.sleep(300)


def _ts(x: Any) -> float:
    if isinstance(x, (int, float)):
        return float(x)
    from datetime import datetime
    return datetime.fromisoformat(str(x)).timestamp()


def _iso(t: float) -> str:
    from datetime import UTC, datetime
    return datetime.fromtimestamp(t, UTC).isoformat()
