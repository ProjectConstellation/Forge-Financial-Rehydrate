"""Twelve Data — founder signup required (TWELVE_DATA_API_KEY)."""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Any

log = logging.getLogger("forge.intel.twelve")

SYMBOLS = ("SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "XLK", "XLF")


def refresh(db: Any) -> dict[str, Any]:
    now = time.time()
    key = os.environ.get("TWELVE_DATA_API_KEY") or ""
    out: dict[str, Any] = {
        "ts": now, "source": "twelve_data",
        "status": "blocked_no_key" if not key else "ok",
        "quotes": {}, "errors": [],
        "signup": "https://twelvedata.com/",
        "env": "TWELVE_DATA_API_KEY",
    }
    if not key:
        db.kv_set("intel.twelve_data", out)
        return out
    try:
        syms = ",".join(SYMBOLS)
        url = (
            "https://api.twelvedata.com/quote?"
            + urllib.parse.urlencode({"symbol": syms, "apikey": key})
        )
        with urllib.request.urlopen(url, timeout=25) as r:
            data = json.loads(r.read().decode())
        # multi-symbol returns dict keyed by symbol
        if isinstance(data, dict) and "symbol" in data:
            data = {data["symbol"]: data}
        for sym, q in (data or {}).items():
            if not isinstance(q, dict):
                continue
            if q.get("status") == "error" or q.get("code"):
                out["errors"].append(f"{sym}:{q.get('message') or q}"[:120])
                continue
            out["quotes"][sym] = {
                "price": _f(q.get("close") or q.get("price")),
                "change_pct": _f(q.get("percent_change")),
                "volume": _f(q.get("volume")),
                "ts": q.get("datetime") or q.get("timestamp"),
            }
        if not out["quotes"] and out["errors"]:
            out["status"] = "error"
    except Exception as e:
        out["status"] = "error"
        out["errors"].append(str(e)[:200])
        log.warning("twelve: %s", e)
    db.kv_set("intel.twelve_data", out)
    return out


def _f(x: Any) -> float | None:
    try:
        return float(x) if x is not None and x != "" else None
    except Exception:
        return None
