"""Time Machine — full-portfolio replay of FORGE through history, minutes instead of months.

Simulates the whole earning loop, not single strategies: all candidate genomes on all markets simultaneously, one shared
treasury with compounding (realized profits immediately fund the next trades), evidence-weighted fractional-Kelly sizing,
one position per market, reserve, real fee tier, $1 venue minimum, maker/taker entry, stops, profit locks/trailing,
time stops. Reports equity curve, daily distribution, drawdown, per-strategy/per-market contribution.
Use `segment="holdout"` to judge only on data the strategies never saw during selection.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from forge.research.backtest import CostModel
from forge.research.evaluate import Dataset
from forge.strategies.genome import Genome, barrier_pcts, chandelier_k, compile_entries, convex_atr
from forge.treasury.sizing import kelly_fraction


@dataclass
class Pos:
    gid: str
    sym: str
    entry_i: int
    entry: float
    qty: float
    cost: float
    tp: float
    stop: float
    sl: float
    hi: float
    fee_in: float
    last_i: int
    g: Genome
    atr: float = 0.0
    ck: float = 3.5


@dataclass
class TMResult:
    equity: list[tuple[float, float]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    start_capital: float = 0.0
    days: float = 0.0

    def summary(self) -> dict[str, Any]:
        if not self.equity:
            return {}
        eq = np.array([e for _, e in self.equity])
        ts = np.array([t for t, _ in self.equity])
        day = (ts // 86400).astype(int)
        closes = {d: eq[np.flatnonzero(day == d)[-1]] for d in np.unique(day)}
        dv = np.array(list(closes.values()))
        daily = np.diff(np.concatenate([[self.start_capital], dv])) if len(dv) else np.array([])
        peak = np.maximum.accumulate(eq)
        net = [t["net_usd"] for t in self.trades]
        by_s: dict[str, float] = {}
        by_m: dict[str, float] = {}
        for t in self.trades:
            by_s[t["gid"]] = by_s.get(t["gid"], 0.0) + t["net_usd"]
            by_m[t["sym"]] = by_m.get(t["sym"], 0.0) + t["net_usd"]
        final = float(eq[-1])
        return {
            "start_usd": self.start_capital, "final_usd": final, "net_usd": final - self.start_capital,
            "return": final / self.start_capital - 1, "days": self.days,
            "daily_compound_rate": (final / self.start_capital) ** (1 / max(self.days, 1e-9)) - 1 if final > 0 else -1.0,
            "max_drawdown": float(((eq - peak) / peak).min()), "trades": len(net),
            "win_rate": float(np.mean([x > 0 for x in net])) if net else None,
            "profit_factor": (sum(x for x in net if x > 0) / -sum(x for x in net if x < 0)) if any(x < 0 for x in net) else None,
            "positive_days": float(np.mean(daily > 0)) if len(daily) else None, "days_traded": len(daily),
            "best_day_usd": float(daily.max()) if len(daily) else 0.0, "worst_day_usd": float(daily.min()) if len(daily) else 0.0,
            "avg_hold_h": float(np.mean([t["hold_h"] for t in self.trades])) if self.trades else 0.0,
            "top_strategies": sorted(by_s.items(), key=lambda kv: -kv[1])[:5],
            "top_markets": sorted(by_m.items(), key=lambda kv: -kv[1])[:5],
            "worst_markets": sorted(by_m.items(), key=lambda kv: kv[1])[:3],
        }


def run_portfolio(genomes: list[Genome], ds: Dataset, cost: CostModel, capital: float = 28.27, segment: str = "holdout",
                  reserve_frac: float = 0.10, max_positions: int = 12, kelly_mult: float = 0.35, max_frac: float = 0.5,
                  evidence: dict[str, dict[str, float]] | None = None, sizing: str = "kelly",
                  risk_per_pos: float = 0.05, risk_total: float = 0.10) -> TMResult:
    evidence = evidence or {}
    syms = list(ds.symbols)
    # global clock = union of bar timestamps within the segment
    seg = {s: ds.split(ds.symbols[s], segment) for s in syms}
    all_ts = np.unique(np.concatenate([ds.symbols[s].bars["ts"][a:b] for s, (a, b) in seg.items()]))
    idx = {s: {float(t): i for i, t in enumerate(ds.symbols[s].bars["ts"])} for s in syms}
    sig = {(g.id, s): compile_entries(g, ds.symbols[s].f, ds.symbols[s].probs) for g in genomes for s in syms}
    res = TMResult(start_capital=capital, days=(all_ts[-1] - all_ts[0]) / 86400 if len(all_ts) > 1 else 0.0)
    cash = capital
    open_: dict[str, Pos] = {}
    pend: list[tuple[str, Genome, int]] = []                     # signals from the previous bar close → act this bar
    slip = (cost.half_spread_bps + cost.slippage_bps) / 1e4
    for t in all_ts:
        t = float(t)
        # ---------- exits (bar t) ----------
        for sym in list(open_):
            p = open_[sym]
            i = idx[sym].get(t)
            if i is None or i <= p.entry_i:
                continue
            b = ds.symbols[sym].bars
            o, h, lo, c = b["open"][i], b["high"][i], b["low"][i], b["close"][i]
            px, reason, fee_out = None, "", cost.taker_fee
            if lo <= p.stop:
                px, reason = min(p.stop, o) * (1 - slip), ("LOCK" if p.stop > p.entry else "SL")
            elif p.g.exit.convex and p.g.exit.progress_bars and i - p.entry_i == p.g.exit.progress_bars and c / p.entry - 1 < p.g.exit.progress_atr * p.atr:
                px, reason = c * (1 - slip), "NO_PROGRESS"
            elif h >= p.tp * 1.0001:
                px, reason, fee_out = max(p.tp, o), "TP", cost.maker_fee
            elif i - p.entry_i >= p.g.exit.time_stop_bars:
                px, reason = c * (1 - slip), "TIME"
            if px is not None:
                proceeds = p.qty * px * (1 - fee_out)
                cash += proceeds
                res.trades.append({"gid": p.g.id, "sym": sym, "net_usd": proceeds - p.cost, "ret": proceeds / p.cost - 1,
                                   "reason": reason, "hold_h": (t - b["ts"][p.entry_i]) / 3600})
                del open_[sym]
                continue
            p.hi = max(p.hi, h)
            fav = p.hi / p.entry - 1
            a = float(ds.symbols[sym].f["atr_14"][i]) if math.isfinite(ds.symbols[sym].f["atr_14"][i]) else 0.01
            if p.g.exit.convex and fav >= p.g.exit.arm_atr * p.atr:
                p.stop = max(p.stop, p.hi * (1 - p.ck * p.atr))
            if p.g.exit.trail_atr:
                p.stop = max(p.stop, p.hi * (1 - p.g.exit.trail_atr * a))
            if p.g.exit.be_trigger_pct < 0.5 and fav >= max(p.g.exit.be_trigger_pct, 1.5 * a):
                p.stop = max(p.stop, p.entry * (1 + p.g.exit.be_buffer_pct), p.entry * (1 + p.g.exit.lock_frac * fav))
        # ---------- entries for signals raised at the previous close ----------
        equity = cash + sum(q.qty * ds.symbols[s].bars["close"][idx[s].get(t, q.last_i)] for s, q in open_.items())
        for sym, g, i_sig in sorted(pend, key=lambda x: -evidence.get(x[1].id, {}).get("score", 0.0)):
            if sym in open_ or len(open_) >= max_positions:
                continue
            i = idx[sym].get(t)
            if i is None or i != i_sig + 1:
                continue
            b, f = ds.symbols[sym].bars, ds.symbols[sym].f
            a = float(f["atr_14"][i_sig])
            if not math.isfinite(a) or a <= 0:
                continue
            tp, sl = barrier_pcts(g, a)
            ck = 3.5
            if g.exit.convex:                                       # barrier_pcts gave (no TP, catastrophe stop)
                a = convex_atr(g, a)
                ck = chandelier_k(g, float(f["vol_pct"][i_sig]))
            ev = evidence.get(g.id, {})
            p_win = ev.get("p_win", 0.45)
            w, l = ev.get("avg_win", min(tp, 3 * sl) - 0.01), ev.get("avg_loss", -(sl + 0.014))
            k = kelly_fraction(p_win, w, l) * kelly_mult * min(1.0, max(0.2, (ev.get("p_edge", 0.6) - 0.5) / 0.4))
            deployable = max(0.0, cash - equity * reserve_frac)
            if sizing == "risk":                                   # risk-at-stop (answers §9)
                open_risk = sum(q.cost * q.sl for q in open_.values())
                budget = max(0.0, risk_total * equity - open_risk)
                rf = min(risk_per_pos, 0.25 * kelly_fraction(p_win, w, l) if kelly_fraction(p_win, w, l) > 0 else risk_per_pos * 0.3)
                notional = min(equity * rf, budget) / max(sl, 1e-4)
                notional = min(notional, deployable * max_frac)
            else:
                notional = min(k, max_frac) * deployable
            if notional < 1.0:
                continue
            if g.execution.entry == "maker":
                limit = b["close"][i_sig] * (1 - g.execution.maker_offset_bps / 1e4)
                if b["low"][i] > limit * (1 - cost.queue_penetration_bps / 1e4):
                    continue                                         # not filled this bar (conservative: no retries)
                px, fee_in = min(limit, b["open"][i]), cost.maker_fee
            else:
                px, fee_in = b["open"][i] * (1 + slip), cost.taker_fee
            qty = notional * (1 - fee_in) / px
            cash -= notional
            open_[sym] = Pos(g.id, sym, i, px, qty, notional, px * (1 + tp), px * (1 - sl), sl, px, fee_in, i, g, a, ck)
        pend = []
        # ---------- new signals at this bar's close ----------
        for g in genomes:
            for sym in syms:
                i = idx[sym].get(t)
                if i is not None and sig[(g.id, sym)][i] and seg[sym][0] <= i < seg[sym][1] - 1:
                    pend.append((sym, g, i))
        for s, q in open_.items():
            q.last_i = idx[s].get(t, q.last_i)
        equity = cash + sum(q.qty * ds.symbols[s].bars["close"][q.last_i] for s, q in open_.items())
        res.equity.append((t, equity))
    return res


def tm_job(market_dir: str, genomes: list[dict[str, Any]], evidence: dict[str, dict[str, float]], capital: float,
           fees: dict[str, float], interval: int = 300) -> dict[str, Any]:
    """Subprocess entry point: full-portfolio replay on unseen (holdout) and earlier (selection) history."""
    import os
    import time
    from pathlib import Path

    from forge.market_data.history import CandleStore
    try:
        os.nice(10)
    except OSError:
        pass
    t0 = time.time()
    from forge.strategies.registry import repair_genome
    gs = [x for x in (repair_genome(dict(g))[0] for g in genomes if g.get("interval_s", 300) == interval) if x is not None]
    if not gs:
        return {"ok": False, "note": "no validated strategies on this interval"}
    store = CandleStore(Path(market_dir))
    raw = {s: store.load(s, interval) for s in store.symbols(interval)}
    # memory: same research window as evolution (5m × 365 d × 62 markets ≈ 1+ GB per replay worker)
    from forge.evolution.worker import RESEARCH_DAYS
    days = RESEARCH_DAYS.get(interval, 365)
    for s_, b_ in list(raw.items()):
        if b_ is not None and len(b_["ts"]):
            k0 = int(np.searchsorted(b_["ts"], b_["ts"][-1] - days * 86400))
            raw[s_] = {k: v[k0:] for k, v in b_.items()}
    ds = Dataset.build({s: b for s, b in raw.items() if b is not None}, interval)
    cost = CostModel(maker_fee=fees.get("maker", 0.005), taker_fee=fees.get("taker", 0.009))
    out = {"ok": True, "strategies": len(gs), "markets": len(ds.symbols), "capital": capital}
    for seg in ("holdout", "selection"):
        r = run_portfolio(gs, ds, cost, capital=capital, segment=seg, evidence=evidence).summary()
        out[seg] = {k: (v if not isinstance(v, list) else [(a, float(b)) for a, b in v]) for k, v in r.items()}
    # elite allocation: rank each strategy stand-alone on the SELECTION period (no peeking), keep those also positive unseen
    ranking = []
    for g in gs:
        a = run_portfolio([g], ds, cost, capital=capital, segment="selection", evidence=evidence).summary()
        b = run_portfolio([g], ds, cost, capital=capital, segment="holdout", evidence=evidence).summary()
        ranking.append({"id": g.id, "family": g.family, "selection_return": a.get("return", -1), "holdout_return": b.get("return", -1),
                        "trades": a.get("trades", 0)})
    ranking.sort(key=lambda r: -r["selection_return"])
    # selection-only choice (validation must not act as a selector — that contaminates it); unseen is reported, not used
    elite = [r["id"] for r in ranking if r["selection_return"] > 0][:3]
    out["ranking"], out["elite"] = ranking, elite
    eg = [g for g in gs if g.id in elite]
    if eg:
        out["elite_holdout"] = run_portfolio(eg, ds, cost, capital=capital, segment="holdout", evidence=evidence, kelly_mult=1.0).summary()
        out["elite_selection"] = run_portfolio(eg, ds, cost, capital=capital, segment="selection", evidence=evidence, kelly_mult=1.0).summary()
    out["seconds"] = time.time() - t0
    out["ts"] = time.time()
    return out
