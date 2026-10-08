"""FORGE founder portal + API (forge.northstarimagine.com via FORGE's own Cloudflare tunnel → 127.0.0.1:8470).

Real-time: /api/live is a Server-Sent-Events stream that PUSHES a fresh snapshot every second (treasury re-marked to live
prices, earnings windows, positions with live P&L) plus timeline events the instant they happen — no polling, no refresh.
Security: everything except the login page requires a signed session (or the operator bearer token for CLI); controls
additionally require the session's CSRF token. Exchange keys never reach the browser.
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

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from forge.api.auth import PortalAuth
from forge.core import state as tstate

WEB = Path(__file__).resolve().parents[1] / "web"
PUBLIC = {"/login", "/auth/login", "/health", "/manifest.webmanifest", "/sw.js", "/static/login.js", "/static/styles.css",
          "/static/icon.svg"}


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


def _clean(x: Any) -> Any:
    """Browser-safe JSON: NaN/±Infinity → null (they are not valid JSON and break JSON.parse in every browser)."""
    if isinstance(x, float):
        return x if x == x and x not in (float("inf"), float("-inf")) else None
    if isinstance(x, Decimal):
        return _clean(float(x))
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, list | tuple | set):
        return [_clean(v) for v in x]
    return x if isinstance(x, str | int | bool) or x is None else str(x)


def _j(x: Any) -> Any:
    return _clean(x)


def jdump(x: Any) -> str:
    return json.dumps(_clean(x), allow_nan=False)


def _ip(req: Request) -> str:
    return req.headers.get("cf-connecting-ip") or (req.client.host if req.client else "?")


def _external(req: Request) -> bool:
    return "cf-connecting-ip" in req.headers or "x-forwarded-for" in req.headers


class LoginBody(BaseModel):
    username: str
    password: str


class StopBody(BaseModel):
    reason: str = "founder emergency stop (portal)"
    flatten: bool = False


class ResumeBody(BaseModel):
    confirm: str


class CashoutBody(BaseModel):
    amount: str = "all"
    now: bool = False


# ---------------------------------------------------------------------------------------------- snapshot builder
def snapshot(forge: Any) -> dict[str, Any]:
    t = forge._snapshot_treasury()                       # re-marked to live prices on every call
    db, book = forge.db, forge.book if forge.book in ("live", "paper") else "paper"

    def window(hours: float) -> dict[str, float]:
        since = f"strftime('%Y-%m-%dT%H:%M:%S','now','-{int(hours * 60)} minutes')"
        trade = float(db.scalar("SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL) - CAST(fees_usd AS REAL)),0) FROM positions "
                                f"WHERE book = ? AND status='CLOSED' AND closed_at > {since}", (book,)) or 0.0)
        opex = float(db.scalar("SELECT COALESCE(SUM(CAST(amount_usd AS REAL)),0) FROM ledger_entries WHERE book = ? AND "
                               f"account LIKE 'OPEX:%' AND ts > {since}", (book,)) or 0.0)
        n = int(db.scalar(f"SELECT COUNT(*) FROM positions WHERE book = ? AND status='CLOSED' AND closed_at > {since} "
                          "AND CAST(cost_usd AS REAL) > 0", (book,)) or 0)
        net = trade - opex
        return {"net_usd": net, "per_hour_usd": net / hours, "trading_net_usd": trade, "costs_usd": opex, "trades": n}

    windows = {k: window(h) for k, h in (("1h", 1), ("8h", 8), ("12h", 12), ("24h", 24))}
    marks = forge.market.marks()
    positions = []
    for p in db.query("SELECT id, symbol, strategy_id, status, qty, cost_usd, entry_price, opened_at, meta FROM positions "
                      "WHERE book = ? AND status != 'CLOSED'", (book,)):
        qty, cost = float(p["qty"]), float(p["cost_usd"])
        px = marks.get(p["symbol"])
        val = qty * px if px and qty > 0 else None
        meta = json.loads(p["meta"] or "{}")
        positions.append({"symbol": p["symbol"], "status": p["status"], "strategy": p["strategy_id"], "qty": qty,
                          "cost_usd": cost, "price": px, "value_usd": val,
                          "live_pnl_usd": (val - cost) if val is not None else None,
                          "live_pnl_pct": ((val / cost - 1) if val is not None and cost > 0 else None),
                          "profit_locked": bool(meta.get("lock_armed")), "opened_at": p["opened_at"]})
    invested_cost = sum(p["cost_usd"] for p in positions)
    invested_value = sum(p["value_usd"] or p["cost_usd"] for p in positions)
    closed = db.query_one("SELECT COUNT(*) n, SUM(CASE WHEN CAST(realized_pnl_usd AS REAL) - CAST(fees_usd AS REAL) > 0 THEN 1 ELSE 0 END) w "
                          "FROM positions WHERE book = ? AND status='CLOSED' AND CAST(cost_usd AS REAL) > 0", (book,)) or {"n": 0, "w": 0}
    counts = forge.reg.counts()
    live_strats = (counts.get("PRODUCTION", 0) or 0) + (counts.get("CHALLENGER", 0) or 0)
    paper_strats = counts.get("SHADOW", 0) or 0
    if positions:
        doing = f"EARNING — {len(positions)} position(s) working · {sum(p['profit_locked'] for p in positions)} profit-locked"
    elif live_strats or (book == "paper" and paper_strats):
        b = forge.breadth
        doing = (f"HUNTING — {live_strats + (paper_strats if book == 'paper' else 0)} validated strategies scanning "
                 f"{len(forge.universe)} markets · market breadth {b.get('up_frac', 0):.0%} up · BTC {b.get('btc_regime')}")
    else:
        doing = (f"LEARNING — racing {len(db.kv_get('evolution.near_miss', []) or [])} near-miss lineages and "
                 f"{counts.get('EXPERIMENTAL', 0)} candidates toward the evidence gate")
    contributed = float(t.get("contributed_usd") or 0)
    acct = forge.account
    return _j({
        "ts": time.time(), "mode": forge.s.mode.value, "book": book, "live_flag": forge.s.live_trading,
        "trading": tstate.get_state(db), "doing_now": doing,
        "account": {"coinbase_total_usd": acct.get("total_usd"), "coinbase_cash_usd": acct.get("cash_usd"),
                    "coinbase_assets": acct.get("assets"), "age_s": round(time.time() - acct["ts"]) if acct.get("ts") else None},
        "book_balance": {"equity_usd": t.get("equity_usd"), "cash_usd": t.get("cash_usd"), "reserve_usd": t.get("reserve_usd"),
                         "contributed_usd": contributed,
                         "roi": (float(t.get("equity_usd") or 0) / contributed - 1) if contributed > 0 else None},
        "invested": {"cost_usd": invested_cost, "market_value_usd": invested_value, "positions": len(positions),
                     "share_of_equity": invested_value / float(t["equity_usd"]) if t.get("equity_usd") else 0.0},
        "earnings": {**windows, "lifetime_true_net_usd": t.get("true_net_usd"), "realized_usd": t.get("realized_pnl_usd"),
                     "unrealized_usd": t.get("unrealized_pnl_usd"), "fees_usd": t.get("fees_usd"),
                     "ai_usd": t.get("opex_inference_usd"), "compute_usd": t.get("opex_compute_usd"),
                     "trades_closed": closed["n"] or 0, "win_rate": (closed["w"] or 0) / closed["n"] if closed["n"] else None},
        "positions": positions, "population": counts, "regime": (t.get("regime") or {}).get("name"),
        "breadth": forge.breadth, "breakers": forge.breakers.snapshot(), "loops": forge.sup.snapshot(),
        "feed": forge.stream.quality.snapshot(time.time_ns()), "universe": len(forge.universe),
        "fees": {"maker": float(forge.fees.maker), "taker": float(forge.fees.taker), "tier": forge.fees.tier},
        "intelligence": forge.brain.spend_summary() if forge.brain else {"available": False},
        "compute": forge.compute.summary() if forge.compute else {"available": False},
        "deepseek_sentinel": db.kv_get("deepseek.sentinel"), "improvement_cycles": forge.improvement_runs,
        "uptime_s": round(time.time() - forge.started), "workers": workers(forge), "lights": lights(forge, positions),
        "throughput": {"genomes_total": int(db.kv_get("stats.genomes_total", 0) or 0), "genomes_last_cycle": forge.genomes_last_cycle,
                       "cycles": forge.improvement_runs, "feed_messages": forge.stream.quality.messages,
                       "mode_label": ((forge.db.kv_get("treasury.truth") or {}).get("mode_label")
                       or "PAPER — REAL MARKET / SIMULATED MONEY"),
                       "forge_live_trading": bool((forge.db.kv_get("treasury.truth") or {}).get("forge_live_trading")),
                       "markets_streaming": len(forge.stream.symbols), "markets_discovered": len(forge.market.products),
                       "opportunities_24h": db.scalar("SELECT COUNT(*) FROM opportunities WHERE ts > strftime('%Y-%m-%dT%H:%M:%S','now','-1 day')") or 0,
                       "paper_trades_open": len(positions)},
        "health": db.kv_get("health.score") or {},
        "testing": db.kv_get("timemachine.report") or {},
        "today": {"realized_net_usd": windows_today(db, book), "unrealized_usd": sum((p["live_pnl_usd"] or 0) for p in positions)},
        "firm": {
            "mode_label": (db.kv_get("treasury.truth") or {}).get("mode_label")
                           or "PAPER — REAL MARKET / SIMULATED MONEY",
            "forge_live_trading": bool((db.kv_get("treasury.truth") or {}).get("forge_live_trading")),
            "treasury_truth": db.kv_get("treasury.truth"),
            "red_zone": db.kv_get("treasury.red_zone"),
            "trial_8h": db.kv_get("trial.8h"),
            "reallocation_top": ((db.kv_get("capital.reallocation") or {}).get("ranking") or [{}])[:3],
            "tcs_best": ((db.kv_get("treasury.tcs") or {}).get("best") or [])[:3],
            "agents": db.kv_get("agents.heartbeat"),
            "freshness": {
                "snapshot_ts": time.time(),
                "feed_age_s": (forge.stream.quality.snapshot(time.time_ns()) or {}).get("age_s"),
                "stale_after_s": 5,
            },
        }})


def windows_today(db: Any, book: str) -> float:
    trade = float(db.scalar("SELECT COALESCE(SUM(CAST(realized_pnl_usd AS REAL) - CAST(fees_usd AS REAL)),0) FROM positions "
                            "WHERE book = ? AND status='CLOSED' AND closed_at > date('now')", (book,)) or 0.0)
    opex = float(db.scalar("SELECT COALESCE(SUM(CAST(amount_usd AS REAL)),0) FROM ledger_entries WHERE book = ? AND "
                           "account LIKE 'OPEX:%' AND ts > date('now')", (book,)) or 0.0)
    return trade - opex


def workers(forge: Any) -> list[dict[str, Any]]:
    now = time.time()
    out = [{"name": k, **v, "elapsed_s": round(now - v.get("since", now))} for k, v in forge.workers.items()]
    q = forge.stream.quality
    out.append({"name": "market_feed", "what": f"{len(forge.universe)} markets · {q.messages} msgs · {q.reconnects} reconnects",
                "count": 1 if q.connected else 0, "where": "Coinbase WebSocket", "elapsed_s": round((time.time_ns() - q.connected_since_ns) / 1e9) if q.connected else 0})
    n_open = forge.db.scalar("SELECT COUNT(*) FROM positions WHERE book = ? AND status != 'CLOSED'", (forge.book,)) or 0
    out.append({"name": "execution", "what": f"{n_open} position(s) under management · profit-lock armed on winners",
                "count": 1, "where": "deterministic engine", "elapsed_s": round(now - forge.started)})
    return out


def lights(forge: Any, positions: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Traffic lights with honest semantics: green = actively doing it right now; amber = ready/limited; red = down/stopped."""
    snap = forge.sup.snapshot()
    crit_ok = all(x["alive"] and x["silent_s"] <= x["limit_s"] for x in snap if x["critical"])
    q = forge.stream.quality
    feed_ok = q.connected and (time.time_ns() - q.last_message_ns) < 15e9
    ts = tstate.trading_state(forge.db)
    counts = forge.reg.counts()
    deployable = (counts.get("PRODUCTION", 0) or 0) + (counts.get("CHALLENGER", 0) or 0) + \
        ((counts.get("SHADOW", 0) or 0) if forge.book == "paper" else 0)
    disc_age = time.time() - forge.last_improvement_ts if forge.last_improvement_ts else 1e9
    busy = any(w.get("count", 0) for k, w in forge.workers.items() if k in ("research", "modal"))
    sent = forge.db.kv_get("deepseek.sentinel") or {}
    last_llm = forge.db.scalar("SELECT MAX(ts) FROM inference_calls") or ""
    return {
        "engine": {"state": "green" if crit_ok else "red", "label": "ENGINE ONLINE" if crit_ok else "ENGINE DEGRADED"},
        "feed": {"state": "green" if feed_ok else "red", "label": "LIVE MARKET DATA" if feed_ok else "FEED DOWN"},
        "earning": {"state": "red" if ts == "STOPPED" else "green" if positions else "amber" if deployable else "blue",
                    "label": "TRADING STOPPED" if ts == "STOPPED" else f"EARNING · {len(positions)} POSITION(S)" if positions
                    else f"HUNTING · {deployable} STRATEGIES" if deployable else "LEARNING · NO VALIDATED EDGE YET"},
        "discovering": {"state": "green" if busy or disc_age < 900 else "amber",
                        "label": "DISCOVERING STRATEGIES" if busy or disc_age < 900 else "RESEARCH IDLE"},
        "brain": {"state": "amber" if sent.get("status") == "LOW" else "green" if last_llm else "amber",
                  "label": f"AI BRAIN · ${sent.get('balance', 0) or 0:.2f}" + (" · ADD $10" if sent.get("status") == "LOW" else "")},
        "safety": {"state": "red" if ts == "STOPPED" else "amber" if forge.breakers.blocking() or ts == "OBSERVE_ONLY" else "green",
                   "label": {"RUNNING": "RISK GOVERNOR ARMED", "STOPPED": "EMERGENCY STOP", "OBSERVE_ONLY": "OBSERVE ONLY"}.get(ts, ts)},
    }


def lists(forge: Any) -> dict[str, Any]:
    from forge.discovery import catalog
    opps = forge.db.query("SELECT id, ts, symbol, strategy_id, family, score, expected_net_bps, probability, status, reason, "
                          "components, outcome FROM opportunities ORDER BY ts_ns DESC LIMIT 25")
    for r in opps:
        r["components"] = json.loads(r["components"] or "{}")
        r["outcome"] = json.loads(r["outcome"]) if r["outcome"] else None
    from forge.evolution.analyst import report
    return _j({"opportunities": opps, "strategies": forge.arena.summary(), "rails": catalog(forge.db), "analyst": report(forge.db),
               "agents": forge.agent_status})


# ---------------------------------------------------------------------------------------------- app
def build_app(forge: Any) -> FastAPI:
    app = FastAPI(title="FORGE", docs_url=None, redoc_url=None, openapi_url=None)
    token = operator_token(forge.s.home)
    auth = PortalAuth(forge.s.home)
    from forge.api.agent_api import agent_token, mount
    mount(app, forge, agent_token(forge.s.home))
    from forge.api.ops_api import eng_token, mount_ops, ops_token
    mount_ops(app, forge, ops_token(forge.s.home), eng_token(forge.s.home))

    def who(req: Request) -> dict | None:
        authz = req.headers.get("authorization", "")
        if authz.startswith("Bearer ") and hmac.compare_digest(authz[7:].strip(), token):
            return {"u": "operator-token", "csrf": None, "token": True}
        return auth.session(req.cookies.get(PortalAuth.COOKIE))

    @app.middleware("http")
    async def gate(request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        if path.startswith(("/api/agent/", "/api/ops/")):
            if _external(request):                                # agent + OPS APIs are loopback-only (never via the tunnel)
                return JSONResponse({"detail": "not found"}, status_code=404)
            return await call_next(request)                       # route enforces the agent token
        if path in ("/ready", "/metrics") and not _external(request):
            pass                                                  # local monitoring only
        elif path.startswith("/api/v1/") and request.method == "GET" and not _external(request):
            pass                                                  # firm read APIs on loopback (same trust as /ready)
        elif path not in PUBLIC and who(request) is None:
            if path.startswith("/api/") or request.method != "GET" or path in ("/ready", "/metrics"):
                return JSONResponse({"detail": "login required"}, status_code=401)
            return RedirectResponse("/login?next=" + ("/setup" if path == "/setup" else "/setup/credential") if path.startswith("/setup")
                                    else "/login", status_code=303)
        resp = await call_next(request)
        if path.startswith("/static/") or path in ("/sw.js", "/manifest.webmanifest"):
            resp.headers["Cache-Control"] = "no-store, max-age=0"     # never let Cloudflare/browser serve stale app code
            resp.headers["CDN-Cache-Control"] = "no-store"
        resp.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
                             "Content-Security-Policy": "default-src 'self'; script-src 'self' https://static.cloudflareinsights.com; connect-src 'self' https://cloudflareinsights.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:",
                             "Strict-Transport-Security": "max-age=31536000", "Permissions-Policy": "geolocation=(), camera=()"})
        return resp

    def require_csrf(request: Request) -> str:
        s = who(request)
        if s is None:
            raise HTTPException(401, "login required")
        if s.get("token"):
            return s["u"]
        if not hmac.compare_digest(request.headers.get("x-csrf", ""), s.get("csrf") or "~"):
            raise HTTPException(403, "invalid CSRF token")
        return f"founder:{s['u']}"

    def _html_login() -> HTMLResponse:
        return _html("login.html")

    # ------------------------------------------------------------------ auth
    @app.get("/login")
    async def login_page() -> HTMLResponse:
        return _html_login()

    @app.post("/auth/login")
    async def login(body: LoginBody, request: Request) -> JSONResponse:
        ip = _ip(request)
        if auth.locked(ip) > 0:
            raise HTTPException(429, f"too many attempts — locked for {auth.locked(ip):.0f}s")
        if not auth.attempt(ip, body.username, body.password):
            forge.audit.append("PORTAL_LOGIN_FAILED", {"ip": ip, "user": body.username[:40]})
            await asyncio.sleep(1.0)
            raise HTTPException(401, "invalid credentials")
        cookie, csrf = auth.issue(auth.user)
        forge.audit.append("PORTAL_LOGIN", {"ip": ip, "user": auth.user})
        resp = JSONResponse({"ok": True, "csrf": csrf})
        secure = request.headers.get("x-forwarded-proto") == "https" or "https" in request.headers.get("cf-visitor", "")
        resp.set_cookie(PortalAuth.COOKIE, cookie, max_age=30 * 86400, httponly=True, secure=secure, samesite="strict", path="/")
        return resp

    @app.post("/auth/logout")
    async def logout() -> JSONResponse:
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(PortalAuth.COOKIE, path="/")
        return resp

    @app.get("/api/session")
    async def session(request: Request) -> Any:
        s = who(request) or {}
        return {"user": s.get("u"), "csrf": s.get("csrf")}

    # ------------------------------------------------------------------ health / metrics
    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "uptime_s": round(time.time() - forge.started)}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        snap = forge.sup.snapshot()
        loops_ok = bool(snap) and all(x["alive"] and (x["limit_s"] is None or x["silent_s"] <= x["limit_s"]) for x in snap if x["critical"])
        feed = forge.stream.quality.healthy(time.time_ns(), 30_000)
        body = {"ready": loops_ok and feed, "loops": len(snap), "loops_ok": loops_ok, "market_feed": feed,
                "restarts": sum(x["restarts"] for x in snap)}
        return JSONResponse(body, status_code=200 if body["ready"] else 503)

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        t, q = forge.treasury, forge.stream.quality
        lines = [f"forge_equity_usd {t.get('equity_usd', 0)}", f"forge_true_net_usd {t.get('true_net_usd', 0)}",
                 f"forge_ws_messages_total {q.messages}", f"forge_ws_reconnects_total {q.reconnects}",
                 f"forge_improvement_cycles_total {forge.improvement_runs}"]
        lines += [f'forge_strategies{{state="{k}"}} {v}' for k, v in forge.reg.counts().items()]
        return PlainTextResponse("\n".join(lines) + "\n")

    # ------------------------------------------------------------------ data
    @app.get("/api/overview")
    async def overview() -> Any:
        return snapshot(forge)

    @app.get("/api/lists")
    async def get_lists() -> Any:
        return lists(forge)

    @app.get("/api/timeline")
    async def timeline(limit: int = 100) -> Any:
        return _j(forge.db.query("SELECT id, ts, agent, level, message FROM timeline ORDER BY id DESC LIMIT ?", (min(limit, 1000),)))

    @app.get("/api/strategies/{sid}")
    async def strategy(sid: str) -> Any:
        g = forge.reg.get(sid)
        if g is None:
            raise HTTPException(404)
        return _j({"genome": g.model_dump(mode="json"), "state": forge.reg.state(sid), "lineage": forge.reg.lineage(sid),
                   "holdout": forge.reg.latest_metrics(sid, "holdout"), "forward": forge.reg.latest_metrics(sid, "forward")})

    @app.get("/api/history")
    async def history(hours: float = 24) -> Any:
        rows = forge.db.query("SELECT ts, equity_usd, true_net_usd, account_total_usd, invested_usd FROM equity_series "
                              "WHERE book = ? AND ts > strftime('%Y-%m-%dT%H:%M:%S','now', ?) ORDER BY ts", (forge.book, f"-{int(hours * 60)} minutes"))
        return _j(rows)

    @app.get("/api/velocity")
    async def velocity() -> Any:
        """FORGE PROFIT VELOCITY: realized/expected true-net $/h, frontier, regime, scaling curve, priorities."""
        return _j(forge.db.kv_get("velocity") or {})

    @app.get("/api/surface")
    async def surface() -> Any:
        """OP-013 Opportunity Surface: rail registry, allocator plan (now vs if-unblocked), cross-rail evidence, listings."""
        db = forge.db
        rails = db.query("SELECT id, provider, category, status, executable, blockers, capabilities, economics, last_probe "
                         "FROM rail_registry ORDER BY executable DESC, id")
        return _j({"allocation": db.kv_get("surface.allocation"), "account": db.kv_get("surface.account"),
                   "product_types": db.kv_get("surface.product_types"),
                   "rails": [{**dict(r), "blockers": json.loads(r["blockers"] or "[]"),
                              "capabilities": json.loads(r["capabilities"] or "{}"),
                              "economics": json.loads(r["economics"] or "{}")} for r in rails],
                   "crossrail": db.kv_get("crossrail.scorecard"), "calibrator": db.kv_get("crossrail.calibrator"),
                   "kalshi_mapping": db.kv_get("crossrail.mapping"),
                   "listing_events": db.query("SELECT ts, product_id, product_type, event FROM listing_events "
                                              "ORDER BY id DESC LIMIT 50")})

    @app.get("/api/calibration")
    async def calibration() -> Any:
        return _j([forge.calib.reliability(c) for c in forge.calib.classes()])

    @app.get("/api/live")
    async def live(request: Request) -> StreamingResponse:
        """Real-time push: snapshot every 1s, lists every 5s, timeline events immediately."""
        async def gen():  # type: ignore[no-untyped-def]
            yield "retry: 2000\n\n"
            last_ev = len(forge.events)
            k = 0
            while not await request.is_disconnected():
                yield f"event: snapshot\ndata: {jdump(snapshot(forge))}\n\n"
                if k % 5 == 0:
                    yield f"event: lists\ndata: {jdump(lists(forge))}\n\n"
                evs = list(forge.events)
                if len(evs) < last_ev:
                    last_ev = 0
                for ev in evs[last_ev:]:
                    yield f"event: timeline\ndata: {jdump(ev)}\n\n"
                last_ev = len(evs)
                k += 1
                await asyncio.sleep(1.0)
        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})

    # ------------------------------------------------------------------ controls (session + CSRF, or operator token)
    @app.post("/api/control/stop")
    async def stop_all(body: StopBody, request: Request) -> Any:
        actor = require_csrf(request)
        st = tstate.stop_all(forge.db, forge.audit, actor=actor, reason=body.reason,
                             safe_stop_policy="flatten_when_safe" if body.flatten else "keep_exits")
        await forge.say("Founder", f"STOP ALL TRADING — {body.reason}", level="warn")
        return st

    @app.post("/api/control/resume")
    async def resume(body: ResumeBody, request: Request) -> Any:
        actor = require_csrf(request)
        try:
            st = tstate.resume(forge.db, forge.audit, actor=actor, confirm=body.confirm)
        except PermissionError as e:
            raise HTTPException(400, str(e)) from e
        await forge.say("Founder", "Trading resumed", level="warn")
        return st

    @app.post("/api/control/cashout")
    async def cashout(body: CashoutBody, request: Request) -> Any:
        actor = require_csrf(request)
        req = {"amount": body.amount, "urgency": "now" if body.now else "patient", "requested_by": actor}
        forge.db.kv_set("cashout.request", req)
        forge.audit.append("CASHOUT_REQUESTED", req, actor=actor)
        await forge.say("Founder", f"Cash-out requested: {body.amount} ({req['urgency']})", level="warn")
        return req

    # ------------------------------------------------------------------ PWA
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    import hashlib as _h
    def _ver() -> str:
        return _h.sha256(b"".join((WEB / f).read_bytes() for f in ("app.js", "styles.css", "login.js", "icon.svg"))).hexdigest()[:12]
    ASSET_VER = _ver()

    def _html(name: str) -> HTMLResponse:
        html = (WEB / name).read_text()
        for f in ("app.js", "styles.css", "login.js", "icon.svg"):
            html = html.replace(f"/static/{f}\"", f"/static/{f}?v={ASSET_VER}\"")
        return HTMLResponse(html, headers={"Cache-Control": "no-store, max-age=0"})

    @app.get("/")
    async def index() -> HTMLResponse:
        return _html("index.html")

    # ------------------------------------------------------------------ EXECUTIVE OPS: one-tap private Telegram setup
    from forge.ops.telegram_setup import TelegramPairer
    pairer = TelegramPairer(forge)
    forge.telegram_pairer = pairer

    @app.get("/setup")
    async def setup_page() -> HTMLResponse:
        return _html("setup.html")

    @app.get("/setup/credential")
    async def cred_page() -> HTMLResponse:
        return _html("credential.html")

    @app.get("/api/setup/credential")
    async def cred_info(request: Request, r: str = "") -> Any:
        if who(request) is None:
            raise HTTPException(401, "login required")
        req = (forge.db.kv_get("ops.cred_requests") or {}).get(r)
        if not req or req.get("used") or req["expires"] < time.time():
            raise HTTPException(404, "link expired or already used — ask FORGE for a new one")
        return {"name": req["name"], "kind": req["kind"], "purpose": req["purpose"],
                "minutes_left": round((req["expires"] - time.time()) / 60)}

    @app.post("/api/setup/credential")
    async def cred_submit(request: Request) -> Any:
        actor = require_csrf(request)
        b = await request.json()
        reqs = forge.db.kv_get("ops.cred_requests") or {}
        req = reqs.get(str(b.get("r") or ""))
        if not req or req.get("used") or req["expires"] < time.time():
            raise HTTPException(404, "link expired or already used")
        val = str(b.get("value") or "").strip()
        if req["kind"] == "pem" and "BEGIN" not in val:
            raise HTTPException(400, "paste the whole key including the BEGIN/END lines")
        if not val or len(val) > 20000 or (req["kind"] == "env" and "\n" in val):
            raise HTTPException(400, "invalid value")
        p = Path(forge.s.home) / "run" / "cred_provision.json"
        fd = os.open(str(p) + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            json.dump({"name": req["name"], "kind": req["kind"], "value": val}, fh)
        os.replace(str(p) + ".tmp", p)                      # root path unit installs it into /etc/forge + restarts FORGE
        req["used"] = True
        forge.db.kv_set("ops.cred_requests", reqs)
        forge.db.kv_set("ops.cred_installed", {**(forge.db.kv_get("ops.cred_installed") or {}),
                                               req["name"]: {"ts": time.time(), "kind": req["kind"]}})
        forge.audit.append("CREDENTIAL_SUBMITTED", {"name": req["name"], "kind": req["kind"], "actor": actor}, actor=actor)
        return {"ok": True, "name": req["name"], "note": "installing — FORGE restarts in a few seconds to load it"}

    @app.get("/api/setup/telegram")
    async def setup_status(request: Request) -> Any:
        if who(request) is None:
            raise HTTPException(401, "login required")
        return {"pairing": pairer.state, "connected": pairer.connected()}

    @app.post("/api/setup/telegram")
    async def setup_start(request: Request) -> Any:
        actor = require_csrf(request)
        if pairer.connected() and not (await request.json()).get("replace"):
            raise HTTPException(409, "already connected — choose 'replace' to bind a new bot")
        body = await request.json()
        try:
            st = await pairer.start(str(body.get("token") or ""))
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        forge.audit.append("OPS_TELEGRAM_SETUP", {"actor": actor, "bot": st.get("bot_username")}, actor=actor)
        return st

    @app.get("/manifest.webmanifest")
    async def manifest() -> FileResponse:
        return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js")
    async def sw() -> FileResponse:
        return FileResponse(WEB / "sw.js", media_type="application/javascript",
                            headers={"Cache-Control": "no-store, max-age=0", "Service-Worker-Allowed": "/"})

    
    try:
        from forge.api.firm_v1 import mount_firm_v1
        mount_firm_v1(app, forge)
    except Exception as _e:
        import logging; logging.getLogger("forge.api").warning("firm_v1 mount failed: %s", _e)

    return app


async def serve(forge: Any) -> None:
    import uvicorn
    cfg = uvicorn.Config(build_app(forge), host=forge.s.api_host, port=forge.s.api_port, log_level="warning",
                         access_log=False, lifespan="off", proxy_headers=True, forwarded_allow_ips="127.0.0.1")
    await uvicorn.Server(cfg).serve()
