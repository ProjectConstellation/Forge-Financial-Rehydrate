from decimal import Decimal as D

from hypothesis import given, settings
from hypothesis import strategies as st

from forge.ledger.ledger import Ledger
from forge.persistence.db import Database


def test_buy_sell_true_net(db):
    lg = Ledger(db)
    lg.deposit("paper", D("28.27"), ref_id="seed")
    lg.record_fill("paper", "coinbase", "SOL-USD", "buy", D("100"), D("0.2"), D("0.10"), "t1", "stg_a", "o1")
    r = lg.record_fill("paper", "coinbase", "SOL-USD", "sell", D("105"), D("0.2"), D("0.105"), "t2", "stg_a", "o2")
    assert r == D("1.0")
    lg.record_opex("paper", "INFERENCE", D("0.05"), "call1", strategy_id="stg_a")
    s = lg.state("paper").summary({})
    assert s["realized_pnl_usd"] == D("1.0")
    assert s["fees_usd"] == D("0.205")
    assert s["true_net_usd"] == D("1.0") - D("0.205") - D("0.05")
    assert s["cash_usd"] == D("28.27") + D("1.0") - D("0.205")
    assert lg.check_balanced("paper") == 0
    per = lg.strategy_pnl("paper")["stg_a"]
    assert per["true_net"] == D("1.0") - D("0.205") - D("0.05")


def test_fill_idempotent(db):
    lg = Ledger(db)
    lg.deposit("paper", D("10"), ref_id="s")
    for _ in range(3):
        lg.record_fill("paper", "coinbase", "BTC-USD", "buy", D("50000"), D("0.0001"), D("0.025"), "dup", None, "o")
    st_ = lg.state("paper")
    assert st_.holdings[("coinbase", "BTC")].qty == D("0.0001")


@settings(max_examples=60, deadline=None)
@given(st.lists(st.tuples(st.integers(1, 1000), st.integers(1, 50), st.integers(0, 30)), min_size=1, max_size=15))
def test_ledger_always_balances(trades):
    """Property: after any sequence of round trips, the ledger balances exactly (DOSSIER §46)."""
    db = Database(":memory:")
    db.migrate()
    lg = Ledger(db)
    lg.deposit("paper", D("1000000"), ref_id="seed")
    for i, (p, q, f) in enumerate(trades):
        price, qty, fee = D(p), D(q) / D(100), D(f) / D(100)
        lg.record_fill("paper", "v", "X-USD", "buy", price, qty, fee, f"b{i}", "s", f"ob{i}")
        lg.record_fill("paper", "v", "X-USD", "sell", price * D("1.01"), qty, fee, f"s{i}", "s", f"os{i}")
    assert lg.check_balanced("paper") == 0
    s = lg.state("paper").summary({})
    assert s["true_net_usd"] == s["realized_pnl_usd"] - s["fees_usd"]
