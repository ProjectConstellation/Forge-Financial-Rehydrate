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

    def run(self) -> None:
        try:
            self._tick()
        except Exception as e:
            log.warning("regime: %s", e)

    def _tick(self) -> None:
        # Use recent closes from market bars if present
        rows = self.f.db.query(
            "SELECT symbol, close, ts FROM market_bars WHERE ts > ? ORDER BY ts DESC LIMIT 800",
            (time.time() - 86400 * 3,),
        ) if hasattr(self.f.db, "query") else []
        by_sym: dict[str, list[float]] = {}
        for r in rows or []:
            try:
                s, c = r["symbol"] if isinstance(r, dict) else r[0], float(r["close"] if isinstance(r, dict) else r[1])
                by_sym.setdefault(str(s), []).append(c)
            except Exception:
                continue
        regimes: dict[str, Any] = {}
        for sym, closes in by_sym.items():
            if len(closes) < 20:
                continue
            closes = list(reversed(closes[:120]))  # oldest→newest approximate
            rets = []
            for i in range(1, len(closes)):
                if closes[i - 1]:
                    rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
            if len(rets) < 15:
                continue
            mean = sum(rets) / len(rets)
            var = sum((x - mean) ** 2 for x in rets) / max(1, len(rets) - 1)
            vol = math.sqrt(var)
            trend = (closes[-1] / closes[0] - 1.0) if closes[0] else 0.0
            if vol > 0.04:
                label = "high_vol"
            elif abs(trend) < 0.01:
                label = "range"
            elif trend > 0.03:
                label = "bull_trend"
            elif trend < -0.03:
                label = "bear_trend"
            else:
                label = "mild_trend"
            regimes[sym] = {"label": label, "vol": round(vol, 5), "trend_3d": round(trend, 4), "n": len(rets)}
        # Global blend
        labels = [v["label"] for v in regimes.values()]
        dominant = max(set(labels), key=labels.count) if labels else "unknown"
        out = {
            "ts": time.time(),
            "dominant": dominant,
            "n_symbols": len(regimes),
            "by_symbol": dict(list(regimes.items())[:40]),
            "paper_bias": {
                "high_vol": ["mean_reversion", "inventory_skew", "microstructure"],
                "range": ["mean_reversion", "peg_maker", "carry_proxy"],
                "bull_trend": ["trend_pullback", "momentum", "cross_asset"],
                "bear_trend": ["trend_pullback", "event_driven", "inventory_skew"],
                "mild_trend": ["trend_pullback", "mean_reversion", "cross_asset"],
                "unknown": ["mean_reversion", "trend_pullback"],
            }.get(dominant, ["mean_reversion", "trend_pullback"]),
        }
        self.f.db.kv_set("lab.regime", out)
