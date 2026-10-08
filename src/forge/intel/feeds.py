"""Always-on external feed loop — EDGAR free; Twelve/Odds when keys installed."""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from forge.intel import edgar, odds_api, twelve_data

log = logging.getLogger("forge.intel.feeds")


class ExternalFeeds:
    def __init__(self, forge: Any) -> None:
        self.f = forge

    def tick(self) -> dict[str, Any]:
        db = self.f.db
        ed = edgar.refresh(db)
        tw = twelve_data.refresh(db)
        od = odds_api.refresh(db)
        # Attribution / readiness board
        board = {
            "ts": time.time(),
            "edgar": {"status": ed.get("status"), "n_filings": len(ed.get("filings") or []),
                      "n_material": len(ed.get("recent_material") or [])},
            "twelve_data": {"status": tw.get("status"), "n_quotes": len(tw.get("quotes") or []),
                            "key_present": bool(os.environ.get("TWELVE_DATA_API_KEY")),
                            "signup": tw.get("signup")},
            "odds_api": {"status": od.get("status"), "n_sports": len(od.get("sports") or []),
                         "key_present": bool(os.environ.get("THE_ODDS_API_KEY")),
                         "signup": od.get("signup")},
            "kalshi": {"key_present": bool(os.environ.get("KALSHI_API_KEY_ID")),
                       "note": "prediction rail — separate founder creds when ready"},
            "policy": "EDGAR always-on; Twelve+Odds real-time once founder pastes keys via setup links",
        }
        db.kv_set("intel.feeds", board)
        # Ask for missing keys once (don't spam) — store pending links in kv
        self._ensure_cred_requests(db, board)
        return board

    def _ensure_cred_requests(self, db: Any, board: dict[str, Any]) -> None:
        try:
            from forge.ops.insights import credential_request
        except Exception:
            return
        installed = db.kv_get("ops.cred_installed") or {}
        pending = db.kv_get("ops.cred_pending_links") or {}
        now = time.time()
        wanted = [
            ("TWELVE_DATA_API_KEY", "Twelve Data real-time equity/ETF quotes & features (blueprint §39)",
             not board["twelve_data"]["key_present"]),
            ("THE_ODDS_API_KEY", "The Odds API bookmaker consensus for event/sports probability (blueprint §39)",
             not board["odds_api"]["key_present"]),
        ]
        for name, purpose, need in wanted:
            if not need or name in installed:
                continue
            prev = pending.get(name) or {}
            if prev.get("link") and float(prev.get("ts") or 0) > now - 1500:
                continue  # reuse live link ~25m
            try:
                out = credential_request(db, name, purpose, "env")
                pending[name] = {"ts": now, "link": out["link"], "purpose": purpose}
            except Exception as e:
                log.debug("cred_request %s: %s", name, e)
        db.kv_set("ops.cred_pending_links", pending)

    async def run(self) -> None:
        import asyncio
        # First tick soon; then every 15m (EDGAR fair-access + free-plan limits)
        while not self.f.stop_event.is_set():
            self.f.sup.beat("external_feeds")
            try:
                board = await asyncio.to_thread(self.tick)
                if board.get("edgar", {}).get("status") == "ok" and not getattr(self, "_announced", False):
                    await self.f.say(
                        "External Feeds",
                        f"EDGAR live ({board['edgar'].get('n_filings')} issuers). "
                        f"Twelve={board['twelve_data']['status']}; Odds={board['odds_api']['status']}.",
                        level="info",
                    )
                    self._announced = True
            except Exception as e:
                log.warning("external_feeds: %s", e, exc_info=True)
            await asyncio.sleep(900)
