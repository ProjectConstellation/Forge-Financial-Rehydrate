"""FORGE runtime — two permanent concurrent loops (OP-007) on live real-time data (OP-005).

EARNING LOOP     live market → bar close → features/regimes → strategy signals → opportunities (velocity, half-life,
                 calibrated confidence) → sizing → deterministic Risk Governor → execution → positions → ledger
IMPROVEMENT LOOP evolution search (local bounded / Modal burst) → promotion gate → shadow → challenger → production;
                 counterfactual learning; calibration; brain (DeepSeek) research & diagnosis
Always at least one of: EARNING → LEARNING → PREPARING TO EARN BETTER.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import os
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import numpy as np

from forge.audit.journal import AuditJournal
from forge.config import Mode, Settings
from forge.core import state as tstate
from forge.core.bus import EventBus, Topic
from forge.core.ids import idempotency_key, new_id
from forge.core.supervisor import Supervisor
from forge.domain.market import d
from forge.domain.trading import ExitPlan, IntentPurpose, RiskVerdict, TradeIntent
from forge.evolution.arena import Arena
from forge.execution.gateway import ExecutionGateway, MarketView
from forge.ledger.ledger import Ledger
from forge.market_data.history import CandleStore
from forge.market_data.live import BarEngine, LiveMarket, select_universe
from forge.persistence.db import Database, dumps
from forge.research.backtest import CostModel
from forge.research.calibration import CalibrationEngine
from forge.risk.breakers import BreakerBoard
from forge.risk.governor import RiskContext, RiskGovernor
from forge.strategies.genome import Genome, barrier_pcts, compile_entries
from forge.strategies.registry import ACTIVE_LIVE, ACTIVE_OBSERVING, State, StrategyRegistry
from forge.treasury.regimes import CapitalRegimeEngine
from forge.treasury.sizing import size_position
from forge.treasury.velocity import OpportunityCostEngine, assess, utilization_pressure
from forge.venues.base import FeeSchedule
from forge.venues.coinbase.adapter import CoinbaseAdapter
from forge.venues.coinbase.auth import CdpSigner
from forge.venues.coinbase.rest import CoinbaseRest
from forge.venues.coinbase.ws import CoinbaseMarketStream
from forge.venues.paper import PaperVenue

log = logging.getLogger("forge.runtime")
INTERVALS = (300, 3600)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Forge:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        settings.ensure_dirs()
        self.db = Database(settings.db_path)
        self.db.migrate()
        self.audit = AuditJournal(settings.audit_dir)
        self.ledger = Ledger(self.db)
        self.reg = StrategyRegistry(self.db)
        self.arena = Arena(self.db, self.reg)
        self.calib = CalibrationEngine(self.db)
        self.capital = CapitalRegimeEngine(self.db, float(settings.treasury.reserve_at_or_above_100.hard_floor_usd),
                                           float(settings.treasury.reserve_at_or_above_100.threshold_usd))
        self.hurdle = OpportunityCostEngine(self.db)
        self.breakers = BreakerBoard()
        self.governor = RiskGovernor(settings.risk.max_orders_per_minute, float(settings.risk.max_slippage_bps_default) + 5)
        self.bus = EventBus()
        self.market = LiveMarket()
        self.store = CandleStore(settings.market_dir)
        self.stop_event = asyncio.Event()
        self.started = time.time()
        self.book = {Mode.LIVE: "live", Mode.PAPER: "paper"}.get(settings.mode, "shadow")
        signer = None
        if settings.secrets.coinbase_key_name and settings.secrets.coinbase_key_secret:
            signer = CdpSigner(settings.secrets.coinbase_key_name, settings.secrets.coinbase_key_secret)
        self.rest = CoinbaseRest(settings.venues.coinbase.rest_base, signer=signer)
        self.coinbase = CoinbaseAdapter(self.rest)
        self.fees = FeeSchedule(settings.venues.coinbase.default_maker_fee, settings.venues.coinbase.default_taker_fee,
                                "assumed", "config")
        self.stream = CoinbaseMarketStream([], self.market, signer=signer, url=settings.venues.coinbase.ws_url)
        self.bars = {i: BarEngine(self.rest, self.store, i, on_close=self.on_bars) for i in INTERVALS}
        self.universe: list[str] = []
        self.venue: Any = None
        self.gateway: ExecutionGateway | None = None
        self.treasury: dict[str, Any] = {"equity_usd": 0.0, "cash_usd": 0.0, "ts": 0.0}
        self.day = {"date": None, "start_equity": 0.0}
        self.reconciled_ok = True
        self.cooldown: dict[tuple[str, str], float] = {}
        self.agent_status: dict[str, dict[str, Any]] = {}
        self.breadth: dict[str, Any] = {"up_frac": 0.0, "n": 0, "btc_regime": "UNKNOWN"}
        self.events: deque[dict[str, Any]] = deque(maxlen=500)
        self.tasks: list[asyncio.Task[Any]] = []
        self.pool: ProcessPoolExecutor | None = None
        self.improvement_runs = 0
        self.brain: Any = None          # attached by forge.brain (DeepSeek) when available
        self.compute: Any = None        # attached by forge.compute (Modal) when available
        self.sup = Supervisor()

    # ================================================================== narration / status
    async def say(self, agent: str, message: str, level: str = "info", **data: Any) -> None:
        ev = {"ts": _now(), "agent": agent, "level": level, "message": message, "data": data}
        self.events.append(ev)
        self.db.insert("timeline", {"ts": ev["ts"], "agent": agent, "level": level, "message": message[:1000],
                                    "data": dumps(data) if data else None})
        await self.bus.publish(Topic.TIMELINE, ev, source=agent)

    def status(self, agent: str, text: str, **extra: Any) -> None:
        self.agent_status[agent] = {"text": text, "ts": _now(), **extra}

    # ================================================================== startup
    async def start(self) -> None:
        await self.say("Forge", f"FORGE starting — mode {self.s.mode.value}, book '{self.book}', "
                                f"live trading flag {'ON' if self.s.live_trading else 'OFF'}")
        self.audit.append("FORGE_START", {"mode": self.s.mode.value, "book": self.book, "pid": os.getpid()})
        n = self.arena.bootstrap()
        if n:
            await self.say("Evolution Arena", f"Seeded {n} strategy families into the population (EXPERIMENTAL)")
        await self._discover()
        await self._init_treasury()
        self._init_execution()
        for eng in self.bars.values():
            eng.load_history(self.universe)
            eng.recompute(self.universe)
        self.stream.set_symbols(self.universe[: self.s.venues.coinbase.ws_symbols_max])
        self.pool = ProcessPoolExecutor(max_workers=1)     # research worker (≤1 core; Modal for bursts)
        B = self.sup.add
        B("market_stream", self.stream.run, 180, critical=True)
        B("feed_watch", self._feed_watch, 120)
        B("execution", self._exec_loop, 90, critical=True)
        B("treasury", self._treasury_loop, 180, critical=True)
        B("backfill", self._backfill_loop, 4 * 3600)
        B("universe", self._universe_loop, 3 * 3600)
        B("improvement", self._improvement_loop, 1800)
        B("arena_review", self._review_loop, 1200)
        B("counterfactual", self._counterfactual_loop, 2400)
        B("self_review", self._housekeeping_loop, 3 * 3600)
        for i, eng in self.bars.items():
            B(f"bars_{i}", (lambda e=eng, n=f"bars_{i}": e.run(lambda: self.universe, self.stop_event,
                                                                beat=lambda: self.sup.beat(n))), i + 900)
        if self.brain is not None:
            B("brain", lambda: self.brain.run(self), 3600)
            from forge.brain.sentinel import BalanceSentinel
            self.sentinel = BalanceSentinel(self)
            B("balance_sentinel", self.sentinel.run, 1200)
        if self.compute is not None:
            B("compute", lambda: self.compute.run(self), 900)
        self.sup.on_restart = self._on_loop_restart
        self.tasks = self.sup.start()
        self.tasks.append(asyncio.create_task(self.sup.watch(self.stop_event), name="supervisor"))
        await self.say("Forge", f"All loops running under supervision: {len(self.sup.loops)} loops + watchdog — "
                                "EARNING + IMPROVEMENT loops active 24/7")

    async def _on_loop_restart(self, name: str, why: str) -> None:
        await self.say("Supervisor", f"Loop '{name}' restarted automatically: {why}", level="warn")
        self.audit.append("LOOP_RESTART", {"loop": name, "why": why})

    async def _feed_watch(self) -> None:
        while not self.stop_event.is_set():
            q = self.stream.quality
            if q.last_message_ns and time.time_ns() - q.last_message_ns < 60e9:
                self.sup.beat("market_stream")
            self.sup.beat("feed_watch")
            await asyncio.sleep(10)

    async def _discover(self) -> None:
        try:
            perms = await self.coinbase.discover_permissions()
            products = await self.coinbase.list_products()
            for p in products:
                self.market.rules[p.symbol] = p.rules
                self.market.products[p.symbol] = p
            if self.rest.authenticated:
                self.fees = await self.coinbase.get_fees()
            policy = self.capital.policy(float(self.treasury.get("equity_usd") or self.s.treasury.initial_capital_usd))
            active_syms = set()
            for g, _, _ in self.reg.list(ACTIVE_OBSERVING):
                if g.universe.symbols != "dynamic":
                    active_syms |= set(g.universe.symbols)
            self.universe = select_universe(products, self.s.venues.coinbase.universe_max,
                                            max(policy.min_liquidity_usd_24h, 1_000_000), active_syms)
            await self.say("Market Scout", f"Discovered {len(products)} Coinbase products; universe = {len(self.universe)} "
                                           f"liquid USD markets; fees {self.fees.tier}: maker {float(self.fees.maker):.2%} / "
                                           f"taker {float(self.fees.taker):.2%}; key perms view={perms.get('can_view')} "
                                           f"trade={perms.get('can_trade')} transfer={perms.get('can_transfer')}")
        except Exception as e:
            log.exception("discovery failed")
            await self.say("Market Scout", f"Discovery degraded: {e}", level="warn")
            self.universe = self.universe or ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD"]

    async def _init_treasury(self) -> None:
        if self.book == "live":
            bals = await self.coinbase.get_balances()
            marks = await self._marks_rest({b.asset for b in bals if b.total > 0})
            if not self.db.kv_get("live.opened"):
                # OP-001: the whole account balance is the treasury — adopt it as opening balances
                for b in bals:
                    if b.total <= 0:
                        continue
                    if b.asset in ("USD", "USDC"):
                        self.ledger.deposit("live", b.total, asset=b.asset, memo="opening balance (OP-001)", ref_id=f"open-{b.asset}")
                    elif b.asset in marks:
                        self.ledger.opening_asset("live", "coinbase", b.asset, b.total, b.total * d(marks[b.asset]), f"open-{b.asset}")
                self.db.kv_set("live.opened", _now())
                self.audit.append("TREASURY_OPENED", {"book": "live", "assets": [b.asset for b in bals if b.total > 0]})
        elif self.book == "paper":
            if not self.db.kv_get("paper.opened"):
                seed = d(self.s.treasury.initial_capital_usd)
                if self.rest.authenticated:
                    with contextlib.suppress(Exception):
                        usd = sum((b.total for b in await self.coinbase.get_balances() if b.asset in ("USD", "USDC")), Decimal(0))
                        seed = usd if usd > 0 else seed
                self.ledger.deposit("paper", seed, memo="paper treasury mirrors live balance (OP-001)", ref_id="paper-open")
                self.db.kv_set("paper.opened", _now())
                await self.say("Accountant", f"Paper treasury opened with ${seed} (mirrors the live Coinbase balance)")
        self._snapshot_treasury()

    async def _marks_rest(self, assets: set[str]) -> dict[str, float]:
        out = {}
        for a in assets:
            if a in ("USD", "USDC"):
                continue
            p = self.market.products.get(f"{a}-USD")
            if p and p.price:
                out[a] = p.price
        return out

    def _init_execution(self) -> None:
        if self.book == "paper":
            st = self.ledger.state("paper")
            bal = {"USD": st.cash_usd}
            for (_, asset), h in st.holdings.items():
                bal[asset] = h.qty
            self.venue = PaperVenue(self.fees, self.market.get_rules, self.market.get_bbo, self.market.get_book, bal)
            self.market.listeners.append(self.venue.on_market)
        elif self.book == "live":
            self.venue = self.coinbase
        if self.venue is not None:
            self.gateway = ExecutionGateway(self.db, self.ledger, self.venue, self.book,
                                            MarketView(self.market.get_bbo, self.market.get_rules), self.audit, self.breakers,
                                            on_event=self._exec_event, on_position_closed=self._on_closed,
                                            taker_fee=float(self.fees.taker), maker_fee=float(self.fees.maker))

    # ================================================================== treasury truth
    def _snapshot_treasury(self) -> dict[str, Any]:
        book = self.book if self.book in ("live", "paper") else "paper"
        st = self.ledger.state(book)
        summ = st.summary(self.market.marks())
        eq = float(summ["equity_usd"])
        self.treasury = {**{k: (float(v) if isinstance(v, Decimal) else v) for k, v in summ.items()}, "ts": time.time()}
        today = datetime.now(UTC).date().isoformat()
        if self.day["date"] != today:
            self.day = {"date": today, "start_equity": eq}
            with contextlib.suppress(Exception):
                tstate.clear_observe(self.db, self.audit, "new trading day")
        self.treasury["daily_pnl_usd"] = eq - float(self.day["start_equity"] or eq)
        pol = self.capital.policy(max(eq, 0.01))
        self.treasury["regime"] = pol.as_dict()
        self.treasury["reserve_usd"] = self.capital.reserve_usd(eq)
        return self.treasury

    async def _treasury_loop(self) -> None:
        n = 0
        while not self.stop_event.is_set():
            n += 1
            self.sup.beat("treasury")
            t = self._snapshot_treasury()
            if self.book == "live" and n % 4 == 0:
                await self._reconcile_live()
            eq0 = float(self.day["start_equity"] or 0)
            if eq0 > 0 and t["daily_pnl_usd"] / eq0 <= -float(self.s.risk.daily_drawdown_breaker_fraction):
                if tstate.trading_state(self.db) == "RUNNING":
                    tstate.observe_only(self.db, self.audit, f"daily loss {t['daily_pnl_usd']:.2f} breached limit")
                    await self.say("Risk Governor", "Daily loss limit reached → OBSERVE_ONLY; Improvement Loop escalated "
                                                    "(postmortem + challenger research)", level="warn")
                    if self.brain is not None:
                        await self.brain.escalate(self, "daily_loss_limit", {"treasury": t})
            self.status("Accountant", f"equity ${t['equity_usd']:.2f} · true net ${t['true_net_usd']:+.4f}")
            await asyncio.sleep(15)

    async def _reconcile_live(self) -> None:
        """Wallet-truth: ledger cash vs Coinbase balances (research lesson: books drift from wallets)."""
        try:
            bals = {b.asset: b.total for b in await self.coinbase.get_balances()}
        except Exception as e:
            self.reconciled_ok = False
            log.warning("reconcile failed: %s", e)
            return
        st = self.ledger.state("live")
        issues = []
        for asset, ledger_amt in st.cash.items():
            venue_amt = bals.get(asset, Decimal(0))
            if abs(venue_amt - ledger_amt) > Decimal("0.05"):
                issues.append(f"{asset}: ledger {ledger_amt} vs venue {venue_amt}")
        for (_, asset), h in st.holdings.items():
            venue_amt = bals.get(asset, Decimal(0))
            if h.qty > 0 and abs(venue_amt - h.qty) / max(h.qty, Decimal("1e-12")) > Decimal("0.01"):
                issues.append(f"{asset}: ledger qty {h.qty} vs venue {venue_amt}")
        self.reconciled_ok = not issues
        if issues:
            self.breakers.record("balance_mismatch", "; ".join(issues)[:300])
            await self.say("Accountant", f"Reconciliation mismatch: {'; '.join(issues)[:300]}", level="error")

    # ================================================================== EARNING LOOP
    async def on_bars(self, interval: int, symbols: list[str]) -> None:
        eng = self.bars[interval]
        if interval == 300:
            up = tot = 0
            for st_ in eng.state.values():
                if st_.features and "ema_gap_slow" in st_.features:
                    v1, v2 = st_.features["ema_gap_slow"][-1], st_.features["ret_288"][-1]
                    if v1 == v1 and v2 == v2:
                        tot += 1
                        up += int(v1 > 0 and v2 > 0)
            btc = eng.state.get("BTC-USD")
            self.breadth = {"up_frac": up / tot if tot else 0.0, "n": tot,
                            "btc_regime": btc.regime if btc else "UNKNOWN"}
        self.status("Market Scout", f"{len(symbols)} new {interval // 60}m bars · {len(self.universe)} markets watched")
        strategies = [(g, st) for g, st, _ in self.reg.list(ACTIVE_OBSERVING) if g.interval_s == interval]
        if not strategies:
            return
        found = 0
        for sym in symbols:
            ss = eng.state.get(sym)
            if ss is None or not ss.features:
                continue
            for g, st in strategies:
                if g.universe.symbols != "dynamic" and sym not in g.universe.symbols:
                    continue
                try:
                    sig = compile_entries(g, ss.features, ss.probs)
                except KeyError:
                    continue
                if not sig[-1] or time.time() < self.cooldown.get((g.id, sym), 0):
                    continue
                self.cooldown[(g.id, sym)] = time.time() + max(g.cooldown_bars, 1) * interval
                found += 1
                await self._opportunity(g, st, sym, ss, interval)
        if found:
            self.status("Opportunity Engine", f"{found} signals on last {interval // 60}m close")

    async def _opportunity(self, g: Genome, st: State, sym: str, ss: Any, interval: int) -> None:
        f = ss.features
        close = float(ss.series.last("close"))
        atr = float(f["atr_14"][-1])
        if not math.isfinite(atr) or close <= 0:
            return
        tp, sl = barrier_pcts(g, atr)
        mf, tf = float(self.fees.maker), float(self.fees.taker)
        micro = self.market.micro(sym)
        spread = micro.get("spread_bps") if math.isfinite(micro.get("spread_bps", float("nan"))) else 10.0
        cost_win = (mf if g.execution.entry == "maker" else tf + spread / 2e4) + mf
        cost_loss = (mf if g.execution.entry == "maker" else tf + spread / 2e4) + tf + 0.0003
        ev = self.arena.evidence(g.id)
        raw_p = ev.p_win if ev else 0.5
        win = ev.avg_win if ev and ev.avg_win > 0 else tp - cost_win
        loss = ev.avg_loss if ev and ev.avg_loss < 0 else -(sl + cost_loss)
        cls = f"strategy:{g.family}"
        p_cal, n_cal = self.calib.calibrate(cls, raw_p)
        p_use = p_cal if n_cal >= 20 else 0.5 * raw_p + 0.5 * p_cal
        hold_h = ev.avg_hold_h if ev and ev.avg_hold_h > 0 else g.exit.time_stop_bars * interval / 3600 * 0.5
        eq = float(self.treasury.get("equity_usd") or 0)
        pol = self.capital.policy(max(eq, 0.01))
        free = max(0.0, float(self.treasury.get("cash_usd") or 0) - self.capital.reserve_usd(eq))
        pressure = utilization_pressure(free, free * 0.5 + 1e-9)
        va = assess(p_use, win, loss, hold_h, self.hurdle.hurdle(pol.hurdle_multiplier), pressure)
        half_life_s = max(interval, g.execution.maker_ttl_bars * interval)
        exp_net_bps = va.expected_return * 1e4
        score = va.adjusted_return * 1e4 * (0.5 + p_use) * (1 + va.capital_velocity_score)
        oid = new_id("opp")
        now_ns = time.time_ns()
        comps = {"p_raw": raw_p, "p_cal": p_cal, "p_used": p_use, "win": win, "loss": loss, "tp": tp, "sl": sl,
                 "hold_h": hold_h, "velocity_per_day": va.velocity_per_day, "hurdle_per_day": va.hurdle_per_h * 24,
                 "opportunity_cost": va.opportunity_cost_frac, "adjusted_return": va.adjusted_return,
                 "velocity_score": va.capital_velocity_score, "half_life_s": half_life_s, "spread_bps": spread,
                 "regime_conf": ss.regime_conf, "evidence_n": ev.n if ev else 0, "p_edge": ev.p_edge if ev else 0.0}
        self.db.insert("opportunities", {
            "id": oid, "ts": _now(), "ts_ns": now_ns, "venue": "coinbase", "symbol": sym, "strategy_id": g.id,
            "family": g.family, "direction": "long", "score": float(score), "expected_net_bps": float(exp_net_bps),
            "probability": float(p_use), "components": dumps(comps), "status": "NEW", "ref_price": f"{close:.10g}",
            "horizon_s": int(g.exit.time_stop_bars * interval), "expires_ns": now_ns + int(half_life_s * 1e9)})
        await self.bus.publish(Topic.OPPORTUNITY_FOUND, {"id": oid, "symbol": sym, "strategy": g.id, "score": score})
        # ---- routing by state ----
        tradable = ACTIVE_LIVE + ((State.SHADOW,) if self.book == "paper" else ())
        if st not in tradable or self.gateway is None:
            self._set_opp(oid, "OBSERVED", f"{st.value}: shadow observation (would-be trade)")
            return
        if self.db.kv_get(f"strategy.sleeve.{g.id}") == "beta":
            b = self.breadth
            if b["up_frac"] < 0.55 or b["btc_regime"] in ("TREND_DOWN", "PANIC_SELLING"):
                self._set_opp(oid, "REJECTED", f"beta sleeve kill switch: breadth {b['up_frac']:.0%} up, BTC {b['btc_regime']}")
                return
        if va.adjusted_return <= 0:
            self._set_opp(oid, "REJECTED", va.rationale)
            await self.say("Allocator", f"{sym} {g.family}: WAIT — {va.rationale}", strategy=g.id, opportunity=oid)
            return
        await self._allocate_and_execute(g, st, sym, oid, p_use, win, loss, tp, sl, interval, va, spread, ev, pol)

    def _set_opp(self, oid: str, status: str, reason: str) -> None:
        self.db.execute("UPDATE opportunities SET status = ?, reason = ? WHERE id = ?", (status, reason[:500], oid))

    async def _allocate_and_execute(self, g: Genome, st: State, sym: str, oid: str, p: float, win: float, loss: float,
                                    tp: float, sl: float, interval: int, va: Any, spread: float, ev: Any, pol: Any) -> None:
        eq = float(self.treasury.get("equity_usd") or 0)
        reserve = self.capital.reserve_usd(eq)
        deployable = max(0.0, float(self.treasury.get("cash_usd") or 0) - reserve)
        sz = size_position(p, win, loss, ev.n if ev else 0, g.sizing.kelly_mult, g.sizing.max_fraction,
                           pol.max_position_fraction, deployable, st.value, self.breakers.size_multiplier(),
                           va.capital_velocity_score)
        if sz.notional_usd < 1.0:
            self._set_opp(oid, "REJECTED", f"size ${sz.notional_usd:.2f} below $1 venue minimum — {sz.explanation}")
            return
        plan = ExitPlan(take_profit_pct=tp, stop_loss_pct=sl, time_stop_s=int(g.exit.time_stop_bars * interval),
                        be_trigger_pct=g.exit.be_trigger_pct, be_buffer_pct=g.exit.be_buffer_pct, lock_frac=g.exit.lock_frac,
                        trailing_pct=(g.exit.trail_atr * float(self.bars[interval].state[sym].features["atr_14"][-1]))
                        if g.exit.trail_atr else None)
        intent = TradeIntent(id=new_id("int"), ts_ns=time.time_ns(), book=self.book, opportunity_id=oid, strategy_id=g.id,
                             venue="coinbase", symbol=sym, side="buy", purpose=IntentPurpose.ENTRY,
                             requested_notional_usd=d(round(sz.notional_usd, 2)),
                             order_type="post_only" if g.execution.entry == "maker" else "market",
                             max_slippage_bps=d(g.execution.max_spread_bps), exit_plan=plan,
                             evidence={"family": g.family, "p": p, "sizing": sz.explanation},
                             idem_key=idempotency_key(oid, g.id))
        open_pos = self.db.query("SELECT strategy_id, cost_usd FROM positions WHERE book = ? AND status != 'CLOSED'", (self.book,))
        fam_exp: dict[str, Decimal] = {}
        for r in open_pos:
            gg = self.reg.get(r["strategy_id"])
            if gg:
                fam_exp[gg.family] = fam_exp.get(gg.family, Decimal(0)) + Decimal(r["cost_usd"])
        ctx = RiskContext(trading_state=tstate.trading_state(self.db), mode=self.s.mode.value, now_ns=time.time_ns(),
                          equity_usd=d(eq), cash_available_usd=d(self.treasury.get("cash_usd") or 0),
                          reserve_required_usd=d(round(reserve, 8)), exit_buffer_usd=d(round(sz.notional_usd * float(self.fees.taker), 8)),
                          deployed_usd=d(self.treasury.get("deployed_usd") or 0), open_positions=len(open_pos),
                          family_exposure_usd=fam_exp, policy=pol, treasury_snapshot_age_s=time.time() - self.treasury["ts"],
                          reconciliation_ok=self.reconciled_ok, market_fresh=self.market.fresh(sym, self.s.risk.stale_market_ms),
                          book_valid=bool(self.market.get_book(sym) and self.market.get_book(sym).valid) or self.book == "paper",
                          spread_bps=spread, rules=self.market.get_rules(sym), daily_pnl_usd=d(round(self.treasury.get("daily_pnl_usd", 0), 8)),
                          day_start_equity_usd=d(round(self.day["start_equity"] or eq, 8)), breakers=self.breakers.blocking(),
                          expected_net_bps=va.adjusted_return * 1e4, est_cost_bps=(-loss - sl) * 1e4,
                          daily_loss_limit_fraction=float(self.s.risk.daily_drawdown_breaker_fraction))
        dec = self.governor.evaluate(intent, ctx, max_spread_bps=g.execution.max_spread_bps)
        self.db.insert("trade_intents", {"id": intent.id, "ts": _now(), "book": self.book, "opportunity_id": oid,
                                         "strategy_id": g.id, "venue": "coinbase", "symbol": sym, "side": "buy", "purpose": "entry",
                                         "requested_notional": str(intent.requested_notional_usd),
                                         "approved_notional": str(dec.approved_notional_usd), "order_type": intent.order_type,
                                         "max_slippage_bps": str(intent.max_slippage_bps), "exit_plan": dumps(plan.model_dump()),
                                         "evidence": dumps(intent.evidence), "status": dec.verdict.value, "idem_key": intent.idem_key},
                       or_ignore=True)
        self.db.insert("risk_decisions", {"intent_id": intent.id, "ts": _now(), "decision": dec.verdict.value,
                                          "approved_notional": str(dec.approved_notional_usd), "reasons": dumps(dec.reasons),
                                          "checks": dumps(dec.checks)})
        if dec.verdict == RiskVerdict.REJECT:
            self._set_opp(oid, "REJECTED", "risk: " + "; ".join(dec.reasons))
            await self.say("Risk Governor", f"REJECTED {sym} {g.family}: {'; '.join(dec.reasons)[:200]}", strategy=g.id)
            return
        if self.book == "live":
            self.audit.append("RISK_DECISION", {"intent": intent.id, "verdict": dec.verdict.value,
                                                "notional": str(dec.approved_notional_usd), "reasons": dec.reasons})
        pid = await self.gateway.execute_entry(intent, dec, ttl_s=g.execution.maker_ttl_bars * interval,
                                               maker_offset_bps=g.execution.maker_offset_bps, entry_style=g.execution.entry,
                                               meta={"family": g.family, "p": p, "win": win, "loss": loss, "class": f"strategy:{g.family}",
                                                     "state": st.value, "interval": interval, "velocity": va.velocity_per_day})
        self._set_opp(oid, "ACTED" if pid else "REJECTED", f"{dec.verdict.value} ${dec.approved_notional_usd} → {pid}")
        if pid:
            await self.say("Execution Engine", f"{'LIVE' if self.book == 'live' else 'PAPER'} BUY {sym} ${dec.approved_notional_usd} "
                                               f"({g.family}, {st.value}, p={p:.2f}, TP {tp:+.2%} / SL {-sl:.2%}) — {va.rationale}",
                           strategy=g.id, position=pid)

    async def _exec_event(self, kind: str, data: dict[str, Any]) -> None:
        await self.bus.publish(Topic.ORDER_FILLED if kind == "ORDER_FILLED" else Topic.TIMELINE, data)
        if kind == "PROFIT_LOCK":
            await self.say("Execution Engine", f"PROFIT LOCKED on {data['symbol']}: peak +{data['peak_gain']:.2%} → stop raised to "
                                               f"breakeven+fees or better; this trade can no longer turn into a loss")
        if kind == "POSITION_OPENED":
            await self.say("Execution Engine", f"Position opened {data['symbol']} qty {data['qty']} cost ${float(data['cost']):.2f}")

    async def _on_closed(self, info: dict[str, Any]) -> None:
        meta = info.get("meta", {})
        win = float(info["net_usd"]) > 0
        self.calib.record(meta.get("class", "strategy:unknown"), float(meta.get("p", 0.5)), win, self.book, info["strategy_id"])
        self.hurdle.observe(float(info["net_return"]), max(float(info["hold_hours"]), 0.1), weight=1.0)
        self.hurdle.flush()
        await self.say("Accountant", f"Position closed {info['symbol']} ({info['reason']}): true net ${float(info['net_usd']):+.4f} "
                                     f"({info['net_return']:+.2%}) after {info['hold_hours']:.1f}h", strategy=info["strategy_id"])
        if self.brain is not None and not win:
            await self.brain.on_loss(self, info)

    async def _exec_loop(self) -> None:
        cancelled_for_stop = False
        while not self.stop_event.is_set():
            self.sup.beat("execution")
            ts = tstate.trading_state(self.db)
            if ts == "STOPPED" and not cancelled_for_stop and self.gateway:
                n = await self.gateway.cancel_all_entries()
                st = tstate.get_state(self.db)
                if st.get("safe_stop_policy") == "flatten_when_safe":
                    await self.gateway.liquidate("EMERGENCY")
                await self.say("Risk Governor", f"STOP ALL TRADING active — cancelled {n} pending entries; "
                                                f"policy {st.get('safe_stop_policy')}", level="warn")
                cancelled_for_stop = True
            elif ts != "STOPPED":
                cancelled_for_stop = False
            req = self.db.kv_get("cashout.request")
            if req and self.gateway:
                await self._handle_cashout(req)
            if self.gateway:
                try:
                    await self.gateway.tick(ts)
                except Exception:
                    log.exception("execution tick failed")
            await asyncio.sleep(2)

    async def _handle_cashout(self, req: dict[str, Any]) -> None:
        """OP-003 Stage 1: operator-initiated liquidation to USD (Trade permission only; never LLM/strategy initiated)."""
        assert self.gateway is not None
        self.db.kv_set("cashout.request", None)
        n_cancel = await self.gateway.cancel_all_entries()
        amount = str(req.get("amount", "all")).lower()
        cash = float(self.treasury.get("cash_usd") or 0)
        target = None if amount == "all" else float(amount)
        n = 0
        if target is None or target > cash:
            n = await self.gateway.liquidate("CASHOUT")
        if amount == "all":
            tstate.stop_all(self.db, self.audit, actor="cashout", reason="cash-out all: entries paused",
                            safe_stop_policy="keep_exits")
        self.audit.append("CASHOUT_EXECUTED", {"request": req, "cancelled_entries": n_cancel, "liquidated_positions": n})
        await self.say("Accountant", f"Cash-out ({amount}, {req.get('urgency')}): cancelled {n_cancel} pending entries, "
                                     f"liquidating {n} positions to USD. When complete, use Coinbase 'Cash out' to move USD "
                                     f"to your bank/card (FORGE's key has no transfer permission by design).", level="warn")

    async def _universe_loop(self) -> None:
        while not self.stop_event.is_set():
            self.sup.beat("universe")
            await asyncio.sleep(3600)
            await self._discover()
            for eng in self.bars.values():
                eng.load_history(self.universe)
            self.stream.set_symbols(self.universe[: self.s.venues.coinbase.ws_symbols_max])

    async def _backfill_loop(self) -> None:
        """Keep research history deep: 5m×60d and 1h×365d for the universe (public data, no credentials)."""
        from forge.market_data.history import backfill
        depth = {300: 60, 3600: 365}
        while not self.stop_event.is_set():
            for interval, days in depth.items():
                have = set(self.store.symbols(interval))
                todo = [s for s in self.universe if s not in have]
                if todo:
                    self.status("Data Engine", f"backfilling {len(todo)} × {interval // 60}m history")
                for s in todo:
                    self.sup.beat("backfill")
                    if self.stop_event.is_set():
                        return
                    try:
                        await backfill(self.rest, self.store, s, interval, days)
                    except Exception as e:
                        log.warning("backfill %s: %s", s, e)
                if todo:
                    await self.say("Data Engine", f"History ready: {len(todo)} new markets × {interval // 60}m ({days}d)")
                    self.bars[interval].state.clear()
                    self.bars[interval].load_history(self.universe)
                    self.bars[interval].recompute(self.universe)
            self.sup.beat("backfill")
            await asyncio.sleep(3600)

    # ================================================================== IMPROVEMENT LOOP
    async def _improvement_loop(self) -> None:
        """Continuous evolution: alternating horizons; local bounded worker (Modal bursts when attached)."""
        await asyncio.sleep(60)
        k = 0
        while not self.stop_event.is_set():
            self.sup.beat("improvement")
            interval = INTERVALS[k % len(INTERVALS)]
            k += 1
            self.status("Evolution Arena", f"evolving {interval // 60}m strategies")
            try:
                parents = [g for g, _, _ in self.reg.list((State.PRODUCTION, State.CHALLENGER, State.SHADOW, State.EXPERIMENTAL))
                           if g.interval_s == interval]
                parents = sorted(parents, key=lambda g: -(self.db.scalar("SELECT COALESCE(fitness,-9) FROM strategies WHERE id=?", (g.id,)) or -9))[:30]
                near_ids = [x["id"] for x in (self.db.kv_get("evolution.near_miss", []) or []) if x["interval"] == interval]
                racing = [g for g in (self.reg.get(i) for i in near_ids) if g is not None]
                parents = racing + [g for g in parents if g.id not in set(near_ids)]     # near-miss racing first
                queue = self.db.kv_get("brain.candidate_queue", []) or []
                llm = [q["genome"] for q in queue if q["genome"].get("interval_s", interval) == interval][:12]
                if llm:
                    keep = [q for q in queue if q["genome"]["id"] not in {g["id"] for g in llm}]
                    self.db.kv_set("brain.candidate_queue", keep)
                    await self.say("Evolution Arena", f"Evaluating {len(llm)} DeepSeek-designed genomes this cycle")
                if self.compute is not None and await self.compute.should_burst(self, interval):
                    results = await asyncio.wait_for(self.compute.burst_search(self, interval, parents, llm), timeout=1200)
                else:
                    loop = asyncio.get_running_loop()
                    from forge.evolution.worker import local_search
                    results = await asyncio.wait_for(loop.run_in_executor(self.pool, local_search, str(self.s.market_dir), interval,
                                                         [g.model_dump(mode="json") for g in parents],
                                                         {"maker": float(self.fees.maker), "taker": float(self.fees.taker)},
                                                         240.0, int(time.time()), llm), timeout=900)
                await self._absorb(results, interval)
            except Exception as e:
                log.exception("improvement cycle failed")
                await self.say("Evolution Arena", f"Improvement cycle error: {e}", level="warn")
            self.improvement_runs += 1
            self.sup.beat("improvement")
            await asyncio.sleep(30)

    async def _absorb(self, results: dict[str, Any], interval: int) -> None:
        passed = 0
        near = self.db.kv_get("evolution.near_miss", []) or []
        for r in results.get("candidates", []):
            g = Genome.model_validate(r["genome"])
            h = r.get("holdout") or {}
            if not r["passed"] and (h.get("p_positive") or 0) >= 0.70 and (h.get("mean_net") or 0) > 0:
                near.append({"id": g.id, "interval": interval, "p": h.get("p_positive"), "n": h.get("n"),
                             "reasons": r.get("reasons", [])[:3]})
            sleeve = r.get("sleeve")
            ok = sleeve in ("alpha", "beta")
            sid = self.arena.admit(g, r.get("rationale", {}), ok,
                                   {"holdout": r["holdout"], "selection": r["selection"], "fitness": r.get("fitness")})
            if ok:
                self.db.kv_set(f"strategy.sleeve.{sid}", sleeve)
            if ok:
                passed += 1
                h = r["holdout"]
                await self.say("Evolution Arena", f"NEW {sleeve.upper()}-SLEEVE strategy {sid} ({g.family}, gen {g.generation}) → paper trading now: holdout n={h['n']} "
                                                  f"mean {h['mean_net']:+.2%} P={h['p_positive']:.2f} alpha P={h.get('alpha_p_positive', 0):.2f}",
                               strategy=sid)
        near = sorted({x["id"]: x for x in near}.values(), key=lambda x: -(x["p"] or 0))[:20]
        self.db.kv_set("evolution.near_miss", near)
        if near:
            self.status("Evolution Arena", f"{len(near)} near-miss lineages being raced toward the gate")
        await self.say("Evolution Arena", f"{interval // 60}m cycle: evaluated {results.get('evaluated', 0)} genomes in "
                                          f"{results.get('seconds', 0):.0f}s ({results.get('where', 'local')}); {passed} passed the gate; "
                                          f"best selection fitness {results.get('best_fitness', 0):+.3f}")

    async def _review_loop(self) -> None:
        while not self.stop_event.is_set():
            self.sup.beat("arena_review")
            await asyncio.sleep(300)
            try:
                cost = CostModel(maker_fee=float(self.fees.maker), taker_fee=float(self.fees.taker))
                regimes = {s: st.regime for s, st in self.bars[300].state.items() if st.features}
                changes = self.arena.review({i: e.state for i, e in self.bars.items()}, cost, regimes)
                for c in changes:
                    await self.say("Evolution Arena", f"{c['strategy']} ({c['family']}): {c['from']} → {c['to']} — {c['why']}",
                                   strategy=c["strategy"])
                    if c["to"] in ("SHADOW", "EXPERIMENTAL") and c["from"] in ("PRODUCTION", "CHALLENGER") and self.brain:
                        await self.brain.escalate(self, "strategy_demoted", c)
            except Exception:
                log.exception("arena review failed")

    async def _counterfactual_loop(self) -> None:
        """OP-009 §4: score every opportunity (acted, rejected, observed) after its horizon."""
        while not self.stop_event.is_set():
            self.sup.beat("counterfactual")
            await asyncio.sleep(600)
            try:
                await self._score_counterfactuals()
            except Exception:
                log.exception("counterfactual scoring failed")

    async def _score_counterfactuals(self) -> None:
        now_ns = time.time_ns()
        rows = self.db.query("SELECT * FROM opportunities WHERE evaluated_at IS NULL AND ts_ns + horizon_s * 1000000000 < ? "
                             "ORDER BY ts_ns LIMIT 500", (now_ns,))
        missed_win = avoided_loss = 0
        for o in rows:
            c = json.loads(o["components"])
            interval = 300 if o["horizon_s"] <= 300 * 2016 and o["strategy_id"] and self.reg.get(o["strategy_id"]) and \
                self.reg.get(o["strategy_id"]).interval_s == 300 else 3600
            st = self.bars[interval].state.get(o["symbol"])
            if st is None or not len(st.series):
                continue
            arr = st.series.arrays()
            t0 = o["ts_ns"] / 1e9
            i0 = int(np.searchsorted(arr["ts"], t0))
            if i0 >= len(arr["ts"]) - 1:
                continue
            ref = float(o["ref_price"])
            tp_px, sl_px = ref * (1 + c["tp"]), ref * (1 - c["sl"])
            end = min(len(arr["ts"]), i0 + max(1, o["horizon_s"] // interval) + 1)
            outcome, exit_px = "TIME", float(arr["close"][end - 1])
            for k in range(i0, end):
                if arr["low"][k] <= sl_px:
                    outcome, exit_px = "SL", sl_px
                    break
                if arr["high"][k] >= tp_px:
                    outcome, exit_px = "TP", tp_px
                    break
            gross = exit_px / ref - 1
            net = gross - (float(self.fees.maker) + (float(self.fees.maker) if outcome == "TP" else float(self.fees.taker)))
            res = {"outcome": outcome, "gross": gross, "net": net, "win": net > 0}
            self.db.execute("UPDATE opportunities SET outcome = ?, evaluated_at = ? WHERE id = ?", (dumps(res), _now(), o["id"]))
            self.calib.record(f"strategy:{o['family']}", float(o["probability"] or 0.5), net > 0, "counterfactual", o["strategy_id"])
            self.hurdle.observe(net, max(o["horizon_s"] / 3600 * 0.5, 0.25), weight=0.3)
            if o["status"] in ("REJECTED", "OBSERVED") and net > 0:
                missed_win += 1
            if o["status"] in ("REJECTED", "OBSERVED") and net <= 0:
                avoided_loss += 1
        self.hurdle.flush()
        if rows:
            await self.say("Counterfactual Engine", f"Scored {len(rows)} past opportunities: {missed_win} not-taken winners, "
                                                    f"{avoided_loss} correctly avoided/observed losers → calibration + hurdle updated")

    async def _housekeeping_loop(self) -> None:
        while not self.stop_event.is_set():
            self.sup.beat("self_review")
            await asyncio.sleep(3600)
            with contextlib.suppress(Exception):
                await self.say("Self-Review", self.self_review_text())

    def self_review_text(self) -> str:
        t = self.treasury
        counts = self.reg.counts()
        return (f"Hourly self-review: equity ${t.get('equity_usd', 0):.2f}, true net ${t.get('true_net_usd', 0):+.4f}, "
                f"fees ${t.get('fees_usd', 0):.4f}, inference ${t.get('opex_inference_usd', 0):.4f}, compute ${t.get('opex_compute_usd', 0):.4f}; "
                f"population {counts}; improvement cycles {self.improvement_runs}; regime {t.get('regime', {}).get('name')}")

    # ================================================================== shutdown
    async def stop(self) -> None:
        self.stop_event.set()
        self.stream.stop()
        for t in self.tasks:
            t.cancel()
        for t in self.tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t
        with contextlib.suppress(Exception):
            for eng in self.bars.values():
                eng.persist()
        self.hurdle.flush()
        if self.pool:
            for proc in list(getattr(self.pool, "_processes", {}).values()):
                with contextlib.suppress(Exception):
                    proc.terminate()            # research worker must never block shutdown
            self.pool.shutdown(wait=False, cancel_futures=True)
        await self.rest.close()
        await self.bus.close()
        self.audit.append("FORGE_STOP", {"uptime_s": round(time.time() - self.started)})
