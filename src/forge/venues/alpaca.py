"""Alpaca Trading API client — PAPER by default.

Official docs:
  https://docs.alpaca.markets/docs/getting-started
  https://docs.alpaca.markets/us/docs/alpaca-mcp-server
  https://docs.alpaca.markets/us/docs/alpacas-cli
  https://docs.alpaca.markets/us/docs/paper-trading

Auth: APCA-API-KEY-ID / APCA-API-SECRET-KEY headers.
Live trading requires ALPACA_LIVE=on AND live keys — never implied by paper keys.
"""
from __future__ import annotations

import os
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

DEFAULT_PAPER = "https://paper-api.alpaca.markets"
DEFAULT_LIVE = "https://api.alpaca.markets"
DATA = "https://data.alpaca.markets"


class AlpacaAPIError(RuntimeError):
    def __init__(self, status: int, method: str, path: str):
        self.status_code = status
        super().__init__(f"Alpaca {method} {path}: HTTP {status}")


class AlpacaClient:
    def __init__(
        self,
        key_id: str | None = None,
        secret: str | None = None,
        base_url: str | None = None,
        *,
        paper: bool | None = None,
    ) -> None:
        self.key_id = (key_id or os.environ.get("APCA_API_KEY_ID", "")).strip()
        self.secret = (secret or os.environ.get("APCA_API_SECRET_KEY", "")).strip()
        live_on = os.environ.get("ALPACA_LIVE", "off").lower() in ("on", "1", "true")
        if base_url:
            self.base = base_url.rstrip("/")
        else:
            env_base = os.environ.get("APCA_API_BASE_URL", "").strip()
            if env_base:
                self.base = env_base.rstrip("/")
            else:
                use_paper = True if paper is None else paper
                if live_on and paper is not True:
                    use_paper = False
                self.base = DEFAULT_PAPER if use_paper else DEFAULT_LIVE
        self.data_base = os.environ.get("APCA_DATA_BASE_URL", DATA).rstrip("/")
        if paper is True and self.base != DEFAULT_PAPER:
            raise ValueError("Paper training requires the official Alpaca paper endpoint")
        if self.base not in (DEFAULT_PAPER, DEFAULT_LIVE) or self.data_base != DATA:
            raise ValueError("Alpaca credentials may only be sent to official Alpaca endpoints")
        self.http = httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "FORGE/1.0-alpaca"})
        self.calls = 0

    @property
    def configured(self) -> bool:
        return bool(self.key_id and self.secret)

    @property
    def is_paper(self) -> bool:
        return self.base == DEFAULT_PAPER

    def _hdr(self) -> dict[str, str]:
        return {"APCA-API-KEY-ID": self.key_id, "APCA-API-SECRET-KEY": self.secret}

    async def close(self) -> None:
        await self.http.aclose()

    async def req(self, method: str, path: str, *, data_api: bool = False, **kwargs: Any) -> Any:
        if not self.configured:
            raise RuntimeError("Alpaca credentials missing (APCA_API_KEY_ID / APCA_API_SECRET_KEY)")
        base = self.data_base if data_api else self.base
        self.calls += 1
        r = await self.http.request(method, base + path, headers=self._hdr(), **kwargs)
        if r.status_code >= 400:
            raise AlpacaAPIError(r.status_code, method, path)
        if not r.content:
            return {}
        return r.json()

    # --- account ---
    async def account(self) -> dict[str, Any]:
        return await self.req("GET", "/v2/account")

    async def asset(self, symbol: str) -> dict[str, Any]:
        return await self.req("GET", f"/v2/assets/{symbol.upper()}")

    async def clock(self) -> dict[str, Any]:
        return await self.req("GET", "/v2/clock")

    async def calendar(self, start: str | None = None, end: str | None = None) -> Any:
        params = {k: v for k, v in {"start": start, "end": end}.items() if v}
        return await self.req("GET", "/v2/calendar", params=params or None)

    async def positions(self) -> list[Any]:
        data = await self.req("GET", "/v2/positions")
        return data if isinstance(data, list) else []

    async def orders(self, status: str = "open", limit: int = 50) -> list[Any]:
        data = await self.req("GET", "/v2/orders", params={"status": status, "limit": limit})
        return data if isinstance(data, list) else []

    async def activities(self, activity_type: str | None = None, page_size: int = 50) -> Any:
        if activity_type:
            return await self.req("GET", f"/v2/account/activities/{activity_type}", params={"page_size": page_size})
        return await self.req("GET", "/v2/account/activities", params={"page_size": page_size})

    # --- market data ---
    async def latest_quote(self, symbol: str) -> dict[str, Any]:
        return await self.req("GET", f"/v2/stocks/{symbol}/quotes/latest", data_api=True, params={"feed":"iex"})

    async def latest_trade(self, symbol: str) -> dict[str, Any]:
        return await self.req("GET", f"/v2/stocks/{symbol}/trades/latest", data_api=True)

    async def snapshot(self, symbol: str) -> dict[str, Any]:
        return await self.req("GET", f"/v2/stocks/{symbol}/snapshot", data_api=True)

    async def bars(self, symbol: str, timeframe: str = "1Day", limit: int = 30) -> dict[str, Any]:
        from datetime import UTC, datetime, timedelta
        return await self.req(
            "GET",
            f"/v2/stocks/{symbol}/bars",
            data_api=True,
            params={"timeframe": timeframe, "limit": limit, "adjustment": "split",
                    "start": (datetime.now(UTC) - timedelta(days=500)).isoformat(),
                    "end": datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
                    "feed": "iex", "sort": "desc"},
        )

    async def most_actives(self, top: int = 10) -> dict[str, Any]:
        return await self.req("GET", "/v1beta1/screener/stocks/most-actives", data_api=True, params={"top": top})

    async def movers(self, top: int = 10) -> dict[str, Any]:
        return await self.req("GET", "/v1beta1/screener/stocks/movers", data_api=True, params={"top": top})

    async def news(self, symbols: str | None = None, limit: int = 10) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if symbols:
            params["symbols"] = symbols
        return await self.req("GET", "/v1beta1/news", data_api=True, params=params)

    # --- orders (PAPER only unless ALPACA_LIVE=on) ---
    def _assert_trade_allowed(self, *, risk_reducing: bool = False) -> None:
        if not self.is_paper:
            raise RuntimeError("Alpaca LIVE blocked: deterministic Forge execution adapter and readiness proof required")
        if risk_reducing:
            return
        from forge.opportunities.alpaca_bankroll import read_runtime_state
        state = read_runtime_state("trading.state")
        if not state or state.get("state") != "RUNNING":
            raise RuntimeError("Alpaca PAPER submission blocked by unknown or non-RUNNING global state")

    async def submit_order(
        self,
        *,
        symbol: str,
        qty: float | str | None = None,
        notional: float | str | None = None,
        side: str = "buy",
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: float | str | None = None,
        stop_price: float | str | None = None,
        client_order_id: str | None = None,
        extended_hours: bool = False,
        _risk_reducing: bool = False,
    ) -> dict[str, Any]:
        if (qty is None) == (notional is None):
            raise ValueError("exactly one of qty or notional is required")
        for value in (qty, notional, limit_price, stop_price):
            if value is not None:
                try:
                    parsed = Decimal(str(value))
                    if not parsed.is_finite() or parsed <= 0:
                        raise ValueError("order values must be finite and positive")
                except InvalidOperation:
                    raise ValueError("invalid decimal order value")
        if side.lower() not in ("buy", "sell") or order_type.lower() not in ("market", "limit", "stop", "stop_limit"):
            raise ValueError("unsupported side or order type")
        if order_type.lower() in ("limit", "stop_limit") and limit_price is None:
            raise ValueError("limit_price required")
        if order_type.lower() in ("stop", "stop_limit") and stop_price is None:
            raise ValueError("stop_price required")
        if extended_hours and (order_type.lower() != "limit" or time_in_force != "day"):
            raise ValueError("extended training orders require limit/day")
        if not client_order_id:
            raise ValueError("stable client_order_id required for reconciliation")
        if _risk_reducing and side.lower() != "sell":
            raise ValueError("risk reducing submission must be a sell")
        self._assert_trade_allowed(risk_reducing=_risk_reducing)
        body: dict[str, Any] = {
            "symbol": symbol.upper(),
            "side": side.lower(),
            "type": order_type.lower(),
            "time_in_force": time_in_force,
            "client_order_id": client_order_id or f"forge-{uuid.uuid4().hex[:20]}",
        }
        if qty is not None:
            body["qty"] = str(qty)
        if notional is not None:
            body["notional"] = str(notional)
        if limit_price is not None:
            body["limit_price"] = str(limit_price)
        if stop_price is not None:
            body["stop_price"] = str(stop_price)
        if extended_hours:
            body["extended_hours"] = True
        return await self.req("POST", "/v2/orders", json=body)

    async def cancel_order(self, order_id: str) -> Any:
        self._assert_trade_allowed(risk_reducing=True)
        return await self.req("DELETE", f"/v2/orders/{order_id}")

    async def cancel_all_orders(self) -> Any:
        self._assert_trade_allowed()
        return await self.req("DELETE", "/v2/orders")

    async def close_position(self, symbol: str) -> Any:
        self._assert_trade_allowed()
        return await self.req("DELETE", f"/v2/positions/{symbol.upper()}")

    async def status_snapshot(self) -> dict[str, Any]:
        acct = await self.account()
        clock = await self.clock()
        pos = await self.positions()
        return {
            "configured": True,
            "paper": self.is_paper,
            "base": self.base,
            "status": acct.get("status"),
            "equity": float(acct.get("equity") or 0),
            "cash": float(acct.get("cash") or 0),
            "buying_power": float(acct.get("buying_power") or 0),
            "multiplier": acct.get("multiplier"),
            "pattern_day_trader": acct.get("pattern_day_trader"),
            "trading_blocked": acct.get("trading_blocked"),
            "market_open": clock.get("is_open"),
            "next_open": clock.get("next_open"),
            "next_close": clock.get("next_close"),
            "positions": len(pos),
            "alpaca_live_env": os.environ.get("ALPACA_LIVE", "off"),
        }
