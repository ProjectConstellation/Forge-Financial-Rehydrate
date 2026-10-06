"""Venue-agnostic market contracts (DOSSIER §9.1, DIRECTIVE §11).

Hot-path events are frozen slotted dataclasses (cheap); prices are floats on the hot path for
feature math, while anything that touches money (orders, ledger) uses Decimal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Literal

Side = Literal["buy", "sell"]


@dataclass(frozen=True, slots=True)
class TradeTick:
    venue: str
    symbol: str
    price: float
    size: float
    side: Literal["buy", "sell", "unknown"]   # aggressor side
    exchange_ts_ns: int
    recv_ts_ns: int
    trade_id: str = ""


@dataclass(frozen=True, slots=True)
class BestBidAsk:
    venue: str
    symbol: str
    bid: float
    bid_size: float
    ask: float
    ask_size: float
    exchange_ts_ns: int
    recv_ts_ns: int

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread_bps(self) -> float:
        m = self.mid
        return (self.ask - self.bid) / m * 1e4 if m > 0 else float("inf")


@dataclass(frozen=True, slots=True)
class Candle:
    venue: str
    symbol: str
    interval_s: int
    start_ts: int          # unix seconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    buy_volume: float = -1.0   # -1 = unknown (e.g. REST candles)


@dataclass(frozen=True, slots=True)
class BookLevel:
    price: float
    size: float


@dataclass(slots=True)
class MarketRules:
    venue: str
    symbol: str
    base: str
    quote: str
    base_increment: Decimal
    quote_increment: Decimal
    base_min_size: Decimal
    quote_min_size: Decimal
    price_increment: Decimal
    trading_enabled: bool = True
    post_only_only: bool = False
    limit_only: bool = False
    cancel_only: bool = False
    status: str = "online"

    def round_base(self, size: Decimal) -> Decimal:
        return _floor_to(size, self.base_increment)

    def round_quote(self, notional: Decimal) -> Decimal:
        return _floor_to(notional, self.quote_increment)

    def round_price(self, price: Decimal, side: Side) -> Decimal:
        # buy limits round down (never pay more), sell limits round up (never sell cheaper)
        inc = self.price_increment
        q = (price / inc)
        q = q.to_integral_value(rounding=ROUND_DOWN if side == "buy" else "ROUND_CEILING")
        return (q * inc).quantize(inc)

    def tradable(self) -> bool:
        return self.trading_enabled and not self.cancel_only and self.status == "online"


def _floor_to(x: Decimal, inc: Decimal) -> Decimal:
    if inc <= 0:
        return x
    return ((x / inc).to_integral_value(rounding=ROUND_DOWN) * inc).quantize(inc)


def d(x: float | str | int | Decimal) -> Decimal:
    """Convert to Decimal safely (floats via repr to avoid binary noise)."""
    if isinstance(x, Decimal):
        return x
    if isinstance(x, float):
        return Decimal(repr(x))
    return Decimal(x)


def usd(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


@dataclass(slots=True)
class Balance:
    asset: str
    available: Decimal
    hold: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.available + self.hold


@dataclass(slots=True)
class ProductInfo:
    """Universe-selection snapshot of a product (from venue product list)."""
    venue: str
    symbol: str
    base: str
    quote: str
    price: float
    volume_24h_quote: float
    change_24h_pct: float
    rules: MarketRules
    extra: dict[str, object] = field(default_factory=dict)
