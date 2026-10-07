"""SAGE-1: 60-s average settlement distribution, strike types, latency-survival rule, dedup."""
import asyncio
import math
import random
import time
import types
from collections import deque

from forge.opportunities import settlement_window as sw


def test_variance_formula_matches_brute_force_and_monte_carlo():
    close, now, spot, sig = 1000.0, 939.0, 100.0, 1e-4        # whole window ahead: samples at close−60 … close−1
    mean, sd, n_real = sw.window_distribution(now, close, spot, sig, [])
    d = list(range(1, 61))
    brute = sum(min(a, b) for a in d for b in d)
    assert abs(sd - spot * sig * math.sqrt(brute) / 60) < 1e-12 and n_real == 0 and mean == spot
    rng = random.Random(7)
    sims = []
    for _ in range(4000):
        x, acc = spot, 0.0
        for _ in range(60):
            x *= math.exp(rng.gauss(0, sig))
            acc += x
        sims.append(acc / 60)
    m = sum(sims) / len(sims)
    mc_sd = math.sqrt(sum((v - m) ** 2 for v in sims) / len(sims))
    assert abs(mc_sd - sd) / sd < 0.06


def test_partially_and_fully_realized_window():
    close = 1000.0
    realized = [(940.0 + i, 101.0) for i in range(60)]
    mean, sd, n = sw.window_distribution(1000.5, close, 50.0, 1e-3, realized)     # window over: spot irrelevant
    assert (round(mean, 9), sd, n) == (101.0, 0.0, 60)
    mean, sd, n = sw.window_distribution(970.0, close, 102.0, 1e-4, realized[:31])  # 31 realized, 29 to come
    assert n == 31 and abs(mean - (31 * 101 + 29 * 102) / 60) < 1e-9 and sd > 0
    assert sw.p_outcome(100.0, 0.0, "greater_or_equal", 100.0, None) == 1.0
    assert abs(sw.p_outcome(100.0, 1.0, "greater", 100.0, None) - 0.5) < 1e-12
    assert abs(sw.p_outcome(100.0, 1.0, "less", None, 100.0) - 0.5) < 1e-12
    assert 0.68 < sw.p_outcome(100.0, 1.0, "between", 99.0, 101.0) < 0.69
    assert math.isnan(sw.p_outcome(100.0, 1.0, "custom", None, None))


def _engine(db, quotes_after):
    from forge.opportunities.kalshi import KalshiMarket
    eng = sw.SettlementWindowEngine.__new__(sw.SettlementWindowEngine)
    eng.stats = {"hot_sweeps": 0, "signals": 0, "missed_after_latency": 0, "calib": 0, "basis_obs": 0}
    eng._last_cal, eng.basis, eng.markets = {}, {"BTC-USD": (0.0, (1.5e-4) ** 2, 10)}, {}
    now = time.time()
    rng = random.Random(1)
    q = deque(maxlen=1800)
    px = 100.0
    for i in range(400):                                    # last 400 s; strongly above the strike all window
        px *= math.exp(rng.gauss(0, 5e-5))
        q.append((now - 400 + i, 105.0 + (px - 100.0)))
    eng.samples = {"BTC-USD": q}

    class K:
        async def market(self, t):
            return quotes_after
    eng.f = types.SimpleNamespace(db=db, crossrail=types.SimpleNamespace(k=K(), series_meta={"KXBTC15M": {}}))
    close = now + 20                                        # 40 s of the window realized at ~105, strike 100
    mk = KalshiMarket("KXBTC15M-T", "EV", "KXBTC15M", "greater_or_equal", 100.0, None, close, 0.80, 0.85, 50, 50, 0, 0, "active", "")
    return eng, {"pid": "BTC-USD", "mk": mk, "series": "KXBTC15M"}


def test_signal_only_if_quote_survives_latency(db, monkeypatch):
    monkeypatch.setattr(sw, "LATENCY_S", 0.0)
    gone = {"ticker": "KXBTC15M-T", "yes_ask_dollars": "0.9900", "yes_bid_dollars": "0.9800", "strike_type": "greater_or_equal",
            "floor_strike": 100.0, "close_time": "2030-01-01T00:00:00Z", "status": "active"}
    eng, info = _engine(db, gone)
    asyncio.run(eng._evaluate(info, "KXBTC15M"))
    assert eng.stats["missed_after_latency"] == 1 and db.scalar("SELECT COUNT(*) FROM crossrail_signals") == 0
    assert db.scalar("SELECT COUNT(*) FROM sw_calibration") == 1                    # calibration sampled regardless
    still = dict(gone, yes_ask_dollars="0.8500", yes_bid_dollars="0.8000", yes_ask_size_fp="50")
    eng, info = _engine(db, still)
    asyncio.run(eng._evaluate(info, "KXBTC15M"))
    r = db.query_one("SELECT kind, side, price, fee, edge, status FROM crossrail_signals")
    assert r["kind"] == "SETTLE_WINDOW" and r["side"] == "yes" and r["price"] == 0.85 and r["edge"] >= 0.02
    asyncio.run(eng._evaluate(info, "KXBTC15M"))                                     # dedup: one signal per ticker/side
    assert db.scalar("SELECT COUNT(*) FROM crossrail_signals") == 1
