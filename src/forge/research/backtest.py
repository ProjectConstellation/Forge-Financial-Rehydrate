"""Realistic event-driven backtester (DOSSIER §15.1, DIRECTIVE §18).

Shared by research, walk-forward, Modal workers and shadow replay. Conservative by design:
- signals use bar-close information only; execution happens on later bars (no lookahead);
- maker entries fill only if price trades *through* the limit (queue penetration), else missed;
- taker fills pay half-spread + slippage; stops are taker and gap-aware;
- if stop and target are both touched within one bar, the stop is assumed first;
- fees on both legs from the live fee schedule (cost ruler is recorded with every result).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np

from forge.research.stats import edge_posterior, max_drawdown, sharpe
from forge.strategies.genome import (
    Genome,
    barrier_pcts,
    chandelier_k,
    compile_entries,
    compile_exit_signal,
    convex_atr,
)


@dataclass(frozen=True)
class CostModel:
    maker_fee: float = 0.005
    taker_fee: float = 0.009
    half_spread_bps: float = 2.0
    slippage_bps: float = 3.0
    queue_penetration_bps: float = 1.0      # maker fill requires trading this far through the limit
    haircut: float = 0.0                    # learned backtest→live degradation per trade (fraction)

    def ruler(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class Trade:
    symbol: str
    entry_idx: int
    exit_idx: int
    entry_ts: float
    exit_ts: float
    entry: float
    exit: float
    gross: float
    net: float
    fees: float
    reason: str
    entry_liq: str
    exit_liq: str
    regime: str = ""
    mae: float = 0.0
    mfe: float = 0.0
    tp_pct: float = 0.0
    sl_pct: float = 0.0


@dataclass
class SimResult:
    trades: list[Trade] = field(default_factory=list)
    signals: int = 0
    missed_fills: int = 0
    bars: int = 0
    days: float = 0.0


def simulate(g: Genome, symbol: str, bars: dict[str, np.ndarray], f: dict[str, np.ndarray],
             probs: dict[str, np.ndarray] | None, cost: CostModel, start: int = 0, end: int | None = None,
             labels: np.ndarray | None = None) -> SimResult:
    o, h, lo, c, ts = (np.asarray(bars[k], dtype=float) for k in ("open", "high", "low", "close", "ts"))
    n = len(c)
    end = n if end is None else min(end, n)
    entries = compile_entries(g, f, probs)
    exit_sig = compile_exit_signal(g, f)
    atr = f["atr_14"]
    res = SimResult(bars=max(0, end - start), days=max(0, end - start) * g.interval_s / 86400)
    slip = (cost.half_spread_bps + cost.slippage_bps) / 1e4
    pen = cost.queue_penetration_bps / 1e4
    free_at = start
    idxs = np.flatnonzero(entries[start:end]) + start
    res.signals = len(idxs)
    for i in idxs:
        if i < free_at or i + 1 >= end:
            continue
        a = float(atr[i])                      # atr_14 is already a fraction of price
        if not math.isfinite(a) or a <= 0:
            continue
        tp, sl = barrier_pcts(g, a)
        # ---- entry ----
        if g.execution.entry == "maker":
            limit = c[i] * (1 - g.execution.maker_offset_bps / 1e4)
            j_end = min(i + 1 + g.execution.maker_ttl_bars, end)
            hit = np.flatnonzero(lo[i + 1:j_end] <= limit * (1 - pen))
            if len(hit) == 0:
                res.missed_fills += 1
                free_at = i + 1
                continue
            e_idx = i + 1 + int(hit[0])
            entry = min(limit, o[e_idx]) if o[e_idx] < limit else limit
            fee_in, liq_in = cost.maker_fee, "maker"
        else:
            e_idx = i + 1
            entry = o[e_idx] * (1 + slip)
            fee_in, liq_in = cost.taker_fee, "taker"
        if g.exit.convex:                                      # barrier_pcts already gave (no TP, catastrophe stop)
            ca = convex_atr(g, a)                              # convex distances in hour-equivalent ATR
            ck = chandelier_k(g, float(f["vol_pct"][i]) if "vol_pct" in f else None)
        tp_px, stop = entry * (1 + tp), entry * (1 - sl)
        trail = g.exit.trail_atr * a if g.exit.trail_atr else None
        last = min(e_idx + g.exit.time_stop_bars, end - 1)
        exit_px, reason, x_idx, fee_out, liq_out = None, "TIME", last, cost.taker_fee, "taker"
        hi_since, mae, mfe = entry, 0.0, 0.0
        for k in range(e_idx, last + 1):
            mae = min(mae, lo[k] / entry - 1)
            mfe = max(mfe, h[k] / entry - 1)
            if lo[k] <= stop:                                   # stop first (conservative)
                exit_px = min(stop, o[k]) * (1 - slip) if k > e_idx else stop * (1 - slip)
                reason = ("LOCK" if stop > entry else "TRAIL") if stop > entry * (1 - sl) + 1e-12 else "SL"
                x_idx = k
                break
            if k > e_idx and h[k] >= tp_px * (1 + pen):
                if g.exit.tp_atr and g.execution.exit_tp == "maker":
                    exit_px, fee_out, liq_out = max(tp_px, o[k]), cost.maker_fee, "maker"
                else:
                    exit_px = max(tp_px, o[k]) * (1 - slip)
                reason, x_idx = "TP", k
                break
            if g.exit.convex and g.exit.progress_bars and k - e_idx == g.exit.progress_bars and c[k] / entry - 1 < g.exit.progress_atr * ca:
                exit_px, reason, x_idx = c[k] * (1 - slip), "NO_PROGRESS", k
                break
            if exit_sig is not None and k > e_idx and exit_sig[k]:
                exit_px, reason, x_idx = c[k] * (1 - slip), "SIGNAL", k
                break
            hi_since = max(hi_since, h[k])
            if g.exit.convex and hi_since / entry - 1 >= g.exit.arm_atr * ca:
                stop = max(stop, hi_since * (1 - ck * ca))
            if trail is not None:
                stop = max(stop, hi_since * (1 - trail))
            fav = hi_since / entry - 1
            if g.exit.be_trigger_pct is not None and g.exit.be_trigger_pct < 0.5 and fav >= g.exit.be_trigger_pct:
                stop = max(stop, entry * (1 + g.exit.be_buffer_pct))
                if g.exit.lock_frac is not None:
                    stop = max(stop, entry * (1 + g.exit.lock_frac * fav))
        if exit_px is None:
            exit_px = c[last] * (1 - slip)
        gross = exit_px / entry - 1
        net = exit_px * (1 - fee_out) / (entry * (1 + fee_in)) - 1 - cost.haircut
        res.trades.append(Trade(
            symbol=symbol, entry_idx=int(e_idx), exit_idx=int(x_idx), entry_ts=float(ts[e_idx]),
            exit_ts=float(ts[x_idx]), entry=float(entry), exit=float(exit_px), gross=float(gross), net=float(net),
            fees=float(fee_in + fee_out), reason=reason, entry_liq=liq_in, exit_liq=liq_out,
            regime=str(labels[i]) if labels is not None else "", mae=float(mae), mfe=float(mfe),
            tp_pct=float(tp), sl_pct=float(sl)))
        free_at = x_idx + 1 + g.cooldown_bars
    return res


def metrics(trades: list[Trade], days: float, n_trials: int = 1) -> dict[str, float | int | dict]:
    r = np.array([t.net for t in trades], dtype=float)
    n = len(r)
    if n == 0:
        return {"n": 0, "trades_per_day": 0.0, "mean_net": 0.0, "win_rate": 0.0, "p_positive": 0.0,
                "sum_net": 0.0, "log_growth": 0.0, "max_dd": 0.0, "profit_factor": 0.0, "sharpe": 0.0,
                "lb90": -1.0, "avg_hold_h": 0.0, "by_regime": {}, "by_reason": {}}
    post = edge_posterior(r)
    wins, losses = r[r > 0], r[r <= 0]
    eq = np.cumprod(1 + r)
    by_regime: dict[str, dict[str, float]] = {}
    for reg in {t.regime for t in trades}:
        rr = np.array([t.net for t in trades if t.regime == reg])
        by_regime[reg or "NA"] = {"n": len(rr), "mean": float(rr.mean()), "win": float((rr > 0).mean())}
    by_reason: dict[str, int] = {}
    for t in trades:
        by_reason[t.reason] = by_reason.get(t.reason, 0) + 1
    return {
        "n": n,
        "trades_per_day": n / max(days, 1e-9),
        "mean_net": float(r.mean()),
        "median_net": float(np.median(r)),
        "win_rate": float((r > 0).mean()),
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "sum_net": float(r.sum()),
        "log_growth": float(np.log1p(np.maximum(r, -0.99)).sum()),
        "max_dd": max_drawdown(np.concatenate([[1.0], eq])),
        "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else float("inf"),
        "sharpe": sharpe(r),
        "p_positive": post["p_positive"],
        "lb90": post["lb90"],
        "post_mean": post["post_mean"],
        "std": post["std"],
        "avg_hold_h": float(np.mean([(t.exit_ts - t.entry_ts) / 3600 for t in trades])),
        # Capital velocity (OP-008): return per capital-day actually deployed
        "capital_days": float(sum(max(t.exit_ts - t.entry_ts, 300.0) for t in trades) / 86400),
        "ret_per_capital_day": float(r.sum() / max(sum(max(t.exit_ts - t.entry_ts, 300.0) for t in trades) / 86400, 1e-9)),
        "log_per_capital_day": float(np.log1p(np.maximum(r, -0.99)).sum()
                                     / max(sum(max(t.exit_ts - t.entry_ts, 300.0) for t in trades) / 86400, 1e-9)),
        "fee_drag": float(np.mean([t.fees for t in trades])),
        "by_regime": by_regime,
        "by_reason": by_reason,
    }
