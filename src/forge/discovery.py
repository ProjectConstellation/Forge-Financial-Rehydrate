"""Income Rail catalog (OP-005 multi-way earning; DOSSIER §31). Every rail competes on the same true-net-value scale.
Status: ACTIVE (earning/evaluated now) · BUILDING · CONFIG_REQUIRED (needs operator credentials/onboarding) · RESEARCH."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from forge.persistence.db import Database, dumps

RAILS: list[dict[str, Any]] = [
    {"id": "coinbase_spot_alpha", "provider": "Coinbase Advanced Trade", "category": "spot trading", "status": "ACTIVE",
     "needs": "—", "edge": "evolved alpha strategies (momentum, breakout, mean reversion, liquidity provision, rotation)"},
    {"id": "coinbase_spot_beta", "provider": "Coinbase Advanced Trade", "category": "trend/beta capture", "status": "ACTIVE",
     "needs": "—", "edge": "regime-gated trend capture with market-breadth kill switch + profit locks"},
    {"id": "coinbase_maker_liquidity", "provider": "Coinbase Advanced Trade", "category": "liquidity provision",
     "status": "ACTIVE", "needs": "—", "edge": "maker-first entries/exits (0.50% vs 0.90%), panic-wick deep bids"},
    {"id": "coinbase_usdc_idle_yield", "provider": "Coinbase (USDC rewards)", "category": "idle-capital yield",
     "status": "RESEARCH", "needs": "verify account eligibility; USD↔USDC convert via Trade permission",
     "edge": "earn on idle cash between trades (only if eligible)"},
    {"id": "kalshi_prediction_markets", "provider": "Kalshi", "category": "regulated prediction markets",
     "status": "CONFIG_REQUIRED", "needs": "Kalshi account + API key (KALSHI_API_KEY_ID, private key)",
     "edge": "probability mispricing, related-contract consistency, event-data reaction, maker spreads"},
    {"id": "base_onchain", "provider": "Coinbase CDP Agentic Wallet (Base)", "category": "on-chain trading / DEX",
     "status": "CONFIG_REQUIRED", "needs": "CDP wallet secret + operator authorization of wallet policy",
     "edge": "DEX/CEX dislocations, on-chain liquidity events"},
    {"id": "x402_services", "provider": "x402 machine-payable APIs", "category": "machine economy",
     "status": "RESEARCH", "needs": "agentic wallet; verified independent demand (x402 audit: most volume manufactured)",
     "edge": "sell FORGE-derived services / pay-per-use data"},
    {"id": "coinbase_fee_tier", "provider": "Coinbase", "category": "cost reduction", "status": "ACTIVE", "needs": "—",
     "edge": "volume growth lowers fee tier → shorter-horizon families unlock automatically"},
]


def seed_catalog(db: Database) -> None:
    now = datetime.now(UTC).isoformat()
    for r in RAILS:
        db.execute("INSERT INTO venue_catalog(id, provider, category, status, data, updated_at) VALUES (?,?,?,?,?,?) "
                   "ON CONFLICT(id) DO UPDATE SET status=excluded.status, data=excluded.data, updated_at=excluded.updated_at",
                   (r["id"], r["provider"], r["category"], r["status"], dumps(r), now))


def catalog(db: Database) -> list[dict[str, Any]]:
    import json
    return [json.loads(r["data"]) for r in db.query("SELECT data FROM venue_catalog ORDER BY status, id")]
