"""Treasury Truth Service — one authoritative money truth (blueprint §27–§29).

Investment Treasury vs Founder Spending are *accounting buckets* when Coinbase
cannot safely automate separate wallets (can_transfer=false). Never invent wallets.
"""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.treasury.truth")
RED_ZONE_NAV = 50.0


class TreasuryTruth:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def compute(self) -> dict[str, Any]:
        db = self.f.db
        now = time.time()
        vel = db.kv_get("velocity") or {}
        tr = vel.get("treasury") or {}
        # live coinbase cash from latest balance snapshots
        cb_cash = float(tr.get("coinbase") or tr.get("total") or 0.0)
        kal = float(tr.get("kalshi") or 0.0)
        # paper NAV from equity metric / positions
        paper_eq = float(getattr(self.f, "equity_usd", None) or 0.0)
        try:
            paper_eq = float(db.kv_get("paper.equity") or paper_eq or 0.0)
        except Exception:
            pass
        # open paper positions marked
        open_pos = db.query(
            "SELECT COALESCE(SUM(CAST(cost_usd AS REAL)),0) c FROM positions WHERE status!='CLOSED' AND book='paper'"
        ) if hasattr(db, "query") else []
        deployed = float((open_pos[0]["c"] if open_pos else 0) or 0.0)
        # founder spending bucket (accounting)
        spend = db.kv_get("treasury.founder_spending") or {"balance_usd": 0.0, "note": "accounting bucket; transfers require founder auth"}
        invest_nav = float(tr.get("total") or cb_cash + kal)
        # surface account flags
        acct = db.kv_get("surface.account") or {}
        mode = "PAPER_REAL_MARKET_SIM_MONEY" if getattr(self.f, "book", "paper") != "live" else "LIVE_REAL_MARKET_REAL_MONEY"
        live_flag = False
        try:
            import os
            live_flag = str(os.environ.get("FORGE_LIVE_TRADING", "false")).lower() in ("1", "true", "yes")
        except Exception:
            pass
        red = invest_nav < RED_ZONE_NAV
        # safe_to_withdraw: advisory only — never auto
        committed = deployed
        buffer = max(5.0, invest_nav * 0.15) if red else max(10.0, invest_nav * 0.1)
        technical_avail = max(0.0, invest_nav - committed - buffer)
        recommended = 0.0 if red else max(0.0, technical_avail * 0.25)
        # reconciliation: velocity total vs snapshot sum
        disc = abs(invest_nav - (cb_cash + kal))
        out = {
            "ts": now,
            "mode": mode,
            "mode_label": "PAPER — REAL MARKET / SIMULATED MONEY" if not live_flag else "LIVE — REAL MARKET / REAL MONEY",
            "forge_live_trading": live_flag,
            "treasury_nav": round(invest_nav, 4),
            "investment_cash_available": round(max(0.0, invest_nav - deployed), 4),
            "capital_deployed": round(deployed, 4),
            "capital_locked": round(deployed, 4),
            "pending_settlement": 0.0,
            "paper_nav": round(paper_eq or invest_nav, 4),
            "live_nav": round(cb_cash + kal, 4) if live_flag else 0.0,
            "venues": {"coinbase": round(cb_cash, 4), "kalshi": round(kal, 4)},
            "founder_spending_balance": float(spend.get("balance_usd") or 0.0),
            "founder_spending": spend,
            "safe_to_withdraw_estimate": {
                "technical_usd": round(technical_avail, 2),
                "recommended_usd": round(recommended, 2),
                "red_zone": red,
                "reason": ("RED ZONE: recommend $0 — capital needed for recovery/validated opportunities"
                           if red else "advisory; confirm before any transfer"),
            },
            "red_zone": red,
            "red_zone_threshold": RED_ZONE_NAV,
            "account_flags": {
                "can_trade": acct.get("can_trade"),
                "can_transfer": acct.get("can_transfer"),
                "portfolio_type": acct.get("portfolio_type"),
                "fee_tier": acct.get("fee_tier"),
            },
            "reconciliation": {
                "discrepancy_usd": round(disc, 4),
                "ok": disc < 0.05,
                "sources": ["velocity.treasury", "balance_snapshots", "positions"],
            },
            "true_net_note": "true-net from velocity/econ; this object is capital location truth",
        }
        return out

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("treasury_truth")
            try:
                rep = await asyncio.to_thread(self.compute)
                self.f.db.kv_set("treasury.truth", rep)
                if rep.get("red_zone"):
                    # intensify: mark research preference, do NOT force size
                    self.f.db.kv_set("treasury.red_zone", {
                        "active": True, "ts": rep["ts"], "nav": rep["treasury_nav"],
                        "policy": "intensify_flow_research_not_size",
                    })
                else:
                    self.f.db.kv_set("treasury.red_zone", {"active": False, "ts": rep["ts"]})
            except Exception as e:
                log.warning("treasury_truth: %s", e, exc_info=True)
            await asyncio.sleep(30)
