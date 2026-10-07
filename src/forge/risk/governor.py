"""Deterministic Risk Governor (DOSSIER §22, DIRECTIVE §8, OP-004, OP-009 §6).

PROTECTED CORE: the evolution system, DeepSeek tools and generated strategies can never modify this
module, credential handling, hard spending ceilings, or emergency-stop behavior. The governor cannot
create profit-seeking orders — it can only approve, reduce, reject (and trigger breakers).
Every decision is fully explained (reasons + per-check booleans) and persisted by the caller.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from forge.domain.market import MarketRules
from forge.domain.trading import IntentPurpose, RiskDecision, RiskVerdict, TradeIntent
from forge.treasury.regimes import RegimePolicy

PROTECTED_MODULES = (
    "forge.risk.governor", "forge.risk.breakers", "forge.execution.gateway", "forge.ledger.ledger",
    "forge.config", "forge.venues.coinbase.auth", "forge.core.state",
)

TRADING_RUNNING = "RUNNING"
TRADING_STOPPED = "STOPPED"            # emergency stop: no new entries; exits per safe-stop policy only
TRADING_OBSERVE = "OBSERVE_ONLY"       # automatic: loss limit / breaker — research continues, no entries


@dataclass
class RiskContext:
    trading_state: str
    mode: str
    now_ns: int
    equity_usd: Decimal
    cash_available_usd: Decimal
    reserve_required_usd: Decimal
    exit_buffer_usd: Decimal
    deployed_usd: Decimal
    open_positions: int
    family_exposure_usd: dict[str, Decimal]
    policy: RegimePolicy
    treasury_snapshot_age_s: float
    reconciliation_ok: bool
    market_fresh: bool
    book_valid: bool
    spread_bps: float
    rules: MarketRules | None
    held_base_qty: Decimal = Decimal("0")
    daily_pnl_usd: Decimal = Decimal("0")
    day_start_equity_usd: Decimal = Decimal("0")
    breakers: set[str] = field(default_factory=set)
    expected_net_bps: float | None = None
    est_cost_bps: float | None = None
    leverage_enabled: bool = False
    daily_loss_limit_fraction: float = 0.15


class OrderRateLimiter:
    def __init__(self, max_per_minute: int) -> None:
        self.max = max_per_minute
        self.ts: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self.ts and now - self.ts[0] > 60:
            self.ts.popleft()
        return len(self.ts) < self.max

    def record(self) -> None:
        self.ts.append(time.monotonic())


class RiskGovernor:
    def __init__(self, max_orders_per_minute: int = 6, max_spread_bps_default: float = 30.0) -> None:
        self.rate = OrderRateLimiter(max_orders_per_minute)
        self.max_spread_bps_default = max_spread_bps_default

    def evaluate(self, intent: TradeIntent, ctx: RiskContext, max_spread_bps: float | None = None) -> RiskDecision:
        checks: dict[str, bool] = {}
        reasons: list[str] = []
        entry = intent.purpose == IntentPurpose.ENTRY
        notional = intent.requested_notional_usd

        def check(name: str, ok: bool, why: str) -> None:
            checks[name] = ok
            if not ok:
                reasons.append(why)

        # ---- global state ----
        if entry:
            check("trading_running", ctx.trading_state == TRADING_RUNNING, f"trading state {ctx.trading_state}")
        check("no_leverage", not ctx.leverage_enabled, "leverage disabled (Phase 1)")
        check("breakers_clear", not (ctx.breakers and entry), f"active breakers: {sorted(ctx.breakers)}")
        # ---- treasury truth ----
        check("treasury_fresh", ctx.treasury_snapshot_age_s <= 120, f"treasury snapshot {ctx.treasury_snapshot_age_s:.0f}s old")
        if entry:
            check("reconciled", ctx.reconciliation_ok, "reconciliation not OK — no new positions")
        # ---- market truth ----
        check("market_fresh", ctx.market_fresh, "stale market data")
        if entry:
            check("book_valid", ctx.book_valid, "order book invalid / awaiting snapshot")
            lim = max_spread_bps or self.max_spread_bps_default
            check("spread_ok", ctx.spread_bps <= lim, f"spread {ctx.spread_bps:.1f}bps > {lim:.1f}")
            check("costs_estimated", ctx.est_cost_bps is not None and ctx.expected_net_bps is not None,
                  "missing fee/slippage estimate")
            if ctx.expected_net_bps is not None:
                check("positive_net_edge", ctx.expected_net_bps > 0, f"expected net edge {ctx.expected_net_bps:.1f}bps ≤ 0")
        # ---- loss limits (OP-004) ----
        if entry and ctx.day_start_equity_usd > 0:
            dd = float(ctx.daily_pnl_usd / ctx.day_start_equity_usd)
            check("daily_loss_limit", dd > -ctx.daily_loss_limit_fraction,
                  f"daily loss {dd:.1%} breached −{ctx.daily_loss_limit_fraction:.0%}")
        # ---- venue rules ----
        rules = ctx.rules
        check("rules_known", rules is not None, "unknown market rules")
        if rules is not None:
            check("market_tradable", rules.tradable(), f"market {rules.symbol} not tradable ({rules.status})")
            if intent.order_type == "market":
                check("market_orders_allowed", not (rules.limit_only or rules.post_only_only), "venue: limit-only")
        # ---- sizing ----
        approved = notional
        if entry:
            check("concurrency", ctx.open_positions < ctx.policy.max_concurrent_positions,
                  f"max concurrent positions {ctx.policy.max_concurrent_positions} reached")
            deployable = ctx.cash_available_usd - ctx.reserve_required_usd - ctx.exit_buffer_usd
            cap_pos = (ctx.equity_usd - ctx.reserve_required_usd) * Decimal(str(ctx.policy.max_position_fraction))
            fam = intent.evidence.get("family", "")
            fam_cap = (ctx.equity_usd * Decimal(str(ctx.policy.max_family_fraction))) - ctx.family_exposure_usd.get(fam, Decimal(0))
            limit = min(deployable, cap_pos, fam_cap)
            if approved > limit:
                approved = max(Decimal("0"), limit)
            check("within_cash", approved > 0, f"no deployable cash (deployable {deployable:.2f}, cap {cap_pos:.2f})")
            if rules is not None:
                approved = rules.round_quote(approved)
                check("venue_minimum", approved >= rules.quote_min_size,
                      f"size {approved} < venue minimum {rules.quote_min_size}")
            check("order_rate", self.rate.allow(), "order rate limit")
        else:
            # exits/cash-outs: may only sell what is actually held (no shorting)
            if intent.side == "sell" and intent.base_size is not None:
                check("held_quantity", intent.base_size <= ctx.held_base_qty + Decimal("1e-12"),
                      f"sell {intent.base_size} > held {ctx.held_base_qty}")
        if reasons:
            return RiskDecision(intent_id=intent.id, verdict=RiskVerdict.REJECT, reasons=reasons, checks=checks)
        verdict = RiskVerdict.APPROVE if approved >= notional else RiskVerdict.REDUCE
        if verdict == RiskVerdict.REDUCE:
            reasons.append(f"reduced {notional} → {approved}")
        if entry:
            self.rate.record()
        base = intent.base_size
        if base is not None and rules is not None:
            base = rules.round_base(min(base, ctx.held_base_qty) if intent.side == "sell" else base)
        return RiskDecision(intent_id=intent.id, verdict=verdict, approved_notional_usd=approved.quantize(
            Decimal("0.00000001"), rounding=ROUND_DOWN), approved_base_size=base, reasons=reasons, checks=checks)
