"""SEC EDGAR public read client — no API key (data.sec.gov). Equity PAPER research input only."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

log = logging.getLogger("forge.sec")
UA = "ImagineForge/1.0 (northstarimagine.com; forge@northstarimagine.com)"
BASE = "https://data.sec.gov"


async def company_tickers(client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    own = client is None
    client = client or httpx.AsyncClient(timeout=30.0, headers={"User-Agent": UA})
    try:
        r = await client.get(f"{BASE}/files/company_tickers.json")
        r.raise_for_status()
        return r.json()
    finally:
        if own:
            await client.aclose()


async def recent_filings(cik: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    own = client is None
    cik = str(cik).lstrip("0") or "0"
    pad = cik.zfill(10)
    client = client or httpx.AsyncClient(timeout=30.0, headers={"User-Agent": UA})
    try:
        r = await client.get(f"{BASE}/submissions/CIK{pad}.json")
        r.raise_for_status()
        return r.json()
    finally:
        if own:
            await client.aclose()


def record_probe(db: Any, ok: bool, detail: str) -> None:
    db.kv_set("data.sec", {"ts": time.time(), "ok": ok, "detail": detail[:500]})
