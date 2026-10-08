"""SEC EDGAR — no signup. Fair-access User-Agent required."""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger("forge.intel.edgar")

UA = "ImagineForge/1.0 (forge@northstarimagine.com)"
TICKERS = ("AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "JPM", "XOM")


def _get(url: str, timeout: float = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return json.loads(raw.decode())


def refresh(db: Any) -> dict[str, Any]:
    """Pull recent company-tickers map + a few companyfacts snapshots for macro/equity features."""
    now = time.time()
    out: dict[str, Any] = {"ts": now, "source": "sec_edgar", "status": "ok", "filings": [], "errors": []}
    try:
        # CIK map (cached aggressively)
        cache = db.kv_get("intel.edgar.cik_map") or {}
        if not cache or now - float(cache.get("ts") or 0) > 7 * 86400:
            tickers = _get("https://www.sec.gov/files/company_tickers.json")
            # tickers is { "0": {"cik_str":..,"ticker":..,"title":..}, ...}
            m = {}
            for v in tickers.values():
                t = str(v.get("ticker") or "").upper()
                if t:
                    m[t] = int(v["cik_str"])
            cache = {"ts": now, "map": m}
            db.kv_set("intel.edgar.cik_map", cache)
        m = cache.get("map") or {}
        for t in TICKERS:
            cik = m.get(t)
            if not cik:
                continue
            try:
                facts = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
                # Keep tiny feature slice — not full dump
                entity = facts.get("entityName")
                shares = None
                try:
                    shares = (
                        facts["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"][-1]["val"]
                    )
                except Exception:
                    pass
                out["filings"].append({"ticker": t, "cik": cik, "entity": entity, "shares_out": shares})
                time.sleep(0.15)  # fair access
            except Exception as e:
                if "404" not in str(e):
                    out["errors"].append(f"{t}:{e}"[:120])
        # Recent 8-K via submissions for SPY constituents proxy — use NVDA as event sample
        for t in ("NVDA", "AAPL"):
            cik = m.get(t)
            if not cik:
                continue
            try:
                sub = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
                recent = sub.get("filings", {}).get("recent", {})
                forms = recent.get("form") or []
                dates = recent.get("filingDate") or []
                accessions = recent.get("accessionNumber") or []
                eights = [
                    {"ticker": t, "form": forms[i], "date": dates[i], "accession": accessions[i]}
                    for i in range(min(len(forms), 40))
                    if forms[i] in ("8-K", "8-K/A", "10-Q", "10-K")
                ][:5]
                out.setdefault("recent_material", []).extend(eights)
                time.sleep(0.15)
            except Exception as e:
                out["errors"].append(f"sub:{t}:{e}"[:120])
    except Exception as e:
        out["status"] = "error"
        out["errors"].append(str(e)[:200])
        log.warning("edgar: %s", e)
    db.kv_set("intel.edgar", out)
    return out
