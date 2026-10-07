"""Economic telemetry for any window (30 s … lifetime): 10-second marks + ledger/position truth.

Every 10 s FORGE records an `econ_ticks` mark: live wallet total, paper equity, cumulative realized (paper + live),
fees, inference and compute spend, deployed capital and unrealized P&L. Any window answer = difference of the two marks
bracketing it (true net = Δ equity − deposits + withdrawals), plus per-strategy and per-rail breakdowns from ledgers.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger("forge.econ")
TICK_S = 10
KEEP_DAYS = 14
WINDOWS = {"30s": 30, "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "24h": 86400, "7d": 604800}


def parse_window(w: str) -> tuple[float, str]:
    """'30s','1m','2h','today','24h','lifetime','7d' → (since_ts, label)."""
    now = time.time()
    w = (w or "1h").strip().lower()
    if w in ("today", "day"):
        return now - now % 86400, "today (UTC)"
    if w in ("lifetime", "all", "total"):
        return 0.0, "lifetime"
    if w in WINDOWS:
        return now - WINDOWS[w], f"last {w}"
    m = re.fullmatch(r"(\d+)\s*(s|sec|m|min|h|hr|d)", w)
    if m:
        mult = {"s": 1, "sec": 1, "m": 60, "min": 60, "h": 3600, "hr": 3600, "d": 86400}[m.group(2)]
        return now - int(m.group(1)) * mult, f"last {m.group(1)}{m.group(2)}"
    raise ValueError("window: 30s, 1m, 15m, 1h, 4h, today, 24h, 7d, lifetime or e.g. 90s / 3h / 2d")


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).isoformat()


def mark(forge: Any) -> dict[str, Any]:
    db = forge.db
    v = db.kv_get("velocity") or {}
    t = getattr(forge, "treasury", {}) or {}
    live_total = (v.get("treasury") or {}).get("total")
    if live_total is None:
        live_total = float(db.scalar("SELECT account_total_usd FROM equity_series ORDER BY ts DESC LIMIT 1") or 0)
    led = {r["account"]: float(r["s"] or 0) for r in db.query(
        "SELECT account, SUM(amount_usd) s FROM ledger_entries WHERE account IN ('FEES','OPEX:INFERENCE','OPEX:COMPUTE') "
        "GROUP BY account")}
    realized = float(db.scalar("SELECT COALESCE(SUM(realized_pnl_usd),0) FROM positions WHERE book='paper' AND status='CLOSED'") or 0)
    live_real = float(db.scalar("SELECT COALESCE(SUM(pnl),0) FROM kalshi_live_orders WHERE status='SETTLED'") or 0) + float(
        db.scalar("SELECT COALESCE(SUM(realized_pnl_usd),0) FROM positions WHERE book='live' AND status='CLOSED'") or 0)
    deployed = float(db.scalar("SELECT COALESCE(SUM(cost_usd),0) FROM positions WHERE status IN ('OPEN','OPENING')") or 0) + float(
        db.scalar("SELECT COALESCE(SUM(cost),0) FROM kalshi_live_orders WHERE status='FILLED'") or 0)
    return {"ts": time.time(), "live_total_usd": float(live_total or 0), "paper_equity_usd": float(t.get("equity_usd") or 0),
            "realized_cum_usd": realized, "live_realized_cum_usd": live_real, "fees_cum_usd": led.get("FEES", 0.0),
            "inference_cum_usd": led.get("OPEX:INFERENCE", 0.0), "compute_cum_usd": led.get("OPEX:COMPUTE", 0.0),
            "deployed_usd": deployed, "unrealized_usd": float(t.get("unrealized_pnl_usd") or 0)}


def _tick_at(db: Any, ts: float, before: bool = True) -> dict[str, Any] | None:
    if before:
        return db.query_one("SELECT * FROM econ_ticks WHERE ts <= ? ORDER BY ts DESC LIMIT 1", (ts,)) or \
            db.query_one("SELECT * FROM econ_ticks ORDER BY ts ASC LIMIT 1")
    return db.query_one("SELECT * FROM econ_ticks ORDER BY ts DESC LIMIT 1")


def window(forge: Any, w: str) -> dict[str, Any]:
    db = forge.db
    since, label = parse_window(w)
    now = mark(forge)
    a = _tick_at(db, since)
    covered_from = float(a["ts"]) if a else now["ts"]
    a = a or now
    d = {k: now[k] - float(a.get(k) or 0) for k in ("live_total_usd", "paper_equity_usd", "realized_cum_usd",
                                                     "live_realized_cum_usd", "fees_cum_usd", "inference_cum_usd",
                                                     "compute_cum_usd")}
    xfer = float(db.scalar("SELECT COALESCE(SUM(amount_usd),0) FROM ops_transfers WHERE status='EXECUTED' AND ts >= ?",
                           (since,)) or 0)
    secs = max(1.0, now["ts"] - max(since, covered_from))
    live_net = d["live_total_usd"] + xfer                      # withdrawals to the owner are not losses
    if since == 0.0:                                           # lifetime: wallet truth vs capital ever deposited
        deposits = float(db.scalar("SELECT COALESCE(SUM(amount_usd),0) FROM ledger_entries WHERE account='CASH:USD' AND "
                                   "kind='DEPOSIT'") or 0) + float(db.kv_get("treasury.external_deposits_usd") or 0)
        live_net = now["live_total_usd"] + xfer - deposits
        d["paper_equity_usd"] = now["paper_equity_usd"] - deposits
        first = db.scalar("SELECT MIN(ts) FROM ledger_entries")
        with contextlib.suppress(Exception):
            secs = max(1.0, now["ts"] - datetime.fromisoformat(str(first)).timestamp())
    iso = _iso(since)
    by_strategy = db.query("SELECT strategy_id, COUNT(*) trades, ROUND(SUM(realized_pnl_usd), 4) pnl FROM positions "
                           "WHERE status='CLOSED' AND closed_at >= ? GROUP BY strategy_id ORDER BY pnl DESC LIMIT 10", (iso,))
    by_rail = db.query("SELECT 'kalshi.' || kind AS rail, COUNT(*) n, ROUND(SUM(pnl), 4) pnl_per_contract_basis FROM "
                       "crossrail_signals WHERE status='SETTLED' AND settled_ts >= ? GROUP BY kind ORDER BY 3 DESC", (since,))
    by_rail += db.query("SELECT rail, COUNT(*) n, ROUND(SUM(pnl_usd), 6) pnl_usd FROM shadow_trades WHERE ts >= ? GROUP BY rail",
                        (since,))
    return {
        "window": label, "since_utc": _iso(since) if since else "inception", "seconds": round(secs),
        "data_coverage_from_utc": _iso(covered_from),
        "LIVE": {"true_net_usd": round(live_net, 6), "usd_per_hour": round(live_net / secs * 3600, 6),
                 "realized_usd": round(d["live_realized_cum_usd"], 6), "treasury_now_usd": round(now["live_total_usd"], 4),
                 "withdrawn_to_owner_usd": round(xfer, 2),
                 "note": "live = real wallets (Coinbase + Kalshi): idle USDC yield + any gated live trades"},
        "PAPER": {"equity_change_usd": round(d["paper_equity_usd"], 6), "realized_usd": round(d["realized_cum_usd"], 6),
                  "unrealized_now_usd": round(now["unrealized_usd"], 6), "paper_equity_now_usd": round(now["paper_equity_usd"], 4)},
        "COSTS": {"fees_usd": round(d["fees_cum_usd"], 6), "inference_usd": round(d["inference_cum_usd"], 6),
                  "compute_usd": round(d["compute_cum_usd"], 6)},
        "deployed_now_usd": round(now["deployed_usd"], 4),
        "deployed_pct": round(100 * now["deployed_usd"] / max(now["live_total_usd"], 1e-9), 1),
        "by_strategy": by_strategy, "by_rail_shadow": by_rail,
    }


class EconSampler:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        self._last_prune = 0.0

    async def run(self) -> None:
        while not self.f.stop_event.is_set():
            self.f.sup.beat("econ")
            with contextlib.suppress(Exception):
                m = await asyncio.to_thread(mark, self.f)
                self.f.db.insert("econ_ticks", m)
                if time.time() - self._last_prune > 3600:
                    self._last_prune = time.time()
                    self.f.db.execute("DELETE FROM econ_ticks WHERE ts < ?", (time.time() - KEEP_DAYS * 86400,))
            await asyncio.sleep(TICK_S)
