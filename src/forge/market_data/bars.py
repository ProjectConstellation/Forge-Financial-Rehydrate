"""Bar series (columnar numpy ring buffers) + live trade→bar aggregation.

The same column layout is used for historical data (Parquet → arrays) and for live bars, so the
feature engine runs identical code in research and production (no train/serve skew).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

COLS = ("ts", "open", "high", "low", "close", "volume", "buy_volume")


class BarSeries:
    """Fixed-capacity columnar bar buffer. `ts` = bar start (unix seconds)."""

    def __init__(self, interval_s: int, capacity: int = 2000) -> None:
        self.interval_s = interval_s
        self.capacity = capacity
        self.n = 0
        self._a = {c: np.full(capacity, np.nan) for c in COLS}

    @classmethod
    def from_arrays(cls, interval_s: int, arrays: dict[str, np.ndarray], capacity: int | None = None) -> BarSeries:
        n = len(arrays["ts"])
        bs = cls(interval_s, capacity or max(n, 16))
        k = min(n, bs.capacity)
        for c in COLS:
            src = arrays.get(c)
            if src is None:
                src = np.full(n, np.nan if c == "buy_volume" else 0.0)
            bs._a[c][:k] = np.asarray(src, dtype=float)[-k:]
        bs.n = k
        return bs

    def append(self, ts: int, o: float, h: float, low: float, c: float, v: float, bv: float = np.nan) -> None:
        if self.n and ts <= self._a["ts"][self.n - 1]:
            if ts == self._a["ts"][self.n - 1]:       # update of the last (forming) bar
                i = self.n - 1
                self._a["high"][i] = max(self._a["high"][i], h)
                self._a["low"][i] = min(self._a["low"][i], low)
                self._a["close"][i], self._a["volume"][i], self._a["buy_volume"][i] = c, v, bv
            return
        if self.n == self.capacity:                    # shift left by 25% (amortized O(1))
            k = self.capacity // 4
            for col in COLS:
                a = self._a[col]
                a[:-k] = a[k:]
                a[-k:] = np.nan
            self.n -= k
        i = self.n
        for col, val in zip(COLS, (ts, o, h, low, c, v, bv), strict=True):
            self._a[col][i] = val
        self.n += 1

    def arrays(self) -> dict[str, np.ndarray]:
        return {c: self._a[c][: self.n] for c in COLS}

    def last(self, col: str) -> float:
        return float(self._a[col][self.n - 1]) if self.n else float("nan")

    def __len__(self) -> int:
        return self.n


@dataclass
class _Forming:
    start: int
    o: float
    h: float
    low: float
    c: float
    v: float = 0.0
    bv: float = 0.0


class TradeBarAggregator:
    """Builds closed bars of `interval_s` from trade ticks (aggressor-signed volume included)."""

    def __init__(self, interval_s: int = 60) -> None:
        self.interval_s = interval_s
        self._f: dict[str, _Forming] = {}

    def on_trade(self, symbol: str, ts_s: float, price: float, size: float, aggressor: str) -> list[tuple]:
        """Returns a list of closed bars (symbol, start, o, h, l, c, v, buy_v) — usually empty."""
        start = int(ts_s // self.interval_s) * self.interval_s
        f = self._f.get(symbol)
        closed: list[tuple] = []
        if f is None:
            self._f[symbol] = _Forming(start, price, price, price, price)
            f = self._f[symbol]
        elif start > f.start:
            closed.append((symbol, f.start, f.o, f.h, f.low, f.c, f.v, f.bv))
            self._f[symbol] = f = _Forming(start, price, price, price, price)
        elif start < f.start:
            return closed                               # late trade from a closed bar — ignore
        f.h = max(f.h, price)
        f.low = min(f.low, price)
        f.c = price
        f.v += size
        if aggressor == "buy":
            f.bv += size
        return closed

    def flush_due(self, now_s: float) -> list[tuple]:
        """Close bars whose interval has ended even if no new trade arrived (quiet markets)."""
        out = []
        for sym, f in list(self._f.items()):
            if now_s >= f.start + self.interval_s + 2:
                out.append((sym, f.start, f.o, f.h, f.low, f.c, f.v, f.bv))
                nxt = int(now_s // self.interval_s) * self.interval_s
                self._f[sym] = _Forming(nxt, f.c, f.c, f.c, f.c)
        return out


def resample(arrays: dict[str, np.ndarray], from_s: int, to_s: int) -> dict[str, np.ndarray]:
    """Aggregate bars to a coarser interval (complete buckets only)."""
    if to_s % from_s:
        raise ValueError("target interval must be a multiple")
    ts = arrays["ts"].astype(np.int64)
    if len(ts) == 0:
        return {c: np.array([]) for c in COLS}
    bucket = ts // to_s * to_s
    idx = np.flatnonzero(np.diff(bucket)) + 1
    starts = np.concatenate([[0], idx])
    ends = np.concatenate([idx, [len(ts)]])
    per = to_s // from_s
    full = (ends - starts) == per
    bv = arrays.get("buy_volume", np.full(len(ts), np.nan))
    hi = np.maximum.reduceat(arrays["high"], starts)
    lo = np.minimum.reduceat(arrays["low"], starts)
    vol = np.add.reduceat(arrays["volume"], starts)
    bvs = np.add.reduceat(bv, starts)
    return {
        "ts": bucket[starts][full].astype(float),
        "open": arrays["open"][starts][full],
        "high": hi[full],
        "low": lo[full],
        "close": arrays["close"][ends - 1][full],
        "volume": vol[full],
        "buy_volume": bvs[full],
    }
