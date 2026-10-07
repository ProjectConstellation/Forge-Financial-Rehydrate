"""Paper venue: realistic simulated execution against LIVE market data (DOSSIER §37 PAPER/SHADOW).

- market orders sweep the live L2 book (or BBO + slippage) and pay taker fee;
- post-only limits are rejected if they would cross; they fill only when the market trades THROUGH the
  limit (queue-penetration model) and pay maker fee;
- balances persist through the ledger (book="paper"); fills are reported like a real venue.
Same interface as the Coinbase adapter, so the execution gateway cannot tell them apart.
"""

from __future__ import annotations

import itertools
import time
from collections.abc import Callable
from decimal import Decimal

from forge.domain.market import Balance, BestBidAsk, MarketRules, ProductInfo, d
from forge.domain.trading import FillReport, OrderAck, OrderRequest, OrderState, OrderStatus
from forge.market_data.orderbook import L2Book
from forge.venues.base import Capability, FeeSchedule, ReconciliationReport, VenueError


class PaperVenue:
    name = "coinbase"     # simulates the coinbase venue (same symbols/rules)

    def __init__(self, fees: FeeSchedule, rules: Callable[[str], MarketRules | None],
                 bbo: Callable[[str], BestBidAsk | None], book: Callable[[str], L2Book | None],
                 balances: dict[str, Decimal], penetration_bps: float = 1.0, extra_slip_bps: float = 1.0) -> None:
        self.fees = fees
        self._rules = rules
        self._bbo = bbo
        self._book = book
        self.balances: dict[str, Decimal] = dict(balances)
        self.holds: dict[str, Decimal] = {}
        self.orders: dict[str, OrderState] = {}
        self.reqs: dict[str, OrderRequest] = {}
        self.fills: dict[str, list[FillReport]] = {}
        self._ids = itertools.count(1)
        self._run = format(time.time_ns(), "x")        # fill ids unique across restarts (pt-<run>-<n>); was pt-<n> → collisions
        self.pen = penetration_bps / 1e4
        self.slip = extra_slip_bps / 1e4

    def capabilities(self) -> set[Capability]:
        return {Capability.MARKET_DATA, Capability.VIEW, Capability.TRADE}

    async def list_products(self) -> list[ProductInfo]:
        return []

    async def get_market_rules(self, symbol: str) -> MarketRules:
        r = self._rules(symbol)
        if r is None:
            raise VenueError(f"unknown market {symbol}")
        return r

    async def get_fees(self) -> FeeSchedule:
        return self.fees

    async def get_balances(self) -> list[Balance]:
        return [Balance(a, v - self.holds.get(a, Decimal(0)), self.holds.get(a, Decimal(0)))
                for a, v in self.balances.items()]

    def _avail(self, asset: str) -> Decimal:
        return self.balances.get(asset, Decimal(0)) - self.holds.get(asset, Decimal(0))

    async def submit_order(self, req: OrderRequest) -> OrderAck:
        if req.client_order_id in self.orders:           # venue-side idempotency (like Coinbase)
            o = self.orders[req.client_order_id]
            return OrderAck(client_order_id=req.client_order_id, venue_order_id=o.venue_order_id, status=o.status)
        rules = self._rules(req.symbol)
        bbo = self._bbo(req.symbol)
        if rules is None or bbo is None:
            return self._reject(req, "NO_MARKET_DATA")
        base, quote = rules.base, rules.quote
        vid = f"paper-{next(self._ids)}"
        st = OrderState(client_order_id=req.client_order_id, venue_order_id=vid, symbol=req.symbol, side=req.side,
                        status=OrderStatus.OPEN)
        if req.order_type == "market":
            self.orders[req.client_order_id], self.reqs[req.client_order_id] = st, req
            if req.side == "buy":
                notional = req.quote_size or Decimal(0)
                if notional > self._avail(quote):
                    return self._reject(req, "INSUFFICIENT_FUND")
                px = self._sweep_px("buy", float(notional), bbo)
                size = rules.round_base(notional / (px * (1 + self.fees.taker)))
            else:
                size = req.base_size or Decimal(0)
                if size > self._avail(base):
                    return self._reject(req, "INSUFFICIENT_FUND")
                px = self._sweep_px("sell", float(size) * bbo.bid, bbo)
            if size <= 0:
                return self._reject(req, "INVALID_SIZE")
            self._fill(req, st, px, size, "taker")
            return OrderAck(client_order_id=req.client_order_id, venue_order_id=vid, status=st.status)
        # limit / post-only
        lp = req.limit_price or Decimal(0)
        size = req.base_size or Decimal(0)
        if req.order_type == "post_only" and ((req.side == "buy" and float(lp) >= bbo.ask) or
                                               (req.side == "sell" and float(lp) <= bbo.bid)):
            return self._reject(req, "POST_ONLY_WOULD_CROSS")
        need_asset, need = (quote, lp * size * (1 + self.fees.maker)) if req.side == "buy" else (base, size)
        if need > self._avail(need_asset):
            return self._reject(req, "INSUFFICIENT_FUND")
        self.holds[need_asset] = self.holds.get(need_asset, Decimal(0)) + need
        self.orders[req.client_order_id], self.reqs[req.client_order_id] = st, req
        if req.order_type == "limit" and ((req.side == "buy" and float(lp) >= bbo.ask) or
                                          (req.side == "sell" and float(lp) <= bbo.bid)):
            self._release(req)
            self._fill(req, st, d(bbo.ask if req.side == "buy" else bbo.bid), size, "taker")
        return OrderAck(client_order_id=req.client_order_id, venue_order_id=vid, status=st.status)

    def _sweep_px(self, side: str, notional: float, bbo: BestBidAsk) -> Decimal:
        bk = self._book(bbo.symbol)
        if bk is not None and bk.valid:
            sw = bk.sweep(side, max(notional, 1.0))
            if sw is not None:
                px = sw[0]
                return d(px * (1 + self.slip) if side == "buy" else px * (1 - self.slip))
        px = bbo.ask * (1 + self.slip) if side == "buy" else bbo.bid * (1 - self.slip)
        return d(px)

    def _reject(self, req: OrderRequest, why: str) -> OrderAck:
        st = OrderState(client_order_id=req.client_order_id, venue_order_id=None, symbol=req.symbol, side=req.side,
                        status=OrderStatus.REJECTED, raw={"reject_reason": why})
        self.orders[req.client_order_id] = st
        return OrderAck(client_order_id=req.client_order_id, venue_order_id=None, status=OrderStatus.REJECTED,
                        reject_reason=why)

    def _release(self, req: OrderRequest) -> None:
        rules = self._rules(req.symbol)
        if rules is None:
            return
        st = self.orders[req.client_order_id]
        remaining = (req.base_size or Decimal(0)) - st.filled_size
        if req.side == "buy":
            amt = (req.limit_price or Decimal(0)) * remaining * (1 + self.fees.maker)
            self.holds[rules.quote] = max(Decimal(0), self.holds.get(rules.quote, Decimal(0)) - amt)
        else:
            self.holds[rules.base] = max(Decimal(0), self.holds.get(rules.base, Decimal(0)) - remaining)

    def _fill(self, req: OrderRequest, st: OrderState, px: Decimal, size: Decimal, liq: str) -> None:
        rules = self._rules(req.symbol)
        assert rules is not None
        fee_rate = self.fees.maker if liq == "maker" else self.fees.taker
        notional = px * size
        fee = (notional * fee_rate).quantize(Decimal("0.00000001"))
        if req.side == "buy":
            self.balances[rules.quote] = self.balances.get(rules.quote, Decimal(0)) - notional - fee
            self.balances[rules.base] = self.balances.get(rules.base, Decimal(0)) + size
        else:
            self.balances[rules.base] = self.balances.get(rules.base, Decimal(0)) - size
            self.balances[rules.quote] = self.balances.get(rules.quote, Decimal(0)) + notional - fee
        tid = f"pt-{self._run}-{next(self._ids)}"
        self.fills.setdefault(req.client_order_id, []).append(FillReport(
            venue=self.name, trade_id=tid, client_order_id=req.client_order_id, venue_order_id=st.venue_order_id,
            symbol=req.symbol, side=req.side, price=px, size=size, fee=fee, liquidity=liq,  # type: ignore[arg-type]
            ts_ns=time.time_ns()))
        prev = st.filled_size
        st.filled_size = prev + size
        st.avg_fill_price = ((st.avg_fill_price or Decimal(0)) * prev + px * size) / st.filled_size
        st.fees += fee
        st.status = OrderStatus.FILLED

    def on_market(self, symbol: str, trade_price: float | None = None) -> None:
        """Called on live trades/BBO: fill resting limits that the market traded through."""
        bbo = self._bbo(symbol)
        for cid, st in list(self.orders.items()):
            if st.symbol != symbol or st.status != OrderStatus.OPEN:
                continue
            req = self.reqs[cid]
            lp = float(req.limit_price or 0)
            px = trade_price if trade_price is not None else (bbo.mid if bbo else None)
            if px is None:
                continue
            hit = (req.side == "buy" and px <= lp * (1 - self.pen)) or (req.side == "sell" and px >= lp * (1 + self.pen))
            if bbo is not None and not hit:
                hit = (req.side == "buy" and bbo.ask <= lp * (1 - self.pen)) or \
                      (req.side == "sell" and bbo.bid >= lp * (1 + self.pen))
            if hit:
                self._release(req)
                self._fill(req, st, req.limit_price or Decimal(0), (req.base_size or Decimal(0)) - st.filled_size, "maker")

    async def cancel_order(self, client_order_id: str, venue_order_id: str | None) -> bool:
        st = self.orders.get(client_order_id)
        if st is None:
            return False
        if st.status == OrderStatus.OPEN:
            self._release(self.reqs[client_order_id])
            st.status = OrderStatus.CANCELLED
        return True

    async def get_order(self, client_order_id: str, venue_order_id: str | None) -> OrderState | None:
        return self.orders.get(client_order_id)

    async def list_open_orders(self) -> list[OrderState]:
        return [o for o in self.orders.values() if o.status == OrderStatus.OPEN]

    async def list_fills(self, client_order_id: str, venue_order_id: str | None) -> list[FillReport]:
        return list(self.fills.get(client_order_id, []))

    async def reconcile(self) -> ReconciliationReport:
        return ReconciliationReport(ok=True, balances=await self.get_balances(), open_orders=await self.list_open_orders())

    async def close(self) -> None:
        return None
