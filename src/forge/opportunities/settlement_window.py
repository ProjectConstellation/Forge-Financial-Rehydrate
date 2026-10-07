"""SAGE-1 — Settlement-window engine for Kalshi crypto markets that settle on a 60-second CF Benchmarks average.

Rule (e.g. KXBTC15M / KXBTCD): YES iff the simple average of the 60 one-second BRTI prints before close is ≥ / ≤ / within
the strike. In the final minutes part of that average is already *realized*; only the remaining seconds are random:
    A = (Σ realized + Σ future) / 60,   future S_{t+d} = S_t · exp(W_d)  (Brownian, per-second vol σ)
    E[A] = (Σ realized + n_f · S_t)/60,   Var[A] ≈ (S_t σ / 60)² · Σ_i Σ_j min(d_i, d_j)
plus the BRTI-vs-Coinbase basis b (estimated per underlying from each 15-minute market's opening strike, which IS the
BRTI 60-s average, vs FORGE's own 1-s Coinbase samples over the same window). When the market quote lags this
narrowing distribution, the conservative probability (σ ×1.25, basis shifted 1 sd against us) can beat ask + fee.

Shadow first: signals are recorded as kind SETTLE_WINDOW in crossrail_signals only if the quote is STILL there after a
simulated order latency; outcomes come from Kalshi's real settlement. Every hot market is also sampled into
sw_calibration (model vs market Brier in the final minutes) — the direct test of whether this edge exists.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import time
from collections import deque
from typing import Any

from forge.opportunities.kalshi import kalshi_fee, parse_market

log = logging.getLogger("forge.settlement_window")

WINDOW_S = 60
HOT_S = 300               # start fast polling 5 min before close
DISCOVER_S = 30
LATENCY_S = 0.35          # simulated order round trip: the quote must survive this to count as fillable
MIN_EDGE = 0.02           # $/contract after fee, on the conservative probability
VOL_INFLATE = 1.25
BASIS_SD_FLOOR = 1.5e-4   # 1.5 bp


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def window_distribution(now: float, close_ts: float, spot: float, sigma_1s: float,
                        realized: list[tuple[float, float]]) -> tuple[float, float, int]:
    """Mean and sd of the 60-s settlement average (in proxy price units) and the number of realized seconds used."""
    secs = [close_ts - WINDOW_S + i for i in range(WINDOW_S)]           # sample instants close−60 … close−1
    rmap: dict[int, float] = {}
    for ts, px in realized:
        k = int(ts)
        if close_ts - WINDOW_S <= k < close_ts:
            rmap[k] = px
    total, future = 0.0, []
    n_real = 0
    for t in secs:
        if t <= now and int(t) in rmap:
            total += rmap[int(t)]
            n_real += 1
        elif t <= now:                       # missed sample in the past: use the latest known price, no variance
            total += spot
        else:
            future.append(t - now)
    mean = (total + len(future) * spot) / WINDOW_S
    if not future:
        return mean, 0.0, n_real
    d = sorted(future)
    n = len(d)
    # Σ_i Σ_j min(d_i, d_j) for sorted d = Σ_k d_k · (2(n−k) − 1)  (k zero-based)
    s = sum(dk * (2 * (n - k) - 1) for k, dk in enumerate(d))
    sd = spot * sigma_1s * math.sqrt(s) / WINDOW_S
    return mean, sd, n_real


def p_outcome(mean: float, sd: float, strike_type: str, floor: float | None, cap: float | None) -> float:
    def above(k: float) -> float:
        if sd <= 0:
            return 1.0 if mean >= k else 0.0
        return 1.0 - norm_cdf((k - mean) / sd)
    st = strike_type or ""
    if st.startswith("greater") and floor is not None:
        return above(floor)
    if st.startswith("less") and cap is not None:
        return 1.0 - above(cap)
    if st == "between" and floor is not None and cap is not None:
        return max(0.0, above(floor) - above(cap))
    return float("nan")


class SettlementWindowEngine:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        self.samples: dict[str, deque[tuple[float, float]]] = {}
        self.basis: dict[str, tuple[float, float, int]] = {}      # pid → (mean log basis, var, n)
        self.markets: dict[str, dict[str, Any]] = {}               # ticker → {series, pid, close_ts, strike...}
        self.stats = {"hot_sweeps": 0, "signals": 0, "missed_after_latency": 0, "calib": 0, "basis_obs": 0}
        self._last_cal: dict[str, float] = {}

    # ---------------------------------------------------------------- inputs
    def _series(self) -> dict[str, str]:
        cr = getattr(self.f, "crossrail", None)
        mp = dict(getattr(cr, "mapping", {}) or {})
        meta = getattr(cr, "series_meta", {}) or {}
        out = {}
        for s, pid in mp.items():
            m = meta.get(s, {})
            src = " ".join(str(x.get("name", "")) for x in (m.get("settlement_sources") or []))
            if "CF Benchmarks" in src and pid != "PAXG-USD" and m.get("frequency") in ("fifteen_min", "hourly", "daily"):
                out[s] = pid
        return out

    def _sigma(self, pid: str) -> float | None:
        q = self.samples.get(pid)
        if not q or len(q) < 120:
            return None
        pts = list(q)[-900:]
        rets = [math.log(b[1] / a[1]) / math.sqrt(max(b[0] - a[0], 0.5)) for a, b in zip(pts, pts[1:], strict=False)
                if a[1] > 0 and b[1] > 0]
        if len(rets) < 60:
            return None
        m = sum(rets) / len(rets)
        return max(math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1)), 2e-5)

    async def sampler(self) -> None:
        """1-s mid samples of every underlying with a CF-settled series (Coinbase WS book → no extra API load)."""
        while not self.f.stop_event.is_set():
            self.f.sup.beat("sw_sampler")
            now = time.time()
            for pid in set(self._series().values()):
                b = self.f.market.get_bbo(pid)
                if b and b.bid > 0 and b.ask > 0:
                    self.samples.setdefault(pid, deque(maxlen=1800)).append((now, 0.5 * (float(b.bid) + float(b.ask))))
            await asyncio.sleep(1.0 - (time.time() % 1.0) + 0.02)

    def _avg(self, pid: str, t0: float, t1: float) -> float | None:
        pts = [px for ts, px in self.samples.get(pid, ()) if t0 <= ts < t1]
        return sum(pts) / len(pts) if len(pts) >= 40 else None

    def _observe_basis(self, pid: str, brti_avg: float, t_end: float) -> None:
        mine = self._avg(pid, t_end - WINDOW_S, t_end)
        if not mine or brti_avg <= 0:
            return
        x = math.log(brti_avg / mine)
        if abs(x) > 0.003:                    # > 30 bp: a data glitch, not a basis
            return
        m, v, n = self.basis.get(pid, (0.0, BASIS_SD_FLOOR ** 2, 0))
        a = 0.2 if n >= 5 else 1.0 / (n + 1)
        m2 = (1 - a) * m + a * x
        v2 = (1 - a) * v + a * (x - m) ** 2
        self.basis[pid] = (m2, max(v2, BASIS_SD_FLOOR ** 2), n + 1)
        self.stats["basis_obs"] += 1

    # ---------------------------------------------------------------- discovery + hot loop
    async def discover(self) -> None:
        k = self.f.crossrail.k
        now = time.time()
        live: dict[str, dict[str, Any]] = {}
        for series, pid in self._series().items():
            with contextlib.suppress(Exception):
                d = await k.get("/markets", {"series_ticker": series, "status": "open", "max_close_ts": int(now + HOT_S + 900),
                                             "limit": 200})
                for m in d.get("markets", []):
                    mk = parse_market(m, series)
                    live[mk.ticker] = {"series": series, "pid": pid, "mk": mk, "open_ts": _ts(m.get("open_time"))}
                    # a 15-min market's floor strike = BRTI 60-s average before its open → basis observation
                    if self.f.crossrail.series_meta.get(series, {}).get("frequency") == "fifteen_min" and mk.floor:
                        key = f"basis:{mk.ticker}"
                        if key not in self._last_cal and now - live[mk.ticker]["open_ts"] < 840:
                            self._last_cal[key] = now
                            self._observe_basis(pid, float(mk.floor), live[mk.ticker]["open_ts"])
        self.markets = live

    async def hot_sweep(self) -> None:
        now = time.time()
        hot_series = {v["series"] for v in self.markets.values() if 0 < v["mk"].close_ts - now <= HOT_S}
        k = self.f.crossrail.k
        for series in hot_series:
            try:
                d = await k.get("/markets", {"series_ticker": series, "status": "open", "max_close_ts": int(now + HOT_S),
                                             "limit": 200})
            except Exception:
                continue
            for m in d.get("markets", []):
                mk = parse_market(m, series)
                info = self.markets.get(mk.ticker)
                if info is None:
                    continue
                info["mk"] = mk
                await self._evaluate(info, series)
        self.stats["hot_sweeps"] += 1

    def _probabilities(self, info: dict[str, Any]) -> dict[str, Any] | None:
        mk, pid = info["mk"], info["pid"]
        now = time.time()
        sig = self._sigma(pid)
        q = self.samples.get(pid)
        if sig is None or not q:
            return None
        spot = q[-1][1]
        if now - q[-1][0] > 3:
            return None                                             # stale feed: never trade on it
        mean_b, var_b, n_b = self.basis.get(pid, (0.0, (5e-4) ** 2, 0))      # unknown basis → wide (5 bp) prior
        sd_b = math.sqrt(var_b)
        realized = [(ts, px) for ts, px in q if ts >= mk.close_ts - WINDOW_S - 1]
        mean, sd, n_real = window_distribution(now, mk.close_ts, spot, sig, realized)
        mean_brti = mean * math.exp(mean_b)
        sd_tot = math.sqrt(sd ** 2 + (mean_brti * sd_b) ** 2)
        sd_cons = math.sqrt((sd * VOL_INFLATE) ** 2 + (mean_brti * sd_b) ** 2)
        p = p_outcome(mean_brti, sd_tot, mk.strike_type, mk.floor, mk.cap)
        p_lo = p_outcome(mean_brti * math.exp(-sd_b), sd_cons, mk.strike_type, mk.floor, mk.cap)
        p_hi = p_outcome(mean_brti * math.exp(sd_b), sd_cons, mk.strike_type, mk.floor, mk.cap)
        if math.isnan(p):
            return None
        return {"p": p, "p_yes_cons": min(p_lo, p_hi), "p_no_cons": 1 - max(p_lo, p_hi), "secs_to_close": mk.close_ts - now,
                "n_realized": n_real, "sigma_1s": sig, "basis_bp": mean_b * 1e4, "basis_sd_bp": sd_b * 1e4, "basis_n": n_b,
                "spot": spot, "mean": mean_brti, "sd": sd_tot}

    async def _evaluate(self, info: dict[str, Any], series: str) -> None:
        mk = info["mk"]
        pr = self._probabilities(info)
        if pr is None:
            return
        now = time.time()
        if now - self._last_cal.get(mk.ticker, 0) >= 10 and mk.yes_bid is not None and mk.yes_ask is not None:
            self._last_cal[mk.ticker] = now
            self.f.db.insert("sw_calibration", {"ts": now, "ticker": mk.ticker, "series": series, "underlying": info["pid"],
                                                "secs_to_close": pr["secs_to_close"], "n_realized": pr["n_realized"],
                                                "p_model": pr["p"], "p_cons_yes": pr["p_yes_cons"], "p_cons_no": pr["p_no_cons"],
                                                "yes_bid": mk.yes_bid, "yes_ask": mk.yes_ask, "close_ts": mk.close_ts})
            self.stats["calib"] += 1
        meta = self.f.crossrail.series_meta.get(series, {})
        ft, mult = str(meta.get("fee_type") or "quadratic"), float(meta.get("fee_multiplier") or 1.0)
        cands = []
        if mk.yes_ask is not None and mk.yes_ask_size >= 1:
            fee = kalshi_fee(mk.yes_ask, 1, ft, mult)
            cands.append(("yes", mk.yes_ask, fee, pr["p_yes_cons"] - mk.yes_ask - fee))
        if mk.no_ask is not None and mk.yes_bid_size >= 1:
            fee = kalshi_fee(mk.no_ask, 1, ft, mult)
            cands.append(("no", mk.no_ask, fee, pr["p_no_cons"] - mk.no_ask - fee))
        for side, price, _fee, edge in cands:
            if edge < MIN_EDGE or not (0.02 <= price <= 0.98):
                continue
            if self.f.db.scalar("SELECT 1 FROM crossrail_signals WHERE kind='SETTLE_WINDOW' AND ticker=? AND side=?",
                                (mk.ticker, side)):
                continue
            await asyncio.sleep(LATENCY_S)                     # would the quote still be there after an order round trip?
            try:
                fresh = parse_market(await self.f.crossrail.k.market(mk.ticker), series)
            except Exception:
                continue
            now_px = fresh.yes_ask if side == "yes" else fresh.no_ask
            if now_px is None or now_px > price + 1e-9:
                self.stats["missed_after_latency"] += 1
                continue
            await self._record(info, series, side, now_px, kalshi_fee(now_px, 1, ft, mult), pr)

    async def _record(self, info: dict[str, Any], series: str, side: str, price: float, fee: float, pr: dict[str, Any]) -> None:
        from forge.persistence.db import dumps
        mk = info["mk"]
        p_side = pr["p"] if side == "yes" else 1 - pr["p"]
        lcb = pr["p_yes_cons"] if side == "yes" else pr["p_no_cons"]
        row = self.f.db.insert_id("crossrail_signals", {
            "ts": time.time(), "kind": "SETTLE_WINDOW", "ticker": mk.ticker, "event_ticker": mk.event_ticker, "series": series,
            "underlying": info["pid"], "ref_price": pr["spot"], "sigma_min": pr["sigma_1s"] * math.sqrt(60),
            "minutes": pr["secs_to_close"] / 60, "side": side, "price": price, "fee": fee, "edge": lcb - price - fee,
            "p_model": p_side, "p_market": price, "p_stacked": None, "p_lcb": lcb, "kelly": None, "close_ts": mk.close_ts,
            "status": "OPEN", "detail": dumps({k: pr[k] for k in ("n_realized", "basis_bp", "basis_sd_bp", "basis_n", "mean",
                                                                   "sd", "secs_to_close")})})
        self.stats["signals"] += 1
        live = getattr(self.f, "kalshi_live", None)
        if live is not None and live.configured:
            asyncio.get_running_loop().create_task(live.on_signal({
                "id": row, "ts": time.time(), "ticker": mk.ticker, "side": side, "price": price, "fee": fee,
                "close_ts": mk.close_ts, "kind": "SETTLE_WINDOW"}))

    async def settle_calibration(self) -> None:
        rows = self.f.db.query("SELECT DISTINCT ticker FROM sw_calibration WHERE outcome IS NULL AND close_ts < ? LIMIT 30",
                               (time.time() - 180,))
        for r in rows:
            with contextlib.suppress(Exception):
                m = await self.f.crossrail.k.market(r["ticker"])
                res = m.get("result")
                if res in ("yes", "no"):
                    self.f.db.execute("UPDATE sw_calibration SET outcome = ? WHERE ticker = ? AND outcome IS NULL",
                                      (1 if res == "yes" else 0, r["ticker"]))
                    ev = m.get("expiration_value")
                    pid = (self.markets.get(r["ticker"]) or {}).get("pid") or self.f.db.scalar(
                        "SELECT underlying FROM sw_calibration WHERE ticker = ? LIMIT 1", (r["ticker"],))
                    if ev and pid:                      # settlement value = BRTI average → another basis observation
                        self._observe_basis(pid, float(ev), float(self.f.db.scalar(
                            "SELECT close_ts FROM sw_calibration WHERE ticker = ? LIMIT 1", (r["ticker"],))))

    def scorecard(self) -> dict[str, Any]:
        rows = self.f.db.query("SELECT p_model, yes_bid, yes_ask, outcome, secs_to_close FROM sw_calibration WHERE outcome IS NOT NULL "
                               "ORDER BY id DESC LIMIT 20000")
        out: dict[str, Any] = {"stats": self.stats, "basis_bp": {k: round(v[0] * 1e4, 2) for k, v in self.basis.items()}}
        for lo, hi in ((0, 60), (60, 180), (180, 300)):
            b = [r for r in rows if lo <= r["secs_to_close"] < hi]
            if b:
                bm = sum((r["p_model"] - r["outcome"]) ** 2 for r in b) / len(b)
                bk = sum((0.5 * (r["yes_bid"] + r["yes_ask"]) - r["outcome"]) ** 2 for r in b) / len(b)
                out[f"brier_{lo}_{hi}s"] = {"n": len(b), "model": round(bm, 5), "market_mid": round(bk, 5)}
        return out

    # ---------------------------------------------------------------- supervised loops
    async def run(self) -> None:
        last_disc = last_settle = 0.0
        while not self.f.stop_event.is_set():
            self.f.sup.beat("settlement_window")
            try:
                if getattr(self.f, "crossrail", None) is not None and self.f.crossrail.mapping:
                    if time.time() - last_disc >= DISCOVER_S:
                        last_disc = time.time()
                        await self.discover()
                    if any(0 < v["mk"].close_ts - time.time() <= HOT_S for v in self.markets.values()):
                        await self.hot_sweep()
                    if time.time() - last_settle >= 120:
                        last_settle = time.time()
                        await self.settle_calibration()
                        self.f.db.kv_set("settlement_window.scorecard", self.scorecard())
            except Exception as e:
                log.warning("settlement window: %s", e)
            hot = any(0 < v["mk"].close_ts - time.time() <= HOT_S for v in self.markets.values())
            await asyncio.sleep(1.5 if hot else 5.0)


def _ts(s: Any) -> float:
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0
