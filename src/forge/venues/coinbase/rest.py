"""Coinbase Advanced Trade REST client (personal account, CDP key).

- Public market endpoints need no auth; private ones are signed per request.
- Token-bucket rate limiting (public ~10 rps, private ~30 rps; we stay well below).
- Retries only on retryable conditions; a timeout on an order POST is *ambiguous* and is
  surfaced as such so the gateway reconciles instead of resubmitting blindly (DOSSIER §35.2).
  (Coinbase also de-duplicates by client_order_id, which makes resubmits safe, but we still
  reconcile first.)
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Any

import httpx

from forge.venues.base import VenueError
from forge.venues.coinbase.auth import CdpSigner

log = logging.getLogger("forge.coinbase.rest")

BROKER = "/api/v3/brokerage"
GRANULARITY = {60: "ONE_MINUTE", 300: "FIVE_MINUTE", 900: "FIFTEEN_MINUTE", 1800: "THIRTY_MINUTE",
               3600: "ONE_HOUR", 7200: "TWO_HOUR", 21600: "SIX_HOUR", 86400: "ONE_DAY"}


class _Bucket:
    def __init__(self, rate: float, burst: int) -> None:
        self.rate, self.capacity = rate, burst
        self.tokens = float(burst)
        self.t = time.monotonic()
        self._lock = asyncio.Lock()

    async def take(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.t) * self.rate)
                self.t = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                await asyncio.sleep((1 - self.tokens) / self.rate)


class CoinbaseRest:
    def __init__(self, base_url: str = "https://api.coinbase.com", signer: CdpSigner | None = None,
                 timeout: float = 15.0, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.signer = signer
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, transport=transport,
                                         headers={"User-Agent": "forge/0.1", "Accept": "application/json"})
        self._public = _Bucket(rate=6.0, burst=6)
        self._private = _Bucket(rate=15.0, burst=10)
        self.calls = 0
        self.errors = 0

    @property
    def authenticated(self) -> bool:
        return self.signer is not None

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None,
                       body: dict[str, Any] | None = None, private: bool = False,
                       retries: int = 3, idempotent: bool = True) -> Any:
        if private and not self.signer:
            raise VenueError("Coinbase credentials not configured (CONFIG_REQUIRED)")
        attempt = 0
        while True:
            attempt += 1
            await (self._private if private else self._public).take()
            headers = {}
            if private:
                assert self.signer is not None
                headers["Authorization"] = f"Bearer {self.signer.rest_jwt(method, path)}"
            if body is not None:
                headers["Content-Type"] = "application/json"
            self.calls += 1
            try:
                r = await self._client.request(method, path, params=params, headers=headers,
                                               content=json.dumps(body) if body is not None else None)
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                self.errors += 1
                if not idempotent:
                    raise VenueError(f"{method} {path}: {type(e).__name__} — outcome unknown",
                                     ambiguous=True, retryable=False) from e
                if attempt > retries:
                    raise VenueError(f"{method} {path}: {type(e).__name__}", retryable=True) from e
                await asyncio.sleep(min(8.0, 0.5 * 2 ** attempt) * (0.5 + random.random()))
                continue
            if r.status_code == 429 or r.status_code >= 500:
                self.errors += 1
                if attempt > retries or (not idempotent and r.status_code >= 500):
                    raise VenueError(f"{method} {path}: HTTP {r.status_code}", status=r.status_code,
                                     retryable=True, ambiguous=not idempotent and r.status_code >= 500)
                ra = r.headers.get("Retry-After")
                await asyncio.sleep(float(ra) if ra and ra.replace(".", "").isdigit()
                                    else min(8.0, 0.5 * 2 ** attempt) * (0.5 + random.random()))
                continue
            if r.status_code >= 400:
                self.errors += 1
                raise VenueError(f"{method} {path}: HTTP {r.status_code} {r.text[:300]}", status=r.status_code)
            return r.json() if r.content else {}

    # ---- public market data --------------------------------------------------------------------
    async def products(self) -> list[dict[str, Any]]:
        d = await self._request("GET", f"{BROKER}/market/products",
                                params={"product_type": "SPOT", "limit": 1000})
        return d.get("products", [])

    async def product(self, product_id: str) -> dict[str, Any]:
        return await self._request("GET", f"{BROKER}/market/products/{product_id}")

    async def candles(self, product_id: str, start: int, end: int, granularity_s: int) -> list[dict[str, Any]]:
        """Up to 350 candles in [start, end) unix seconds; returned oldest→newest."""
        g = GRANULARITY[granularity_s]
        d = await self._request("GET", f"{BROKER}/market/products/{product_id}/candles",
                                params={"start": str(start), "end": str(end), "granularity": g,
                                        "limit": 350})
        return sorted(d.get("candles", []), key=lambda c: int(c["start"]))

    async def book(self, product_id: str, limit: int = 50) -> dict[str, Any]:
        d = await self._request("GET", f"{BROKER}/market/product_book",
                                params={"product_id": product_id, "limit": limit})
        return d.get("pricebook", {})

    async def server_time(self) -> dict[str, Any]:
        return await self._request("GET", f"{BROKER}/time")

    # ---- private: account ------------------------------------------------------------------------
    async def key_permissions(self) -> dict[str, Any]:
        return await self._request("GET", f"{BROKER}/key_permissions", private=True)

    async def transaction_summary(self) -> dict[str, Any]:
        return await self._request("GET", f"{BROKER}/transaction_summary", private=True)

    async def accounts(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        cursor = None
        while True:
            params: dict[str, Any] = {"limit": 250}
            if cursor:
                params["cursor"] = cursor
            d = await self._request("GET", f"{BROKER}/accounts", params=params, private=True)
            out.extend(d.get("accounts", []))
            if not d.get("has_next"):
                return out
            cursor = d.get("cursor")

    # ---- private: orders ------------------------------------------------------------------------
    async def create_order(self, body: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"{BROKER}/orders", body=body, private=True,
                                   idempotent=False, retries=0)

    async def preview_order(self, body: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"{BROKER}/orders/preview", body=body, private=True)

    async def cancel_orders(self, order_ids: list[str]) -> dict[str, Any]:
        return await self._request("POST", f"{BROKER}/orders/batch_cancel",
                                   body={"order_ids": order_ids}, private=True)

    async def get_order(self, order_id: str) -> dict[str, Any]:
        d = await self._request("GET", f"{BROKER}/orders/historical/{order_id}", private=True)
        return d.get("order", {})

    async def list_orders(self, status: str | None = "OPEN", limit: int = 250,
                          product_id: str | None = None, start_date: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["order_status"] = status
        if product_id:
            params["product_ids"] = product_id
        if start_date:
            params["start_date"] = start_date
        d = await self._request("GET", f"{BROKER}/orders/historical/batch", params=params, private=True)
        return d.get("orders", [])

    async def fills(self, order_id: str) -> list[dict[str, Any]]:
        d = await self._request("GET", f"{BROKER}/orders/historical/fills",
                                params={"order_ids": order_id, "limit": 100}, private=True)
        return d.get("fills", [])

    # ---- private: convert (USD <-> USDC etc.; Trade permission) -----------------------------------
    async def convert_quote(self, from_account: str, to_account: str, amount: str) -> dict[str, Any]:
        return await self._request("POST", f"{BROKER}/convert/quote",
                                   body={"from_account": from_account, "to_account": to_account,
                                         "amount": amount}, private=True, idempotent=False, retries=0)

    async def convert_commit(self, trade_id: str, from_account: str, to_account: str) -> dict[str, Any]:
        return await self._request("POST", f"{BROKER}/convert/trade/{trade_id}",
                                   body={"from_account": from_account, "to_account": to_account},
                                   private=True, idempotent=False, retries=0)
