"""FORGE host preflight — READ-ONLY checks of every external dependency from this host (no orders, no writes).

Run as the forge user with /etc/forge/forge.env loaded:
  sudo -u forge bash -c 'set -a; . /etc/forge/forge.env; set +a; cd /srv/forge; .venv/bin/python scripts/preflight.py'
Prints only pass/fail + non-secret facts (balances rounded, key permission flags).
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

import httpx

OK: list[str] = []
BAD: list[str] = []


def res(name: str, good: bool, info: str) -> None:
    (OK if good else BAD).append(name)
    print(f"[{'PASS' if good else 'FAIL'}] {name}: {info}")


async def coinbase() -> None:
    from pydantic import SecretStr

    from forge.venues.coinbase.adapter import CoinbaseAdapter
    from forge.venues.coinbase.auth import CdpSigner
    from forge.venues.coinbase.rest import CoinbaseRest
    signer = CdpSigner(SecretStr(os.environ["COINBASE_CDP_API_KEY_NAME"]),
                       SecretStr(os.environ["COINBASE_CDP_API_KEY_SECRET"]))
    rest = CoinbaseRest(signer=signer)
    try:
        perms = await rest.key_permissions()
        res("coinbase.auth", True, f"can_view={perms.get('can_view')} can_trade={perms.get('can_trade')} "
                                   f"can_transfer={perms.get('can_transfer')}")
        bals = await CoinbaseAdapter(rest).get_balances()
        tot = {b.asset: float(b.total) for b in bals if float(b.total) > 0}
        res("coinbase.balances", True, ", ".join(f"{k} {v:.2f}" for k, v in sorted(tot.items())) or "empty")
        t = await rest.server_time()
        res("coinbase.clock", True, f"server epoch {t.get('epochSeconds')} vs local {int(time.time())}")
    except Exception as e:
        res("coinbase", False, str(e)[:200])
    finally:
        await rest.close()


async def http_checks() -> None:
    async with httpx.AsyncClient(timeout=20) as h:
        try:
            r = await h.get("https://api.deepseek.com/models",
                            headers={"Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY', '')}"})
            res("deepseek", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            res("deepseek", False, str(e)[:120])
        try:
            r = await h.get("https://api.elections.kalshi.com/trade-api/v2/markets", params={"limit": 1, "series_ticker": "KXBTCD"})
            res("kalshi.public", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            res("kalshi.public", False, str(e)[:120])
        try:
            r = await h.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker")
            res("coinbase.public", r.status_code == 200, f"BTC {r.json().get('price')}")
        except Exception as e:
            res("coinbase.public", False, str(e)[:120])


def modal_check() -> None:
    try:
        import modal
        env = os.environ.get("MODAL_ENVIRONMENT", "forge")
        fn = modal.Function.from_name("forge-research", "search", environment_name=env)
        fn.hydrate()
        res("modal", True, f"forge-research.search resolvable in env '{env}' (modal {modal.__version__})")
    except Exception as e:
        res("modal", False, str(e)[:200])


async def main() -> int:
    await coinbase()
    await http_checks()
    await asyncio.to_thread(modal_check)
    print(f"\npreflight: {len(OK)} pass, {len(BAD)} fail {BAD if BAD else ''}")
    return 1 if BAD else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
