"""Simple multi-asset regime labels for PAPER rotation (no external creds)."""
from __future__ import annotations

import logging
import math
import time
from typing import Any

log = logging.getLogger("forge.regime")


class RegimeDetector:
    def __init__(self, forge: Any):
        self.f = forge

    def _tick(self) -> None:
        regimes: dict[str, Any] = {}
        # Prefer live in-memory bar engines
        bars = getattr(self.f, "bars", None) or {}
        for interval, eng in list(bars.items())[:3]:
            state = getattr(eng, "state", None) or {}
            for sym, ss in list(state.items())[:80]:
                try:
                    closes = list(getattr(ss, "close", None) or getattr(ss, "closes", None) or [])
                    if not closes and hasattr(ss, "df"):
                        closes = list(ss.df["close"].tail(120).astype(float))
                    if len(closes) < 20:
                        # try last price path
                        px = float(getattr(ss, "last", 0) or getattr(ss, "price", 0) or 0)
                        if px <= 0:
                            continue
                        closes = [px]
                    closes = [float(x) for x in closes[-120:]]
                    if len(closes) < 8:
                        label = str(getattr(ss, "regime", None) or "unknown")
                        regimes[str(sym)] = {"label": label, "vol": None, "trend_3d": None, "n": len(closes), "src": "engine"}
                        continue
                    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]]
                    if len(rets) < 5:
                        continue
                    mean = sum(rets) / len(rets)
                    var = sum((x - mean) ** 2 for x in rets) / max(1, len(rets) - 1)
                    vol = math.sqrt(var)
                    trend = (closes[-1] / closes[0] - 1.0) if closes[0] else 0.0
                    # Prefer engine regime label when present
                    eng_lab = str(getattr(ss, "regime", "") or "")
                    if eng_lab and eng_lab not in ("UNKNOWN", "None"):
                        label = eng_lab
                    elif vol > 0.04:
                        label = "high_vol"
                    elif abs(trend) < 0.01:
                        label = "range"
                    elif trend > 0.03:
                        label = "bull_trend"
                    elif trend < -0.03:
                        label = "bear_trend"
                    else:
                        label = "mild_trend"
                    regimes[str(sym)] = {"label": label, "vol": round(vol, 5), "trend_3d": round(trend, 4), "n": len(rets)}
                except Exception:
                    continue
            if regimes:
                break
        labels = [v["label"] for v in regimes.values()]
        dominant = max(set(labels), key=labels.count) if labels else "unknown"
        bias_map = {
            "high_vol": ["mean_reversion", "inventory", "microstructure"],
            "range": ["mean_reversion", "stable_triangle", "carry_proxy"],
            "RANGE_LOW_VOL": ["mean_reversion", "stable_triangle", "carry_proxy"],
            "RANGE_HIGH_VOL": ["mean_reversion", "inventory", "microstructure"],
            "bull_trend": ["trend_pullback", "momentum", "cross_asset"],
            "TREND_UP": ["trend_pullback", "momentum", "cross_asset"],
            "bear_trend": ["trend_pullback", "event_driven", "inventory"],
            "TREND_DOWN": ["event_driven", "inventory", "mean_reversion"],
            "mild_trend": ["trend_pullback", "mean_reversion", "cross_asset"],
            "unknown": ["mean_reversion", "trend_pullback", "microstructure"],
            "UNKNOWN": ["mean_reversion", "trend_pullback", "microstructure"],
        }
        out = {
            "ts": time.time(),
            "dominant": dominant,
            "n_symbols": len(regimes),
            "by_symbol": dict(list(regimes.items())[:40]),
            "paper_bias": bias_map.get(dominant, ["mean_reversion", "trend_pullback", "microstructure"]),
        }
        self.f.db.kv_set("lab.regime", out)

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("regime")
            try:
                await asyncio.to_thread(self._tick)
            except Exception as e:
                log.warning("regime: %s", e)
            await asyncio.sleep(1200)
