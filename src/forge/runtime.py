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
from forge.strategies.genome import Genome, barrier_pcts, chandelier_k, compile_entries, convex_atr
from forge.strategies.registry import ACTIVE_LIVE, ACTIVE_OBSERVING, State, StrategyRegistry, repair_genome
from forge.treasury.allocation import (
    SPECIALIST_FAMILIES,
    breadth_multiplier,
    drawdown_state,
    ecr_tier,
    edge_coverage_ratio,
    haircut_probability,
    retention_haircut,
    risk_at_stop_cap,
    volatility_multiplier,
)
from forge.treasury.regimes import CapitalRegimeEngine
from forge.treasury.sizing import SizeDecision, kelly_fraction, size_position
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
        self.account: dict[str, Any] = {"total_usd": None, "cash_usd": None, "assets": [], "ts": 0.0}
        self.workers: dict[str, dict[str, Any]] = {}      # live worker board for the founder portal
        self.last_improvement_ts = 0.0
        self.genomes_total = 0
        from forge.research.metalabel import SecondOpinion
        self.second = SecondOpinion(self.db)
        self.genomes_last_cycle = 0
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
        from forge.discovery import seed_catalog
        seed_catalog(self.db)
        self.db.execute("UPDATE compute_jobs SET status='FAILED', error='orphaned by restart' WHERE status='RUNNING'")
        n = self.arena.bootstrap()
        if n:
            await self.say("Evolution Arena", f"Seeded {n} strategy families into the population (EXPERIMENTAL)")
        await self._discover()
        await self._init_treasury()
        self._init_execution()
        for eng in self.bars.values():                      # heavy parquet + feature work off the event loop
            await asyncio.to_thread(eng.load_history, self.universe)
            await asyncio.to_thread(eng.recompute, self.universe)
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
        from forge.evolution.analyst import StrategyAnalyst
        self.analyst = StrategyAnalyst(self)
        B("analyst", self.analyst.run, 600)
        B("time_machine", self._time_machine_loop, 3 * 3600)
        # OP-013 Opportunity Surface: discovery registry + allocator, Listing Sentinel, cross-rail (Kalshi) shadow engine
        from forge.opportunities.crossrail import CrossRailScanner
        from forge.opportunities.surface import ListingSentinel, SurfaceRegistry
        self.surface = SurfaceRegistry(self)
        self.listings = ListingSentinel(self)
        self.crossrail = CrossRailScanner(self)
        B("surface", self.surface.run, 3600)
        B("listing_sentinel", self.listings.run, 600)
        B("crossrail", self.crossrail.run, 1200)
        B("crossrail_fast", self.crossrail.fast_lane, 600)
        from forge.opportunities.kalshi_live import KalshiLive
        self.kalshi_live = KalshiLive(self)
        B("kalshi_live", self.kalshi_live.run, 600)
        from forge.treasury.profit_velocity import VelocityEngine
        self.velocity = VelocityEngine(self)
        B("velocity", self.velocity.run, 900)
        from forge.treasury.edge_decay import EdgeDecayMonitor
        self.edge_decay = EdgeDecayMonitor(self)
        B("edge_decay", self.edge_decay.run, 900)
        from forge.research.equity_paper import EquityPaperResearch
        self.equity_paper = EquityPaperResearch(self)
        B("equity_paper", self.equity_paper.run, 1800)
        from forge.treasury.truth import TreasuryTruth
        self.treasury_truth = TreasuryTruth(self)
        B("treasury_truth", self.treasury_truth.run, 900)
        from forge.treasury.tcs import TreasuryContribution
        self.tcs = TreasuryContribution(self)
        B("tcs", self.tcs.run, 900)
        from forge.treasury.reallocator import CapitalReallocator
        self.reallocator = CapitalReallocator(self)
        B("capital_reallocator", self.reallocator.run, 900)
        from forge.research.algo_factory import AlgoFactory
        self.algo_factory = AlgoFactory(self)
        B("algo_factory", self.algo_factory.run, 900)
        from forge.opportunities.half_life import HalfLifeEngine
        self.half_life = HalfLifeEngine(self)
        B("half_life", self.half_life.run, 900)
        from forge.agents.heartbeat import AgentHeartbeat
        self.agent_heartbeat = AgentHeartbeat(self)
        B("agent_heartbeat", self.agent_heartbeat.run, 900)
        from forge.treasury.red_zone import RedZoneGovernor
        self.red_zone = RedZoneGovernor(self)
        B("red_zone", self.red_zone.run, 900)
        from forge.agents.stale_nudge import StaleNudge
        self.stale_nudge = StaleNudge(self)
        B("stale_nudge", self.stale_nudge.run, 900)
        from forge.lab.paper_lab import PaperLab
        self.paper_lab = PaperLab(self)
        B("paper_lab", self.paper_lab.run, 900)
        from forge.lab.evidence_board import EvidenceBoard
        self.evidence_board = EvidenceBoard(self)
        B("evidence_board", self.evidence_board.run, 900)
        from forge.lab.regime import RegimeDetector
        self.regime = RegimeDetector(self)
        B("regime", self.regime.run, 1200)
        from forge.lab.scanner_boost import ScannerBoost
        self.scanner_boost = ScannerBoost(self)
        B("scanner_boost", self.scanner_boost.run, 1200)
        from forge.lab.position_vigil import PositionVigil
        self.position_vigil = PositionVigil(self)
        B("position_vigil", self.position_vigil.run, 45)
        from forge.lab.officer_dispatch import OfficerDispatch
        self.officer_dispatch = OfficerDispatch(self)
        B("officer_dispatch", self.officer_dispatch.run, 60)
        from forge.intel.feeds import ExternalFeeds
        self.external_feeds = ExternalFeeds(self)
        B("external_feeds", self.external_feeds.run, 900)
        from forge.opportunities.paper_bets import PaperBetDesk
        self.paper_bets = PaperBetDesk(self)
        B("paper_bets", self.paper_bets.run, 900)
        from forge.treasury.econ_orchestrator import EconOrchestrator
        self.econ_orchestrator = EconOrchestrator(self)
        B("econ_orchestrator", self.econ_orchestrator.run, 300)



        async def _trial_scorecard_loop():
            import asyncio
            from forge.treasury.paper_trial import update_8h_scorecard
            while not self.stop_event.is_set():
                self.sup.beat("trial_scorecard")
                try:
                    await asyncio.to_thread(update_8h_scorecard, self)
                except Exception:
                    pass
                await asyncio.sleep(60)
        B("trial_scorecard", _trial_scorecard_loop, 900)
        from forge.opportunities.settlement_window import SettlementWindowEngine
        self.settlement_window = SettlementWindowEngine(self)
        B("sw_sampler", self.settlement_window.sampler, 60)
        B("settlement_window", self.settlement_window.run, 300)
        from forge.ops.econ import EconSampler
        B("econ", EconSampler(self).run, 120)
        B("ops_alerts", self._ops_alerts_loop, 180)
        from forge.agents.genome import PromptGenomes
        self.prompt_genomes = PromptGenomes(self)
        self.prompt_genomes.seed()
        B("prompt_lab", self._prompt_lab_loop, 1800)
        from forge.opportunities.pegmaker import PegMaker
        self.pegmaker = PegMaker(self)
        B("pegmaker", self.pegmaker.run, 300)
        from forge.core.healing import HealthMonitor
        self.health = HealthMonitor(self)
        B("healing", self.health.run, 120, critical=True)
        self.sup.on_restart = self._on_loop_restart
        self.tasks = self.sup.start()
        self.tasks.append(asyncio.create_task(self.sup.watch(self.stop_event), name="supervisor"))
        await self.say("Forge", f"All loops running under supervision: {len(self.sup.loops)} loops + watchdog — "
                                "EARNING + IMPROVEMENT loops active 24/7")

        try:
            from forge.treasury.paper_trial import start_trial, start_8h_trial, snapshot
            if not self.db.kv_get("paper_trial"):
                start_8h_trial(self)
            if not self.db.kv_get("paper_trial"):
                st = start_trial(self, 24.0)
                await self.say("Firm", f"PAPER trial started — {st['mode']} · PRIMARY TARGET $1.00/h TRUE-NET · $0.50/h diagnostic only · LIVE money OFF · continuous (does not stop at window end)")
            else:
                snapshot(self)
        except Exception as _e:
            pass

    async def _prompt_lab_loop(self) -> None:
        """Agent cognitive architecture: score forecasts vs real gate outcomes, evaluate paired prompt runs, promote/archive
        prompt genomes, open blind panels for high-stakes items. Deterministic; no LLM spend."""
        while not self.stop_event.is_set():
            self.sup.beat("prompt_lab")
            try:
                pg = self.prompt_genomes
                scored = await asyncio.to_thread(pg.score_predictions)
                decisions = await asyncio.to_thread(pg.evaluate)
                panels = await asyncio.to_thread(pg.open_panels)
                for pid, d in decisions.items():
                    await self.say("Prompt Lab", f"Prompt genome {pid} {d} on paired, identical-evidence comparisons")
                self.db.kv_set("prompt_lab.last", {"ts": time.time(), "scored": scored, "decisions": decisions, "panels": panels})
            except Exception as e:
                log.warning("prompt lab failed: %s", e)
            await asyncio.sleep(600)

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
            from forge.treasury.idle_yield import IdleYield
            with contextlib.suppress(Exception):            # USDC idle-yield cash → USD before trading -USD books
                g = await IdleYield(self).live_start_guard()
                if g:
                    await self.say("Treasury", f"Live-start guard: USDC → USD {g.get('amount')} ({g.get('status')})")
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
            repaired = self.gateway.repair_unrecorded_fills()
            if repaired:
                log.warning("accounting repair: rebuilt %d unrecorded fills from order truth", repaired)
                if self.book == "paper":                       # venue balances must match the repaired ledger
                    st = self.ledger.state("paper")
                    self.venue.balances = {"USD": st.cash_usd, **{asset: h.qty for (_, asset), h in st.holdings.items()}}

    async def _ops_alerts_loop(self) -> None:
        from forge.ops.insights import evaluate_alerts
        while not self.stop_event.is_set():
            self.sup.beat("ops_alerts")
            try:
                await asyncio.to_thread(evaluate_alerts, self)
            except Exception as e:
                log.warning("ops alerts: %s", e)
            await asyncio.sleep(30)

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
        hwm_key = f"treasury.hwm.{book}"
        hwm = float(self.db.kv_get(hwm_key, 0.0) or 0.0)
        if eq > hwm:
            hwm = eq
            self.db.kv_set(hwm_key, hwm)
        dds = drawdown_state(eq, hwm)
        self.treasury["high_water_usd"] = hwm
        self.treasury["drawdown_state"] = {"state": dds.state, "drawdown": dds.drawdown, "multiplier": dds.multiplier,
                                           "generic_live_paused": dds.generic_live_paused, "postmortem": dds.postmortem_required}
        return self.treasury

    async def _treasury_loop(self) -> None:
        n = 0
        while not self.stop_event.is_set():
            n += 1
            self.sup.beat("treasury")
            t = self._snapshot_treasury()
            if self.book == "live" and n % 4 == 0:
                await self._reconcile_live()
            if self.rest.authenticated and n % 4 == 1:
                await self._refresh_account()
            if self.rest.authenticated and n % 120 == 3:          # ~hourly: verify USDC rewards from wallet truth
                from forge.treasury.idle_yield import IdleYield
                with contextlib.suppress(Exception):
                    await IdleYield(self).observe()
            eq0 = float(self.day["start_equity"] or 0)
            if eq0 > 0 and t["daily_pnl_usd"] / eq0 <= -float(self.s.risk.daily_drawdown_breaker_fraction):
                if tstate.trading_state(self.db) == "RUNNING":
                    tstate.observe_only(self.db, self.audit, f"daily loss {t['daily_pnl_usd']:.2f} breached limit")
                    await self.say("Risk Governor", "Daily drawdown limit reached → OBSERVE_ONLY; Improvement Loop escalated "
                                                    "(postmortem + challenger research)", level="warn")
                    if self.brain is not None:
                        await self.brain.escalate(self, "daily_loss_limit", {"treasury": t})
            self.status("Accountant", f"equity ${t['equity_usd']:.2f} · true net ${t['true_net_usd']:+.4f}")
            if n % 4 == 0:
                self.db.insert("equity_series", {"ts": _now(), "book": self.book, "equity_usd": t["equity_usd"],
                                                 "true_net_usd": t.get("true_net_usd"), "account_total_usd": self.account.get("total_usd"),
                                                 "invested_usd": t.get("deployed_usd")})
            await asyncio.sleep(15)

    async def _refresh_account(self) -> None:
        """The real Coinbase account as a whole (read-only view), marked to live prices."""
        try:
            bals = [b for b in await self.coinbase.get_balances() if b.total > 0]
        except Exception as e:
            log.warning("account refresh failed: %s", e)
            return
        cash = float(sum((b.total for b in bals if b.asset in ("USD", "USDC")), Decimal(0)))
        assets, total = [], cash
        for b in bals:
            if b.asset in ("USD", "USDC"):
                continue
            bbo = self.market.get_bbo(f"{b.asset}-USD")
            px = bbo.mid if bbo else (self.market.products.get(f"{b.asset}-USD").price if self.market.products.get(f"{b.asset}-USD") else 0.0)
            v = float(b.total) * px
            total += v
            assets.append({"asset": b.asset, "qty": float(b.total), "price": px, "value_usd": v})
        self.account = {"total_usd": total, "cash_usd": cash, "assets": assets, "ts": time.time()}

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
        signals: dict[str, list[tuple[Genome, State]]] = {}
        for sym in symbols:
            if self.db.kv_get(f"quarantine.{sym}"):
                continue                                        # data self-healing: no decisions on suspect data
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
                signals.setdefault(sym, []).append((g, st))
        for sym, lst in signals.items():
            families = {g.family for g, _ in lst}
            for g, st in lst:
                found += 1
                await self._opportunity(g, st, sym, eng.state[sym], interval, consensus=len(families))
        if found:
            self.status("Opportunity Engine", f"{found} signals on last {interval // 60}m close")

    async def _opportunity(self, g: Genome, st: State, sym: str, ss: Any, interval: int, consensus: int = 1) -> None:
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
        win = ev.avg_win if ev and ev.avg_win > 0 else min(tp, 3 * sl) - cost_win      # convex: no fixed TP → 3R prior
        loss = ev.avg_loss if ev and ev.avg_loss < 0 else -(sl + cost_loss)
        cls = f"strategy:{g.family}"
        p_cal, n_cal = self.calib.calibrate(cls, raw_p)
        p_use = p_cal if n_cal >= 20 else 0.5 * raw_p + 0.5 * p_cal
        # agreement boosting: independent families agreeing on the same market raise confidence (bounded, logged)
        if consensus > 1:
            z = math.log(p_use / (1 - p_use)) + 0.2 * min(consensus - 1, 3)
            p_use = 1 / (1 + math.exp(-z))
        feat = {k: float(f[k][-1]) for k in ("ret_12", "ret_48", "vol_48", "vol_pct", "rvol_12", "er_24", "z_50", "rs_btc_48",
                                             "dd_288", "atr_14") if k in f and f[k][-1] == f[k][-1]}
        feat.update(regime_conf=float(ss.regime_conf), breadth=float(self.breadth.get("up_frac", 0.0)))
        # second opinion: calibrated evidence with EARNED weight (never an automatic veto)
        p_strat = p_use
        p_use, p_meta, meta_w = self.second.opinion(g.family, {**feat, "spread_bps": 0.0}, p_use)
        # P0.3 live-retention haircut: backtest-derived expectations keep H (prior 0.25) until forward evidence earns more
        hold_m = self.reg.latest_metrics(g.id, "holdout") or {}
        fwd_m = self.reg.latest_metrics(g.id, "forward") or {}
        real = self.arena.real_outcomes(g.id)
        f_n = int(fwd_m.get("n", 0) or 0) + len(real)
        f_mean = ((float(fwd_m.get("mean_net", 0) or 0) * int(fwd_m.get("n", 0) or 0) + sum(real)) / f_n) if f_n else None
        h_ret = retention_haircut(float(hold_m.get("mean_net", 0) or 0), f_mean, f_n)
        p_pre_haircut = p_use
        p_use = haircut_probability(p_use, win, loss, h_ret)
        # P0.2 Edge Coverage Ratio on the un-haircut expectation (cost-survival gate; never used alone)
        ecr = edge_coverage_ratio(p_pre_haircut, win, loss, cost_win, cost_loss, uncertainty=spread / 2e4)
        ecr_t = ecr_tier(ecr)
        hold_h = ev.avg_hold_h if ev and ev.avg_hold_h > 0 else g.exit.time_stop_bars * interval / 3600 * 0.5
        eq = float(self.treasury.get("equity_usd") or 0)
        pol = self.capital.policy(max(eq, 0.01))
        free = max(0.0, float(self.treasury.get("cash_usd") or 0) - self.capital.reserve_usd(eq))
        pressure = utilization_pressure(free, free * 0.5 + 1e-9)
        va = assess(p_use, win, loss, hold_h, self._effective_hurdle(pol), pressure)
        half_life_s = max(interval, g.execution.maker_ttl_bars * interval)
        exp_net_bps = va.expected_return * 1e4
        score = va.adjusted_return * 1e4 * (0.5 + p_use) * (1 + va.capital_velocity_score)
        oid = new_id("opp")
        now_ns = time.time_ns()
        feat["spread_bps"] = float(spread)
        comps = {"p_raw": raw_p, "p_cal": p_cal, "p_strategy": p_strat, "p_meta": p_meta, "meta_weight": meta_w,
                 "consensus": consensus, "feat": feat, "p_used": p_use, "win": win, "loss": loss, "tp": tp, "sl": sl,
                 "hold_h": hold_h, "velocity_per_day": va.velocity_per_day, "hurdle_per_day": va.hurdle_per_h * 24,
                 "opportunity_cost": va.opportunity_cost_frac, "adjusted_return": va.adjusted_return,
                 "velocity_score": va.capital_velocity_score, "half_life_s": half_life_s, "spread_bps": spread,
                 "regime_conf": ss.regime_conf, "evidence_n": ev.n if ev else 0, "p_edge": ev.p_edge if ev else 0.0,
                 "haircut_H": h_ret, "forward_n": f_n, "p_pre_haircut": p_pre_haircut, "ecr": ecr, "ecr_tier": ecr_t}
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
        # Stable rails are executed by PegMaker shadow/bridge — not spot genome signals on alts
        if g.id.startswith("paper_stable_") or g.family in ("stable_triangle", "stable_peg_mm"):
            self._set_opp(oid, "OBSERVED", "stable rail: pegmaker path (not spot genome)")
            return
        # Continuous kill/realloc gate — decay PAUSE / realloc REDUCE blocks new size immediately
        # Half-life urgency: microstructure-class edges expire fast — mark expires_ns tightly
        try:
            hl_rep = (self.db.kv_get("opportunity.half_life") or {}).get("families") or {}
            fam0 = (g.family or "").split("+")[0]
            hl_info = hl_rep.get(fam0) or hl_rep.get("microstructure") or {}
            urgency = hl_info.get("urgency") or "SAME_DAY"
            hl_s = float(hl_info.get("half_life_s") or 1800)
            comps["half_life_s"] = hl_s
            comps["urgency"] = urgency
            if urgency == "IMMEDIATE":
                # shrink horizon; if opportunity already older than half-life, drop
                import time as _t
                age = _t.time() - float(self.db.scalar("SELECT ts FROM opportunities WHERE id=?", (oid,)) or _t.time())
                if age > hl_s:
                    self._set_opp(oid, "REJECTED", f"half-life expired ({age:.0f}s > {hl_s:.0f}s) — drop stale edge")
                    return
        except Exception:
            pass
        ed = self.db.kv_get("edge_decay") or {}
        for a in (ed.get("actions") or []):
            if a.get("strategy_id") == g.id and a.get("state") in ("PAUSE", "REDUCE"):
                self._set_opp(oid, "REJECTED", f"edge_decay {a.get('state')}: capital withdrawn — hunt next edge")
                return
        realloc = self.db.kv_get("capital.reallocation") or {}
        for a in (realloc.get("actions") or []):
            if a.get("strategy") == g.id and a.get("type") in ("PAUSE", "REDUCE"):
                self._set_opp(oid, "REJECTED", f"reallocator {a.get('type')}: rotate to higher marginal value")
                return
        comps["breadth_at_entry"] = self.breadth.get("up_frac")
        if self.db.kv_get(f"strategy.sleeve.{g.id}") == "beta":
            b = self.breadth
            if b["up_frac"] < 0.55 or b["btc_regime"] in ("TREND_DOWN", "PANIC_SELLING"):
                if self.book != "paper":
                    self._set_opp(oid, "REJECTED", f"beta sleeve kill switch: breadth {b['up_frac']:.0%} up, BTC {b['btc_regime']}")
                    return
                # paper explores, live exploits: gather evidence on whether the kill switch is needed for this strategy
                comps["paper_exploration"] = True
        # ECR gate: live needs ≥ 2.0 (small-live tier); paper explores to measure whether ECR predicts outcomes
        if ecr_t == "REJECT" or (ecr_t == "SHADOW_ONLY"):
            if self.book != "paper":
                self._set_opp(oid, "REJECTED", f"ECR {ecr:.2f} ({ecr_t}): expected gross edge does not cover costs ×2")
                return
            comps["paper_exploration"] = True
            try:
                from forge.lab.counterfactual import record as cf_record
                cf_record(self.db, decision="ecr_gate", chosen="paper_explore",
                          alts=["reject_as_live_would"], context={"ecr": ecr, "ecr_t": ecr_t, "oid": oid})
            except Exception:
                pass
        # treasury drawdown state: −15% from high-water pauses generic live deployment (research/paper continue)
        dds = self.treasury.get("drawdown_state") or {}
        if dds.get("generic_live_paused") and self.book != "paper" and g.family not in SPECIALIST_FAMILIES:
            self._set_opp(oid, "REJECTED", f"drawdown {dds.get('drawdown', 0):.1%} from high-water: generic live paused")
            return
        # one position per market across all strategies (no doubled bets on one coin)
        if self.book == "paper":
            n_open = int(self.db.scalar("SELECT COUNT(*) FROM positions WHERE book='paper' AND status!='CLOSED'") or 0)
            max_open = int((self.db.kv_get("lab.paper_aggression") or {}).get("max_concurrent_positions") or 12)
            if n_open >= max_open:
                return None  # PAPER concurrent cap — rotate capital across probes
        if self.db.scalar("SELECT 1 FROM positions WHERE book = ? AND symbol = ? AND status != 'CLOSED'", (self.book, sym)):
            self._set_opp(oid, "REJECTED", f"already holding {sym} (one position per market)")
            return
        if self.book == "paper" and va.adjusted_return <= 0 and p_pre_haircut != p_use:
            # paper explores, live exploits: the haircut must never stop paper from gathering the forward evidence that
            # is the only way to earn the haircut back (deadlock found 2026-10-07: 161/193 paper opportunities rejected)
            va = assess(p_pre_haircut, win, loss, hold_h, self._effective_hurdle(pol), pressure)
            comps["paper_exploration"] = True
        if va.adjusted_return <= 0:
            self._set_opp(oid, "REJECTED", va.rationale)
            await self.say("Allocator", f"{sym} {g.family}: WAIT — {va.rationale}", strategy=g.id, opportunity=oid)
            return
        p_trade = p_pre_haircut if (self.book == "paper" and comps.get("paper_exploration")) else p_use
        await self._allocate_and_execute(g, st, sym, oid, p_trade, win, loss, tp, sl, interval, va, spread, ev, pol)

    IDLE_YIELD_PER_H = 0.0375 / 365 / 24         # what an idle dollar earns (USDC rewards, OP-019)

    def _effective_hurdle(self, pol: Any) -> float:
        """Opportunity cost of capital per hour, utilization-aware: when most capital is idle, the marginal dollar's
        alternative is the idle yield; as deployment rises toward full, the hurdle rises to the learned/regime rate.
        (A fixed ~1.5%/day hurdle rejected every multi-day trade while ~70% of capital sat idle — 2026-10-07.)"""
        eq = float(self.treasury.get("equity_usd") or 0) or 1.0
        u = float(self.treasury.get("deployed_usd") or 0) / eq
        full = self.hurdle.hurdle(pol.hurdle_multiplier)
        w = min(1.0, max(0.0, (u - 0.3) / 0.6))
        return self.IDLE_YIELD_PER_H + (full - self.IDLE_YIELD_PER_H) * w

    def _set_opp(self, oid: str, status: str, reason: str) -> None:
        self.db.execute("UPDATE opportunities SET status = ?, reason = ? WHERE id = ?", (status, reason[:500], oid))

    async def _allocate_and_execute(self, g: Genome, st: State, sym: str, oid: str, p: float, win: float, loss: float,
                                    tp: float, sl: float, interval: int, va: Any, spread: float, ev: Any, pol: Any) -> None:
        eq = float(self.treasury.get("equity_usd") or 0)
        reserve = self.capital.reserve_usd(eq)
        deployable = max(0.0, float(self.treasury.get("cash_usd") or 0) - reserve)
        if self.book == "paper":
            # PAPER tournament: deploy up to 85% of paper equity (minus open cost) so probes clear $1
            cash = float(self.treasury.get("cash_usd") or 0)
            deployed = float(self.treasury.get("deployed_usd") or 0)
            free = max(0.0, cash - min(reserve, eq * 0.05))
            deployable = max(deployable, free, cash * 0.85, max(0.0, eq - deployed) * 0.85)
            deployable = max(deployable, 8.0)  # floor so $1 probes always possible on ~$28 book
        # continuous evidence weighting + correlation discount (no fixed concurrency: capital flows to the best, decorrelated bets)
        evid = min(1.0, max(0.2, ((ev.p_edge if ev else 0.5) - 0.5) / 0.4))
        ss = self.bars[interval].state.get(sym)
        c_new = float(ss.features["corr_btc_96"][-1]) if ss and "corr_btc_96" in ss.features and ss.features["corr_btc_96"][-1] == ss.features["corr_btc_96"][-1] else 0.6
        rho = 0.0
        for r in self.db.query("SELECT symbol FROM positions WHERE book = ? AND status != 'CLOSED'", (self.book,)):
            so = self.bars[interval].state.get(r["symbol"])
            c_o = float(so.features["corr_btc_96"][-1]) if so and "corr_btc_96" in so.features and so.features["corr_btc_96"][-1] == so.features["corr_btc_96"][-1] else 0.6
            rho += max(0.0, c_new * c_o)
        corr_disc = 1.0 / (1.0 + rho)
        elite = self.db.kv_get("allocation.elite") or []
        if self.book == "paper":
            # PAPER tournament: every SHADOW/CHALLENGER probe needs real size to learn fees — no elite starvation
            kmult = max(float(g.sizing.kelly_mult or 0.5), 0.55)
        else:
            kmult = 1.0 if g.id in elite else (0.15 if elite else g.sizing.kelly_mult)      # elite allocation (Time Machine evidence)
        # conditional exposure scaling (answers §10): breadth tiers × volatility gate × high-water drawdown state
        fz = ss.features if ss else {}
        vp = float(fz["vol_pct"][-1]) if "vol_pct" in fz and fz["vol_pct"][-1] == fz["vol_pct"][-1] else None
        specialist = g.family in SPECIALIST_FAMILIES
        m_breadth = breadth_multiplier(self.breadth.get("up_frac") if self.breadth.get("n") else None, g.family)
        m_vol = volatility_multiplier(vp, specialist)
        m_dd = float((self.treasury.get("drawdown_state") or {}).get("multiplier", 1.0))
        exposure = m_breadth * m_vol * m_dd
        if self.book == "paper":
            agg = self.db.kv_get("lab.paper_aggression") or {}
            floor = float(agg.get("probe_exposure_floor") or 0.35)
            if exposure < floor:
                exposure = floor      # aggressive PAPER probes — learn fee survival fast
        if exposure <= 0:
            self._set_opp(oid, "REJECTED", f"exposure gate: breadth×{m_breadth:.2f} vol×{m_vol:.2f} drawdown×{m_dd:.2f}")
            return
        min_shr = 0.22 if self.book == "paper" else 0.0  # n=0 SHADOW must still clear $1 venue min on PAPER
        # Prefer reallocator top streams: slight size bump when preferred
        prefer = {(a.get("to") or "") for a in ((self.db.kv_get("capital.reallocation") or {}).get("actions") or []) if a.get("type") == "PREFER"}
        prefer_boost = 1.15 if (g.id in prefer or g.family in prefer or any(x in prefer for x in (g.family,))) else 1.0
        sz = size_position(p, win, loss, ev.n if ev else 0, kmult, g.sizing.max_fraction,
                           pol.max_position_fraction, deployable * evid * corr_disc * exposure * prefer_boost, st.value,
                           self.breakers.size_multiplier(), va.capital_velocity_score,
                           min_evidence_shrink=min_shr)
        # risk-at-stop cap (answers §9): per-position ≤ 5% equity at the stop, aggregate open risk ≤ 10%
        open_risk = 0.0
        for r in self.db.query("SELECT cost_usd, exit_plan FROM positions WHERE book = ? AND status != 'CLOSED'", (self.book,)):
            with contextlib.suppress(Exception):
                open_risk += float(r["cost_usd"]) * float(json.loads(r["exit_plan"] or "{}").get("stop_loss_pct", 0.05))
        rc = risk_at_stop_cap(eq, sl, kelly_fraction(p, win, loss), open_risk)
        if sz.notional_usd > rc.max_notional:
            sz = SizeDecision(sz.fraction, rc.max_notional, sz.kelly_raw, sz.shrink, sz.explanation + " | capped: " + rc.explanation)
        sz = SizeDecision(sz.fraction, sz.notional_usd, sz.kelly_raw, sz.shrink,
                          sz.explanation + f" | exposure breadth×{m_breadth:.2f} vol×{m_vol:.2f} dd×{m_dd:.2f}")
        if self.book == "paper" and 0.01 <= sz.notional_usd < 1.05 and sz.kelly_raw > 0:
            # PAPER probes: clear Coinbase $1 min — learn fee survival (don't starve at $0.06–$0.99)
            cap = max(deployable * 0.25, 1.05)
            n = min(1.25, cap)  # small but tradeable probes
            sz = SizeDecision(sz.fraction, max(1.05, n), sz.kelly_raw, sz.shrink, sz.explanation + " | paper_min_probe")
        if sz.notional_usd < 1.0:
            self._set_opp(oid, "REJECTED", f"size ${sz.notional_usd:.2f} below $1 venue minimum — {sz.explanation}")
            return
        # regime-aware profit capture: downside protection always; in trends exceptional winners run (looser ratchet + ATR trail)
        atr_now = float(self.bars[interval].state[sym].features["atr_14"][-1])
        regime_now = self.bars[interval].state[sym].regime
        trending = regime_now in ("TREND_UP", "BREAKOUT_EXPANSION", "EUPHORIA_BUYING")
        be_trig = g.exit.be_trigger_pct if g.exit.be_trigger_pct >= 0.5 else max(g.exit.be_trigger_pct, 1.5 * atr_now)
        lock_frac = (min(g.exit.lock_frac, 0.35) if trending else g.exit.lock_frac) if be_trig < 0.5 else g.exit.lock_frac
        _ts = int(g.exit.time_stop_bars * interval)
        if self.book == "paper":
            _ts = min(_ts, 6 * 3600)  # paper_time_cap: recirculate capital within 6h
        plan = ExitPlan(take_profit_pct=tp, stop_loss_pct=sl, time_stop_s=_ts,
                        be_trigger_pct=be_trig, be_buffer_pct=g.exit.be_buffer_pct, lock_frac=lock_frac,
                        trailing_pct=(g.exit.trail_atr * atr_now) if g.exit.trail_atr else None,
                        **(convex_plan(g, atr_now, interval, self.bars[interval].state[sym].features) if g.exit.convex else {}))
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
        depth = {300: 365, 3600: 365}
        while not self.stop_event.is_set():
            for interval, days in depth.items():
                have = set(self.store.symbols(interval))
                todo = [s for s in self.universe if s not in have]
                for s_ in self.universe:
                    if s_ not in have or self.db.kv_get(f"backfill.deep.{interval}.{s_}"):
                        continue                                         # deepen at most once (young coins can't reach 365 d)
                    a_ = await asyncio.to_thread(self.store.load, s_, interval)   # off the event loop
                    if a_ is not None and len(a_["ts"]) and a_["ts"][0] > time.time() - days * 86400 * 0.9:
                        todo.append(s_)                                  # deepen history to the full window
                    self.db.kv_set(f"backfill.deep.{interval}.{s_}", time.time())
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
                    await self.say("Data Engine", f"History ready: {len(todo)} markets × {interval // 60}m ({days}d)")
                    eng = self.bars[interval]
                    for s_ in todo:                                      # reload ONLY the changed markets, off the loop
                        eng.state.pop(s_, None)
                    await asyncio.to_thread(eng.load_history, list(todo))
                    await asyncio.to_thread(eng.recompute, list(todo))
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
                    await self.say("Evolution Arena", f"Evaluating {len(llm)} LLM-designed genomes (Hermes / DeepSeek brain) this cycle")
                self.workers["research"] = {"what": f"evolving {interval // 60}m strategies ({len(parents)} parents, "
                                                    f"{len(llm)} LLM designs)", "since": time.time(), "count": 1, "where": "local"}
                if self.compute is not None and await self.compute.should_burst(self, interval):
                    results = await asyncio.wait_for(self.compute.burst_search(self, interval, parents, llm), timeout=1200)
                else:
                    loop = asyncio.get_running_loop()
                    from forge.evolution.worker import local_search
                    results = await asyncio.wait_for(loop.run_in_executor(self.pool, local_search, str(self.s.market_dir), interval,
                                                         [g.model_dump(mode="json") for g in parents],
                                                         {"maker": float(self.fees.maker), "taker": float(self.fees.taker)},
                                                         240.0, int(time.time()), llm,
                                                         int(self.db.kv_get(f"stats.trials.{interval}", 0) or 0),
                                                         *self.sealed_context(interval)), timeout=900)
                await self._absorb(results, interval)
                self.last_improvement_ts = time.time()
            except Exception as e:
                log.exception("improvement cycle failed")
                self.improvement_failures = getattr(self, "improvement_failures", 0) + 1
                await self.say("Evolution Arena", f"Improvement cycle error: {e}", level="warn")
                if self.improvement_failures in (3, 20, 100):          # a loop that is alive but never succeeds is NOT healthy
                    self.audit.append("IMPROVEMENT_DEGRADED", {"consecutive_failures": self.improvement_failures, "error": str(e)[:300]})
                    await self.say("Self-Healing", f"Evolution has failed {self.improvement_failures} cycles in a row "
                                                   f"({type(e).__name__}) — earning loop continues; flagged for diagnosis", level="error")
            else:
                self.improvement_failures = 0
            self.improvement_runs += 1
            self.workers["research"] = {"what": "idle between cycles (next in ~30s)", "since": time.time(), "count": 0, "where": "-"}
            self.sup.beat("improvement")
            await asyncio.sleep(30)

    def sealed_context(self, interval: int) -> tuple[dict[str, bool], int]:
        """Genomes that already sat the sealed exam (verdict stands forever) + exams taken on the current sealed window."""
        seen = {r["genome_id"]: bool(r["sealed_passed"]) for r in self.db.query(
            "SELECT genome_id, sealed_passed FROM research_trials WHERE sealed_exam = 1 AND interval_s = ?", (interval,))}
        start = float(self.db.kv_get(f"research.sealed_start.{interval}", 0) or 0)
        n = int(self.db.scalar("SELECT COUNT(*) FROM research_trials WHERE sealed_exam = 1 AND interval_s = ? "
                               "AND sealed_start_ts >= ?", (interval, start - 86400 * 3)) or 0)
        return seen, n

    def _record_trials(self, results: dict[str, Any], interval: int) -> None:  # noqa: C901
        """P0.5 Research Trial Ledger — one row per adjudicated candidate."""
        import hashlib
        ds = results.get("dataset") or {}
        if results.get("sealed_start_ts"):
            self.db.kv_set(f"research.sealed_start.{interval}", float(results["sealed_start_ts"]))
        trials = int(self.db.kv_get(f"stats.trials.{interval}", 0) or 0)
        for r in results.get("candidates", []):
            g = r["genome"]
            sealed = r.get("sealed")
            exam = bool(sealed) and not sealed.get("reused")
            feats = sorted({c.get("f") for part in ("all", "any") for c in (g.get("entry") or {}).get(part, []) if c.get("f")})
            seg = ["selection", "holdout"] + (["sealed"] if exam else [])
            with contextlib.suppress(Exception):
                self.db.insert("research_trials", {
                    "ts": _now(), "genome_id": g["id"], "family": g.get("family"), "interval_s": interval,
                    "generation": g.get("generation"), "parents": dumps(g.get("parents", [])),
                    "origin": str((r.get("rationale") or {}).get("operator", "seed")), "features": dumps(feats),
                    "params_hash": hashlib.sha256(dumps({k: g.get(k) for k in ("entry", "exit", "execution")}).encode()).hexdigest()[:16],
                    "where_run": results.get("where", "local"), "segments_seen": dumps(seg),
                    "dataset": dumps({**ds, "sealed_start_ts": results.get("sealed_start_ts")}), "trials_cumulative": trials,
                    "selection": dumps(r.get("selection")), "holdout": dumps(r.get("holdout")),
                    "passed_validation": int(all(x.startswith("holdout alpha vs market drift") for x in r.get("reasons", [])
                                                 if not x.startswith("sealed final exam"))),
                    "sealed_exam": int(exam), "sealed_passed": (int(r.get("sleeve") is not None) if exam else None),
                    "sealed": dumps(sealed) if exam else None, "sealed_start_ts": results.get("sealed_start_ts"),
                    "promoted": int(r.get("sleeve") in ("alpha", "beta")), "reasons": dumps(r.get("reasons", [])[:6])})

    async def _absorb(self, results: dict[str, Any], interval: int) -> None:
        self._record_trials(results, interval)
        passed = 0
        self.genomes_last_cycle = int(results.get("evaluated", 0))
        self.genomes_total += self.genomes_last_cycle
        self.db.kv_set("stats.genomes_total", int(self.db.kv_get("stats.genomes_total", 0) or 0) + self.genomes_last_cycle)
        self.db.kv_set(f"stats.trials.{interval}", int(self.db.kv_get(f"stats.trials.{interval}", 0) or 0) + self.genomes_last_cycle)
        near = self.db.kv_get("evolution.near_miss", []) or []
        for r in results.get("candidates", []):
            await asyncio.sleep(0)                       # yield: market data / execution / API never wait on evolution
            g, _fix = repair_genome(dict(r["genome"]))
            if g is None:
                continue
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

    async def _time_machine_loop(self) -> None:
        """Hourly full-portfolio replay of the validated system on unseen history (testing at machine speed)."""
        import json as _json
        from concurrent.futures import ProcessPoolExecutor as _PPE

        from forge.research.timemachine import tm_job
        pool = _PPE(max_workers=1)
        await asyncio.sleep(120)
        while not self.stop_event.is_set():
            self.sup.beat("time_machine")
            try:
                rows = self.db.query("SELECT s.id, s.genome, m.metrics FROM strategies s JOIN strategy_metrics m "
                                     "ON m.strategy_id = s.id AND m.scope = 'holdout' WHERE s.population IN ('SHADOW','CHALLENGER','PRODUCTION')")
                gs, ev = [], {}
                for r in rows:
                    g = _json.loads(r["genome"])
                    m = _json.loads(r["metrics"])
                    gs.append(g)
                    ev[g["id"]] = {"p_win": m.get("win_rate", 0.45), "avg_win": m.get("avg_win", 0.03),
                                   "avg_loss": m.get("avg_loss", -0.03), "p_edge": m.get("p_positive", 0.6), "score": m.get("mean_net", 0)}
                if gs:
                    self.workers["time_machine"] = {"what": f"replaying {len(gs)} validated strategies × all markets through history",
                                                    "count": 1, "since": time.time(), "where": "local (low priority)"}
                    eq = float(self.treasury.get("equity_usd") or 28.27)
                    rep = await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(
                        pool, tm_job, str(self.s.market_dir), gs, ev, eq,
                        {"maker": float(self.fees.maker), "taker": float(self.fees.taker)}), timeout=1200)
                    self.db.kv_set("timemachine.report", rep)
                    if rep.get("elite") is not None:
                        old = self.db.kv_get("allocation.elite") or []
                        self.db.kv_set("allocation.elite", rep["elite"])
                        if set(old) != set(rep["elite"]):
                            eh = rep.get("elite_holdout") or {}
                            await self.say("Allocator", f"ELITE ALLOCATION → {len(rep['elite'])} strategies get full-strength capital "
                                                        f"(elite portfolio on unseen days: {eh.get('return', 0):+.1%}, PF "
                                                        f"{(eh.get('profit_factor') or 0):.2f}); others keep earning evidence at exploratory size")
                    h = rep.get("holdout") or {}
                    if h:
                        await self.say("Time Machine", f"Portfolio replay on {h.get('days', 0):.0f} unseen days: ${rep['capital']:.2f} → "
                                                       f"${h['final_usd']:.2f} ({h['return']:+.1%}) · {h['trades']} trades · PF "
                                                       f"{(h.get('profit_factor') or 0):.2f} · max DD {h['max_drawdown']:.1%} · "
                                                       f"{(h.get('positive_days') or 0):.0%} profitable days")
                    self.workers["time_machine"] = {"what": "idle until next hourly replay", "count": 0, "since": time.time(), "where": "-"}
            except Exception as e:
                log.exception("time machine failed")
                await self.say("Time Machine", f"replay error (engine unaffected): {str(e)[:160]}", level="warn")
            self.sup.beat("time_machine")
            await asyncio.sleep(3600)

    async def _review_loop(self) -> None:
        while not self.stop_event.is_set():
            self.sup.beat("arena_review")
            await asyncio.sleep(120)
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
                if time.time() - self.second.trained_at > 3600:
                    out = await asyncio.to_thread(self.second.train)
                    for fam, m in out.items():
                        await self.say("Learning Engine", f"Second-opinion model ({fam}) retrained on {m['n']} scored opportunities: "
                                                          f"OOS log-loss {m['oos_logloss_meta']:.3f} vs strategy {m['oos_logloss_base']:.3f} "
                                                          f"→ earned weight {m['weight']:.2f}")
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
                                                    f"{avoided_loss} correctly avoided weak setups → calibration + hurdle updated")

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


def convex_plan(g: Genome, atr: float, interval: int, f: dict[str, Any]) -> dict[str, Any]:
    """ExitPlan fields for Convex Trend Exit V1 — identical semantics to the backtester/Time Machine."""
    vp = f.get("vol_pct")
    vpv = float(vp[-1]) if vp is not None and len(vp) else None
    atr = convex_atr(g, atr)
    return {"chandelier_arm_pct": g.exit.arm_atr * atr, "chandelier_pct": chandelier_k(g, vpv) * atr,
            "progress_s": int(g.exit.progress_bars * interval) if g.exit.progress_bars else None,
            "progress_min_pct": g.exit.progress_atr * atr}
