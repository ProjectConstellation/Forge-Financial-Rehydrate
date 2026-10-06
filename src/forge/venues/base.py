"""Venue-agnostic adapter contract (DOSSIER §2.2, §20.1; DIRECTIVE §11).

Core strategy logic never sees venue payloads — adapters normalize at the boundary.
Capabilities are explicit so new permissions/rails (Transfer, Agentic Wallet, x402, Kalshi)
plug in without redesign (OP-002).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

from forge.domain.market import Balance, MarketRules, ProductInfo
from forge.domain.trading import FillReport, OrderAck, OrderRequest, OrderState


class Capability(StrEnum):
    MARKET_DATA = "MARKET_DATA"
    VIEW = "VIEW"
    TRADE = "TRADE"
    TRANSFER = "TRANSFER"
    RECEIVE = "RECEIVE"
    CONVERT = "CONVERT"
    WALLET_BALANCE = "WALLET_BALANCE"
    TRADE_ON_BASE = "TRADE_ON_BASE"
    PAY_X402 = "PAY_X402"


@dataclass
class FeeSchedule:
    maker: Decimal
    taker: Decimal
    tier: str = "unknown"
    source: str = "default"


@dataclass
class ReconciliationReport:
    ok: bool
    balances: list[Balance] = field(default_factory=list)
    open_orders: list[OrderState] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


class VenueError(Exception):
    """Venue call failed. `retryable` = safe to retry; `ambiguous` = outcome unknown (must reconcile)."""

    def __init__(self, msg: str, *, retryable: bool = False, ambiguous: bool = False,
                 status: int | None = None) -> None:
        super().__init__(msg)
        self.retryable = retryable
        self.ambiguous = ambiguous
        self.status = status


@runtime_checkable
class VenueAdapter(Protocol):
    name: str

    def capabilities(self) -> set[Capability]: ...
    async def list_products(self) -> list[ProductInfo]: ...
    async def get_market_rules(self, symbol: str) -> MarketRules: ...
    async def get_fees(self) -> FeeSchedule: ...
    async def get_balances(self) -> list[Balance]: ...
    async def submit_order(self, req: OrderRequest) -> OrderAck: ...
    async def cancel_order(self, client_order_id: str, venue_order_id: str | None) -> bool: ...
    async def get_order(self, client_order_id: str, venue_order_id: str | None) -> OrderState | None: ...
    async def list_open_orders(self) -> list[OrderState]: ...
    async def list_fills(self, client_order_id: str, venue_order_id: str | None) -> list[FillReport]: ...
    async def reconcile(self) -> ReconciliationReport: ...
    async def close(self) -> None: ...
