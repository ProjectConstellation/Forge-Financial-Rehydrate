"""FORGE operator API + PWA host (DIRECTIVE §28–31; DOSSIER §32–34).

Bound to 127.0.0.1 (private during build). Read endpoints are open on localhost; controls (STOP ALL TRADING, resume,
cash-out) always require the operator token. Exchange keys never reach the browser — the frontend talks only to
this backend. Endpoints: /health /ready /metrics /api/* /api/stream (SSE).
"""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import secrets
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from forge.core import state as tstate

WEB = Path(__file__).resolve().parents[1] / "web"


def operator_token(home: Path) -> str:
    env = os.environ.get("FORGE_OPERATOR_TOKEN", "").strip()
    if env:
        return env
    p = home / "run" / "operator_token"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(secrets.token_urlsafe(32))
        p.chmod(0o600)
    return p.read_text().strip()


def _j(x: Any) -> Any:
    return json.loads(json.dumps(x, default=lambda o: float(o) if isinstance(o, Decimal) else str(o)))


class StopBody(BaseModel):
    reason: str = "operator emergency stop (dashboard)"
    flatten: bool = False


class ResumeBody(BaseModel):
    confirm: str


class CashoutBody(BaseModel):
    amount: str = "all"
    now: bool = False


def build_app(forge: Any) -> FastAPI:
    app = FastAPI(title="FORGE", docs_url=None, redoc_url=None, openapi_url=None)
    token = operator_token(forge.s.home)

    def require_token(authorization: str = Header(default="")) -> None:
        got = authorization.removeprefix("Bearer ").strip()
        if not got or not hmac.compare_digest(got, token):
            raise HTTPException(status_code=401, detail="operator token required")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
        return resp

    # ------------------------------------------------------------------ health
    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "uptime_s": round(time.time() - forge.started)}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        snap = forge.sup.snapshot()
        loops_ok = bool(snap) and all(x["alive"] and x["silent_s"] <= x["limit_s"] for x in snap if x["critical"])
        feed = forge.stream.quality.healthy(time.time_ns(), 30_000)
        body = {"ready": loops_ok and feed, "loops": len(snap), "loops_ok": loops_ok, "market_feed": feed,
                "restarts": sum(x["restarts"] for x in snap)}
        return JSONResponse(body, status_code=200 if body["ready"] else 503)

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        t = forge.treasury
        q = forge.stream.quality
        lines = [
            f"forge_equity_usd {t.get('equity_usd', 0)}", f"forge_true_net_usd {t.get('true_net_usd', 0)}",
            f"forge_fees_usd {t.get('fees_usd', 0)}", f"forge_opex_inference_usd {t.get('opex_inference_usd', 0)}",
            f"forge_opex_compute_usd {t.get('opex_compute_usd', 0)}", f"forge_ws_messages_total {q.messages}",
            f"forge_ws_reconnects_total {q.reconnects}", f"forge_ws_sequence_gaps_total {q.sequence_gaps}",
            f"forge_improvement_cycles_total {forge.improvement_runs}",
        ]
        for k, v in forge.reg.counts().items():
            lines.append(f'forge_strategies{{state="{k}"}} {v}')
        return PlainTextResponse("\n".join(lines) + "\n")

    # ------------------------------------------------------------------ read API
    def earnings() -> dict[str, Any]:
        db, book = forge.db, forge.book if forge.book in ("live", "paper") else "paper"
        def net(since: str) -> float:
            pos = db.scalar("SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL) - CAST(fees_usd AS REAL)),0) FROM positions "
                            f"WHERE book = ? AND status='CLOSED' AND closed_at > {since}", (book,)) or 0.0
            opex = db.scalar("SELECT COALESCE(SUM(CAST(amount_usd AS REAL)),0) FROM ledger_entries WHERE book = ? AND "
                             f"account LIKE 'OPEX:%' AND ts > {since}", (book,)) or 0.0
            return float(pos) - float(opex)
        today, d7 = net("date('now')"), net("datetime('now','-7 day')")
        life = float(forge.treasury.get("true_net_usd") or 0.0)
        trades_today = db.scalar("SELECT COUNT(*) FROM positions WHERE book = ? AND status='CLOSED' AND closed_at > date('now') "
                                 "AND CAST(cost_usd AS REAL) > 0", (book,)) or 0
        hours = max((time.time() - (time.time() // 86400) * 86400) / 3600, 0.25)
        counts = forge.reg.counts()
        live_strats = (counts.get("PRODUCTION", 0) or 0) + (counts.get("CHALLENGER", 0) or 0)
        open_n = db.scalar("SELECT COUNT(*) FROM positions WHERE book = ? AND status != 'CLOSED'", (book,)) or 0
        near = len(db.kv_get("evolution.near_miss", []) or [])
        if open_n:
            doing = f"EARNING — {open_n} position(s) working; {live_strats} validated strategies deployed"
        elif live_strats:
            doing = f"HUNTING — {live_strats} validated strategies scanning {len(forge.universe)} markets for their entry signals"
        else:
            doing = (f"LEARNING — no strategy has passed the evidence gate yet; capital protected while the Improvement "
                     f"Loop races {near} near-miss lineages and {counts.get('EXPERIMENTAL', 0)} candidates (paper/live P&L appears here "
                     "the moment a strategy proves itself)")
        return {"today_usd": today, "7d_usd": d7, "lifetime_true_net_usd": life, "per_hour_today_usd": today / hours,
                "trades_today": trades_today, "doing_now": doing, "book": book}

    @app.get("/api/overview")
    async def overview() -> Any:
        t = forge.treasury
        st = tstate.get_state(forge.db)
        opp = forge.db.query_one("SELECT COUNT(*) n FROM opportunities WHERE ts > datetime('now','-1 day')") or {"n": 0}
        pos = forge.db.query("SELECT symbol, strategy_id, status, qty, cost_usd, opened_at FROM positions "
                             "WHERE book = ? AND status != 'CLOSED'", (forge.book,))
        intel = forge.brain.spend_summary() if forge.brain else {"available": False}
        compute = forge.compute.summary() if forge.compute else {"available": False}
        return _j({
            "mode": forge.s.mode.value, "book": forge.book, "live_flag": forge.s.live_trading, "trading": st,
            "treasury": t, "positions": pos, "population": forge.reg.counts(), "opportunities_24h": opp["n"],
            "agents": forge.agent_status, "breakers": forge.breakers.snapshot(),
            "feed": forge.stream.quality.snapshot(time.time_ns()), "universe": len(forge.universe),
            "fees": {"maker": float(forge.fees.maker), "taker": float(forge.fees.taker), "tier": forge.fees.tier},
            "intelligence": intel, "compute": compute, "improvement_cycles": forge.improvement_runs,
            "hurdle_per_day": forge.hurdle.hurdle(t.get("regime", {}).get("hurdle_multiplier", 1.0)) * 24,
            "uptime_s": round(time.time() - forge.started), "earnings": earnings(), "loops": forge.sup.snapshot(),
            "deepseek_sentinel": forge.db.kv_get("deepseek.sentinel"), "breadth": forge.breadth})

    @app.get("/api/opportunities")
    async def opportunities(limit: int = 50) -> Any:
        rows = forge.db.query("SELECT id, ts, symbol, strategy_id, family, score, expected_net_bps, probability, status, "
                              "reason, components, outcome FROM opportunities ORDER BY ts_ns DESC LIMIT ?", (min(limit, 500),))
        for r in rows:
            r["components"] = json.loads(r["components"] or "{}")
            r["outcome"] = json.loads(r["outcome"]) if r["outcome"] else None
        return _j(rows)

    @app.get("/api/strategies")
    async def strategies() -> Any:
        return _j(forge.arena.summary())

    @app.get("/api/strategies/{sid}")
    async def strategy(sid: str) -> Any:
        g = forge.reg.get(sid)
        if g is None:
            raise HTTPException(404)
        return _j({"genome": g.model_dump(mode="json"), "state": forge.reg.state(sid), "lineage": forge.reg.lineage(sid),
                   "holdout": forge.reg.latest_metrics(sid, "holdout"), "forward": forge.reg.latest_metrics(sid, "forward"),
                   "events": forge.db.query("SELECT ts, from_population, to_population, reason FROM strategy_events "
                                            "WHERE strategy_id = ? ORDER BY id", (sid,))})

    @app.get("/api/timeline")
    async def timeline(limit: int = 100) -> Any:
        return _j(forge.db.query("SELECT id, ts, agent, level, message FROM timeline ORDER BY id DESC LIMIT ?", (min(limit, 1000),)))

    @app.get("/api/calibration")
    async def calibration() -> Any:
        return _j([forge.calib.reliability(c) for c in forge.calib.classes()])

    @app.get("/api/stream")
    async def stream(request: Request) -> StreamingResponse:
        async def gen():  # type: ignore[no-untyped-def]
            last = len(forge.events)
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                evs = list(forge.events)
                if len(evs) > last or (evs and last > len(evs)):
                    for ev in evs[last:] if last <= len(evs) else evs[-5:]:
                        yield f"data: {json.dumps(_j(ev))}\n\n"
                    last = len(evs)
                await asyncio.sleep(1.0)
        return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})

    # ------------------------------------------------------------------ controls (token required)
    @app.post("/api/control/stop", dependencies=[Depends(require_token)])
    async def stop_all(body: StopBody) -> Any:
        st = tstate.stop_all(forge.db, forge.audit, actor="operator-dashboard", reason=body.reason,
                             safe_stop_policy="flatten_when_safe" if body.flatten else "keep_exits")
        await forge.say("Operator", f"STOP ALL TRADING — {body.reason}", level="warn")
        return st

    @app.post("/api/control/resume", dependencies=[Depends(require_token)])
    async def resume(body: ResumeBody) -> Any:
        try:
            st = tstate.resume(forge.db, forge.audit, actor="operator-dashboard", confirm=body.confirm)
        except PermissionError as e:
            raise HTTPException(400, str(e)) from e
        await forge.say("Operator", "Trading resumed by operator", level="warn")
        return st

    @app.post("/api/control/cashout", dependencies=[Depends(require_token)])
    async def cashout(body: CashoutBody) -> Any:
        req = {"amount": body.amount, "urgency": "now" if body.now else "patient", "requested_by": "operator-dashboard"}
        forge.db.kv_set("cashout.request", req)
        forge.audit.append("CASHOUT_REQUESTED", req, actor="operator-dashboard")
        await forge.say("Operator", f"Cash-out requested: {body.amount} ({req['urgency']})", level="warn")
        return req

    # ------------------------------------------------------------------ PWA
    if WEB.exists():
        app.mount("/static", StaticFiles(directory=WEB), name="static")

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-store"})

        @app.get("/manifest.webmanifest")
        async def manifest() -> FileResponse:
            return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")

        @app.get("/sw.js")
        async def sw() -> FileResponse:
            return FileResponse(WEB / "sw.js", media_type="application/javascript")

    return app


async def serve(forge: Any) -> None:
    import uvicorn
    cfg = uvicorn.Config(build_app(forge), host=forge.s.api_host, port=forge.s.api_port, log_level="warning",
                         access_log=False, lifespan="off")
    await uvicorn.Server(cfg).serve()
