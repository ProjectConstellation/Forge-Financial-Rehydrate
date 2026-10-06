"""Coinbase Advanced Trade market-data WebSocket (verified live 2026-10-06).

- One subscription message per channel, spaced, each with a fresh ES256 JWT when credentials exist
  (level2/candles require auth; ticker/market_trades/heartbeats work without).
- Message channels: ticker, market_trades, l2_data, candles (5m), heartbeats, subscriptions.
- `sequence_num` is per-connection and monotonically increasing: a gap invalidates all books and
  forces a reconnect (fresh snapshots) — DOSSIER §20.2.
- Reconnect with exponential backoff + jitter; silence watchdog.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
import time
from collections.abc import Callable
from datetime import datetime

import websockets

from forge.domain.market import BestBidAsk, Candle, TradeTick
from forge.market_data.quality import FeedQuality
from forge.venues.coinbase.auth import CdpSigner

log = logging.getLogger("forge.coinbase.ws")

VENUE = "coinbase"


def parse_ts_ns(s: str) -> int:
    """RFC3339 with up to 9 fractional digits → ns."""
    if not s:
        return time.time_ns()
    s = s.replace("Z", "")
    if "." in s:
        base, frac = s.split(".", 1)
        frac = "".join(ch for ch in frac if ch.isdigit())[:9].ljust(9, "0")
    else:
        base, frac = s, "0" * 9
    dt = datetime.fromisoformat(base + "+00:00")
    return int(dt.timestamp()) * 1_000_000_000 + int(frac)


class MarketSink:
    """Callbacks invoked synchronously by the stream (must be fast; no awaits)."""

    def on_bbo(self, b: BestBidAsk) -> None: ...
    def on_trade(self, t: TradeTick) -> None: ...
    def on_book_snapshot(self, symbol: str, levels: list[tuple[str, float, float]], ts_ns: int) -> None: ...
    def on_book_update(self, symbol: str, levels: list[tuple[str, float, float]], ts_ns: int) -> None: ...
    def on_candle(self, c: Candle) -> None: ...
    def on_feed_reset(self) -> None: ...


class CoinbaseMarketStream:
    def __init__(self, symbols: list[str], sink: MarketSink, signer: CdpSigner | None = None,
                 url: str = "wss://advanced-trade-ws.coinbase.com", level2: bool = True,
                 silence_timeout_s: float = 15.0) -> None:
        self.symbols = list(dict.fromkeys(symbols))
        self.sink = sink
        self.signer = signer
        self.url = url
        self.level2 = level2 and signer is not None
        self.silence_timeout_s = silence_timeout_s
        self.quality = FeedQuality()
        self._stop = asyncio.Event()
        self._resubscribe = asyncio.Event()
        self._last_seq = -1
        self.on_status: Callable[[str], None] | None = None

    def set_symbols(self, symbols: list[str]) -> None:
        new = list(dict.fromkeys(symbols))
        if set(new) != set(self.symbols):
            self.symbols = new
            self._resubscribe.set()      # reconnect with the new universe

    def stop(self) -> None:
        self._stop.set()

    def _channels(self) -> list[str]:
        ch = ["heartbeats", "ticker", "market_trades"]
        if self.signer is not None:
            ch.append("candles")
        if self.level2:
            ch.append("level2")
        return ch

    async def run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                await self._session()
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as e:  # network errors, protocol errors
                log.warning("coinbase ws session ended: %s: %s", type(e).__name__, e)
            finally:
                if self.quality.connected:
                    self.quality.connected = False
                self.sink.on_feed_reset()
            if self._stop.is_set():
                break
            self.quality.reconnects += 1
            delay = min(30.0, backoff) * (0.5 + random.random())
            backoff *= 2
            await asyncio.sleep(delay)

    async def _session(self) -> None:
        self._resubscribe.clear()
        async with websockets.connect(self.url, max_size=2 ** 25, open_timeout=15,
                                      ping_interval=20, ping_timeout=20, close_timeout=5) as ws:
            self._last_seq = -1
            for ch in self._channels():
                msg: dict[str, object] = {"type": "subscribe", "product_ids": self.symbols, "channel": ch}
                if self.signer is not None:
                    msg["jwt"] = self.signer.ws_jwt()
                await ws.send(json.dumps(msg))
                await asyncio.sleep(0.25)
            self.quality.connected = True
            self.quality.connected_since_ns = time.time_ns()
            if self.on_status:
                self.on_status("connected")
            while not self._stop.is_set() and not self._resubscribe.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=self.silence_timeout_s)
                except TimeoutError:
                    log.warning("coinbase ws silent for %.0fs — reconnecting", self.silence_timeout_s)
                    return
                if not self._handle(raw):
                    return

    def _handle(self, raw: str | bytes) -> bool:
        """Process one message. Returns False to force a reconnect (sequence gap)."""
        now = time.time_ns()
        q = self.quality
        q.messages += 1
        q.last_message_ns = now
        try:
            m = json.loads(raw)
        except ValueError:
            q.parse_errors += 1
            return True
        seq = m.get("sequence_num")
        if isinstance(seq, int):
            if self._last_seq >= 0 and seq != self._last_seq + 1:
                q.sequence_gaps += 1
                log.warning("sequence gap %s -> %s; invalidating books", self._last_seq, seq)
                self._last_seq = seq
                return False
            self._last_seq = seq
        ch = m.get("channel")
        try:
            if ch == "ticker":
                self._on_ticker(m, now)
            elif ch == "market_trades":
                self._on_trades(m, now)
            elif ch == "l2_data":
                self._on_l2(m, now)
            elif ch == "candles":
                self._on_candles(m)
            elif ch == "heartbeats":
                q.last_heartbeat_ns = now
            elif m.get("type") == "error":
                log.error("coinbase ws error: %s", str(m)[:300])
        except (KeyError, ValueError, TypeError):
            q.parse_errors += 1
        return True

    def _on_ticker(self, m: dict, now: int) -> None:
        ts = parse_ts_ns(m.get("timestamp", ""))
        for ev in m.get("events", []):
            for t in ev.get("tickers", []):
                bid, ask = float(t["best_bid"] or 0), float(t["best_ask"] or 0)
                if bid <= 0 or ask <= 0:
                    continue
                sym = t["product_id"]
                sq = self.quality.sym(sym)
                if bid >= ask:
                    sq.crossed += 1
                    continue
                sq.last_tick_ns = now
                lag = (now - ts) / 1e6
                sq.exchange_lag_ms = 0.9 * sq.exchange_lag_ms + 0.1 * lag if sq.exchange_lag_ms else lag
                self.sink.on_bbo(BestBidAsk(VENUE, sym, bid, float(t["best_bid_quantity"] or 0), ask,
                                            float(t["best_ask_quantity"] or 0), ts, now))

    def _on_trades(self, m: dict, now: int) -> None:
        for ev in m.get("events", []):
            if ev.get("type") == "snapshot":
                continue          # historical backfill; avoid double-counting flow
            for t in reversed(ev.get("trades", [])):
                sym = t["product_id"]
                self.quality.sym(sym).last_trade_ns = now
                side = t.get("side", "").lower()
                # Coinbase market_trades `side` is the maker side; aggressor is the opposite.
                aggressor = {"buy": "sell", "sell": "buy"}.get(side, "unknown")
                self.sink.on_trade(TradeTick(VENUE, sym, float(t["price"]), float(t["size"]), aggressor,  # type: ignore[arg-type]
                                             parse_ts_ns(t.get("time", "")), now, str(t.get("trade_id", ""))))

    def _on_l2(self, m: dict, now: int) -> None:
        for ev in m.get("events", []):
            sym = ev["product_id"]
            levels = [(u["side"] if u["side"] == "bid" else "ask", float(u["price_level"]),
                       float(u["new_quantity"])) for u in ev.get("updates", [])]
            self.quality.sym(sym).last_book_ns = now
            if ev.get("type") == "snapshot":
                self.sink.on_book_snapshot(sym, levels, now)
            else:
                self.sink.on_book_update(sym, levels, now)

    def _on_candles(self, m: dict) -> None:
        for ev in m.get("events", []):
            for c in ev.get("candles", []):
                self.sink.on_candle(Candle(VENUE, c["product_id"], 300, int(c["start"]), float(c["open"]),
                                           float(c["high"]), float(c["low"]), float(c["close"]),
                                           float(c["volume"])))

    async def aclose(self) -> None:
        self.stop()
        with contextlib.suppress(Exception):
            pass
