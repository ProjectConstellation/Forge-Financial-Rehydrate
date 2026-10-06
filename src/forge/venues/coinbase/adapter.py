"""Coinbase Advanced Trade adapter (personal account; OP-002).

Normalizes Coinbase payloads into FORGE contracts at the boundary. Capabilities are discovered
at runtime from `key_permissions` (view/trade/transfer) so permissions can expand later without
redesign. Transfers are not implemented on this adapter by design (Stage-2 cash-out lives in a
separate, policy-gated TransferRail).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from forge.domain.market import Balance, MarketRules, ProductInfo
from forge.domain.trading import FillReport, OrderAck, OrderRequest, OrderState, OrderStatus
from forge.venues.base import Capability, FeeSchedule, ReconciliationReport, VenueError
from forge.venues.coinbase.rest import CoinbaseRest

log = logging.getLogger("forge.coinbase")

NAME = "coinbase"

_STATUS = {
    "PENDING": OrderStatus.PENDING, "QUEUED": OrderStatus.PENDING, "OPEN": OrderStatus.OPEN,
    "FILLED": OrderStatus.FILLED, "CANCELLED": OrderStatus.CANCELLED, "CANCEL_QUEUED": OrderStatus.OPEN,
    "EXPIRED": OrderStatus.EXPIRED, "FAILED": OrderStatus.REJECTED,
    "UNKNOWN_ORDER_STATUS": OrderStatus.UNKNOWN,
}


def _dec(x: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(x)) if x not in (None, "") else Decimal(default)
    except Exception:
        return Decimal(default)


def rules_from_product(p: dict[str, Any]) -> MarketRules:
    return MarketRules(
        venue=NAME, symbol=p["product_id"], base=p.get("base_currency_id") or p["product_id"].split("-")[0],
        quote=p.get("quote_currency_id") or p["product_id"].split("-")[1],
        base_increment=_dec(p.get("base_increment"), "0.00000001"),
        quote_increment=_dec(p.get("quote_increment"), "0.01"),
        base_min_size=_dec(p.get("base_min_size"), "0"),
        quote_min_size=_dec(p.get("quote_min_size"), "1"),
        price_increment=_dec(p.get("price_increment") or p.get("quote_increment"), "0.01"),
        trading_enabled=not p.get("trading_disabled", False) and not p.get("is_disabled", False),
        post_only_only=bool(p.get("post_only")), limit_only=bool(p.get("limit_only")),
        cancel_only=bool(p.get("cancel_only")), status=p.get("status", "online"),
    )


class CoinbaseAdapter:
    name = NAME

    def __init__(self, rest: CoinbaseRest) -> None:
        self.rest = rest
        self._rules: dict[str, MarketRules] = {}
        self._perms: dict[str, Any] | None = None
        self._accounts: dict[str, dict[str, Any]] = {}

    # ---- discovery -----------------------------------------------------------------------------
    async def discover_permissions(self) -> dict[str, Any]:
        if not self.rest.authenticated:
            self._perms = {"can_view": False, "can_trade": False, "can_transfer": False}
        else:
            self._perms = await self.rest.key_permissions()
        return self._perms

    def capabilities(self) -> set[Capability]:
        caps = {Capability.MARKET_DATA}
        p = self._perms or {}
        if p.get("can_view"):
            caps.add(Capability.VIEW)
        if p.get("can_trade"):
            caps |= {Capability.TRADE, Capability.CONVERT}
        if p.get("can_transfer"):
            caps.add(Capability.TRANSFER)
        return caps

    async def list_products(self) -> list[ProductInfo]:
        out = []
        for p in await self.rest.products():
            try:
                r = rules_from_product(p)
                self._rules[r.symbol] = r
                out.append(ProductInfo(
                    venue=NAME, symbol=r.symbol, base=r.base, quote=r.quote,
                    price=float(p.get("price") or 0),
                    volume_24h_quote=float(p.get("approximate_quote_24h_volume") or 0),
                    change_24h_pct=float(p.get("price_percentage_change_24h") or 0),
                    rules=r, extra={"new": bool(p.get("new")), "alias": p.get("alias")}))
            except (KeyError, ValueError):
                continue
        return out

    async def get_market_rules(self, symbol: str) -> MarketRules:
        if symbol not in self._rules:
            self._rules[symbol] = rules_from_product(await self.rest.product(symbol))
        return self._rules[symbol]

    async def get_fees(self) -> FeeSchedule:
        s = await self.rest.transaction_summary()
        ft = s.get("fee_tier", {})
        return FeeSchedule(maker=_dec(ft.get("maker_fee_rate"), "0.006"),
                           taker=_dec(ft.get("taker_fee_rate"), "0.012"),
                           tier=str(ft.get("pricing_tier", "unknown")), source="transaction_summary")

    # ---- balances ------------------------------------------------------------------------------
    async def get_balances(self) -> list[Balance]:
        accts = await self.rest.accounts()
        self._accounts = {a["currency"]: a for a in accts}
        return [Balance(asset=a["currency"], available=_dec(a["available_balance"]["value"]),
                        hold=_dec((a.get("hold") or {}).get("value"))) for a in accts]

    def account_uuid(self, currency: str) -> str | None:
        a = self._accounts.get(currency)
        return a.get("uuid") if a else None

    # ---- orders --------------------------------------------------------------------------------
    @staticmethod
    def _order_body(req: OrderRequest) -> dict[str, Any]:
        if req.order_type == "market":
            cfg: dict[str, Any] = {"market_market_ioc": (
                {"quote_size": str(req.quote_size)} if req.side == "buy" and req.quote_size is not None
                else {"base_size": str(req.base_size)})}
        else:
            if req.limit_price is None or req.base_size is None:
                raise VenueError("limit orders require limit_price and base_size")
            cfg = {"limit_limit_gtc": {"base_size": str(req.base_size), "limit_price": str(req.limit_price),
                                       "post_only": req.order_type == "post_only"}}
        return {"client_order_id": req.client_order_id, "product_id": req.symbol,
                "side": req.side.upper(), "order_configuration": cfg}

    async def submit_order(self, req: OrderRequest) -> OrderAck:
        body = self._order_body(req)
        d = await self.rest.create_order(body)   # may raise VenueError(ambiguous=True)
        if d.get("success"):
            sr = d.get("success_response", {})
            return OrderAck(client_order_id=req.client_order_id, venue_order_id=sr.get("order_id"),
                            status=OrderStatus.PENDING, raw={"order_id": sr.get("order_id")})
        er = d.get("error_response", {})
        reason = er.get("new_order_failure_reason") or er.get("preview_failure_reason") or er.get("error") \
            or er.get("message") or "unknown"
        return OrderAck(client_order_id=req.client_order_id, venue_order_id=None,
                        status=OrderStatus.REJECTED, reject_reason=str(reason), raw={"error": er})

    async def preview_order(self, req: OrderRequest) -> dict[str, Any]:
        body = self._order_body(req)
        body.pop("client_order_id", None)
        return await self.rest.preview_order(body)

    async def cancel_order(self, client_order_id: str, venue_order_id: str | None) -> bool:
        if not venue_order_id:
            st = await self._find_by_client_id(client_order_id)
            venue_order_id = st.venue_order_id if st else None
            if not venue_order_id:
                return False
        d = await self.rest.cancel_orders([venue_order_id])
        res = (d.get("results") or [{}])[0]
        return bool(res.get("success")) or res.get("failure_reason") in ("UNKNOWN_CANCEL_ORDER", "DUPLICATE_CANCEL_REQUEST")

    def _state(self, o: dict[str, Any]) -> OrderState:
        return OrderState(
            client_order_id=o.get("client_order_id", ""), venue_order_id=o.get("order_id"),
            symbol=o.get("product_id", ""), side=o.get("side", "BUY").lower(),  # type: ignore[arg-type]
            status=_STATUS.get(o.get("status", ""), OrderStatus.UNKNOWN),
            filled_size=_dec(o.get("filled_size")),
            avg_fill_price=_dec(o.get("average_filled_price")) if o.get("average_filled_price") else None,
            fees=_dec(o.get("total_fees")), raw={k: o.get(k) for k in ("status", "completion_percentage",
                                                                          "reject_reason", "cancel_message")})

    async def get_order(self, client_order_id: str, venue_order_id: str | None) -> OrderState | None:
        if venue_order_id:
            try:
                return self._state(await self.rest.get_order(venue_order_id))
            except VenueError as e:
                if e.status != 404:
                    raise
        return await self._find_by_client_id(client_order_id)

    async def _find_by_client_id(self, client_order_id: str) -> OrderState | None:
        since = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for o in await self.rest.list_orders(status=None, limit=250, start_date=since):
            if o.get("client_order_id") == client_order_id:
                return self._state(o)
        return None

    async def list_open_orders(self) -> list[OrderState]:
        return [self._state(o) for o in await self.rest.list_orders(status="OPEN")]

    async def list_fills(self, client_order_id: str, venue_order_id: str | None) -> list[FillReport]:
        if not venue_order_id:
            st = await self._find_by_client_id(client_order_id)
            venue_order_id = st.venue_order_id if st else None
            if not venue_order_id:
                return []
        out = []
        for f in await self.rest.fills(venue_order_id):
            ts = f.get("trade_time", "")
            try:
                ts_ns = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1e9)
            except ValueError:
                ts_ns = 0
            out.append(FillReport(
                venue=NAME, trade_id=str(f.get("entry_id") or f.get("trade_id")), client_order_id=client_order_id,
                venue_order_id=venue_order_id, symbol=f.get("product_id", ""),
                side=f.get("side", "BUY").lower(),  # type: ignore[arg-type]
                price=_dec(f.get("price")), size=_dec(f.get("size")), fee=_dec(f.get("commission")),
                liquidity={"MAKER": "maker", "TAKER": "taker"}.get(f.get("liquidity_indicator", ""), "unknown"),  # type: ignore[arg-type]
                ts_ns=ts_ns))
        return out

    async def reconcile(self) -> ReconciliationReport:
        issues: list[str] = []
        try:
            bals = await self.get_balances()
            opens = await self.list_open_orders()
        except VenueError as e:
            return ReconciliationReport(ok=False, issues=[f"venue error: {e}"])
        return ReconciliationReport(ok=not issues, balances=bals, open_orders=opens, issues=issues)

    # ---- conversion (e.g. USD <-> USDC); Trade permission ---------------------------------------
    async def convert(self, from_ccy: str, to_ccy: str, amount: Decimal) -> dict[str, Any]:
        if not self._accounts:
            await self.get_balances()
        fa, ta = self.account_uuid(from_ccy), self.account_uuid(to_ccy)
        if not fa or not ta:
            raise VenueError(f"no account for {from_ccy} or {to_ccy}")
        q = await self.rest.convert_quote(fa, ta, str(amount))
        trade = q.get("trade", {})
        tid = trade.get("id")
        if not tid:
            raise VenueError(f"convert quote failed: {str(q)[:200]}")
        return await self.rest.convert_commit(tid, fa, ta)

    async def close(self) -> None:
        await self.rest.close()
