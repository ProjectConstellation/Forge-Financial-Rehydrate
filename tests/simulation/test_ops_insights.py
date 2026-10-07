"""EXECUTIVE OPS insight tools: leaderboard, trades, changes, series, edge-triggered alerts, credential requests."""
import json
import time
import types

import pytest

from forge.ops import insights


@pytest.fixture()
def f(db):
    db.kv_set("velocity", {"treasury": {"total": 28.27}, "realized": {"1h": {"usd_per_h": 0.01}},
                           "expected_usd_per_h": {"potential": 0.03},
                           "streams": [{"id": "kalshi.SETTLE_WINDOW", "n": 12, "mu": 0.04, "lam": 3.0, "tier": "LOW", "p_pos": 0.85},
                                       {"id": "kalshi.MAKE", "n": 90, "mu": -0.2, "lam": 8.0, "tier": "UNPROVEN", "p_pos": 0.01}],
                           "frontier": {"potential": {"streams": [{"stream": "kalshi.SETTLE_WINDOW", "usd_per_h": 0.02}]}}})
    now_iso = insights._iso(time.time() - 600)
    db.insert("strategies", {"id": "stg_a", "family": "breakout", "generation": 1, "population": "SHADOW", "genome": "{}",
                             "genome_hash": "h", "parent_ids": "[]", "hypothesis": "", "fitness": 1.0,
                             "virtual_allocation_usd": 0, "created_at": now_iso, "updated_at": now_iso})
    for i, pnl in enumerate((0.3, -0.1)):
        db.insert("positions", {"id": f"p{i}", "book": "paper", "venue": "paper", "symbol": "BTC-USD", "strategy_id": "stg_a",
                                "status": "CLOSED", "qty": "0", "cost_usd": "5", "fees_usd": "0.01", "realized_pnl_usd": str(pnl),
                                "opened_at": now_iso, "closed_at": now_iso, "exit_reason": "TP", "meta": "{}"})
    return types.SimpleNamespace(db=db, treasury={"equity_usd": 27.5}, health=None)


def test_leaderboard_trades_changes_series(f):
    lb = insights.leaderboard(f, "24h")
    assert lb["strategies_best"][0]["id"] == "stg_a" and abs(lb["strategies_best"][0]["net_usd"] - 0.18) < 1e-9
    assert [s["id"] for s in lb["streams_ranked"]] == ["kalshi.SETTLE_WINDOW", "kalshi.MAKE"]
    assert lb["streams_ranked"][0]["potential_usd_per_h"] == 0.02
    tr = insights.trades(f, "24h")
    assert len(tr["positions"]) == 2 and tr["open_now"] == 0 and "kalshi_signals" in tr
    ch = insights.changes(f, "today")
    assert {"deployments", "strategy_promotions", "owner_and_agent_actions", "incidents_repaired"} <= set(ch)
    s = insights.series(f, "stream_pnl", "24h")
    assert s["kind"] == "bar"
    with pytest.raises(ValueError):
        insights.series(f, "nonsense", "24h")


def test_alerts_edge_triggered(f):
    db = f.db
    db.insert("ops_alerts", {"ts": time.time(), "metric": "treasury_usd", "op": ">", "threshold": "30", "note": "hit $30"})
    assert insights.evaluate_alerts(f) == 0
    db.kv_set("velocity", {**db.kv_get("velocity"), "treasury": {"total": 31.0}})
    assert insights.evaluate_alerts(f) == 1
    assert insights.evaluate_alerts(f) == 0                         # stays true → no repeat
    db.kv_set("velocity", {**db.kv_get("velocity"), "treasury": {"total": 29.0}})
    insights.evaluate_alerts(f)                                    # re-arms
    db.kv_set("velocity", {**db.kv_get("velocity"), "treasury": {"total": 32.0}})
    assert insights.evaluate_alerts(f) == 1
    msgs = db.kv_get("ops.outbox")
    assert len(msgs) == 2 and "hit $30" in msgs[0]["text"]
    db.insert("ops_alerts", {"ts": time.time(), "metric": "stream_tier", "arg": "kalshi.SETTLE_WINDOW", "op": "==",
                             "threshold": "MEDIUM", "note": "SAGE-1 proven", "once": 1})
    assert insights.evaluate_alerts(f) == 0


def test_credential_request_validation(f):
    r = insights.credential_request(f.db, "KALSHI_API_KEY_ID", "Kalshi trading key id")
    assert r["link"].startswith("https://forge.northstarimagine.com/setup/credential?r=")
    assert insights.credential_request(f.db, "kalshi_private_key", "Kalshi key", "pem")["kind"] == "pem"
    for bad, kind in (("lower_env", "env"), ("BAD-NAME", "env"), ("UPPER", "pem")):
        with pytest.raises(ValueError):
            insights.credential_request(f.db, bad, "x", kind)
    assert len(f.db.kv_get("ops.cred_requests")) == 2 and json.dumps(f.db.kv_get("ops.cred_requests")).count("used") == 2
