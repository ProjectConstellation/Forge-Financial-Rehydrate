"""Twelve Data — founder signup required (TWELVE_DATA_API_KEY). Free-tier aware."""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

log = logging.getLogger("forge.intel.twelve")

# Keep small — free plans are ~8 credits/min; quote costs 1 credit/symbol
SYMBOLS = ("SPY", "QQQ", "AAPL", "NVDA", "MSFT")
CACHE_S = 900  # 15m — matches external_feeds cadence


def refresh(db: Any) -> dict[str, Any]:
    now = time.time()
    key = os.environ.get("TWELVE_DATA_API_KEY") or ""
    prev = db.kv_get("intel.twelve_data") or {}
    if key and prev.get("status") == "ok" and prev.get("quotes") and now - float(prev.get("ts") or 0) < CACHE_S:
        return prev

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

    quotes = dict(prev.get("quotes") or {}) if prev.get("status") in ("ok", "partial", "error", "rate_limited") else {}
    remaining = [s for s in SYMBOLS if s not in quotes]
    try:
        for i, sym in enumerate(remaining):
            url = "https://api.twelvedata.com/quote?" + urllib.parse.urlencode({"symbol": sym, "apikey": key})
            try:
                with urllib.request.urlopen(url, timeout=20) as r:
                    q = json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    out["status"] = "partial" if quotes else "rate_limited"
                    out["errors"].append(f"{sym}:429 rate limit — will continue next cycle")
                    break
                out["errors"].append(f"{sym}:HTTP {e.code}"[:120])
                continue
            if not isinstance(q, dict) or q.get("status") == "error" or q.get("code"):
                out["errors"].append(f"{sym}:{q.get('message') or q}"[:120])
                continue
            quotes[sym] = {
                "price": _f(q.get("close") or q.get("price")),
                "change_pct": _f(q.get("percent_change")),
                "volume": _f(q.get("volume")),
                "ts": q.get("datetime") or q.get("timestamp"),
            }
            if i < len(remaining) - 1:
                time.sleep(8)  # free-tier pacing
        out["quotes"] = quotes
        if quotes and out["status"] not in ("partial", "rate_limited"):
            out["status"] = "ok"
        elif quotes:
            out["status"] = "partial"
        elif not out["errors"]:
            out["status"] = "error"
            out["errors"].append("no quotes returned")
    except Exception as e:
        out["status"] = "partial" if quotes else "error"
        out["errors"].append(str(e)[:200])
        log.warning("twelve: %s", e)
    db.kv_set("intel.twelve_data", out)
    return out


def _f(x: Any) -> float | None:
    try:
        return float(x) if x is not None and x != "" else None
    except Exception:
        return None
