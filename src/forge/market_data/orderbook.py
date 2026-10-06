"""L2 order book with microstructure analytics (DOSSIER §10.3).

Maintained from Coinbase `l2_data` snapshot + incremental updates. Exposes the quantities the
feature engine and execution model need: microprice, depth imbalance, slippage curve for a
notional, and validity (a book becomes invalid on sequence gaps / crossed state until a fresh
snapshot arrives — DOSSIER §20.2).
"""

from __future__ import annotations

from dataclasses import dataclass

from sortedcontainers import SortedDict


@dataclass(slots=True)
class BookStats:
    bid: float
    ask: float
    mid: float
    spread_bps: float
    microprice: float
    imbalance_l1: float          # (bidsz - asksz)/(bidsz + asksz) at top
    imbalance_5: float           # depth imbalance top-5 levels (size-weighted)
    imbalance_bps25: float       # depth imbalance within ±25 bps of mid (USD-weighted)
    depth_bid_usd_50bps: float
    depth_ask_usd_50bps: float


class L2Book:
    __slots__ = ("symbol", "bids", "asks", "valid", "last_update_ns", "updates")

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.bids: SortedDict = SortedDict()   # price -> size (iterate reversed for best)
        self.asks: SortedDict = SortedDict()
        self.valid = False
        self.last_update_ns = 0
        self.updates = 0

    def apply_snapshot(self, levels: list[tuple[str, float, float]], ts_ns: int) -> None:
        self.bids.clear()
        self.asks.clear()
        self.apply_updates(levels, ts_ns)
        self.valid = self._sane()

    def apply_updates(self, levels: list[tuple[str, float, float]], ts_ns: int) -> None:
        for side, price, size in levels:
            book = self.bids if side == "bid" else self.asks
            if size <= 0:
                book.pop(price, None)
            else:
                book[price] = size
        self.last_update_ns = ts_ns
        self.updates += 1
        if self.valid and not self._sane():
            self.valid = False       # crossed/empty → require fresh snapshot

    def invalidate(self) -> None:
        self.valid = False

    def _sane(self) -> bool:
        if not self.bids or not self.asks:
            return False
        return self.bids.peekitem(-1)[0] < self.asks.peekitem(0)[0]

    def best_bid(self) -> tuple[float, float] | None:
        return self.bids.peekitem(-1) if self.bids else None

    def best_ask(self) -> tuple[float, float] | None:
        return self.asks.peekitem(0) if self.asks else None

    def stats(self) -> BookStats | None:
        if not self.valid or not self.bids or not self.asks:
            return None
        bp, bs = self.bids.peekitem(-1)
        ap, as_ = self.asks.peekitem(0)
        mid = (bp + ap) / 2
        micro = (bp * as_ + ap * bs) / (bs + as_) if (bs + as_) > 0 else mid
        b5 = sum(self.bids.peekitem(-1 - i)[1] for i in range(min(5, len(self.bids))))
        a5 = sum(self.asks.peekitem(i)[1] for i in range(min(5, len(self.asks))))
        bd25 = self._depth_usd("bid", mid * (1 - 0.0025))
        ad25 = self._depth_usd("ask", mid * (1 + 0.0025))
        return BookStats(
            bid=bp, ask=ap, mid=mid, spread_bps=(ap - bp) / mid * 1e4, microprice=micro,
            imbalance_l1=(bs - as_) / (bs + as_) if (bs + as_) > 0 else 0.0,
            imbalance_5=(b5 - a5) / (b5 + a5) if (b5 + a5) > 0 else 0.0,
            imbalance_bps25=(bd25 - ad25) / (bd25 + ad25) if (bd25 + ad25) > 0 else 0.0,
            depth_bid_usd_50bps=self._depth_usd("bid", mid * (1 - 0.005)),
            depth_ask_usd_50bps=self._depth_usd("ask", mid * (1 + 0.005)),
        )

    def _depth_usd(self, side: str, limit_price: float) -> float:
        total = 0.0
        if side == "bid":
            for p in self.bids.irange(minimum=limit_price, reverse=True):
                total += p * self.bids[p]
        else:
            for p in self.asks.irange(maximum=limit_price):
                total += p * self.asks[p]
        return total

    def sweep(self, side: str, notional_usd: float) -> tuple[float, float] | None:
        """Simulate a taker order: returns (avg_price, slippage_bps vs touch) or None if too thin."""
        levels = self.asks.items() if side == "buy" else reversed(self.bids.items())
        remaining, cost, qty, touch = notional_usd, 0.0, 0.0, None
        for p, s in levels:
            touch = touch or p
            take = min(remaining, p * s)
            cost += take
            qty += take / p
            remaining -= take
            if remaining <= 1e-9:
                break
        if remaining > 1e-9 or qty == 0 or touch is None:
            return None
        avg = cost / qty
        slip = (avg - touch) / touch * 1e4 if side == "buy" else (touch - avg) / touch * 1e4
        return avg, slip

    def top(self, n: int = 10) -> dict[str, list[tuple[float, float]]]:
        return {
            "bids": [self.bids.peekitem(-1 - i) for i in range(min(n, len(self.bids)))],
            "asks": [self.asks.peekitem(i) for i in range(min(n, len(self.asks)))],
        }
