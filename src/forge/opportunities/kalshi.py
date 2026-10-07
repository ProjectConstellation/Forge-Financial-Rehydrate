"""Kalshi read-only discovery client (official public REST API; no credentials, no order capability).

Kalshi is the exchange behind Coinbase prediction markets. FORGE uses only the documented public market-data endpoints
here; trading requires an operator-provided Kalshi API key and is NOT implemented in this module (shadow first).

Fees (verified 2026-10-07 against docs.kalshi.com/getting_started/fee_rounding worked example):
  taker trade fee = ceil_6dp(0.07 × fee_multiplier × contracts × P × (1 − P))   [fee_type "quadratic*"]
  maker fee: only for fee_type "quadratic_with_maker_fees" — coefficient 0.0175 (Kalshi fee schedule; re-verify on first fills)
  non-direct (FCM/Coinbase-cleared) members pay an extra rounding fee to the cent → modelled as +$0.01 per order worst case.
The fee_type / fee_multiplier are read per series at runtime (never hard-coded per market).
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from typing import Any

import httpx

BASE = "https://api.elections.kalshi.com/trade-api/v2"
TAKER_COEF = 0.07
MAKER_COEF = 0.0175


def kalshi_fee(price: float, contracts: float = 1.0, fee_type: str = "quadratic", multiplier: float = 1.0,
               maker: bool = False, rounding_cents: bool = True) -> float:
    """Fee in dollars for `contracts` at `price` (0..1)."""
    if maker and "maker" not in (fee_type or ""):
        return 0.0
    coef = MAKER_COEF if maker else TAKER_COEF
    raw = coef * multiplier * contracts * price * (1.0 - price)
    fee = math.ceil(raw * 1e6 - 1e-6) / 1e6                 # ceil to $0.000001 (epsilon guards float noise)
    if rounding_cents:                                  # FCM-cleared balances align to the cent
        fee = math.ceil(fee * 100 - 1e-9) / 100
    return fee


@dataclass
class KalshiMarket:
    ticker: str
    event_ticker: str
    series: str
    strike_type: str            # greater | less | between | ...
    floor: float | None
    cap: float | None
    close_ts: float
    yes_bid: float | None
    yes_ask: float | None
    yes_bid_size: float
    yes_ask_size: float
    volume_24h: float
    open_interest: float
    status: str
    result: str

    @property
    def no_ask(self) -> float | None:
        return None if self.yes_bid is None else 1.0 - self.yes_bid

    @property
    def no_bid(self) -> float | None:
        return None if self.yes_ask is None else 1.0 - self.yes_ask


def _f(x: Any) -> float | None:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _ts(s: str | None) -> float:
    if not s:
        return 0.0
    from datetime import datetime
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def parse_market(m: dict[str, Any], series: str) -> KalshiMarket:
    yb, ya = _f(m.get("yes_bid_dollars")), _f(m.get("yes_ask_dollars"))
    return KalshiMarket(
        ticker=m["ticker"], event_ticker=m.get("event_ticker", ""), series=series, strike_type=m.get("strike_type") or "",
        floor=_f(m.get("floor_strike")), cap=_f(m.get("cap_strike")), close_ts=_ts(m.get("close_time")),
        yes_bid=yb if yb and yb > 0 else None, yes_ask=ya if ya and 0 < ya < 1 else None,
        yes_bid_size=_f(m.get("yes_bid_size_fp")) or 0.0, yes_ask_size=_f(m.get("yes_ask_size_fp")) or 0.0,
        volume_24h=_f(m.get("volume_24h_fp")) or 0.0, open_interest=_f(m.get("open_interest_fp")) or 0.0,
        status=m.get("status", ""), result=m.get("result") or "")


class KalshiPublic:
    """Rate-limited (≤ ~4 req/s), timeout-bounded public client."""

    def __init__(self, base: str = BASE, min_interval_s: float = 0.25) -> None:
        self.base = base
        self._client = httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "FORGE/1.0 (read-only discovery)"})
        self._gap = min_interval_s
        self._last = 0.0
        self._lock = asyncio.Lock()
        self.calls = 0
        self.errors = 0

    async def close(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self._lock:
            wait = self._last + self._gap - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()
        self.calls += 1
        try:
            r = await self._client.get(self.base + path, params=params)
            r.raise_for_status()
            return r.json()
        except Exception:
            self.errors += 1
            raise

    async def exchange_status(self) -> dict[str, Any]:
        return await self.get("/exchange/status")

    async def series(self) -> list[dict[str, Any]]:
        return (await self.get("/series", {"limit": 1000})).get("series", [])

    async def open_events(self, series: str, limit: int = 3) -> list[dict[str, Any]]:
        d = await self.get("/events", {"series_ticker": series, "status": "open", "limit": limit,
                                       "with_nested_markets": "true"})
        return d.get("events", [])

    async def market(self, ticker: str) -> dict[str, Any]:
        return (await self.get(f"/markets/{ticker}")).get("market", {})
