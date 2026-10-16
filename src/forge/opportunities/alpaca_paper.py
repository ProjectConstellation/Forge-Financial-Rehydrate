"""Alpaca PAPER training rail — micro-bankroll realism ($200 default)."""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from forge.opportunities.alpaca_bankroll import PaperBankrollPolicy

STATUS_PATH = Path(os.environ.get("ALPACA_PAPER_STATUS_PATH", "/srv/forge/var/alpaca_paper_status.json"))
MEMORY_PATH = Path(os.environ.get("ALPACA_PAPER_MEMORY_PATH", "/srv/forge/var/alpaca_paper_memory.jsonl"))


class AlpacaPaperRail:
    rail = "alpaca.equities.paper"

    def __init__(self) -> None:
        from forge.venues.alpaca import AlpacaClient

        self.client = AlpacaClient(paper=True) if os.environ.get("APCA_API_KEY_ID") else None
        self.policy = PaperBankrollPolicy.from_env()
        self.status: dict[str, Any] = {}

    @property
    def configured(self) -> bool:
        return bool(self.client and self.client.configured)

    async def probe(self) -> dict[str, Any]:
        if not self.configured:
            self.status = {"ts": time.time(), "configured": False, "why": "missing APCA credentials"}
            return self.status
        assert self.client is not None
        snap = await self.client.status_snapshot()
        discovery: dict[str, Any] = {}
        try:
            discovery["most_actives"] = await self.client.most_actives(top=8)
        except Exception as e:
            discovery["most_actives_err"] = str(e)[:160]
        try:
            discovery["movers"] = await self.client.movers(top=8)
        except Exception as e:
            discovery["movers_err"] = str(e)[:160]
        syms = []
        for row in ((discovery.get("most_actives") or {}).get("most_actives") or [])[:3]:
            if isinstance(row, dict) and row.get("symbol"):
                syms.append(row["symbol"])
        if syms:
            try:
                discovery["news"] = await self.client.news(symbols=",".join(syms), limit=5)
            except Exception as e:
                discovery["news_err"] = str(e)[:160]

        broker_eq = float(snap.get("equity") or 0)
        train_nav = self.policy.effective_nav(broker_eq)
        self.status = {
            "ts": time.time(),
            "configured": True,
            "rail": self.rail,
            "mode": "PAPER_MICRO",
            "training_nav_usd": train_nav,
            "bankroll_policy": self.policy.as_dict(),
            "broker_account": {
                "equity": broker_eq,
                "cash": float(snap.get("cash") or 0),
                "buying_power": float(snap.get("buying_power") or 0),
                "multiplier": snap.get("multiplier"),
                "market_open": snap.get("market_open"),
                "positions": snap.get("positions"),
                "status": snap.get("status"),
                "paper": snap.get("paper"),
                "note": "BROKER equity is NOT the training bankroll when ignore_broker_equity=true",
            },
            "discovery": {
                "n_actives": len((discovery.get("most_actives") or {}).get("most_actives") or []),
                "n_gainers": len((discovery.get("movers") or {}).get("gainers") or []),
                "n_losers": len((discovery.get("movers") or {}).get("losers") or []),
                "raw_keys": list(discovery.keys()),
            },
            "sizing_rules": {
                "max_per_order_usd": self.policy.max_per_order_usd,
                "max_open_usd": self.policy.max_open_usd,
                "max_positions": self.policy.max_positions,
                "example_ok": self.policy.allow_order(notional_usd=25, open_usd=0, n_positions=0)[1],
                "example_reject_whale": self.policy.allow_order(notional_usd=5000, open_usd=0, n_positions=0),
            },
            "why": "micro-bankroll active",
        }
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(self.status, indent=2) + "\n")
        with MEMORY_PATH.open("a") as f:
            f.write(json.dumps({"ts": self.status["ts"], "training_nav_usd": train_nav, "discovery": self.status["discovery"]}) + "\n")
        return self.status


async def main() -> None:
    print(json.dumps(await AlpacaPaperRail().probe(), indent=2)[:5000])


if __name__ == "__main__":
    asyncio.run(main())
