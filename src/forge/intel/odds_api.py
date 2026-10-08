"""The Odds API — founder signup required (THE_ODDS_API_KEY)."""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Any

log = logging.getLogger("forge.intel.odds")


def refresh(db: Any) -> dict[str, Any]:
    now = time.time()
    key = os.environ.get("THE_ODDS_API_KEY") or ""
    out: dict[str, Any] = {
        "ts": now, "source": "the_odds_api",
        "status": "blocked_no_key" if not key else "ok",
        "sports": [], "events_sample": [], "errors": [],
        "signup": "https://the-odds-api.com/",
        "env": "THE_ODDS_API_KEY",
        "note": "bookmaker consensus → proprietary probs; never blind-follow",
    }
    if not key:
        db.kv_set("intel.odds_api", out)
        return out
    try:
        url = "https://api.the-odds-api.com/v4/sports/?" + urllib.parse.urlencode({"apiKey": key})
        with urllib.request.urlopen(url, timeout=25) as r:
            sports = json.loads(r.read().decode())
        active = [s for s in sports if s.get("active")][:12]
        out["sports"] = [{"key": s.get("key"), "title": s.get("title")} for s in active]
        # Sample one popular sport odds if available
        for sport in ("americanfootball_nfl", "basketball_nba", "soccer_epl"):
            if not any(s.get("key") == sport for s in active):
                continue
            u2 = (
                f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?"
                + urllib.parse.urlencode({
                    "apiKey": key, "regions": "us", "markets": "h2h", "oddsFormat": "decimal",
                })
            )
            with urllib.request.urlopen(u2, timeout=25) as r:
                events = json.loads(r.read().decode())
            for ev in (events or [])[:3]:
                books = ev.get("bookmakers") or []
                # dispersion across books for first market
                prices = []
                for b in books[:8]:
                    for m in b.get("markets") or []:
                        if m.get("key") != "h2h":
                            continue
                        for o in m.get("outcomes") or []:
                            prices.append(float(o.get("price") or 0))
                out["events_sample"].append({
                    "sport": sport,
                    "id": ev.get("id"),
                    "home": ev.get("home_team"),
                    "away": ev.get("away_team"),
                    "commence": ev.get("commence_time"),
                    "n_books": len(books),
                    "price_min": min(prices) if prices else None,
                    "price_max": max(prices) if prices else None,
                    "dispersion": (max(prices) - min(prices)) if len(prices) >= 2 else None,
                })
            break
    except Exception as e:
        out["status"] = "error"
        out["errors"].append(str(e)[:200])
        log.warning("odds: %s", e)
    db.kv_set("intel.odds_api", out)
    return out
