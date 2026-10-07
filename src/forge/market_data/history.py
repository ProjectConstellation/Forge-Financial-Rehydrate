"""Historical candle store: Coinbase REST → Parquet (DOSSIER §9.3, §26.2).

Layout: <market_dir>/candles/interval=<s>/symbol=<SYM>.parquet (one file per symbol/interval,
rewritten atomically on update). Small (5m × 60d × 30 symbols ≈ 0.5M rows) and fast to load.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from forge.market_data.bars import COLS

if TYPE_CHECKING:
    from forge.venues.coinbase.rest import CoinbaseRest

log = logging.getLogger("forge.history")


class CandleStore:
    def __init__(self, root: Path) -> None:
        self.root = root / "candles"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, interval_s: int) -> Path:
        return self.root / f"interval={interval_s}" / f"symbol={symbol}.parquet"

    def load(self, symbol: str, interval_s: int) -> dict[str, np.ndarray] | None:
        p = self._path(symbol, interval_s)
        if not p.exists():
            return None
        t = pq.read_table(p)
        a = {c: t.column(c).to_numpy().astype(float) if c in t.column_names
             else np.full(t.num_rows, np.nan) for c in COLS}
        ts = a["ts"]
        if len(ts) > 1 and np.any(np.diff(ts) <= 0):        # defensive: never hand out time-scrambled bars
            _, idx = np.unique(ts, return_index=True)        # sorted unique timestamps (first occurrence)
            a = {c: v[idx] for c, v in a.items()}
        return a

    def save(self, symbol: str, interval_s: int, arrays: dict[str, np.ndarray]) -> None:
        p = self._path(symbol, interval_s)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        pq.write_table(pa.table({c: arrays[c] for c in COLS}), tmp, compression="zstd")
        tmp.replace(p)

    def merge(self, symbol: str, interval_s: int, new: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        old = self.load(symbol, interval_s)
        if old is not None and len(old["ts"]):
            cat = {c: np.concatenate([old[c], new[c]]) for c in COLS}
        else:
            cat = new
        ts = cat["ts"]
        # keep the LAST occurrence per timestamp (newer data wins), sorted
        _, idx = np.unique(ts[::-1], return_index=True)
        keep = len(ts) - 1 - idx
        keep = keep[np.argsort(ts[keep], kind="stable")]    # sort by TIME (was: by row position → scrambled files)
        merged = {c: cat[c][keep] for c in COLS}
        self.save(symbol, interval_s, merged)
        return merged

    def symbols(self, interval_s: int) -> list[str]:
        d = self.root / f"interval={interval_s}"
        return sorted(p.stem.split("=", 1)[1] for p in d.glob("symbol=*.parquet")) if d.exists() else []


async def backfill(rest: CoinbaseRest, store: CandleStore, symbol: str, interval_s: int, days: float,
                   end: int | None = None) -> int:
    """Fetch missing history (pages of 350 candles). Returns rows now stored."""
    end = end or int(time.time()) // interval_s * interval_s
    start = end - int(days * 86400)
    existing = await asyncio.to_thread(store.load, symbol, interval_s)   # parquet I/O off the event loop
    if existing is not None and len(existing["ts"]):
        have_lo, have_hi = int(existing["ts"].min()), int(existing["ts"].max())
        ranges = []
        if start < have_lo:
            ranges.append((start, have_lo))
        if have_hi + interval_s < end:
            ranges.append((have_hi + interval_s, end))
    else:
        ranges = [(start, end)]
    rows: list[dict] = []
    for lo, hi in ranges:
        t = lo
        page = 350 * interval_s
        while t < hi:
            t2 = min(hi, t + page)
            try:
                rows.extend(await rest.candles(symbol, t, t2, interval_s))
            except Exception as e:
                log.warning("candles %s %s [%s,%s): %s", symbol, interval_s, t, t2, e)
                await asyncio.sleep(1.0)
            t = t2
    if rows:
        arr = {
            "ts": np.array([float(r["start"]) for r in rows]),
            "open": np.array([float(r["open"]) for r in rows]),
            "high": np.array([float(r["high"]) for r in rows]),
            "low": np.array([float(r["low"]) for r in rows]),
            "close": np.array([float(r["close"]) for r in rows]),
            "volume": np.array([float(r["volume"]) for r in rows]),
            "buy_volume": np.full(len(rows), np.nan),
        }
        merged = await asyncio.to_thread(store.merge, symbol, interval_s, arr)
        return len(merged["ts"])
    return 0 if existing is None else len(existing["ts"])
