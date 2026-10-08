"""Multi-asset regime labels for PAPER rotation — reads live BarEngine state."""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.regime")


class RegimeDetector:
    def __init__(self, forge: Any):
        self.f = forge

    def _tick(self) -> None:
        regimes: dict[str, Any] = {}
        bars = getattr(self.f, "bars", None) or {}
        for interval, eng in bars.items():
            state = getattr(eng, "state", None) or {}
            for sym, ss in state.items():
                try:
                    label = str(getattr(ss, "regime", None) or "UNKNOWN")
                    conf = float(getattr(ss, "regime_conf", 0) or 0)
                    closes = []
                    series = getattr(ss, "series", None)
                    if series is not None:
                        c = getattr(series, "close", None) or getattr(series, "closes", None)
                        if c is not None:
                            try:
                                closes = list(c)[-80:]
                            except Exception:
                                closes = []
                    regimes[str(sym)] = {
                        "label": label,
                        "conf": round(conf, 3),
                        "n": len(closes),
                        "interval": int(interval) if not isinstance(interval, int) else interval,
                    }
                except Exception:
                    continue
            if len(regimes) >= 10:
                break
        labels = [v["label"] for v in regimes.values() if v.get("label") and v["label"] != "UNKNOWN"]
        dominant = max(set(labels), key=labels.count) if labels else "UNKNOWN"
        bias_map = {
            "high_vol": ["mean_reversion", "inventory", "microstructure"],
            "RANGE_LOW_VOL": ["mean_reversion", "stable_triangle", "carry_proxy"],
            "RANGE_HIGH_VOL": ["mean_reversion", "inventory", "microstructure"],
            "TREND_UP": ["trend_pullback", "momentum", "cross_asset"],
            "TREND_DOWN": ["event_driven", "inventory", "mean_reversion"],
            "BREAKOUT_EXPANSION": ["breakout", "momentum", "volatility"],
            "PANIC_SELLING": ["liquidity_provision", "mean_reversion", "inventory"],
            "EUPHORIA_BUYING": ["momentum", "trend_pullback", "breakout"],
            "UNKNOWN": ["mean_reversion", "trend_pullback", "microstructure"],
        }
        out = {
            "ts": time.time(),
            "dominant": dominant,
            "n_symbols": len(regimes),
            "by_symbol": dict(list(regimes.items())[:50]),
            "paper_bias": bias_map.get(dominant, bias_map["UNKNOWN"]),
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
            await asyncio.sleep(300)
