"""Cross-rail information engine (operator directive OP-013): Coinbase prices ↔ Kalshi event contracts.

1. DISCOVERY — Kalshi series are mapped to Coinbase underlyings automatically (CF Benchmarks crypto → <ASSET>-USD spot;
   gold → PAXG-USD proxy). A mapping is accepted only if the contract strikes are on the same scale as the Coinbase
   price (0.33×–3×), so a new Kalshi series on a Coinbase-listed asset becomes a candidate without code changes.
2. PROBABILITY — forge.opportunities.probability: HAR-RV volatility (bias-corrected Garman–Klass, 1m + 5m bars) ×
   intraday seasonality over the exact contract window, filtered-historical-simulation tails (365 d), 60 s settlement
   averaging, then a Bayesian STACKED calibrator that blends model and market and only trusts the model as far as
   settled outcomes prove it adds information. Trades use the lower confidence bound.
3. SIGNALS (shadow only — no Kalshi orders exist in FORGE):
   - TAKE: buy YES/NO when the stacked lower bound beats the executable ask by ≥ max(2¢, fee) after fees.
   - MAKE: zero-fee (most series) passive bid at (stacked bound − margin) inside the spread; counted as filled ONLY when
     the opposite side later trades through our price (adverse selection included), then held to settlement.
   - MODEL_RAW: raw-model taker signals, recorded separately so the raw model's profitability is measured too.
   - LADDER_ARB: monotonicity violation across "greater" strikes (YES ask at a lower strike < YES bid at a higher strike).
   - RANGE_ARB: mutually exclusive range bins whose YES asks sum < $1 (or bids sum > $1) after fees.
4. SETTLEMENT — every signal and calibration sample is scored when the market settles (true would-be net P&L per contract
   after Kalshi fees). This evidence is what can later justify funding the Kalshi rail.
"""

from __future__ import annotations

import contextlib
import logging
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from forge.opportunities.kalshi import KalshiMarket, KalshiPublic, kalshi_fee, parse_market
from forge.opportunities.probability import (
    StackedCalibrator,
    UnderlyingModel,
    binary_kelly,
    fit_underlying,
    stack_features,
)
from forge.opportunities.probsurface import (
    best_lead,
    fit_surface,
    half_life,
    implied_median,
    lead_lag,
    surface_rv_candidates,
)

log = logging.getLogger("forge.crossrail")

ALIASES = {"BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL", "RIPPLE": "XRP", "DOGECOIN": "DOGE", "CARDANO": "ADA",
           "AVALANCHE": "AVAX", "CHAINLINK": "LINK", "LITECOIN": "LTC", "POLKADOT": "DOT", "SHIBA": "SHIB", "ZCASH": "ZEC",
           "STELLAR": "XLM"}
COMMODITY_PROXIES = {"GOLD": "PAXG-USD"}        # Pyth gold ↔ PAXG (1 PAXG = 1 troy oz; basis learned, never assumed 0)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fair_probability(spot: float, sigma_per_min: float, minutes: float, strike_type: str,
                     floor: float | None, cap: float | None) -> float | None:
    """Driftless lognormal probability that the settlement value satisfies the contract."""
    if spot <= 0 or minutes <= 0 or sigma_per_min <= 0:
        return None
    s = sigma_per_min * math.sqrt(minutes)

    def p_above(k: float) -> float:
        return norm_cdf((math.log(spot / k) - 0.5 * s * s) / s)
    if strike_type == "greater" and floor:
        return p_above(floor)
    if strike_type == "less" and cap:
        return 1.0 - p_above(cap)
    if strike_type == "between" and floor and cap and cap > floor:
        return max(0.0, p_above(floor) - p_above(cap))
    return None


def map_series(series: dict[str, Any], spot_bases: set[str]) -> str | None:
    """Kalshi series → Coinbase product id (or None). Pure, deterministic."""
    srcs = " ".join(str(x.get("name", "")) for x in (series.get("settlement_sources") or []))
    tick = str(series.get("ticker", "")).upper()
    title = str(series.get("title", "")).upper()
    if "PYTH - GOLD" in srcs.upper() or (series.get("category") == "Commodities" and tick.startswith("KXGOLD")
                                         and "VS" not in tick):
        return COMMODITY_PROXIES["GOLD"] if "PAXG" in spot_bases else None
    if "CF BENCHMARKS" not in srcs.upper() or series.get("category") != "Crypto":
        return None
    if any(w in tick for w in ("COMP", "LEAD", "VS", "ATH", "FDV", "MEGA", "MAX", "MIN", "TOUCH", "HIT")):  # multi-asset, non-price or PATH-DEPENDENT (one-touch) series: terminal model invalid
        return None
    core = tick[2:] if tick.startswith("KX") else tick
    for word, base in ALIASES.items():                         # explicit names in the CODE first (KXRIPPLE, KXSHIBA)
        if core.startswith(word):
            return f"{base}-USD" if base in spot_bases else None
    for n in range(min(6, len(core)), 2, -1):                 # longest Coinbase base that prefixes the series code
        if core[:n] in spot_bases:
            return f"{core[:n]}-USD"
    if "CASH" in title or "CLASSIC" in title or "SV" in title.split():   # forks must never map to the parent asset
        return None
    for word, base in ALIASES.items():
        if re.search(rf"\b{word}\b", title):
            return f"{base}-USD" if base in spot_bases else None
    return None


def scale_ok(strikes: list[float], spot: float) -> bool:
    ks = sorted(k for k in strikes if k and k > 0)
    if not ks or spot <= 0:
        return False
    med = ks[len(ks) // 2]
    return 0.33 <= med / spot <= 3.0


@dataclass
class Signal:
    kind: str
    ticker: str
    side: str            # yes | no | basket
    price: float         # per contract (cost)
    fee: float
    edge: float          # expected (TAKE/MAKE) or locked (ARB) net $ per contract/basket
    detail: dict[str, Any]


def ladder_arbs(markets: list[KalshiMarket]) -> list[Signal]:
    """Buy YES at the lower strike + NO at the higher strike: payout ≥ $1 in every state → locked if cost < $1 − fees."""
    g = sorted((m for m in markets if m.strike_type == "greater" and m.floor), key=lambda m: m.floor or 0)
    out = []
    for i, lo in enumerate(g):
        if lo.yes_ask is None:
            continue
        for hi in g[i + 1:]:
            if hi.no_ask is None:
                continue
            cost = lo.yes_ask + hi.no_ask
            fee = kalshi_fee(lo.yes_ask) + kalshi_fee(hi.no_ask)
            edge = 1.0 - cost - fee
            if edge > 0.01:
                out.append(Signal("LADDER_ARB", f"{lo.ticker}|{hi.ticker}", "basket", cost, fee, edge,
                                  {"lo": lo.floor, "hi": hi.floor}))
    return out


def range_arbs(markets: list[KalshiMarket], mutually_exclusive: bool) -> list[Signal]:
    if not mutually_exclusive or len(markets) < 2:
        return []
    out = []
    asks = [m.yes_ask for m in markets]
    if all(a is not None for a in asks):
        cost = sum(asks)                                       # type: ignore[arg-type]
        fee = sum(kalshi_fee(a) for a in asks)                 # type: ignore[arg-type]
        if 1.0 - cost - fee > 0.01:
            out.append(Signal("RANGE_ARB", markets[0].event_ticker, "basket", cost, fee, 1.0 - cost - fee,
                              {"legs": len(markets), "type": "buy_all_yes"}))
    nos = [m.no_ask for m in markets]
    if all(a is not None for a in nos):
        n = len(markets)
        cost = sum(nos)                                        # type: ignore[arg-type]
        fee = sum(kalshi_fee(a) for a in nos)                  # type: ignore[arg-type]
        if (n - 1) - cost - fee > 0.01:
            out.append(Signal("RANGE_ARB", markets[0].event_ticker, "basket", cost, fee, (n - 1) - cost - fee,
                              {"legs": n, "type": "buy_all_no"}))
    return out


def taker_signals(mk: KalshiMarket, p_lo: float, p_hi: float, kind: str = "TAKE", min_edge: float = 0.02,
                  fee_type: str = "quadratic", mult: float = 1.0) -> list[Signal]:
    """Conservative: YES judged on the lower bound, NO on the upper bound of P(yes)."""
    out = []
    for side, ask, p_win in (("yes", mk.yes_ask, p_lo), ("no", mk.no_ask, 1.0 - p_hi)):
        if ask is None or not (0.03 <= ask <= 0.97):
            continue
        fee = kalshi_fee(ask, fee_type=fee_type, multiplier=mult)
        edge = p_win - ask - fee
        if edge >= max(min_edge, fee):
            out.append(Signal(kind, mk.ticker, side, ask, fee, edge, {"kelly": binary_kelly(p_win, ask, fee)}))
    return out


def maker_quotes(mk: KalshiMarket, p_lo: float, p_hi: float, margin: float = 0.02, fee_type: str = "quadratic",
                 mult: float = 1.0) -> list[Signal]:
    """Passive bids strictly inside the spread (never crossing), priced so the bound still clears margin + maker fee."""
    out = []
    if mk.yes_bid is None or mk.yes_ask is None or mk.yes_ask - mk.yes_bid < 0.02:
        return out
    q = min(math.floor((p_lo - margin) * 100) / 100, round(mk.yes_bid + 0.01, 2))
    if 0.03 <= q < mk.yes_ask and q >= mk.yes_bid:                      # join or improve the best bid — or don't quote
        fee = kalshi_fee(q, fee_type=fee_type, multiplier=mult, maker=True)
        if p_lo - q - fee >= margin:
            out.append(Signal("MAKE", mk.ticker, "yes", q, fee, p_lo - q - fee, {}))
    no_bid, no_ask = 1.0 - mk.yes_ask, 1.0 - mk.yes_bid
    qn = min(math.floor((1.0 - p_hi - margin) * 100) / 100, round(no_bid + 0.01, 2))
    if 0.03 <= qn < no_ask and qn >= no_bid - 1e-9:
        fee = kalshi_fee(qn, fee_type=fee_type, multiplier=mult, maker=True)
        if (1.0 - p_hi) - qn - fee >= margin:
            out.append(Signal("MAKE", mk.ticker, "no", qn, fee, (1.0 - p_hi) - qn - fee, {}))
    return out


def maker_filled(side: str, quote: float, mk: KalshiMarket) -> bool:
    """A resting bid is filled once the opposite side trades/offers through it (adverse selection included)."""
    if side == "yes":
        return mk.yes_ask is not None and mk.yes_ask <= quote
    return mk.no_ask is not None and mk.no_ask <= quote


class CrossRailScanner:
    """Supervised loop inside FORGE. Read-only on every rail; writes shadow evidence + calibration to the DB."""

    SCAN_S = 60
    SERIES_REFRESH_S = 6 * 3600
    MODEL_REFIT_S = 1800
    CALIB_REFIT_S = 1800
    MAX_SERIES = 40

    def __init__(self, forge: Any) -> None:
        self.f = forge
        self.k = KalshiPublic()
        self.mapping: dict[str, str] = {}
        self.series_meta: dict[str, dict[str, Any]] = {}
        self.models: dict[str, UnderlyingModel] = {}
        self.basis: dict[str, float] = {}
        self.calib = StackedCalibrator()
        self.last_series = self.last_calib_fit = 0.0
        self.last_sample: dict[str, float] = {}
        self.stats: dict[str, Any] = {"scans": 0, "markets": 0, "signals": 0, "settled": 0, "fills": 0}
        saved = self.f.db.kv_get("crossrail.calibrator")
        if saved and len(saved.get("w", [])) == len(self.calib.w):     # feature set changed → refit from samples
            with contextlib.suppress(Exception):
                self.calib.w, self.calib.cov, self.calib.n = np.array(saved["w"]), np.array(saved["cov"]), int(saved["n"])
        self.ticks: dict[str, list[tuple[float, float, float]]] = {}      # underlying → [(ts, spot, implied median)]

    # ---------------------------------------------------------------- discovery
    async def refresh_series(self) -> None:
        series = await self.k.series()
        rules = getattr(self.f.market, "rules", {}) or {}
        bases = {p.split("-")[0] for p in rules} | {s.split("-")[0] for s in getattr(self.f, "universe", [])}
        bases.add("PAXG")                                     # gold proxy (verified listed on Coinbase spot)
        freq_rank = {"fifteen_min": 0, "hourly": 1, "daily": 2, "weekly": 3}
        cands = []
        for s in series:
            pid = map_series(s, bases)
            if pid and s.get("frequency") in freq_rank:
                cands.append((freq_rank[s["frequency"]], s["ticker"], pid, s))
        cands.sort()
        self.mapping = {t: pid for _, t, pid, _ in cands[: self.MAX_SERIES]}
        self.series_meta = {t: s for _, t, _, s in cands[: self.MAX_SERIES]}
        self.last_series = time.time()
        self.f.db.kv_set("crossrail.mapping", {"ts": time.time(), "mapped": self.mapping, "candidates": len(cands),
                                               "series_total": len(series)})

    # ---------------------------------------------------------------- probability models
    async def _bars(self, pid: str) -> dict[str, np.ndarray] | None:
        from forge.market_data.history import CandleStore
        try:
            b = CandleStore(Path(self.f.s.market_dir)).load(pid, 300)
        except Exception:
            b = None
        if b is not None and len(b["close"]) >= 2000:
            return {k: np.asarray(v, dtype=float) for k, v in b.items()}
        now = int(time.time()) // 300 * 300                    # not in the store → 14 days of 5m candles via REST
        rows: list[dict[str, Any]] = []
        for i in range(12):
            end = now - i * 350 * 300
            rows += await self.f.rest.candles(pid, end - 350 * 300, end, 300)
        rows = sorted({int(r["start"]): r for r in rows}.values(), key=lambda r: int(r["start"]))
        if len(rows) < 600:
            return None
        return {"ts": np.array([float(r["start"]) for r in rows]), **{k: np.array([float(r[k]) for r in rows])
                                                                    for k in ("open", "high", "low", "close")}}

    async def _model(self, pid: str) -> UnderlyingModel | None:
        m = self.models.get(pid)
        if m and time.time() - m.fitted_ts < self.MODEL_REFIT_S:
            return m
        bars = await self._bars(pid)
        if bars is None:
            return m
        now = int(time.time())
        r1 = await self.f.rest.candles(pid, now - 120 * 60, now, 60)
        one = {k: np.array([float(r[k]) for r in r1]) for k in ("open", "high", "low", "close")} if r1 else None
        import asyncio
        nm = await asyncio.get_running_loop().run_in_executor(None, fit_underlying, pid, bars, 300, one)
        if nm:
            nm.fitted_ts = time.time()
            self.models[pid] = nm
        return nm or m

    def _ref_price(self, pid: str) -> float | None:
        b = self.f.market.get_bbo(pid)
        if b and b.bid > 0 and b.ask > 0:
            return 0.5 * (b.bid + b.ask)
        return None

    def refit_calibrator(self) -> None:
        rows = self.f.db.query("SELECT p_model, p_market, minutes, flow, direction, outcome FROM crossrail_calibration "
                               "WHERE outcome IS NOT NULL ORDER BY id DESC LIMIT 20000")
        if len(rows) < 30:
            return
        X = np.array([stack_features(r["p_model"], r["p_market"], r["minutes"], r["flow"] or 0.0, r["direction"] or 0)
                      for r in rows])
        y = np.array([float(r["outcome"]) for r in rows])
        self.calib.fit(X, y)
        self.last_calib_fit = time.time()
        self.f.db.kv_set("crossrail.calibrator", {"w": self.calib.w.tolist(), "cov": self.calib.cov.tolist(),
                                                  "n": self.calib.n, "model_share": self.calib.model_weight_share(),
                                                  "ts": time.time()})

    # ---------------------------------------------------------------- scan
    async def scan_once(self, only: set[str] | None = None) -> dict[str, Any]:
        if time.time() - self.last_series > self.SERIES_REFRESH_S or not self.mapping:
            await self.refresh_series()
        if time.time() - self.last_calib_fit > self.CALIB_REFIT_S:
            self.refit_calibrator()
        now = time.time()
        n_mk = n_sig = 0
        for series, pid in list(self.mapping.items()):
            if only is not None and series not in only:
                continue
            meta = self.series_meta.get(series, {})
            ft, mult = str(meta.get("fee_type") or "quadratic"), float(meta.get("fee_multiplier") or 1.0)
            ref = self._ref_price(pid)
            try:
                if ref is None:
                    ref = float((await self.f.rest.product(pid)).get("price") or 0) or None
                if not ref:
                    continue
                model = await self._model(pid)
                events = await self.k.open_events(series, limit=2)
            except Exception as e:
                log.debug("crossrail %s: %s", series, e)
                continue
            for ev in events:
                mks = [parse_market(m, series) for m in ev.get("markets", [])]
                mks = [m for m in mks if m.status in ("active", "open")]
                if not mks or not scale_ok([m.floor or m.cap or 0 for m in mks], ref):
                    continue
                n_mk += len(mks)
                self._check_quotes(mks)
                live = [m for m in mks if m.close_ts > now + 120]
                adj = ref * math.exp(self._update_basis(pid, live, ref))
                sigs: list[Signal] = ladder_arbs(live)
                sigs += range_arbs(live, bool(ev.get("mutually_exclusive")))
                # implied probability surface: relative value vs neighbouring strikes (no directional view needed)
                surf = fit_surface([(m.ticker, m.floor, m.yes_bid, m.yes_ask) for m in live
                                    if m.strike_type == "greater" and m.floor])
                fitted = {p.ticker: p.fitted for p in surf}
                for t, side, ask, fair in surface_rv_candidates(surf):
                    fee = kalshi_fee(ask, fee_type=ft, multiplier=mult)
                    if fair - ask - fee >= max(0.02, fee):
                        sigs.append(Signal("SURFACE_RV", t, side, ask, fee, fair - ask - fee, {"surface_fair": fair}))
                med = implied_median(surf)
                if med and ev.get("event_ticker"):
                    self._tick(pid, ev["event_ticker"], ref, med, now)
                micro = self.f.market.micro(pid) if hasattr(self.f.market, "micro") else {}
                flow = micro.get("flow_imb_60s", 0.0)
                flow = flow if flow == flow else 0.0
                quotes_now: dict[str, tuple[float, float, KalshiMarket]] = {}
                for m in live:
                    minutes = (m.close_ts - now) / 60
                    if model is None or minutes > 26 * 60:
                        continue
                    pm = model.prob(adj, now, minutes, m.strike_type, m.floor, m.cap)
                    if pm is None:
                        continue
                    if m.yes_bid is not None and m.yes_ask is not None:
                        mid = 0.5 * (m.yes_bid + m.yes_ask)
                        direction = 1 if m.strike_type == "greater" else -1 if m.strike_type == "less" else 0
                        ps, plo, phi = self.calib.predict(pm, mid, minutes, flow, direction)
                        quotes_now[m.ticker] = (plo, phi, m)
                        self._calib_sample(m, pm, mid, ps, ref, model, minutes, pid, flow, direction, fitted.get(m.ticker))
                        thresh = taker_signals(m, plo, phi, "TAKE_THRESH", fee_type=ft, mult=mult) \
                            if m.strike_type in ("greater", "less") else []          # pre-registered 2026-10-07 14:5x UTC
                        thresh = [x for x in thresh if 0.40 <= x.price <= 0.80]
                        for s_ in taker_signals(m, plo, phi, "TAKE", fee_type=ft, mult=mult) + thresh + \
                                maker_quotes(m, plo, phi, fee_type=ft, mult=mult):
                            s_.detail.update(p_model=pm, p_market=mid, p_stacked=ps, p_lo=plo, p_hi=phi, minutes=minutes)
                            sigs.append(s_)
                    for s_ in taker_signals(m, pm, pm, "MODEL_RAW", min_edge=0.04, fee_type=ft, mult=mult):
                        s_.detail.update(p_model=pm, minutes=minutes)
                        sigs.append(s_)
                for s_ in sigs:
                    n_sig += self._record(s_, series, pid, ref, model, ev, live)
                self._edge_decay(quotes_now, now, fitted)
        self.stats["scans"] += 1
        self.stats["markets"] = n_mk
        self.stats["signals"] += n_sig
        return {"markets": n_mk, "signals": n_sig}

    def _update_basis(self, pid: str, mks: list[KalshiMarket], ref: float) -> float:
        """Crypto: CF Benchmarks RTI ≈ Coinbase (basis 0). Gold proxy (PAXG vs Pyth gold): learn the log basis slowly
        from the ladder's 50% crossing — only FAST deviations can then be signals, never the level."""
        if not pid.startswith("PAXG"):
            return 0.0
        g = sorted((m for m in mks if m.strike_type == "greater" and m.floor and m.yes_bid and m.yes_ask),
                   key=lambda m: m.floor or 0)
        for a, b in zip(g[:-1], g[1:], strict=False):
            ma, mb = 0.5 * (a.yes_bid + a.yes_ask), 0.5 * (b.yes_bid + b.yes_ask)   # type: ignore[operator]
            if ma >= 0.5 >= mb and a.floor and b.floor:
                implied = a.floor + (b.floor - a.floor) * (ma - 0.5) / max(ma - mb, 1e-9)
                obs = math.log(implied / ref)
                old = self.basis.get(pid)
                self.basis[pid] = obs if old is None else 0.97 * old + 0.03 * obs
                break
        return self.basis.get(pid, 0.0)

    def _calib_sample(self, m: KalshiMarket, pm: float, mid: float, ps: float, ref: float, model: UnderlyingModel,
                      minutes: float, pid: str, flow: float = 0.0, direction: int = 0, p_surface: float | None = None) -> None:
        if not (0.05 <= mid <= 0.95) or (m.yes_ask or 1) - (m.yes_bid or 0) > 0.12:
            return
        if time.time() - self.last_sample.get(m.ticker, 0) < 900:          # ≤ 1 sample / market / 15 min
            return
        self.last_sample[m.ticker] = time.time()
        self.f.db.insert("crossrail_calibration", {
            "ts": time.time(), "ticker": m.ticker, "series": m.series, "underlying": pid, "ref_price": ref,
            "sigma_min": model.sigma_min_now, "minutes": minutes, "p_model": pm, "p_market": mid, "p_stacked": ps,
            "spread": (m.yes_ask or 0) - (m.yes_bid or 0), "close_ts": m.close_ts, "outcome": None,
            "flow": flow, "direction": direction, "p_surface": p_surface})

    def _tick(self, pid: str, event: str, spot: float, med: float, now: float) -> None:
        buf = self.ticks.setdefault(pid, [])
        if buf and now - buf[-1][0] < 10:
            return
        buf.append((now, spot, med))
        del buf[:-2000]
        self.f.db.insert("crossrail_ticks", {"ts": now, "underlying": pid, "event_ticker": event, "spot": spot,
                                             "implied_median": med})

    def lead_lag_report(self) -> dict[str, Any]:
        """Lead/lag per underlying on ~15 s samples (fast lane). A lead is trusted only when t ≥ 3 with n ≥ 15."""
        out = {}
        for pid, buf in self.ticks.items():
            if len(buf) < 40:
                continue
            spot, imp = [b[1] for b in buf[-400:]], [b[2] for b in buf[-400:]]
            gaps = [b[0] - a[0] for a, b in zip(buf[-400:-1], buf[-399:], strict=False)]
            step = sorted(gaps)[len(gaps) // 2] if gaps else 15.0
            sc = lead_lag(spot, imp)
            b = best_lead(sc)
            out[pid] = {"samples": len(spot), "step_s": step,
                        "lead": ({"lag_s": b.lag_steps * step, "corr": b.corr, "t": b.t_stat, "beta": b.beta} if b else None),
                        "lag0_corr": sc[0].corr if sc else None}
        return out

    def _edge_decay(self, quotes_now: dict[str, tuple[float, float, KalshiMarket]], now: float,
                    fitted: dict[str, float] | None = None) -> None:
        """Re-measure open taker signals (5 s – 30 min old) at the current quote → edge-decay curve per signal.
        SURFACE_RV edges are measured against the smoothed SURFACE fair value (model-free), TAKE against the stacked bound."""
        rows = self.f.db.query("SELECT id, ts, ticker, side, kind, fee FROM crossrail_signals WHERE status = 'OPEN' "
                               "AND kind IN ('TAKE','SURFACE_RV') AND ts > ? AND ts < ?", (now - 1800, now - 5))
        for r in rows:
            q = quotes_now.get(r["ticker"])
            if q is None:
                continue
            plo, phi, m = q
            ask = m.yes_ask if r["side"] == "yes" else m.no_ask
            if ask is None:
                continue
            if r["kind"] == "SURFACE_RV":
                fv = (fitted or {}).get(r["ticker"])
                if fv is None:
                    continue
                p_win = fv if r["side"] == "yes" else 1.0 - fv
            else:
                p_win = plo if r["side"] == "yes" else 1.0 - phi
            self.f.db.insert("edge_decay", {"signal_id": r["id"], "dt_s": now - r["ts"],
                                            "edge": p_win - ask - kalshi_fee(ask)})

    def half_life_report(self) -> dict[str, Any]:
        rows = self.f.db.query("SELECT s.id, s.kind, s.edge, d.dt_s, d.edge AS e FROM crossrail_signals s JOIN edge_decay d "
                               "ON d.signal_id = s.id ORDER BY s.id, d.dt_s")
        by: dict[int, dict[str, Any]] = {}
        for r in rows:
            by.setdefault(r["id"], {"kind": r["kind"], "obs": [(0.0, r["edge"])]})["obs"].append((r["dt_s"], r["e"]))
        out: dict[str, Any] = {}
        for v in by.values():
            hl = half_life(v["obs"])
            k = out.setdefault(v["kind"], {"n": 0, "decayed": 0, "half_lives": []})
            k["n"] += 1
            if hl is not None:
                k["decayed"] += 1
                k["half_lives"].append(hl)
        for k in out.values():
            hl = sorted(k.pop("half_lives"))
            k["median_t50_s"] = hl[len(hl) // 2] if hl else None
        return out

    async def _rti_proxy(self, ticker: str, pid: str | None, close_ts: float) -> None:
        """Settlement index (CF Benchmarks via Kalshi expiration_value) vs Coinbase 1m close at the same time."""
        if not pid or self.f.db.scalar("SELECT 1 FROM rti_proxy WHERE ticker = ?", (ticker,)):
            return
        try:
            m = await self.k.market(ticker)
            sv = float(m.get("expiration_value") or 0)
            c = await self.f.rest.candles(pid, int(close_ts) - 120, int(close_ts) + 60, 60)
        except Exception:
            return
        if sv <= 0 or not c:
            return
        cb = float(min(c, key=lambda x: abs(int(x["start"]) + 60 - close_ts))["close"])
        self.f.db.insert("rti_proxy", {"ts": time.time(), "ticker": ticker, "underlying": pid, "close_ts": close_ts,
                                       "settlement_value": sv, "coinbase_close": cb, "log_error": math.log(cb / sv)})

    def _check_quotes(self, mks: list[KalshiMarket]) -> None:
        by = {m.ticker: m for m in mks}
        now = time.time()
        for q in self.f.db.query("SELECT id, ticker, side, price, expires_ts FROM crossrail_signals WHERE kind = 'MAKE' "
                                 "AND status = 'QUOTED'"):
            m = by.get(q["ticker"])
            if m is None:
                continue
            if maker_filled(q["side"], float(q["price"]), m):
                self.f.db.execute("UPDATE crossrail_signals SET status = 'OPEN', fill_ts = ? WHERE id = ?", (now, q["id"]))
                self.stats["fills"] += 1
            elif now >= float(q["expires_ts"] or 0):
                self.f.db.execute("UPDATE crossrail_signals SET status = 'EXPIRED' WHERE id = ?", (q["id"],))

    def _record(self, s: Signal, series: str, pid: str, ref: float, model: UnderlyingModel | None, ev: dict[str, Any],
                mks: list[KalshiMarket]) -> int:
        db = self.f.db
        if s.kind == "MAKE":
            if db.scalar("SELECT 1 FROM crossrail_signals WHERE kind='MAKE' AND ticker=? AND side=? AND status IN "
                         "('QUOTED','OPEN')", (s.ticker, s.side)):
                return 0                                       # one live quote / position per market side
        elif db.scalar("SELECT 1 FROM crossrail_signals WHERE ticker = ? AND side = ? AND kind = ?", (s.ticker, s.side, s.kind)):
            return 0                                           # takers/arbs: first sighting only
        legs = s.ticker.split("|")
        close_ts = max((m.close_ts for m in mks if m.ticker in legs or m.event_ticker == s.ticker), default=0.0)
        from forge.persistence.db import dumps
        d = s.detail
        row_id = db.insert_id("crossrail_signals", {
            "ts": time.time(), "kind": s.kind, "ticker": s.ticker, "event_ticker": ev.get("event_ticker"), "series": series,
            "underlying": pid, "ref_price": ref, "sigma_min": model.sigma_min_now if model else None,
            "minutes": d.get("minutes"), "side": s.side, "price": s.price, "fee": s.fee, "edge": s.edge,
            "p_model": d.get("p_model"), "p_market": d.get("p_market"), "p_stacked": d.get("p_stacked"),
            "p_lcb": d.get("p_lo") if s.side == "yes" else (1 - d["p_hi"] if d.get("p_hi") is not None else None),
            "kelly": d.get("kelly"), "close_ts": close_ts,
            "expires_ts": min(close_ts - 60, time.time() + 900) if s.kind == "MAKE" else None,
            "status": "QUOTED" if s.kind == "MAKE" else "OPEN",
            "detail": dumps({**{k: v for k, v in d.items() if k not in ("p_model", "p_market", "p_stacked")},
                             "basis": self.basis.get(pid, 0.0), "calib_n": self.calib.n,
                             "model_share": self.calib.model_weight_share()})})
        live = getattr(self.f, "kalshi_live", None)
        if s.kind == "TAKE_THRESH" and live is not None and live.configured:
            import asyncio
            asyncio.get_running_loop().create_task(live.on_signal({
                "id": row_id, "ts": time.time(), "ticker": s.ticker, "side": s.side, "price": s.price, "fee": s.fee,
                "close_ts": close_ts}))
        return 1

    # ---------------------------------------------------------------- settlement scoring
    async def settle(self, max_lookups: int = 40) -> int:
        import json as _j
        now = time.time()
        db = self.f.db
        db.execute("UPDATE crossrail_signals SET status = 'EXPIRED' WHERE kind='MAKE' AND status='QUOTED' AND close_ts < ?",
                   (now,))
        rows = db.query("SELECT id, kind, ticker, side, price, fee, detail FROM crossrail_signals WHERE status = 'OPEN' "
                        "AND close_ts < ? ORDER BY close_ts LIMIT ?", (now - 180, max_lookups))
        cal = db.query("SELECT DISTINCT ticker FROM crossrail_calibration WHERE outcome IS NULL AND close_ts < ? LIMIT ?",
                       (now - 180, max_lookups))
        cache: dict[str, str] = {}

        async def result(t: str) -> str:
            if t not in cache:
                cache[t] = (await self.k.market(t)).get("result") or ""
            return cache[t]
        n = 0
        for r in rows:
            try:
                res = [] if r["kind"] == "RANGE_ARB" else [await result(t) for t in r["ticker"].split("|")]
            except Exception:
                continue
            if any(x not in ("yes", "no") for x in res):
                continue
            if r["kind"] == "LADDER_ARB":
                payout = (1.0 if res[0] == "yes" else 0.0) + (1.0 if res[1] == "no" else 0.0)
            elif r["kind"] == "RANGE_ARB":
                dd = _j.loads(r["detail"] or "{}")
                payout = 1.0 if dd.get("type") == "buy_all_yes" else float(dd.get("legs", 2) - 1)
            else:
                payout = 1.0 if res[0] == r["side"] else 0.0
            pnl = payout - float(r["price"]) - float(r["fee"])
            db.execute("UPDATE crossrail_signals SET status = 'SETTLED', payout = ?, pnl = ?, settled_ts = ? WHERE id = ?",
                       (payout, pnl, now, r["id"]))
            n += 1
        for r in cal:
            try:
                res = await result(r["ticker"])
            except Exception:
                continue
            if res in ("yes", "no"):
                meta = db.query_one("SELECT underlying, close_ts FROM crossrail_calibration WHERE ticker = ? LIMIT 1", (r["ticker"],))
                if meta and db.scalar("SELECT COUNT(*) FROM rti_proxy") < 5000:
                    await self._rti_proxy(r["ticker"], meta["underlying"], float(meta["close_ts"] or 0))
                db.execute("UPDATE crossrail_calibration SET outcome = ? WHERE ticker = ? AND outcome IS NULL",
                           (1 if res == "yes" else 0, r["ticker"]))
        self.stats["settled"] += n
        return n

    def scorecard(self) -> dict[str, Any]:
        """Evidence: out-of-sample Brier (model / market / stacked-at-the-time) and shadow P&L by signal kind."""
        db = self.f.db
        c = db.query("SELECT p_model, p_market, p_stacked, outcome FROM crossrail_calibration WHERE outcome IS NOT NULL")
        out: dict[str, Any] = {"calibration_n": len(c), "calibrator_n": self.calib.n,
                               "model_weight_share": self.calib.model_weight_share()}
        if c:
            for k in ("p_model", "p_market", "p_stacked"):
                out[f"brier_{k[2:]}"] = sum((r[k] - r["outcome"]) ** 2 for r in c) / len(c)
            out["stack_beats_market"] = out["brier_stacked"] < out["brier_market"]
        kinds = {}
        for r in db.query("SELECT kind, COUNT(*) n, SUM(status='SETTLED') s, SUM(CASE WHEN status='SETTLED' THEN pnl END) pnl, "
                          "SUM(CASE WHEN status='SETTLED' AND pnl > 0 THEN 1 ELSE 0 END) w, AVG(edge) e, "
                          "SUM(status='EXPIRED') x FROM crossrail_signals GROUP BY kind"):
            kinds[r["kind"]] = {"signals": r["n"], "settled": r["s"], "pnl_per_contract_sum": r["pnl"] or 0.0,
                                "wins": r["w"], "avg_expected_edge": r["e"], "expired_quotes": r["x"]}
        out["signals"] = kinds
        rp = db.query("SELECT underlying, AVG(log_error) m, COUNT(*) n, AVG(ABS(log_error)) a FROM rti_proxy GROUP BY underlying")
        out["rti_proxy_bp"] = {r["underlying"]: {"n": r["n"], "mean_bp": (r["m"] or 0) * 1e4, "mae_bp": (r["a"] or 0) * 1e4}
                               for r in rp}
        out["lead_lag"] = self.lead_lag_report()
        out["edge_half_life"] = self.half_life_report()
        return out

    async def fast_lane(self) -> None:
        """15-minute contracts re-priced every 15 s against the live Coinbase WebSocket price: when Coinbase moves, Kalshi
        quotes can lag — stale quotes are exactly where a fast fair-value model earns (taker signals, settled honestly)."""
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("crossrail_fast")
            fast = {t for t, m in self.series_meta.items() if m.get("frequency") == "fifteen_min"}
            if fast:
                try:
                    await asyncio.wait_for(self.scan_once(only=fast), timeout=60)
                except Exception as e:
                    log.debug("fast lane: %s", e)
            await asyncio.sleep(15)

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("crossrail")
            try:
                r = await asyncio.wait_for(self.scan_once(), timeout=300)
                await asyncio.wait_for(self.settle(), timeout=120)
                self.f.db.kv_set("crossrail.scorecard", {**self.scorecard(), **self.stats, "last": r, "ts": time.time(),
                                                         "models": {p: {"sigma_min": m.sigma_min_now, "bars": m.n_bars,
                                                                        "horizons": sorted(m.cdfs)} for p, m in self.models.items()}})
            except Exception as e:
                log.warning("crossrail scan failed: %s", e)
            await asyncio.sleep(self.SCAN_S)
