"""Kalshi live: signing (Ed25519 + RSA-PSS), V2 order bodies, evidence ladder, CUSUM, gated execution round trip."""
import asyncio
import base64
import time
import types

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from forge.opportunities.kalshi_live import KalshiLive, cusum, ladder_contracts, posterior_positive
from forge.venues.kalshi import auth_headers, order_body


def test_signatures_verify_for_both_key_types():
    for pk in (ed25519.Ed25519PrivateKey.generate(), rsa.generate_private_key(public_exponent=65537, key_size=2048)):
        h = auth_headers("kid", pk, "post", "/trade-api/v2/portfolio/events/orders?x=1", ts_ms=1700000000000)
        msg = b"1700000000000POST/trade-api/v2/portfolio/events/orders"          # query stripped, method upper-cased
        sig = base64.b64decode(h["KALSHI-ACCESS-SIGNATURE"])
        if isinstance(pk, ed25519.Ed25519PrivateKey):
            pk.public_key().verify(sig, msg)
        else:
            pk.public_key().verify(sig, msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                                         salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
        assert h["KALSHI-ACCESS-KEY"] == "kid" and h["KALSHI-ACCESS-TIMESTAMP"] == "1700000000000"


def test_v2_order_bodies():
    y = order_body("KXBTCD-X", "yes", 0.56, 1, "c1")
    n = order_body("KXBTCD-X", "no", 0.62, 2, "c2")
    assert (y["side"], y["price"], y["count"], y["time_in_force"]) == ("bid", "0.5600", "1.00", "immediate_or_cancel")
    assert (n["side"], n["price"], n["count"]) == ("ask", "0.3800", "2.00")       # buy NO 0.62 ≡ sell YES 0.38


def test_ladder_and_cusum():
    assert ladder_contracts([0.1] * 5)[0] == 0                                   # too few
    assert ladder_contracts([0.45, -0.55, 0.45, 0.45, 0.45, -0.55, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45])[0] == 2   # MEDIUM
    assert ladder_contracts([0.45, -0.55] * 15)[0] == 0                            # mean −5¢ → closed
    strong = [0.40, 0.40, 0.40, -0.60] * 15                                        # mean +15¢, n=60
    assert ladder_contracts(strong)[0] == 50 and posterior_positive(strong)[1] > 0.99      # EXCEPTIONAL → frontier
    assert cusum([-0.05] * 3) < -0.08 and cusum([0.0] * 50) == 0.0


def test_gated_round_trip(db, monkeypatch):
    class FakeClient:
        def __init__(self): self.orders = []
        async def buy(self, ticker, side, price, count, cid):
            self.orders.append((ticker, side, price, count, cid))
            return {"order": {"order_id": "o1", "fill_count": f"{count}.00", "average_fill_price": f"{1 - price:.4f}" if side == "no" else f"{price:.4f}",
                              "average_fee_paid": "0.0100"}}
        async def balance(self): return {"balance_dollars": "15.00"}
    said = []
    async def say(*a, **k): said.append(a)
    f = types.SimpleNamespace(db=db, say=say)
    kl = KalshiLive(f)
    assert kl.decision()[0] == 0 and "credentials" in kl.decision()[1]
    kl.client = FakeClient()
    monkeypatch.setattr("forge.core.state.trading_state", lambda d: "RUNNING")
    # evidence: 12 settled out-of-sample TAKE_THRESH signals, +25¢ mean
    for i in range(12):
        db.insert("crossrail_signals", {"ts": time.time() - 4000, "kind": "TAKE_THRESH", "ticker": f"T{i}", "side": "yes",
                                        "price": 0.5, "fee": 0.02, "edge": 0.05, "status": "SETTLED",
                                        "pnl": 0.48 if i % 4 else -0.52, "settled_ts": time.time() - 3000, "close_ts": 0})
    assert kl.decision()[0] == 2
    db.kv_set("velocity", {"treasury": {"total": 30.0}})                         # bootstrap regime, $30 treasury
    sid = db.insert_id("crossrail_signals", {"ts": time.time(), "kind": "TAKE_THRESH", "ticker": "KXBTCD-LIVE", "side": "no",
                                             "price": 0.60, "fee": 0.02, "edge": 0.05, "status": "OPEN", "close_ts": time.time() - 200})
    sig = {"id": sid, "ts": time.time(), "ticker": "KXBTCD-LIVE", "side": "no", "price": 0.60, "fee": 0.02, "close_ts": time.time() - 200}
    asyncio.run(kl.on_signal(sig))
    asyncio.run(kl.on_signal(sig))                                                # idempotent: no duplicate order
    assert len(kl.client.orders) == 1 and kl.client.orders[0][:4] == ("KXBTCD-LIVE", "no", 0.60, 2)
    o = db.query_one("SELECT * FROM kalshi_live_orders")
    assert o["status"] == "FILLED" and abs(o["avg_price"] - 0.60) < 1e-9 and abs(o["cost"] - 1.22) < 1e-9
    db.execute("UPDATE crossrail_signals SET status='SETTLED', payout=1.0, pnl=0.38, settled_ts=? WHERE id=?", (time.time(), sid))
    assert asyncio.run(kl.settle()) == 1
    o = db.query_one("SELECT * FROM kalshi_live_orders")
    assert o["status"] == "SETTLED" and abs(o["pnl"] - 0.78) < 1e-9
    # bootstrap circuit breakers on a $30 treasury: hourly 15% ($4.50), daily 35% ($10.50)
    db.execute("UPDATE kalshi_live_orders SET pnl = -4.0, shadow_pnl = -2.0")
    assert kl.decision()[0] == 2
    db.execute("UPDATE kalshi_live_orders SET pnl = -5.0, shadow_pnl = -2.5")
    assert kl.decision()[0] == 0 and kl.paused_until > time.time()        # hourly breaker → 1 h pause
    kl.paused_until = 0.0
    now = time.time()
    day0 = now - now % 86400
    if now - day0 > 3700:                                   # an earlier-today loss: outside the hour, inside the day
        db.execute("UPDATE kalshi_live_orders SET pnl = -11.0, shadow_pnl = -5.5, settled_ts = ?", (day0 + 1,))
        assert kl.decision()[0] == 0 and "daily circuit breaker" in kl.decision()[1]
