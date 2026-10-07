"""Idle-capital yield (OP-013 §6 / OP-016): idle cash earns Coinbase One USDC rewards (3.75% APY, members only).

- Conversion USD⇄USDC via the official Advanced Trade convert API (currency codes; measured fee $0, 1:1 on 2026-10-07).
- A USD buffer stays liquid for the Coinbase One membership fee.
- REWARDS ARE VERIFIED, NOT ASSUMED: every hour the USDC balance is compared with the expected balance (sum of FORGE's own
  conversions); unexplained increases are booked as realized rewards → the realized APY drives the rail's economics.
- LIVE-START GUARD: before FORGE trades live on -USD books, USDC is converted back to USD (deterministic, logged).
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Any

USD_BUFFER = Decimal("5.00")


async def convert(rest: Any, frm: str, to: str, amount: Decimal) -> dict[str, Any]:
    """Quote → verify free 1:1 → commit → poll until COMPLETED. Never commits a conversion with a fee or a bad rate."""
    q = (await rest.convert_quote(frm, to, str(amount.quantize(Decimal("0.01"))))).get("trade", {})
    fee = Decimal(str(((q.get("total_fee") or {}).get("amount") or {}).get("value") or "0"))
    total = Decimal(str((q.get("total") or {}).get("value") or "0"))
    if fee != 0 or abs(total - amount) > Decimal("0.01"):
        return {"ok": False, "reason": f"not free 1:1 (fee {fee}, total {total})", "quote": q.get("id")}
    await rest.convert_commit(q["id"], frm, to)
    status = ""
    for _ in range(12):
        await asyncio.sleep(5)
        t = (await rest._request("GET", f"/api/v3/brokerage/convert/trade/{q['id']}",
                                 params={"from_account": frm, "to_account": to}, private=True)).get("trade", {})
        status = str(t.get("status"))
        if "COMPLETED" in status or "FAIL" in status or "CANCEL" in status:
            break
    return {"ok": "COMPLETED" in status, "trade_id": q["id"], "status": status, "amount": str(amount), "fee": str(fee)}


class IdleYield:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _state(self) -> dict[str, Any]:
        return self.f.db.kv_get("yield.usdc") or {"conversions_net_usdc": "0", "rewards_usdc": "0", "samples": []}

    def record_conversion(self, delta_usdc: Decimal, trade_id: str, why: str) -> None:
        st = self._state()
        st["conversions_net_usdc"] = str(Decimal(st["conversions_net_usdc"]) + delta_usdc)
        st.setdefault("conversions", []).append({"ts": time.time(), "delta": str(delta_usdc), "trade": trade_id, "why": why})
        st.setdefault("baseline_usdc", None)
        self.f.db.kv_set("yield.usdc", st)
        self.f.audit.append("IDLE_YIELD_CONVERSION", {"delta_usdc": str(delta_usdc), "trade": trade_id, "why": why})

    async def observe(self) -> dict[str, Any]:
        """Hourly: USDC balance vs expected (opening + net conversions) → realized rewards and APY."""
        bals = {b.asset: b.total for b in await self.f.coinbase.get_balances()}
        usdc = Decimal(bals.get("USDC", Decimal(0)))
        st = self._state()
        expected = Decimal(st["conversions_net_usdc"]) + Decimal(st.get("opening_usdc", "0"))
        rewards = max(Decimal(0), usdc - expected)
        st["rewards_usdc"] = str(rewards)
        st["usdc_balance"] = str(usdc)
        conv = st.get("conversions") or []
        t0 = conv[0]["ts"] if conv else time.time()
        days = max((time.time() - t0) / 86400, 1e-6)
        avg_bal = max(expected, Decimal("0.01"))
        st["realized_apy"] = float(rewards / avg_bal) * 365 / days if days > 1 else None   # needs ≥ 1 day to mean anything
        st["observed_ts"] = time.time()
        self.f.db.kv_set("yield.usdc", st)
        if rewards > 0:
            self.f.db.kv_set("config.usdc_reward_apy_verified", st["realized_apy"])
        return st

    async def live_start_guard(self) -> dict[str, Any] | None:
        """Before LIVE trading on -USD books: bring USDC back to USD (deterministic, logged)."""
        bals = {b.asset: b.total for b in await self.f.coinbase.get_balances()}
        usdc = Decimal(bals.get("USDC", Decimal(0)))
        if usdc < Decimal("1"):
            return None
        res = await convert(self.f.rest, "USDC", "USD", usdc.quantize(Decimal("0.01"), rounding="ROUND_DOWN"))
        if res.get("ok"):
            self.record_conversion(-Decimal(res["amount"]), res["trade_id"], "live-start guard: USDC → USD for -USD books")
        return res
