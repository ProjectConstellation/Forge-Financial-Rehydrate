"""Fresh capability and capital view; a research feed never implies permission to trade."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def matrix(forge: Any) -> dict[str, Any]:
    db = forge.db
    truth = db.kv_get("treasury.truth") or {}
    kalshi = db.kv_get("kalshi.live") or {}
    alpaca: dict[str, Any] = {}
    path = Path("/srv/forge/var/alpaca_paper_status.json")
    try:
        alpaca = json.loads(path.read_text())
    except (ValueError, OSError):
        pass
    broker = alpaca.get("broker_account") or {}
    execution = {}
    try:
        execution = json.loads(Path("/srv/forge/var/alpaca_broker_trials.json").read_text())
    except (ValueError, OSError):
        pass
    rows = [dict(r) for r in db.query("SELECT id,status,executable FROM rail_registry ORDER BY id")]
    return {"ts": time.time(), "mode": getattr(forge, "book", "paper"),
            "coinbase": {"real_nav_usd": (truth.get("venues") or {}).get("coinbase"),
                         "source_ts": truth.get("source_ts"), "fresh": truth.get("fresh"),
                         "account_flags": truth.get("account_flags"), "session": "24/7_subject_to_venue_status"},
            "kalshi": {"authenticated_adapter_configured": bool(getattr(getattr(forge, "kalshi_live", None), "configured", False)),
                       "real_balance_usd": kalshi.get("balance_usd"), "source_ts": kalshi.get("ts"),
                       "session": "24/7_except_Thursday_03_05_America_New_York_maintenance",
                       "requirements": ["market_status", "funding", "fees", "settlement_rules", "independent_evidence", "live_gate"]},
            "alpaca": {"paper_configured": alpaca.get("configured", False), "source_ts": alpaca.get("ts"),
                       "training_nav_usd": alpaca.get("training_nav_usd"), "broker_simulation_equity_usd": broker.get("equity"),
                       "regular_session_open": broker.get("market_open"), "paper_endpoint": broker.get("paper"),
                       "session": "calendar_and_asset_eligible_24_5_sessions",
                       "live_ready": False, "execution_adapter": "BROKER_PAPER_GATEWAY" if execution else "DETERMINISTIC_INTEGRATION_REQUIRED",
                       "execution_status": execution.get("status"), "execution_ts": execution.get("ts"),
                       "execution_fresh": 0 <= time.time()-float(execution.get("ts") or 0) <= 180,
                       "reconciliation": execution.get("reconciliation"),
                       "constraints": ["no_leverage", "account_assets_permissions", "settlement", "fees_spread_slippage", "exit_reconciliation"]},
            "data_feeds": {"odds_configured": bool(os.environ.get("ODDS_API_KEY")),
                           "twelve_data_configured": bool(os.environ.get("TWELVE_DATA_API_KEY")),
                           "execution_assumed": False},
            "registered_rails": rows,
            "allocation_rule": "only funded eligible executable rails with clean evidence enter money allocation"}
