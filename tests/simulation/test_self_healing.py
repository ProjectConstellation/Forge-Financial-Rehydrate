"""Induced-failure tests for OP-012 self-healing."""
import asyncio
import time
from decimal import Decimal as D

import httpx
import numpy as np

from forge.config import load_settings
from forge.core.healing import Circuit, bar_integrity
from forge.persistence.db import Database


def test_circuit_open_halfopen_close():
    c = Circuit("x", threshold=2, base_cooldown_s=0.05)
    assert c.allow()
    c.failure("e1"); assert c.state == "CLOSED"
    c.failure("e2"); assert c.state == "OPEN" and not c.allow()
    time.sleep(0.06); assert c.allow() and c.state == "HALF_OPEN"
    c.failure("e3"); assert c.state == "OPEN" and c.cooldown_s == 0.1      # half-open failure doubles cooldown
    time.sleep(0.11); assert c.allow(); c.success(); assert c.state == "CLOSED"


def test_deepseek_outage_opens_circuit_and_never_raises_into_engine():
    """AI is never a single point of failure: provider 503s open the circuit; calls fail fast afterwards."""
    from forge.brain.agent import Brain
    from forge.brain.deepseek import DeepSeekClient
    from forge.ledger.ledger import Ledger
    s = load_settings()
    db = Database(":memory:"); db.migrate()
    calls = {"n": 0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(503, json={"error": "down"})
    client = DeepSeekClient(s.deepseek, "sk-test", db, Ledger(db), "paper", transport=httpx.MockTransport(handler))
    class F:  # minimal forge stub
        pass
    f = F(); f.db = db; f.s = s
    async def say(*a, **k): pass
    f.say = say
    b = Brain(f, client)
    async def run():
        import forge.brain.deepseek as dsm
        orig = dsm._sleep
        async def fast(_s): return None
        dsm._sleep = fast
        try:
            for _ in range(5):
                try:
                    await b._chat([{"role": "user", "content": "x"}], agent="t", purpose="t")
                except RuntimeError:
                    pass
        finally:
            dsm._sleep = orig
    asyncio.run(run())
    assert b.circuit.state == "OPEN"
    assert calls["n"] == 9          # 3 failing calls × 3 HTTP attempts, then fail-fast without touching the network
    b._queue("rebuild", {"key": "stg_x", "mode": "repair"}); b._queue("rebuild", {"key": "stg_x", "mode": "repair"})
    assert len(db.kv_get("brain.pending")) == 1                # queued once for retry, deduplicated


def test_corrupt_bars_detected():
    n = 400
    c = 100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.003, n)))
    good = {"ts": np.arange(n) * 300.0, "close": c, "high": c * 1.001, "low": c * 0.999}
    assert bar_integrity(good) == []
    bad = {k: v.copy() for k, v in good.items()}
    bad["close"][-3] = bad["close"][-4] * 3.5                      # spike that reverts next bar = bad print
    assert any("bad print" in i for i in bar_integrity(bad))
    pump = {k: v.copy() for k, v in good.items()}
    pump["close"][-3:] = pump["close"][-4] * 1.6                    # genuine 60% move that HOLDS → not corruption
    pump["high"][-3:] = pump["close"][-3:] * 1.001; pump["low"][-3:] = pump["close"][-3:] * 0.999
    assert bar_integrity(pump, live_price=float(pump["close"][-1])) == []
    assert any("disagree" in i for i in bar_integrity(good, live_price=float(good["close"][-1]) * 1.5))
    bad2 = {k: v.copy() for k, v in good.items()}
    bad2["high"][-2] = bad2["low"][-2] * 0.5                       # contradictory bar
    assert any("high < low" in i for i in bar_integrity(bad2))
    bad3 = {k: v.copy() for k, v in good.items()}
    bad3["close"][-1] = float("nan")
    assert any("non-finite" in i for i in bar_integrity(bad3))


def test_second_opinion_earns_weight_only_when_it_helps(db):
    import json
    from forge.research.metalabel import FEATS, SecondOpinion
    rng = np.random.default_rng(3)
    for i in range(400):
        f = {k: float(rng.normal()) for k in FEATS}
        win = int(f["ret_12"] + 0.3 * rng.normal() > 0)            # feature genuinely predictive
        db.insert("opportunities", {"id": f"o{i}", "ts": "t", "ts_ns": i, "venue": "v", "symbol": "S", "direction": "long",
                                    "score": 0, "expected_net_bps": 0, "probability": 0.5, "family": "fam_pred",
                                    "components": json.dumps({"feat": f}), "status": "OBSERVED",
                                    "outcome": json.dumps({"win": bool(win)})})
        g = {k: float(rng.normal()) for k in FEATS}
        db.insert("opportunities", {"id": f"r{i}", "ts": "t", "ts_ns": i, "venue": "v", "symbol": "S", "direction": "long",
                                    "score": 0, "expected_net_bps": 0, "probability": 0.5, "family": "fam_noise",
                                    "components": json.dumps({"feat": g}), "status": "OBSERVED",
                                    "outcome": json.dumps({"win": bool(rng.random() > 0.5)})})
    out = SecondOpinion(db).train()
    assert out["fam_pred"]["weight"] > 0.3                       # earned influence
    assert out["fam_noise"]["weight"] < 0.1                      # noise model earns ~nothing (no veto power)


def test_maker_requote_no_duplicates(db, tmp_path):
    from forge.audit.journal import AuditJournal
    from forge.core.ids import idempotency_key
    from forge.domain.market import BestBidAsk, MarketRules
    from forge.domain.trading import ExitPlan, IntentPurpose, RiskDecision, RiskVerdict, TradeIntent
    from forge.execution.gateway import ExecutionGateway, MarketView
    from forge.ledger.ledger import Ledger
    from forge.risk.breakers import BreakerBoard
    from forge.venues.base import FeeSchedule
    from forge.venues.paper import PaperVenue
    rules = MarketRules(venue="coinbase", symbol="SOL-USD", base="SOL", quote="USD", base_increment=D("0.00000001"),
                        quote_increment=D("0.01"), base_min_size=D("0"), quote_min_size=D("1"), price_increment=D("0.01"))
    box = {"b": BestBidAsk("coinbase", "SOL-USD", 100.0, 5, 100.02, 5, 0, 0)}
    lg = Ledger(db); lg.deposit("paper", D("28"), ref_id="s")
    v = PaperVenue(FeeSchedule(D("0.005"), D("0.009")), lambda s: rules, lambda s: box["b"], lambda s: None, {"USD": D("28")})
    gw = ExecutionGateway(db, lg, v, "paper", MarketView(lambda s: box["b"], lambda s: rules), AuditJournal(tmp_path), BreakerBoard())
    it = TradeIntent(id="i1", ts_ns=0, book="paper", opportunity_id="o1", strategy_id="s1", venue="coinbase", symbol="SOL-USD",
                     side="buy", purpose=IntentPurpose.ENTRY, requested_notional_usd=D("10"),
                     exit_plan=ExitPlan(take_profit_pct=0.03, stop_loss_pct=0.02, time_stop_s=3600), idem_key=idempotency_key("o1"))
    dec = RiskDecision(intent_id="i1", verdict=RiskVerdict.APPROVE, approved_notional_usd=D("10"))
    async def run():
        pid = await gw.execute_entry(it, dec, ttl_s=300, maker_offset_bps=0, entry_style="maker", meta={"intent_id": "i1"})
        for k in range(3):                                         # market lifts away from our bid three times
            box["b"] = BestBidAsk("coinbase", "SOL-USD", 100.10 + 0.1 * k, 5, 100.12 + 0.1 * k, 5, 0, 0)
            db.execute("UPDATE positions SET meta = json_set(meta, '$.quoted_at', 0) WHERE id = ?", (pid,))
            await gw.tick(); await gw.tick()
        return pid
    pid = asyncio.run(run())
    import json
    meta = json.loads(db.query_one("SELECT meta FROM positions WHERE id = ?", (pid,))["meta"])
    orders = db.query("SELECT client_order_id, status, limit_price FROM orders ORDER BY submitted_at")
    assert meta["reprices"] == 3 and len(orders) == 4
    assert len({o["client_order_id"] for o in orders}) == 4                    # unique idempotent ids
    assert sum(o["status"] == "OPEN" for o in orders) == 1                     # exactly one live entry order at any time
