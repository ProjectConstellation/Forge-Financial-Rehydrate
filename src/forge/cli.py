"""FORGE command line.  `forge run | stop-all | resume | status | readiness | cashout | backfill | verify-audit`"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
from decimal import Decimal


def _settings():
    from forge.config import load_settings
    return load_settings()


def cmd_run(args: argparse.Namespace) -> int:
    from forge.observability.logging import setup_logging
    from forge.runtime import Forge
    s = _settings()
    setup_logging(s)
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    async def main() -> None:
        forge = Forge(s)
        try:
            from forge.brain.agent import attach_brain
            attach_brain(forge)
        except Exception as e:  # brain optional: never blocks the engine
            logging.getLogger("forge").warning("brain not attached: %s", e)
        try:
            from forge.compute.modal_client import attach_compute
            attach_compute(forge)
        except Exception as e:
            logging.getLogger("forge").warning("modal compute not attached: %s", e)
        if not args.no_api:
            from forge.api.server import serve
            forge.sup.add("api", lambda: serve(forge), float("inf"))
        await forge.start()
        api_task = None
        loop = asyncio.get_running_loop()
        stop = asyncio.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        if args.duration:
            await asyncio.wait([asyncio.create_task(stop.wait())], timeout=args.duration)
        else:
            await stop.wait()
        if api_task:
            api_task.cancel()
        await forge.stop()

    asyncio.run(main())
    return 0


def _db_audit():
    from forge.audit.journal import AuditJournal
    from forge.persistence.db import Database
    s = _settings()
    s.ensure_dirs()
    db = Database(s.db_path)
    db.migrate()
    return s, db, AuditJournal(s.audit_dir)


def cmd_stop_all(args: argparse.Namespace) -> int:
    from forge.core.state import stop_all
    _, db, audit = _db_audit()
    st = stop_all(db, audit, actor="operator-cli", reason=args.reason,
                  safe_stop_policy="flatten_when_safe" if args.flatten else "keep_exits")
    print("STOP ALL TRADING:", json.dumps(st, indent=2))
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    from forge.core.state import resume
    _, db, audit = _db_audit()
    phrase = input("Type RESUME TRADING to confirm: ") if not args.confirm else args.confirm
    print(json.dumps(resume(db, audit, actor="operator-cli", confirm=phrase), indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from forge.core.state import get_state
    from forge.ledger.ledger import Ledger
    from forge.strategies.registry import StrategyRegistry
    s, db, audit = _db_audit()
    out = {"mode": s.mode.value, "trading": get_state(db), "population": StrategyRegistry(db).counts(),
           "books": {b: {k: (str(v) if isinstance(v, Decimal) else v) for k, v in Ledger(db).state(b).summary({}).items()
                         if k != "holdings"} for b in ("paper", "live")},
           "audit_chain": audit.verify()[:2]}
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_verify_audit(args: argparse.Namespace) -> int:
    _, _, audit = _db_audit()
    ok, n, msg = audit.verify()
    print(f"audit chain {'OK' if ok else 'BROKEN'}: {n} records — {msg}")
    return 0 if ok else 2


def cmd_readiness(args: argparse.Namespace) -> int:
    from forge.readiness import readiness_report
    s, db, _ = _db_audit()
    rep = asyncio.run(readiness_report(s, db))
    print(json.dumps(rep, indent=2, default=str))
    return 0 if rep["ready"] else 1


def cmd_cashout(args: argparse.Namespace) -> int:
    """Stage-1 cash-out (OP-003): request liquidation to USD; the running engine executes it."""
    from forge.core.state import get_state
    s, db, audit = _db_audit()
    req = {"amount": args.amount, "urgency": "now" if args.now else "patient", "requested_by": "operator-cli"}
    db.kv_set("cashout.request", req)
    audit.append("CASHOUT_REQUESTED", req, actor="operator-cli")
    print("Cash-out requested:", req, "| trading state:", get_state(db)["state"])
    print("FORGE will pause new entries, liquidate to USD, and report. Then use Coinbase 'Cash out' to your bank/card.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="forge", description="FORGE — Find Opportunities · Reinvest · Grow · Evolve")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the engine")
    r.add_argument("--duration", type=float, default=None, help="seconds to run (testing)")
    r.add_argument("--no-api", action="store_true")
    sa = sub.add_parser("stop-all", help="STOP ALL TRADING (emergency)")
    sa.add_argument("--reason", default="operator emergency stop")
    sa.add_argument("--flatten", action="store_true", help="also flatten positions when safe")
    rs = sub.add_parser("resume", help="resume trading (deliberate)")
    rs.add_argument("--confirm", default=None)
    sub.add_parser("status")
    sub.add_parser("verify-audit")
    sub.add_parser("readiness")
    co = sub.add_parser("cashout", help="liquidate to USD (Stage 1)")
    co.add_argument("amount", help="USD amount or 'all'")
    co.add_argument("--now", action="store_true", help="urgent: market orders")
    a = p.parse_args(argv)
    return {"run": cmd_run, "stop-all": cmd_stop_all, "resume": cmd_resume, "status": cmd_status,
            "verify-audit": cmd_verify_audit, "readiness": cmd_readiness, "cashout": cmd_cashout}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
