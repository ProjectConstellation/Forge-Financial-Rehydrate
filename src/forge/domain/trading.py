"""Decision contracts: Opportunity, TradeIntent, RiskDecision, orders/fills (DOSSIER §11, §23)."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Direction(StrEnum):
    LONG = "long"          # spot only in Phase 1 (no shorting, no leverage)
    FLAT = "flat"


class ExitPlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    take_profit_pct: float            # e.g. 0.025 = +2.5% from entry
    stop_loss_pct: float              # e.g. 0.015 = -1.5% from entry
    time_stop_s: int
    trailing_pct: float | None = None
    be_trigger_pct: float | None = None
    be_buffer_pct: float = 0.015
    lock_frac: float | None = None
    exit_order: Literal["maker_then_taker", "taker", "maker"] = "maker_then_taker"


class Opportunity(BaseModel):
    id: str
    ts_ns: int
    venue: str
    symbol: str
    strategy_id: str
    family: str
    direction: Direction = Direction.LONG
    hypothesis: str = ""
    ref_price: float
    horizon_s: int
    probability: float                # calibrated P(win)
    expected_gross_bps: float
    expected_cost_bps: float          # fees + spread + slippage (round trip)
    expected_net_bps: float
    expected_value_usd: float = 0.0
    max_capital_useful_usd: float = 0.0
    uncertainty: float = 1.0
    liquidity_score: float = 0.0
    regime: str = "UNKNOWN"
    regime_match: float = 0.0
    freshness: float = 1.0
    score: float = 0.0
    components: dict[str, float] = Field(default_factory=dict)
    exit_plan: ExitPlan
    evidence_refs: list[str] = Field(default_factory=list)
    expires_ns: int


class IntentPurpose(StrEnum):
    ENTRY = "entry"
    EXIT = "exit"
    CASHOUT = "cashout"
    EMERGENCY = "emergency"


class TradeIntent(BaseModel):
    id: str
    ts_ns: int
    book: str
    opportunity_id: str | None
    strategy_id: str
    venue: str
    symbol: str
    side: Literal["buy", "sell"]
    purpose: IntentPurpose
    requested_notional_usd: Decimal          # for sells: estimated USD value of base being sold
    base_size: Decimal | None = None         # sells specify base size
    order_type: Literal["market", "limit", "post_only"] = "post_only"
    limit_price: Decimal | None = None
    max_slippage_bps: Decimal = Decimal("25")
    thesis_expiry_ns: int | None = None
    exit_plan: ExitPlan | None = None
    position_id: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    idem_key: str


class RiskVerdict(StrEnum):
    APPROVE = "APPROVE"
    REDUCE = "REDUCE"
    REJECT = "REJECT"


class RiskDecision(BaseModel):
    intent_id: str
    verdict: RiskVerdict
    approved_notional_usd: Decimal = Decimal("0")
    approved_base_size: Decimal | None = None
    reasons: list[str] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"     # e.g. timeout after submit — must be reconciled, never assumed failed


TERMINAL = {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED}


class OrderRequest(BaseModel):
    client_order_id: str
    venue: str
    symbol: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "post_only"]
    quote_size: Decimal | None = None   # market buys by quote
    base_size: Decimal | None = None
    limit_price: Decimal | None = None


class OrderAck(BaseModel):
    client_order_id: str
    venue_order_id: str | None
    status: OrderStatus
    reject_reason: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class FillReport(BaseModel):
    venue: str
    trade_id: str
    client_order_id: str
    venue_order_id: str | None
    symbol: str
    side: Literal["buy", "sell"]
    price: Decimal
    size: Decimal
    fee: Decimal
    liquidity: Literal["maker", "taker", "unknown"] = "unknown"
    ts_ns: int


class OrderState(BaseModel):
    client_order_id: str
    venue_order_id: str | None
    symbol: str
    side: Literal["buy", "sell"]
    status: OrderStatus
    filled_size: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    fees: Decimal = Decimal("0")
    raw: dict[str, Any] = Field(default_factory=dict)
