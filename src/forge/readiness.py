"""Automated live-readiness gate (DIRECTIVE §42, RESOLUTIONS #1 — evidence, not a fixed waiting period).

LIVE micro-capital may be enabled only when every check passes. `forge readiness` prints the report; the
runtime refuses Mode.LIVE unless FORGE_LIVE_TRADING=true (config validator) and this gate is green.
"""

from __future__ import annotations

import subprocess
import sys
from decimal import Decimal
from typing import Any

from forge.config import REPO_ROOT, Settings
from forge.ledger.ledger import Ledger
from forge.persistence.db import Database
from forge.strategies.registry import State, StrategyRegistry


async def readiness_report(s: Settings, db: Database) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    # 1. credentials + Coinbase connectivity / permissions / fees / minimums
    from forge.venues.coinbase.adapter import CoinbaseAdapter
    from forge.venues.coinbase.auth import CdpSigner
    from forge.venues.coinbase.rest import CoinbaseRest
    creds = s.secrets.available()
    add("live credentials supplied", creds["coinbase"], "COINBASE_CDP_API_KEY_NAME/SECRET present" if creds["coinbase"] else "missing")
    if creds["coinbase"]:
        rest = CoinbaseRest(signer=CdpSigner(s.secrets.coinbase_key_name, s.secrets.coinbase_key_secret))  # type: ignore[arg-type]
        ad = CoinbaseAdapter(rest)
        try:
            p = await ad.discover_permissions()
            add("coinbase connection + trade permission", bool(p.get("can_view") and p.get("can_trade")),
                f"view={p.get('can_view')} trade={p.get('can_trade')} transfer={p.get('can_transfer')}")
            f = await ad.get_fees()
            add("fees discovered", f.source == "transaction_summary", f"{f.tier}: maker {f.maker} taker {f.taker}")
            prods = await ad.list_products()
            add("min sizes discovered", len(prods) > 100, f"{len(prods)} products with rules")
            bals = await ad.get_balances()
            usd = sum((b.total for b in bals if b.asset in ("USD", "USDC")), Decimal(0))
            add("balances readable", True, f"USD+USDC {usd}")
        except Exception as e:
            add("coinbase connection + trade permission", False, str(e)[:200])
        finally:
            await rest.close()
    # 2. safety tests (emergency stop, risk governor, idempotency, P&L accounting) — run the suites
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", str(REPO_ROOT / "tests")],
                       capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=600)
    tail = (r.stdout.strip().splitlines() or ["?"])[-1]
    add("emergency stop / risk governor / idempotency / accounting tests", r.returncode == 0, tail)
    # 3. ledger integrity on the paper book
    lg = Ledger(db)
    resid = lg.check_balanced("paper")
    add("P&L accounting balanced (paper)", resid == 0, f"residual {resid}")
    st = lg.state("paper").summary({})
    add("true costs tracked", True, f"fees ${st['fees_usd']} · inference ${st['opex_inference_usd']} · compute ${st['opex_compute_usd']}")
    # 4. strategy evidence: at least one strategy passed replay/holdout + live-forward criteria
    reg = StrategyRegistry(db)
    counts = reg.counts()
    ready_strats = [g.id for g, stt, _ in reg.list((State.PRODUCTION, State.CHALLENGER))]
    add("≥1 strategy passed replay + shadow criteria", bool(ready_strats),
        f"{len(ready_strats)} CHALLENGER/PRODUCTION; population {counts}")
    # 5. market feed recently healthy (from runtime timeline)
    recent = db.scalar("SELECT COUNT(*) FROM timeline WHERE agent = 'Market Scout' AND ts > strftime('%Y-%m-%dT%H:%M:%S','now','-2 hours')") or 0
    add("market feed stable (runtime active in last 2h)", recent > 0, f"{recent} market-scout events in 2h")
    stop_tested = db.scalar("SELECT COUNT(*) FROM timeline WHERE message LIKE 'STOP ALL TRADING%'") or 0
    add("emergency stop exercised end-to-end", stop_tested > 0, f"{stop_tested} recorded stop events")
    # 6. explicit live flag
    add("FORGE_LIVE_TRADING=true", s.live_trading, "operator flag set" if s.live_trading else "flag is false (expected until gate passes)")
    blocking = [c for c in checks if not c["ok"] and c["check"] != "FORGE_LIVE_TRADING=true"]
    return {"ready": not blocking and s.live_trading, "gate_green_except_flag": not blocking, "checks": checks}
