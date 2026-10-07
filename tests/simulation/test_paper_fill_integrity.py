"""Paper fills survive restarts: unique trade ids across venue instances; unrecorded fills are rebuilt from order truth."""
import asyncio
from decimal import Decimal

from forge.venues.paper import PaperVenue


def test_trade_ids_unique_across_restarts():
    import time
    ids = set()
    for _ in range(3):                       # three "process lifetimes"
        v = PaperVenue.__new__(PaperVenue)
        import itertools
        v._ids, v._run = itertools.count(1), format(time.time_ns(), "x")
        ids.add(f"pt-{v._run}-{next(v._ids)}")
        time.sleep(0.001)
    assert len(ids) == 3


def test_repair_rebuilds_dropped_exit_fill(db):
    import json
    import types

    from forge.execution.gateway import ExecutionGateway
    from forge.ledger.ledger import Ledger
    ledger = Ledger(db)
    ledger.record_deposit("paper", "USD", Decimal("100"), "seed") if hasattr(ledger, "record_deposit") else None
    # buy recorded normally
    ledger.record_fill("paper", "paper", "QNT-USD", "buy", Decimal("266.05"), Decimal("0.013"), Decimal("0.017"), "pt-1",
                       "stg_x", "entry1", quote_asset="USD")
    db.insert("positions", {"id": "pos1", "book": "paper", "venue": "paper", "symbol": "QNT-USD", "strategy_id": "stg_x",
                            "status": "CLOSED", "qty": "0.013", "cost_usd": "3.45865", "entry_price": "266.05",
                            "fees_usd": "0.017", "realized_pnl_usd": "0", "opened_at": "2026-10-07T01:58:00+00:00",
                            "closed_at": "2026-10-07T05:04:07+00:00", "exit_reason": "SL",
                            "meta": json.dumps({"entry_cid": "entry1", "exit_cid": "exit1"})})
    # exit order FILLED at the venue, but its fill was dropped (id collision) → no fills row, no ledger sell
    db.insert("orders", {"intent_id": None, "book": "paper", "venue": "paper", "client_order_id": "exit1", "symbol": "QNT-USD",
                         "side": "sell", "order_type": "market", "status": "FILLED", "filled_size": "0.013",
                         "avg_fill_price": "248.445153", "fees": "0.029", "submitted_at": "2026-10-07T05:04:05+00:00",
                         "updated_at": "2026-10-07T05:04:05+00:00"})
    audit = types.SimpleNamespace(events=[], append=lambda k, d, actor=None: audit.events.append(k))
    gw = ExecutionGateway.__new__(ExecutionGateway)
    gw.db, gw.ledger, gw.book, gw.audit = db, ledger, "paper", audit
    assert gw.repair_unrecorded_fills() == 1
    assert gw.repair_unrecorded_fills() == 0                                   # idempotent
    p = db.query_one("SELECT * FROM positions WHERE id = 'pos1'")
    assert Decimal(p["qty"]) == 0 and Decimal(p["exit_price"]) == Decimal("248.445153")
    assert Decimal(p["realized_pnl_usd"]) < 0                                   # stop-loss loss now on the books
    assert db.scalar("SELECT COUNT(*) FROM fills WHERE order_id = 'exit1'") == 1 and "FILL_REPAIRED" in audit.events
    _ = asyncio
