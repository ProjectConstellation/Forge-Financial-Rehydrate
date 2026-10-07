import asyncio
from decimal import Decimal as D

from forge.audit.journal import AuditJournal
from forge.core.ids import idempotency_key
from forge.domain.market import BestBidAsk, MarketRules
from forge.domain.trading import ExitPlan, IntentPurpose, OrderRequest, TradeIntent
from forge.execution.gateway import ExecutionGateway, MarketView
from forge.ledger.ledger import Ledger
from forge.risk.breakers import BreakerBoard
from forge.risk.governor import RiskContext, RiskGovernor
from forge.treasury.regimes import CapitalRegimeEngine
from forge.venues.base import FeeSchedule
from forge.venues.paper import PaperVenue

RULES = MarketRules(venue="coinbase", symbol="SOL-USD", base="SOL", quote="USD", base_increment=D("0.00000001"),
                    quote_increment=D("0.01"), base_min_size=D("0"), quote_min_size=D("1"), price_increment=D("0.01"))


class Mkt:
    def __init__(self): self.b = BestBidAsk("coinbase", "SOL-USD", 100.0, 5, 100.02, 5, 0, 0)
    def set(self, bid, ask): self.b = BestBidAsk("coinbase", "SOL-USD", bid, 5, ask, 5, 0, 0)


def _setup(db, tmp_path):
    mkt = Mkt()
    lg = Ledger(db); lg.deposit("paper", D("28.27"), ref_id="seed")
    venue = PaperVenue(FeeSchedule(D("0.005"), D("0.009")), lambda s: RULES, lambda s: mkt.b, lambda s: None,
                       {"USD": D("28.27")})
    closed = []
    async def on_closed(info): closed.append(info)
    gw = ExecutionGateway(db, lg, venue, "paper", MarketView(lambda s: mkt.b, lambda s: RULES),
                          AuditJournal(tmp_path / "audit"), BreakerBoard(), on_position_closed=on_closed)
    return mkt, lg, venue, gw, closed


def _intent(n=D("20")):
    return TradeIntent(id="int1", ts_ns=0, book="paper", opportunity_id="opp1", strategy_id="stg_test", venue="coinbase",
                       symbol="SOL-USD", side="buy", purpose=IntentPurpose.ENTRY, requested_notional_usd=n,
                       exit_plan=ExitPlan(take_profit_pct=0.02, stop_loss_pct=0.015, time_stop_s=3600),
                       evidence={"family": "momentum"}, idem_key=idempotency_key("opp1", "stg_test"))


def _ctx(policy, equity=D("28.27")):
    return RiskContext(trading_state="RUNNING", mode="PAPER", now_ns=0, equity_usd=equity, cash_available_usd=equity,
                       reserve_required_usd=D("2.83"), exit_buffer_usd=D("0.34"), deployed_usd=D(0), open_positions=0,
                       family_exposure_usd={}, policy=policy, treasury_snapshot_age_s=1, reconciliation_ok=True,
                       market_fresh=True, book_valid=True, spread_bps=2.0, rules=RULES, expected_net_bps=80, est_cost_bps=140)


def test_full_paper_round_trip_tp(db, tmp_path):
    mkt, lg, venue, gw, closed = _setup(db, tmp_path)
    policy = CapitalRegimeEngine(db).policy(28.27)
    dec = RiskGovernor().evaluate(_intent(), _ctx(policy))
    assert dec.verdict.value in ("APPROVE", "REDUCE"), dec.reasons
    assert dec.approved_notional_usd <= D("28.27") * D("0.6")          # SURVIVAL max position fraction
    async def run():
        pid = await gw.execute_entry(_intent(), dec, ttl_s=60, maker_offset_bps=0, entry_style="maker", meta={})
        assert pid
        mkt.set(99.90, 99.92); venue.on_market("SOL-USD", 99.89)        # trades through our bid → maker fill
        await gw.tick(); await gw.tick()
        p = db.query_one("SELECT * FROM positions WHERE id = ?", (pid,))
        assert p["status"] == "OPEN", p
        mkt.set(102.2, 102.22); venue.on_market("SOL-USD", 102.25)      # TP rests at +2% → maker fill
        await gw.tick(); await gw.tick()
        return pid
    pid = asyncio.run(run())
    p = db.query_one("SELECT * FROM positions WHERE id = ?", (pid,))
    assert p["status"] == "CLOSED" and p["exit_reason"] == "TP"
    s = lg.state("paper").summary({})
    assert s["realized_pnl_usd"] > 0 and s["fees_usd"] > 0
    assert lg.check_balanced("paper") == 0
    assert abs(s["cash_usd"] - venue.balances["USD"]) < D("0.0001")     # ledger == venue (wallet-truth)
    assert closed and closed[0]["net_usd"] and float(closed[0]["net_usd"]) > 0


def test_stop_loss_and_duplicate_protection(db, tmp_path):
    mkt, lg, venue, gw, closed = _setup(db, tmp_path)
    policy = CapitalRegimeEngine(db).policy(28.27)
    dec = RiskGovernor().evaluate(_intent(), _ctx(policy))
    async def run():
        pid = await gw.execute_entry(_intent(), dec, ttl_s=60, maker_offset_bps=0, entry_style="taker", meta={})
        await gw.tick(); await gw.tick()
        mkt.set(98.0, 98.02)                                             # below −1.5% stop
        await gw.tick(); await gw.tick(); await gw.tick()
        again = await gw._submit(OrderRequest(client_order_id=idempotency_key("int1", "entry") if False else
                                              db.query_one("SELECT client_order_id FROM orders LIMIT 1")["client_order_id"],
                                              venue="coinbase", symbol="SOL-USD", side="buy", order_type="market",
                                              quote_size=D("5")), None)
        return pid, again
    pid, again = asyncio.run(run())
    p = db.query_one("SELECT * FROM positions WHERE id = ?", (pid,))
    assert p["status"] == "CLOSED" and p["exit_reason"] == "SL", p
    assert again is False                                                # duplicate client order id blocked
    assert lg.state("paper").summary({})["realized_pnl_usd"] < 0
    assert lg.check_balanced("paper") == 0


def test_risk_rejects_stale_and_stopped(db):
    policy = CapitalRegimeEngine(db).policy(28.27)
    g = RiskGovernor()
    c = _ctx(policy); c.market_fresh = False
    assert g.evaluate(_intent(), c).verdict.value == "REJECT"
    c = _ctx(policy); c.trading_state = "STOPPED"
    assert g.evaluate(_intent(), c).verdict.value == "REJECT"
    c = _ctx(policy); c.expected_net_bps = -5
    assert g.evaluate(_intent(), c).verdict.value == "REJECT"
    c = _ctx(policy); c.cash_available_usd = D("3")
    assert g.evaluate(_intent(), c).verdict.value == "REJECT"           # below reserve + venue min
