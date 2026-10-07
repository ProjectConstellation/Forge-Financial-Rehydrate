"""Kalshi signed trading client (official Trade API v2; Ed25519 or RSA-PSS keys).

Auth (docs.kalshi.com/getting_started/api_keys): headers KALSHI-ACCESS-KEY, KALSHI-ACCESS-TIMESTAMP (ms),
KALSHI-ACCESS-SIGNATURE = base64(sign(timestamp_ms + METHOD + path_without_query)); Ed25519 signs the text directly, RSA uses
PSS/SHA-256 (MGF1 SHA-256, salt = digest length). Orders: POST /portfolio/events/orders (V2: side bid=buy YES / ask=sell YES
≡ buy NO at 1−price, fixed-point dollar prices). The private key file lives in /etc/forge (0600, owner forge); it is never
logged, never sent to an LLM.
"""

from __future__ import annotations

import base64
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

BASE = "https://api.elections.kalshi.com"
PREFIX = "/trade-api/v2"


def load_private_key(pem: bytes) -> Any:
    from cryptography.hazmat.primitives import serialization
    return serialization.load_pem_private_key(pem, password=None)


def sign_text(private_key: Any, text: str) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    msg = text.encode("utf-8")
    if isinstance(private_key, Ed25519PrivateKey):
        sig = private_key.sign(msg)
    else:
        sig = private_key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
                               hashes.SHA256())
    return base64.b64encode(sig).decode("ascii")


def auth_headers(key_id: str, private_key: Any, method: str, path: str, ts_ms: int | None = None) -> dict[str, str]:
    ts = str(ts_ms if ts_ms is not None else int(time.time() * 1000))
    return {"KALSHI-ACCESS-KEY": key_id, "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": sign_text(private_key, ts + method.upper() + path.split("?")[0])}


def order_body(ticker: str, buy_side: str, price: float, count: int, client_order_id: str | None = None,
               tif: str = "immediate_or_cancel") -> dict[str, Any]:
    """Buy YES at `price` → bid YES @ price. Buy NO at `price` → ask (sell) YES @ 1 − price. Never worse than `price`."""
    if buy_side not in ("yes", "no"):
        raise ValueError(buy_side)
    if not (0.01 <= price <= 0.99) or count < 1:
        raise ValueError("price must be 0.01–0.99 and count ≥ 1")
    yes_px = price if buy_side == "yes" else 1.0 - price
    return {"ticker": ticker, "side": "bid" if buy_side == "yes" else "ask", "count": f"{int(count)}.00",
            "price": f"{yes_px:.4f}", "time_in_force": tif, "self_trade_prevention_type": "taker_at_cross",
            "post_only": False, "client_order_id": client_order_id or f"forge-{uuid.uuid4().hex[:20]}"}


class KalshiClient:
    def __init__(self, key_id: str, private_key_path: str | Path, base: str = BASE) -> None:
        self.key_id = key_id
        self._pk = load_private_key(Path(private_key_path).read_bytes())
        self.base = base
        self.http = httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "FORGE/1.0"})
        self.calls = 0

    async def close(self) -> None:
        await self.http.aclose()

    async def req(self, method: str, path: str, params: dict[str, Any] | None = None,
                  body: dict[str, Any] | None = None) -> dict[str, Any]:
        full = PREFIX + path
        h = auth_headers(self.key_id, self._pk, method, full)
        if body is not None:
            h["Content-Type"] = "application/json"
        self.calls += 1
        r = await self.http.request(method, self.base + full, params=params, json=body, headers=h)
        if r.status_code >= 400:
            raise RuntimeError(f"Kalshi {method} {path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json() if r.content else {}

    # ---- account
    async def balance(self) -> dict[str, Any]:
        return await self.req("GET", "/portfolio/balance")

    async def positions(self) -> dict[str, Any]:
        return await self.req("GET", "/portfolio/positions", params={"limit": 200})

    async def fills(self, limit: int = 100) -> dict[str, Any]:
        return await self.req("GET", "/portfolio/fills", params={"limit": limit})

    async def settlements(self, limit: int = 100) -> dict[str, Any]:
        return await self.req("GET", "/portfolio/settlements", params={"limit": limit})

    async def order(self, order_id: str) -> dict[str, Any]:
        return await self.req("GET", f"/portfolio/orders/{order_id}")

    # ---- trading
    async def buy(self, ticker: str, side: str, price: float, count: int, client_order_id: str) -> dict[str, Any]:
        return await self.req("POST", "/portfolio/events/orders", body=order_body(ticker, side, price, count, client_order_id))

    # ---- market data
    async def orderbook(self, ticker: str) -> dict[str, Any]:
        return await self.req("GET", f"/markets/{ticker}/orderbook")
