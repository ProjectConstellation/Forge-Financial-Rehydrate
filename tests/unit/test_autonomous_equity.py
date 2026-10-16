from datetime import date, timedelta
import json

from forge.research.autonomous_equity import advance, signal


def bars(n=100, falling=False):
    rows = []
    for i in range(n):
        price = 100 * ((.997 if falling else 1.003) ** i)
        rows.append(dict(t=(date(2026, 1, 1) + timedelta(days=i)).isoformat(), o=price, c=price))
    return rows


def call(state, rows, today, running=True):
    return advance(state, rows, bars(len(rows)), today=today, now=1., running=running,
                   bankroll=50., max_open=25., max_order=15.)


def test_registration_never_backfills_history():
    s = call(None, bars(70), "2026-03-11")
    assert all(t["sessions"] == 0 and not t["trades"] for t in s["trials"])
    assert s["earned_usd"] == 0 and not s["live_ready"]
    assert sum(t["allocation_usd"] for t in s["trials"]) <= 25


def test_automatic_rotation_and_idempotency():
    s = call(None, bars(30), "2026-01-30")
    s = call(s, bars(65), "2026-03-07")
    assert len(s["history"]) == 2
    assert all(t["state"] == "RETIRED" for t in s["history"])
    assert s["trials"][0]["mechanism"] == "dip_reversion"
    assert s["trials"][1]["mechanism"] == "trend_following"
    serialized = json.dumps(s, sort_keys=True)
    assert json.dumps(call(s, bars(65), "2026-03-07"), sort_keys=True) == serialized


def test_future_paper_trade_complete_and_costed():
    s = call(None, bars(30), "2026-01-30")
    s["trials"][0]["mechanism"] = "trend_following"
    s = call(s, bars(65), "2026-03-07")
    measured = s["history"][0]
    assert len(measured["trades"]) >= 3
    for trade in measured["trades"]:
        assert trade["signal_at"] < trade["entry_at"] < trade["exit_at"]
        expected = trade["notional_usd"] * (trade["exit_price"] / trade["entry_price"] - 1 - .002)
        assert trade["net_usd"] == expected
    assert measured["state"] == "RETIRED"  # profitable but loses to buy-and-hold
    assert s["earned_usd"] == 0


def test_global_stop_prevents_advancing_or_entering():
    s = call(None, bars(30), "2026-01-30")
    stopped = call(s, bars(65), "2026-03-07", running=False)
    assert stopped["blocked"] == "GLOBAL_TRADING_NOT_RUNNING"
    assert all(t["sessions"] == 0 and t["position"] is None for t in stopped["trials"])


def test_signals_exclude_unknown_mechanisms():
    import pytest
    with pytest.raises(ValueError):
        signal("invented", list(zip(bars(30), bars(30))))


def test_shared_loss_limit_blocks_new_entries():
    s = call(None, bars(30), "2026-01-30")
    s["trials"][0]["net_usd"] = -6.
    s["trials"][1]["mechanism"] = "trend_following"
    s = call(s, bars(40), "2026-02-10")
    assert all(t["position"] is None for t in s["trials"])
    assert s["blocked"] == "SHARED_SIMULATION_LOSS_LIMIT"


def test_positive_trial_is_retained_for_new_future_block(monkeypatch):
    monkeypatch.setattr("forge.research.autonomous_equity.signal", lambda mechanism, history: len(history) % 6 == 0)
    rows = bars(50)
    for i, row in enumerate(rows):
        row["o"] = row["c"] = 100 + i % 6
    s = call(None, rows[:30], "2026-01-30")
    s = call(s, rows, "2026-02-20")
    assert all(t["state"] == "RETAINED" for t in s["history"])
    assert all(t["sessions"] == 0 and t["generation"] == 2 for t in s["trials"])
    assert s["trials"][0]["mechanism"] == "relative_momentum"
    assert not s["live_ready"]


def test_paused_sessions_are_not_backfilled():
    s = call(None, bars(30), "2026-01-30")
    s["paused_after"] = "2026-02-08"
    s = call(s, bars(40), "2026-02-10")
    assert all(t["sessions"] == 1 for t in s["trials"])
