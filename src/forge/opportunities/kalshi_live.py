"""Kalshi LIVE execution for the pre-registered TAKE_THRESH signal (answers Q16 launch protocol).

Live orders are placed only when ALL hold:
  1. credentials present (KALSHI_API_KEY_ID + private key file) and KALSHI_LIVE != "off";
  2. FORGE global trading state is RUNNING (STOP ALL overrides everything);
  3. the out-of-sample evidence ladder passes on INDEPENDENT CLUSTERS (signals on the same underlying, expiry and
     direction count once — 8 correlated NO bets on one hour are one bet):
       n ≥ 10, P(μ>0) ≥ 0.80, mean > 0   → 1 contract (LOW: probe)
       n ≥ 10, P(μ>0) ≥ 0.90, mean ≥ 2¢  → 2 (MEDIUM)      n ≥ 20, P ≥ 0.95, mean ≥ 3¢ → 3 (HIGH)
       n ≥ 40, P(μ>0) ≥ 0.99, mean ≥ 2¢  → sized by the profit-velocity frontier (EXCEPTIONAL, ≤ 50/signal)
     and the most recent 30 clusters are not decaying (P ≥ 0.70, mean > 0);
  4. treasury regime (OP-021): BOOTSTRAP (< $50 HWM) may deploy essentially the whole Kalshi balance; RESERVE never
     touches the protected reserve; circuit breakers hourly 15% / daily 35% of treasury (bootstrap), signal fresh
     (≤ 60 s), IOC limit never worse than the signal ask;
  5. live-vs-shadow CUSUM (k = 1¢, h = 8¢) not tripped.
Every order is idempotent (client_order_id derived from the signal id) and recorded; P&L comes from actual fills and the
market's real settlement — never from the model.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("forge.kalshi_live")

KIND = "TAKE_THRESH"
# (min independent clusters, min P(mean>0), min mean $/contract, max contracts/signal; 0 = sized by the velocity frontier)
LADDER = ((40, 0.99, 0.02, 0), (20, 0.95, 0.03, 3), (10, 0.90, 0.02, 2), (10, 0.80, 0.0, 1))
FRONTIER_MAX = 50
CUSUM_K, CUSUM_H = 0.01, 0.08


def posterior_positive(pnls: list[float]) -> tuple[float, float]:
    """(mean, P(μ>0)) — normal approx on the mean with a conservative sd floor (binary payoffs: sd ≈ 0.3–0.5)."""
    n = len(pnls)
    if n == 0:
        return 0.0, 0.0
    m = sum(pnls) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in pnls) / max(n - 1, 1)) if n > 1 else 0.5
    se = max(sd, 0.20) / math.sqrt(n)
    return m, 0.5 * (1 + math.erf(m / se / math.sqrt(2)))


def ladder_contracts(pnls: list[float]) -> tuple[int, str]:
    n = len(pnls)
    m, p = posterior_positive(pnls)
    if n >= 30:
        rm, rp = posterior_positive(pnls[-30:])
        if rp < 0.70 or rm <= 0:
            return 0, f"decay stop: last-30 mean {rm*100:+.1f}¢ P={rp:.2f}"
    for need_n, need_p, need_m, k in LADDER:
        if n >= need_n and p >= need_p and m >= need_m:
            k = k or FRONTIER_MAX
            return k, f"ladder n={n} clusters mean {m*100:+.1f}¢ P={p:.3f} → up to {k} contract(s)"
    return 0, f"gate closed: n={n} clusters mean {m*100:+.1f}¢ P={p:.2f} (need ≥10 independent clusters, P≥0.80, mean>0)"


def cusum(diffs: list[float], k: float = CUSUM_K) -> float:
    s = 0.0
    for d in diffs:
        s = min(0.0, s + d + k)
    return s


class KalshiLive:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        self.key_id = os.environ.get("KALSHI_API_KEY_ID", "").strip()
        self.key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH", "/etc/forge/kalshi_private_key.pem")
        self.enabled = os.environ.get("KALSHI_LIVE", "on").lower() != "off"
        self.client = None
        self.paused_until = 0.0
        self.status: dict[str, Any] = {}
        if self.key_id and Path(self.key_path).exists():
            with contextlib.suppress(Exception):
                from forge.venues.kalshi import KalshiClient
                self.client = KalshiClient(self.key_id, self.key_path)

    @property
    def configured(self) -> bool:
        return self.client is not None

    # ------------------------------------------------------------------ evidence + risk
    def oos_pnls(self) -> list[float]:
        # the TAKE_THRESH kind only exists since its pre-registration → every settled signal is out-of-sample
        from forge.treasury.profit_velocity import cluster_unit_pnls
        rows = self.f.db.query("SELECT ticker, underlying, close_ts, side, pnl FROM crossrail_signals WHERE kind = ? AND "
                               "status = 'SETTLED' ORDER BY settled_ts", (KIND,))
        return cluster_unit_pnls(rows)          # one value per independent cluster (correlation-safe evidence)

    def realized(self, since: float) -> float:
        return float(self.f.db.scalar("SELECT COALESCE(SUM(pnl),0) FROM kalshi_live_orders WHERE settled_ts >= ?",
                                      (since,)) or 0.0)

    def open_cost(self) -> float:
        return float(self.f.db.scalar("SELECT COALESCE(SUM(cost),0) FROM kalshi_live_orders WHERE status = 'FILLED'") or 0.0)

    def decision(self) -> tuple[int, str]:
        from forge.core import state as tstate
        if not self.configured:
            return 0, "no Kalshi credentials (KALSHI_API_KEY_ID + private key file)"
        if not self.enabled:
            return 0, "KALSHI_LIVE=off"
        if tstate.trading_state(self.f.db) != "RUNNING":
            return 0, "FORGE STOP ALL active"
        if time.time() < self.paused_until:
            return 0, f"paused until {time.strftime('%H:%M', time.gmtime(self.paused_until))} UTC (loss stop / CUSUM)"
        day0 = time.time() - (time.time() % 86400)
        reg = self.regime()
        day_pnl, hour_pnl = self.realized(day0), self.realized(time.time() - 3600)
        if day_pnl < 0 and day_pnl <= -reg["daily_loss_stop"]:
            return 0, f"daily circuit breaker (−${reg['daily_loss_stop']:.2f}, {reg['regime']}) reached"
        if hour_pnl < 0 and hour_pnl <= -reg["hourly_loss_stop"]:
            self.paused_until = time.time() + 3600
            return 0, f"hourly circuit breaker (−${reg['hourly_loss_stop']:.2f}): paused 1 h"
        diffs = [r["live_minus_shadow"] for r in self.f.db.query(
            "SELECT (pnl / fill_count) - shadow_pnl AS live_minus_shadow FROM kalshi_live_orders WHERE status = 'SETTLED' "
            "AND fill_count > 0 AND shadow_pnl IS NOT NULL ORDER BY settled_ts")]
        if diffs and cusum(diffs) < -CUSUM_H:
            self.paused_until = time.time() + 3 * 3600
            return 0, "live/shadow CUSUM divergence: paused 3 h for diagnosis"
        return ladder_contracts(self.oos_pnls())

    def regime(self) -> dict[str, Any]:
        from forge.treasury import regime as treg
        v = self.f.db.kv_get("velocity") or {}
        tr = (v.get("treasury") or {}).get("total")
        if not tr:
            tr = float(self.f.db.scalar("SELECT account_total_usd FROM equity_series ORDER BY ts DESC LIMIT 1") or 0) + \
                float((self.status or {}).get("balance_usd") or 0)
        st = self.f.db.kv_get("treasury.regime") or {}
        return treg.regime_for(float(tr), max(float(st.get("hwm", 0)), float(tr)))

    def frontier_units(self) -> float | None:
        """Contracts per signal the profit-velocity frontier allocates to this stream (live-now scenario)."""
        v = self.f.db.kv_get("velocity") or {}
        for st in ((v.get("frontier") or {}).get("live_now") or {}).get("streams", []):
            if st.get("stream") == f"kalshi.{KIND}":
                return float(st.get("units") or 0)
        return None

    # ------------------------------------------------------------------ execution
    async def on_signal(self, sig: dict[str, Any]) -> None:
        """Called for every freshly recorded TAKE_THRESH signal."""
        n, why = self.decision()
        self.status = {"ts": time.time(), "decision": n, "why": why, "configured": self.configured}
        if n <= 0 or self.client is None:
            return
        if time.time() - float(sig["ts"]) > 60:
            return
        price, cost_each = float(sig["price"]), float(sig["price"]) + float(sig["fee"])
        fu = self.frontier_units()
        if fu is not None and fu >= 1:
            n = min(n, int(fu))                         # confidence-weighted size from the velocity frontier
        reg = self.regime()
        bal = float((self.status or {}).get("balance_usd") or 0) or reg["deployable"]
        cap = min(bal, reg["deployable"]) * 0.95         # bootstrap: whole treasury usable; reserve regime: above reserve
        n = min(n, int((cap - self.open_cost()) // max(cost_each, 0.01)))
        if n <= 0:
            return
        cid = f"forge-{sig['id']}"
        if self.f.db.scalar("SELECT 1 FROM kalshi_live_orders WHERE client_order_id = ?", (cid,)):
            return
        self.f.db.insert("kalshi_live_orders", {"ts": time.time(), "signal_id": sig["id"], "ticker": sig["ticker"],
                                                "side": sig["side"], "limit_price": price, "count": n, "client_order_id": cid,
                                                "status": "SUBMITTED", "close_ts": sig.get("close_ts")})
        try:
            r = await self.client.buy(sig["ticker"], sig["side"], price, n, cid)
        except Exception as e:
            self.f.db.execute("UPDATE kalshi_live_orders SET status = 'REJECTED', error = ? WHERE client_order_id = ?",
                              (str(e)[:300], cid))
            log.warning("kalshi order failed: %s", e)
            return
        o = r.get("order", r)
        filled = int(float(o.get("fill_count") or 0))
        yes_avg = float(o.get("average_fill_price") or 0) or (price if sig["side"] == "yes" else 1.0 - price)
        avg = yes_avg if sig["side"] == "yes" else 1.0 - yes_avg       # V2 reports the YES leg; NO cost = 1 − YES price
        fee = float(o.get("average_fee_paid") or 0) * max(filled, 1)
        cost = filled * avg + fee
        self.f.db.execute("UPDATE kalshi_live_orders SET order_id = ?, fill_count = ?, avg_price = ?, fee = ?, cost = ?, "
                          "status = ? WHERE client_order_id = ?",
                          (o.get("order_id"), filled, avg, fee, cost, "FILLED" if filled else "NO_FILL", cid))
        if filled:
            await self.f.say("Kalshi Live", f"LIVE BUY {filled}× {sig['side'].upper()} {sig['ticker']} @ ${avg:.2f} "
                                            f"(fee ${fee:.2f}) — TAKE_THRESH, {why}")

    async def settle(self) -> int:
        """Resolve filled orders from the market's real result (same source as the shadow settlement)."""
        n = 0
        for o in self.f.db.query("SELECT * FROM kalshi_live_orders WHERE status = 'FILLED' AND close_ts < ?",
                                 (time.time() - 120,)):
            sig = self.f.db.query_one("SELECT status, payout, pnl FROM crossrail_signals WHERE id = ?", (o["signal_id"],))
            if not sig or sig["status"] != "SETTLED":
                continue
            win = float(sig["payout"] or 0) >= 1.0
            payout = o["fill_count"] * (1.0 if win else 0.0)
            pnl = payout - float(o["cost"] or 0)
            self.f.db.execute("UPDATE kalshi_live_orders SET status = 'SETTLED', payout = ?, pnl = ?, settled_ts = ?, "
                              "shadow_pnl = ? WHERE id = ?", (payout, pnl, time.time(), sig["pnl"], o["id"]))
            n += 1
            await self.f.say("Kalshi Live", f"SETTLED {o['ticker']} {o['side'].upper()}: {'WIN' if win else 'LOSS'} "
                                            f"${pnl:+.2f} (live)")
        return n

    async def run(self) -> None:
        while not self.f.stop_event.is_set():
            self.f.sup.beat("kalshi_live")
            try:
                await self.settle()
                n, why = self.decision()
                bal = None
                if self.client is not None:
                    with contextlib.suppress(Exception):
                        b = await self.client.balance()
                        bal = float(b.get("balance_dollars") or (float(b.get("balance", 0)) / 100.0))
                self.status = {"ts": time.time(), "decision": n, "why": why, "configured": self.configured,
                               "balance_usd": bal, "open_cost": self.open_cost(),
                               "realized_today": self.realized(time.time() - (time.time() % 86400)),
                               "oos": dict(zip(("mean", "p_positive"), posterior_positive(self.oos_pnls()), strict=True))
                               | {"n": len(self.oos_pnls())}}
                self.f.db.kv_set("kalshi.live", self.status)
            except Exception as e:
                log.warning("kalshi live loop: %s", e)
            await asyncio.sleep(60)
