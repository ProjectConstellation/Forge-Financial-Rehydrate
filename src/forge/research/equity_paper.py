"""Equity / ETF PAPER intelligence layer — parallel to Kalshi (founder correction §4).

Uses SEC EDGAR automatically; Twelve Data when TWELVE_DATA_API_KEY present.
Does NOT assume Coinbase equity execution — probes eligibility and records blockers.
Objective: proprietary stock/event algorithms validated on real-market PAPER paths.
"""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("forge.equity_paper")

# Seed watchlist for proprietary research (not a trade list)
WATCH = ("SGOV", "BIL", "GLD", "IAU", "SPY", "QQQ", "IWM", "TLT", "COIN")


class EquityPaperResearch:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def _twelve_configured(self) -> bool:
        import os
        return bool(os.environ.get("TWELVE_DATA_API_KEY") or (self.f.db.kv_get("secrets.meta") or {}).get("TWELVE_DATA_API_KEY"))

    async def probe_coinbase_equity_eligibility(self) -> dict[str, Any]:
        """Verify what official Advanced Trade equity surface is available — do not assume automation."""
        out: dict[str, Any] = {"ts": time.time(), "executable_assumed": False}
        try:
            rest = getattr(self.f, "rest", None)
            if rest is None:
                out["status"] = "no_rest_client"
                out["blockers"] = ["Coinbase REST not attached in this runtime context"]
                return out
            # Prefer existing surface/rail registry
            rail = self.f.db.query_one("SELECT * FROM rail_registry WHERE id='coinbase.equity'") or {}
            out["rail_status"] = rail.get("status")
            out["rail_blockers"] = rail.get("blockers")
            out["capabilities"] = rail.get("capabilities")
            out["status"] = "registry"
            out["note"] = ("Equity LIVE automation requires verified account eligibility + official API path; "
                           "PAPER research proceeds regardless.")
        except Exception as e:
            out["status"] = "error"
            out["error"] = str(e)[:300]
        self.f.db.kv_set("equity.coinbase_eligibility", out)
        return out

    async def sec_refresh(self) -> dict[str, Any]:
        from forge.data.sec_edgar import company_tickers, record_probe
        try:
            tickers = await company_tickers()
            # map watch symbols → CIK when possible
            by_ticker = {}
            if isinstance(tickers, dict):
                for _, row in tickers.items():
                    if not isinstance(row, dict):
                        continue
                    t = str(row.get("ticker") or "").upper()
                    if t in WATCH:
                        by_ticker[t] = {"cik": row.get("cik_str") or row.get("cik"), "title": row.get("title")}
            st = {"ts": time.time(), "ok": True, "watch": by_ticker, "universe_n": len(tickers) if isinstance(tickers, dict) else 0}
            self.f.db.kv_set("equity.sec_watch", st)
            record_probe(self.f.db, True, f"watch={list(by_ticker)} universe={st['universe_n']}")
            return st
        except Exception as e:
            record_probe(self.f.db, False, str(e))
            st = {"ts": time.time(), "ok": False, "error": str(e)[:300]}
            self.f.db.kv_set("equity.sec_watch", st)
            return st

    def propose_event_drift_hypotheses(self) -> list[dict[str, Any]]:
        """Proprietary research hypotheses — not third-party signals."""
        return [
            {"family": "EventDriftGenome", "hypothesis": "Material 8-K/10-Q surprises produce residual drift after initial gap",
             "inputs": ["SEC filings", "intraday returns", "sector residual"], "mode": "PAPER_RESEARCH"},
            {"family": "ResidualMomentumGenome", "hypothesis": "Idiosyncratic residual momentum persists after beta removal",
             "inputs": ["daily returns", "SPY/QQQ beta", "ADV"], "mode": "PAPER_RESEARCH"},
            {"family": "IdleTreasuryETF", "hypothesis": "When no +EV active edge, park PAPER capital in short-duration T-bill ETF economics as benchmark hurdle",
             "inputs": ["SGOV/BIL yield proxy", "opportunity cost"], "mode": "PAPER_BENCHMARK"},
        ]

    async def run(self) -> None:
        import asyncio
        while not self.f.stop_event.is_set():
            self.f.sup.beat("equity_paper")
            try:
                sec = await self.sec_refresh()
                elig = await self.probe_coinbase_equity_eligibility()
                hyps = self.propose_event_drift_hypotheses()
                twelve = self._twelve_configured()
                report = {
                    "ts": time.time(),
                    "mode": "PAPER_REAL_MARKET_SIM_MONEY",
                    "twelve_data_configured": twelve,
                    "sec": {"ok": sec.get("ok"), "watch_n": len((sec.get("watch") or {}))},
                    "coinbase_eligibility": elig,
                    "hypotheses": hyps,
                    "note": "Parallel to Kalshi. Moat = proprietary event/residual models. External feeds are inputs only.",
                }
                self.f.db.kv_set("equity.paper_research", report)
                # Keep a research queue item so Quinn/Ada can pick up
                q = self.f.db.kv_get("research.queue") or []
                if not any(x.get("kind") == "equity_paper" for x in q[-10:]):
                    q.append({"ts": time.time(), "kind": "equity_paper", "priority": "normal",
                              "why": "parallel equity/ETF PAPER research (founder mandate)", "hypotheses": [h["family"] for h in hyps]})
                    self.f.db.kv_set("research.queue", q[-50:])
            except Exception as e:
                log.warning("equity_paper: %s", e, exc_info=True)
            await asyncio.sleep(1800)
