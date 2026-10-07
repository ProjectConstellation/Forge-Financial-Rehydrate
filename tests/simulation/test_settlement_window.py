"""SAGE-1: 60-s average settlement distribution, strike types, latency-survival rule, dedup."""
import asyncio
import math
import random
import time
import types
from collections import deque

import pytest

from forge.opportunities import settlement_window as sw
from forge.opportunities.kalshi_live import posterior_positive


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


def _seed_scorecard_db(db):
    def sig(series, underlying, ticker, close_ts, side, minutes, pnl, kind="SETTLE_WINDOW", status="SETTLED"):
        db.insert("crossrail_signals", {"ts": close_ts - minutes * 60, "kind": kind, "ticker": ticker, "series": series,
                                        "underlying": underlying, "minutes": minutes, "side": side, "price": 0.80,
                                        "fee": 0.01, "edge": 0.03, "close_ts": close_ts, "status": status, "pnl": pnl,
                                        "settled_ts": close_ts + 200 if status == "SETTLED" else None})
    # KXBTC15M: two signals in ONE cluster (same underlying / expiry / side, different strikes) + one losing NO
    sig("KXBTC15M", "BTC-USD", "KXBTC15M-A", 1000.0, "yes", 0.5, 0.19)          # 30 s   → 0_60s
    sig("KXBTC15M", "BTC-USD", "KXBTC15M-B", 1000.0, "yes", 0.5, 0.17)          # 30 s   → 0_60s, same cluster
    sig("KXBTC15M", "BTC-USD", "KXBTC15M-C", 2000.0, "no", 2.0, -0.86)          # 120 s  → 60_180s
    # KXETHD: three independent winners
    sig("KXETHD", "ETH-USD", "KXETHD-A", 3000.0, "yes", 4.0, 0.08)              # 240 s  → 180_300s
    sig("KXETHD", "ETH-USD", "KXETHD-B", 4000.0, "no", 1.0, 0.05)               # 60 s   → 60_180s (lower bound)
    sig("KXETHD", "ETH-USD", "KXETHD-C", 5000.0, "yes", 0.99, 0.10)             # 59.4 s → 0_60s
    sig("KXSOL15M", "SOL-USD", "KXSOL15M-A", 6000.0, "no", 5.5, -0.30)          # 330 s  → other
    # must be ignored: unsettled SETTLE_WINDOW, and other signal kinds
    sig("KXBTC15M", "BTC-USD", "KXBTC15M-D", 7000.0, "yes", 0.5, None, status="OPEN")
    sig("KXBTC15M", "BTC-USD", "KXBTC15M-E", 8000.0, "yes", 0.5, 5.0, kind="TAKE_THRESH")

    def cal(series, ticker, secs, p_model, bid, ask, outcome):
        db.insert("sw_calibration", {"ts": 1.0, "ticker": ticker, "series": series, "underlying": "X", "secs_to_close": secs,
                                     "n_realized": 0, "p_model": p_model, "p_cons_yes": p_model, "p_cons_no": 1 - p_model,
                                     "yes_bid": bid, "yes_ask": ask, "close_ts": 1000.0, "outcome": outcome})
    cal("KXBTC15M", "KXBTC15M-A", 30, 0.9, 0.70, 0.80, 1)       # model .1², mid .75 → .25²
    cal("KXBTC15M", "KXBTC15M-A", 100, 0.8, 0.65, 0.75, 1)      # model .2², mid .70 → .3²
    cal("KXBTC15M", "KXBTC15M-B", 200, 0.2, 0.35, 0.45, 0)      # model .2², mid .40 → .4²
    cal("KXETHD", "KXETHD-A", 45, 0.6, 0.45, 0.55, 0)           # model .6², mid .50 → .5²
    cal("KXETHD", "KXETHD-B", 45, 0.6, 0.45, 0.55, None)        # unsettled: excluded
    cal("KXSOL15M", "KXSOL15M-A", 45, 0.6, 0.45, 0.55, None)    # series with no settled calibration: absent


def _scorecard_engine(db):
    eng = sw.SettlementWindowEngine.__new__(sw.SettlementWindowEngine)
    eng.f = types.SimpleNamespace(db=db)
    eng.stats = {"hot_sweeps": 0, "signals": 0, "missed_after_latency": 0, "calib": 0, "basis_obs": 0}
    eng.basis = {"BTC-USD": (1.0e-4, (1.5e-4) ** 2, 10)}
    return eng


def test_scorecard_by_series_pnl_and_cluster_posterior(db):
    _seed_scorecard_db(db)
    sc = _scorecard_engine(db).scorecard()
    assert set(sc["by_series"]) == {"KXBTC15M", "KXETHD", "KXSOL15M"}
    btc = sc["by_series"]["KXBTC15M"]
    assert (btc["n"], btc["wins"], btc["n_clusters"]) == (3, 2, 2)              # OPEN + TAKE_THRESH rows ignored
    assert btc["pnl"] == pytest.approx(-0.50) and btc["mean_pnl_per_contract"] == pytest.approx(-0.5 / 3, abs=1e-5)
    m, p = posterior_positive([0.18, -0.86])                                    # the two KXBTC15M-A/B bets count once
    assert btc["cluster_mean_pnl"] == pytest.approx(m, abs=1e-5) and btc["p_mean_positive"] == round(p, 4)
    assert btc["p_mean_positive"] < 0.5
    eth = sc["by_series"]["KXETHD"]
    assert (eth["n"], eth["wins"], eth["n_clusters"]) == (3, 3, 3)
    assert eth["pnl"] == pytest.approx(0.23) and eth["mean_pnl_per_contract"] == pytest.approx(0.23 / 3, abs=1e-5)
    assert eth["p_mean_positive"] == round(posterior_positive([0.08, 0.05, 0.10])[1], 4) and eth["p_mean_positive"] > 0.5
    assert sc["by_series"]["KXSOL15M"]["n"] == 1 and sc["by_series"]["KXSOL15M"]["wins"] == 0


def test_scorecard_by_seconds_to_close_buckets(db):
    _seed_scorecard_db(db)
    b = _scorecard_engine(db).scorecard()["by_seconds_to_close"]
    assert list(b) == ["0_60s", "60_180s", "180_300s", "other"]
    assert (b["0_60s"]["n"], b["0_60s"]["wins"], b["0_60s"]["n_clusters"]) == (3, 3, 2)
    assert b["0_60s"]["pnl"] == pytest.approx(0.46)
    assert b["0_60s"]["p_mean_positive"] == round(posterior_positive([0.18, 0.10])[1], 4)
    assert (b["60_180s"]["n"], b["60_180s"]["wins"]) == (2, 1) and b["60_180s"]["pnl"] == pytest.approx(-0.81)
    assert (b["180_300s"]["n"], b["180_300s"]["wins"]) == (1, 1) and b["180_300s"]["pnl"] == pytest.approx(0.08)
    assert b["other"]["n"] == 1 and b["other"]["pnl"] == pytest.approx(-0.30)
    assert sw._secs_bucket(179.99999999999997 / 60) == "180_300s" and sw._secs_bucket(None) == "other"


def test_scorecard_brier_by_series_and_existing_keys_unchanged(db):
    _seed_scorecard_db(db)
    sc = _scorecard_engine(db).scorecard()
    bs = sc["brier_by_series"]
    assert set(bs) == {"KXBTC15M", "KXETHD"}
    assert (bs["KXBTC15M"]["n"], bs["KXBTC15M"]["n_markets"]) == (3, 2)
    assert bs["KXBTC15M"]["model"] == pytest.approx(0.03) and bs["KXBTC15M"]["market_mid"] == pytest.approx(0.10417)
    assert bs["KXBTC15M"]["model_minus_market"] == pytest.approx(0.03 - 0.3125 / 3, abs=1e-5)
    assert (bs["KXETHD"]["n"], bs["KXETHD"]["model"], bs["KXETHD"]["market_mid"]) == (1, 0.36, 0.25)
    # pre-existing keys keep their shape and values
    assert sc["stats"]["signals"] == 0 and sc["basis_bp"] == {"BTC-USD": 1.0}
    assert sc["brier_0_60s"] == {"n": 2, "model": 0.185, "market_mid": 0.15625}
    assert sc["brier_60_180s"] == {"n": 1, "model": 0.04, "market_mid": 0.09}
    assert sc["brier_180_300s"] == {"n": 1, "model": 0.04, "market_mid": 0.16}
    db.kv_set("settlement_window.scorecard", sc)                                # what run() persists: JSON-safe
    assert db.kv_get("settlement_window.scorecard")["by_series"]["KXETHD"]["wins"] == 3


def test_scorecard_empty_db_has_new_keys(db):
    sc = _scorecard_engine(db).scorecard()
    assert sc["by_series"] == {} and sc["by_seconds_to_close"] == {} and sc["brier_by_series"] == {}
    assert not any(k in sc for k in ("brier_0_60s", "brier_60_180s", "brier_180_300s"))
