"""Live market service (DOSSIER §9, DIRECTIVE §11; OP-005 always-live).

- WebSocket → BBO, L2 books, trade flow (microstructure, execution, paper fills)
- REST candles → guaranteed-complete bars at each interval boundary (feature/strategy clock)
- Liquidity-aware dynamic universe (DOSSIER §20.3)
Bars, features and regimes are computed with exactly the same code as research (no train/serve skew).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from forge.domain.market import BestBidAsk, Candle, MarketRules, ProductInfo, TradeTick
from forge.features.engine import add_cross_asset, add_market_features, compute_features
from forge.market_data.bars import BarSeries
from forge.market_data.history import CandleStore
from forge.market_data.orderbook import L2Book
from forge.regime.engine import latest_regime, regime_probs
from forge.venues.coinbase.rest import CoinbaseRest
from forge.venues.coinbase.ws import MarketSink

log = logging.getLogger("forge.live")

STABLE = {"USDT", "USDC", "DAI", "PYUSD", "EURC", "GUSD", "PAX", "USDS", "FDUSD", "TUSD", "RLUSD", "USD1",
          "WBTC", "CBBTC", "CBETH", "WETH", "STETH", "LSETH", "MSOL", "JITOSOL"}


@dataclass
class FlowWindow:
    trades: deque = field(default_factory=lambda: deque(maxlen=5000))   # (ts_s, signed_usd)

    def add(self, ts: float, usd: float, aggressor: str) -> None:
        self.trades.append((ts, usd if aggressor == "buy" else -usd if aggressor == "sell" else 0.0))

    def stats(self, now: float, window: float = 60.0) -> tuple[float, float]:
        while self.trades and now - self.trades[0][0] > 600:
            self.trades.popleft()
        recent = [x for t, x in self.trades if now - t <= window]
        if not recent:
            return 0.0, 0.0
        gross = sum(abs(x) for x in recent)
        return (sum(recent) / gross if gross else 0.0), len(recent) / window


def select_universe(products: list[ProductInfo], max_n: int, min_volume_usd: float,
                    must_include: set[str] | None = None) -> list[str]:
    elig = [p for p in products if p.quote == "USD" and p.base not in STABLE and p.rules.tradable()
            and p.volume_24h_quote >= min_volume_usd]
    elig.sort(key=lambda p: p.volume_24h_quote, reverse=True)
    out = [p.symbol for p in elig[:max_n]]
    for s in sorted(must_include or set()):
        if s not in out:
            out.append(s)
    if "BTC-USD" not in out:
        out.insert(0, "BTC-USD")                    # benchmark for cross-asset features
    return out


class LiveMarket(MarketSink):
    """Synchronous sink for the WS stream + views used by risk/execution/paper venue."""

    def __init__(self) -> None:
        self.bbo: dict[str, BestBidAsk] = {}
        self.books: dict[str, L2Book] = {}
        self.flow: dict[str, FlowWindow] = {}
        self.rules: dict[str, MarketRules] = {}
        self.products: dict[str, ProductInfo] = {}
        self.last_trade: dict[str, float] = {}
        self.listeners: list[Callable[[str, float | None], None]] = []

    # sink callbacks
    def on_bbo(self, b: BestBidAsk) -> None:
        self.bbo[b.symbol] = b
        for fn in self.listeners:
            fn(b.symbol, None)

    def on_trade(self, t: TradeTick) -> None:
        self.flow.setdefault(t.symbol, FlowWindow()).add(t.recv_ts_ns / 1e9, t.price * t.size, t.side)
        self.last_trade[t.symbol] = t.price
        for fn in self.listeners:
            fn(t.symbol, t.price)

    def on_book_snapshot(self, symbol: str, levels: list[tuple[str, float, float]], ts_ns: int) -> None:
        self.books.setdefault(symbol, L2Book(symbol)).apply_snapshot(levels, ts_ns)

    def on_book_update(self, symbol: str, levels: list[tuple[str, float, float]], ts_ns: int) -> None:
        bk = self.books.get(symbol)
        if bk is not None:
            bk.apply_updates(levels, ts_ns)

    def on_candle(self, c: Candle) -> None:
        pass

    def on_feed_reset(self, symbols: list[str] | None = None) -> None:
        for s, bk in self.books.items():
            if symbols is None or s in symbols:
                bk.invalidate()

    # views
    def get_bbo(self, s: str) -> BestBidAsk | None:
        return self.bbo.get(s)

    def get_book(self, s: str) -> L2Book | None:
        return self.books.get(s)

    def get_rules(self, s: str) -> MarketRules | None:
        return self.rules.get(s)

    def marks(self) -> dict[str, float]:
        return {s: b.mid for s, b in self.bbo.items()}

    def fresh(self, s: str, stale_ms: int) -> bool:
        b = self.bbo.get(s)
        return b is not None and (time.time_ns() - b.recv_ts_ns) / 1e6 <= stale_ms

    def micro(self, s: str) -> dict[str, float]:
        out = {k: float("nan") for k in ("spread_bps", "imb_l1", "imb_5", "imb_25bps", "micro_disp_bps",
                                         "depth_50bps_usd", "flow_imb_60s", "trade_rate_60s")}
        b = self.bbo.get(s)
        if b:
            out["spread_bps"] = b.spread_bps
        bk = self.books.get(s)
        st = bk.stats() if bk else None
        if st:
            out.update(spread_bps=st.spread_bps, imb_l1=st.imbalance_l1, imb_5=st.imbalance_5,
                       imb_25bps=st.imbalance_bps25, micro_disp_bps=(st.microprice - st.mid) / st.mid * 1e4,
                       depth_50bps_usd=min(st.depth_bid_usd_50bps, st.depth_ask_usd_50bps))
        fl = self.flow.get(s)
        if fl:
            out["flow_imb_60s"], out["trade_rate_60s"] = fl.stats(time.time())
        return out


@dataclass
class SymbolState:
    symbol: str
    series: BarSeries
    features: dict[str, np.ndarray] = field(default_factory=dict)
    probs: dict[str, np.ndarray] = field(default_factory=dict)
    regime: str = "UNKNOWN"
    regime_dist: dict[str, float] = field(default_factory=dict)
    regime_conf: float = 0.0
    updated: float = 0.0


class BarEngine:
    """Keeps complete bars per (interval, symbol) fresh via REST, computes features + regimes on close."""

    def __init__(self, rest: CoinbaseRest, store: CandleStore, interval_s: int, window: int = 1200,
                 on_close: Callable[[int, list[str]], Awaitable[None]] | None = None) -> None:
        self.rest, self.store, self.interval_s, self.window = rest, store, interval_s, window
        self.state: dict[str, SymbolState] = {}
        self.on_close = on_close
        self.last_close_ts = 0
        self.refreshes = 0

    def load_history(self, symbols: list[str]) -> None:
        for s in symbols:
            if s in self.state:
                continue
            arr = self.store.load(s, self.interval_s)
            ser = BarSeries.from_arrays(self.interval_s, arr, capacity=self.window * 2) if arr is not None \
                else BarSeries(self.interval_s, self.window * 2)
            self.state[s] = SymbolState(s, ser)

    async def refresh(self, symbols: list[str]) -> list[str]:
        """Fetch the latest complete bars; returns symbols that got a new closed bar."""
        self.load_history(symbols)
        now = int(time.time())
        last_complete = now // self.interval_s * self.interval_s - self.interval_s
        updated = []
        for s in symbols:
            st = self.state.get(s)
            if st is None:                                   # removed concurrently (data healing rebuild) → reload, next pass
                self.load_history([s])
                continue
            have = int(st.series.last("ts")) if len(st.series) else 0
            if have >= last_complete:
                continue
            start = max(have + self.interval_s, last_complete - self.interval_s * 300)
            try:
                rows = await self.rest.candles(s, start, last_complete + self.interval_s, self.interval_s)
            except Exception as e:
                log.warning("candle refresh %s: %s", s, e)
                continue
            for r in rows:
                ts = int(r["start"])
                if ts <= last_complete:
                    st.series.append(ts, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]),
                                     float(r["volume"]))
            if int(st.series.last("ts")) > have:
                updated.append(s)
        self.refreshes += 1
        if updated:
            self.recompute(updated)
            self.last_close_ts = last_complete
        return updated

    def recompute(self, symbols: list[str]) -> None:
        bench = self.state.get("BTC-USD")
        btc = bench.series.arrays() if bench and len(bench.series) else None
        for s in symbols:
            st = self.state.get(s)
            if st is None or len(st.series) < 300:
                continue
            arr = {k: v[-self.window:] for k, v in st.series.arrays().items()}
            f = compute_features(arr, self.interval_s)
            if btc is not None and s != "BTC-USD":
                add_cross_asset(f, arr, {k: v[-self.window * 2:] for k, v in btc.items()})
            st.features = f
            st.updated = time.time()
        live = {s: (dict((k, v[-self.window:]) for k, v in st.series.arrays().items()), st.features)
                for s, st in self.state.items() if st.features and len(st.series) >= 300}
        add_market_features(live, horizon=288 if self.interval_s <= 300 else 24)
        for s in symbols:
            st = self.state.get(s)
            if st is None or not st.features:
                continue
            p = regime_probs(st.features)
            st.probs = p
            st.regime, st.regime_dist, st.regime_conf = latest_regime(p)

    def persist(self) -> None:
        for s, st in self.state.items():
            if len(st.series):
                self.store.merge(s, self.interval_s, st.series.arrays())

    async def run(self, symbols_fn: Callable[[], list[str]], stop: asyncio.Event,
                  beat: Callable[[], None] | None = None) -> None:
        while not stop.is_set():
            if beat:
                beat()
            now = time.time()
            nxt = (int(now) // self.interval_s + 1) * self.interval_s + 8      # 8s after the boundary
            try:
                await asyncio.wait_for(stop.wait(), timeout=max(1.0, nxt - now))
                break
            except TimeoutError:
                pass
            syms = symbols_fn()
            updated = await asyncio.wait_for(self.refresh(syms), timeout=max(120, self.interval_s // 2))
            if beat:
                beat()
            if updated and self.on_close:
                await self.on_close(self.interval_s, updated)
            if self.refreshes % 12 == 0:
                await asyncio.to_thread(self.persist)


def market_dir(home: Path) -> Path:
    return home / "market"
