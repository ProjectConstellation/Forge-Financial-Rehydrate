"""DeepSeek Balance Sentinel (OP-011). Free balance polling every 5 min (no tokens consumed).

States: OK → LOW (balance < threshold: ONE refill alert per episode, "add $10") → OK again when a top-up is detected
(balance jump ≥ $1 not explained by spend). Top-ups are recorded as inference funding so the dashboard can show how far
FORGE's own earnings are from covering its intelligence costs (self-funding progress).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx

log = logging.getLogger("forge.sentinel")
TOPUP_URL = "https://platform.deepseek.com/top_up"


class BalanceSentinel:
    def __init__(self, forge: Any, threshold_usd: float = 5.0, refill_usd: float = 10.0, period_s: float = 300.0) -> None:
        self.f = forge
        self.threshold, self.refill, self.period = threshold_usd, refill_usd, period_s
        self.ntfy_topic = os.environ.get("FORGE_NTFY_TOPIC", "").strip()

    def state(self) -> dict[str, Any]:
        return self.f.db.kv_get("deepseek.sentinel") or {"status": "UNKNOWN", "balance": None, "alert_sent": False,
                                                          "topups": [], "last_balance": None}

    async def notify(self, title: str, msg: str) -> None:
        if not self.ntfy_topic:
            return
        with contextlib.suppress(Exception):
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(f"https://ntfy.sh/{self.ntfy_topic}", content=msg.encode(),
                             headers={"Title": title, "Priority": "high", "Click": TOPUP_URL, "Tags": "moneybag"})

    async def check(self) -> dict[str, Any]:
        brain = self.f.brain
        bal = await brain.c.balance()
        st = self.state()
        if bal is None:
            return st
        brain.balance = bal
        prev = st.get("last_balance")
        now = datetime.now(UTC).isoformat()
        if prev is not None and bal - prev >= 1.0:                       # top-up detected
            st["topups"] = (st.get("topups") or [])[-50:] + [{"ts": now, "amount": round(bal - prev, 2)}]
            self.f.audit.append("DEEPSEEK_TOPUP_DETECTED", {"amount": round(bal - prev, 2), "balance": bal})
            await self.f.say("Balance Sentinel", f"DeepSeek top-up detected: +${bal - prev:.2f} → balance ${bal:.2f}. Research capacity restored.")
            st["alert_sent"] = False
        if bal < self.threshold:
            st["status"] = "LOW"
            if not st.get("alert_sent"):
                st["alert_sent"], st["alert_ts"] = True, now
                text = (f"DeepSeek balance ${bal:.2f} < ${self.threshold:.0f}. Please add ${self.refill:.0f} (one top-up). "
                        f"FORGE keeps trading and evolving; AI research is throttled until funded. {TOPUP_URL}")
                await self.f.say("Balance Sentinel", text, level="warn")
                self.f.audit.append("DEEPSEEK_REFILL_REQUESTED", {"balance": bal, "requested_usd": self.refill})
                await self.notify("FORGE: add $10 DeepSeek credit", text)
        else:
            st["status"] = "OK"
        st["balance"], st["last_balance"], st["checked"] = bal, bal, now
        # self-funding progress: trading net profit vs total intelligence spend
        spent = float(self.f.db.scalar("SELECT COALESCE(SUM(CAST(cost_usd AS REAL)),0) FROM inference_calls") or 0.0)
        earned = float(self.f.db.scalar("SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL) - CAST(fees_usd AS REAL)),0) "
                                        "FROM positions WHERE status='CLOSED'") or 0.0)
        st["self_funding"] = {"intelligence_spend_usd": round(spent, 4), "trading_net_usd": round(earned, 4),
                              "coverage": round(earned / spent, 3) if spent > 0 else None}
        self.f.db.kv_set("deepseek.sentinel", st)
        return st

    async def run(self) -> None:
        while not self.f.stop_event.is_set():
            self.f.sup.beat("balance_sentinel")
            try:
                await self.check()
            except Exception:
                log.exception("sentinel check failed")
            await asyncio.sleep(self.period)
