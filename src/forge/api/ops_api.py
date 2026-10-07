"""FORGE OPS COMMANDER API — the operations surface for the human-facing Hermes OPS agent (OP-023).

Security model (defence in depth):
  * separate bearer token (var/run/ops_token, 0600) — distinct from the research agents' token; loopback clients only;
  * scope = FORGE only: curated read tools, directives to Hermes roles, a closed whitelist of actions; no shell, no
    secrets, no file access, no other project;
  * every call is written to `ops_audit` (actor, channel, action, args, outcome);
  * rate limits per class (read / write / confirm);
  * actions are classed SAFE (risk-reducing or routine maintenance → execute) or CONFIRM (risk-increasing / irreversible
    → a one-time 6-digit code is returned ONLY in `owner_code`, which the OPS plugin delivers to the owner's chat
    out-of-band and strips before the model sees the response; the model can only execute after the human types it).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import subprocess
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

ROLES = ("governor", "alpha_inventor", "adversary", "critic", "doctor", "rail_hunter", "architect", "all")
# read tools the OPS agent may call (FORGE ToolRouter, attributed to role "ops"); writes go through actions below
READ_TOOLS = ("get_system_state", "get_market_state", "list_strategies", "get_strategy", "get_recent_failures",
              "get_missed_opportunities", "get_calibration", "get_research_log", "get_opportunity_surface",
              "get_crossrail_evidence", "get_profit_velocity", "get_shadow_rails", "get_listing_events",
              "get_intelligence_budget", "get_recent_candidates", "get_role_reports", "get_prompt_performance",
              "get_system_health")
# action → (class, description). CONFIRM = out-of-band owner code required.
ACTIONS: dict[str, tuple[str, str]] = {
    "stop_trading": ("SAFE", "STOP ALL trading immediately (risk-reducing; exits kept)"),
    "resume_trading": ("CONFIRM", "resume trading after a STOP ALL"),
    "research_focus": ("SAFE", "prioritise a research focus next cycle: params {focus, interval_s: 300|3600}"),
    "compute_boost": ("SAFE", "run Modal research bursts every cycle for N hours (≤ 6; Modal $30/month cap and budget "
                              "states still apply): params {hours}"),
    "kalshi_live_off": ("SAFE", "disable Kalshi live execution (shadow continues)"),
    "kalshi_live_on": ("CONFIRM", "re-enable Kalshi live execution (still gated by the evidence ladder + breakers)"),
    "cancel_directive": ("SAFE", "cancel an open directive: params {id}"),
}
LOOPBACK = {"127.0.0.1", "::1", "localhost"}
RATE = {"read": (240, 60.0), "write": (30, 600.0), "confirm": (12, 3600.0)}     # (max calls, window seconds)
_hits: dict[str, list[float]] = {}


def ops_token(home: Path) -> str:
    p = Path(home) / "run" / "ops_token"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(secrets.token_urlsafe(32))
        os.chmod(p, 0o600)
    return p.read_text().strip()


def _rate(cls: str) -> bool:
    n, win = RATE[cls]
    now = time.time()
    h = [t for t in _hits.get(cls, []) if now - t < win]
    if len(h) >= n:
        _hits[cls] = h
        return False
    h.append(now)
    _hits[cls] = h
    return True


def _version() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    try:
        head = (root / ".git" / "HEAD").read_text().strip()
        ref = head[5:] if head.startswith("ref: ") else None
        sha = (root / ".git" / ref).read_text().strip() if ref and (root / ".git" / ref).exists() else head
        if ref and not sha:
            raise ValueError
        msg = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%cI %s"], capture_output=True, text=True,
                             timeout=5).stdout.strip()
        return {"commit": sha[:10], "branch": (ref or "").rsplit("/", 1)[-1], "last_commit": msg[:160]}
    except Exception:
        return {"commit": None}


def status(forge: Any) -> dict[str, Any]:
    """One-call live operational + economic status (what the owner asks for most)."""
    from forge.core import state as tstate
    db = forge.db
    t = getattr(forge, "treasury", {}) or {}
    v = db.kv_get("velocity") or {}
    loops = forge.sup.snapshot() if hasattr(forge.sup, "snapshot") else []
    stale = [x["name"] for x in loops if not x["alive"] or (x["limit_s"] is not None and x["silent_s"] > x["limit_s"])]
    day0 = time.time() - time.time() % 86400
    from datetime import UTC, datetime
    iso0 = datetime.fromtimestamp(day0, UTC).isoformat()
    shadow_today = db.query("SELECT kind, COUNT(*) n, ROUND(SUM(pnl), 2) pnl FROM crossrail_signals WHERE status='SETTLED' "
                            "AND settled_ts >= ? GROUP BY kind ORDER BY pnl DESC", (day0,))
    paper_today = db.scalar("SELECT COALESCE(SUM(realized_pnl_usd), 0) FROM positions WHERE book = 'paper' AND status = 'CLOSED' "
                            "AND closed_at >= ?", (iso0,))
    open_pos = db.query("SELECT book, symbol, strategy_id, ROUND(cost_usd, 2) cost_usd, opened_at FROM positions "
                        "WHERE status IN ('OPEN','OPENING') ORDER BY opened_at DESC LIMIT 10")
    intel_24h = db.scalar("SELECT ROUND(COALESCE(SUM(cost_usd), 0), 4) FROM inference_calls WHERE ts >= ? AND model LIKE 'deepseek%'",
                          (datetime.fromtimestamp(time.time() - 86400, UTC).isoformat(),))
    roles = db.query("SELECT role, MAX(ts) last_ts, COUNT(*) n FROM role_reports WHERE ts >= ? GROUP BY role",
                     (time.time() - 86400,))
    comp = getattr(forge, "compute", None)
    warn = db.query("SELECT ts, agent, substr(message, 1, 200) message FROM timeline WHERE level IN ('warn','error') "
                    "ORDER BY id DESC LIMIT 5")
    h = getattr(forge, "health", None)
    return {
        "utc": datetime.now(UTC).isoformat(timespec="seconds"), "version": _version(),
        "uptime_h": round((time.time() - getattr(forge, "started", time.time())) / 3600, 2),
        "mode": forge.s.mode.value, "book": forge.book, "trading_state": tstate.get_state(db),
        "treasury": {"total_usd": (v.get("treasury") or {}).get("total"), "regime": (v.get("regime") or {}).get("regime"),
                     "paper_equity_usd": t.get("equity_usd"), "true_net_usd": t.get("true_net_usd")},
        "profit": {"target_usd_per_h": v.get("target_usd_per_h"),
                   "realized_live_usd_per_h": {k: round(x.get("usd_per_h", 0.0), 4) for k, x in (v.get("realized") or {}).items()},
                   "expected_usd_per_h": {k: round(x, 4) for k, x in (v.get("expected_usd_per_h") or {}).items()},
                   "paper_realized_today_usd": round(float(paper_today or 0), 4),
                   "kalshi_shadow_today_per_contract": shadow_today,
                   "top_levers": [p["action"] for p in (v.get("priorities") or [])[:3]]},
        "open_positions": open_pos, "population": forge.reg.counts() if hasattr(forge, "reg") else None,
        "health": {"score": h.score() if h else None, "loops": len(loops), "stale_loops": stale, "recent_warnings": warn},
        "compute": comp.summary() if comp else None, "deepseek_spend_24h_usd": intel_24h,
        "hermes_roles_24h": roles,
        "open_directives": db.query("SELECT id, role, priority, substr(instruction, 1, 120) instruction, ts FROM ops_directives "
                                    "WHERE status = 'OPEN' ORDER BY id"),
    }


def mount_ops(app: FastAPI, forge: Any, token: str) -> None:
    db = forge.db

    def audit(actor: str, action: str, args: Any, outcome: str, detail: Any = None, channel: str = "ops") -> None:
        db.insert("ops_audit", {"ts": time.time(), "actor": actor[:80], "channel": channel[:40], "action": action[:80],
                                "args": json.dumps(args, default=str)[:4000], "outcome": outcome,
                                "detail": json.dumps(detail, default=str)[:4000] if detail is not None else None})

    def check(req: Request, cls: str, action: str) -> str:
        host = req.client.host if req.client else ""
        a = req.headers.get("authorization", "")
        if host not in LOOPBACK or not (a.startswith("Bearer ") and
                                                                 hmac.compare_digest(a[7:].strip(), token)):
            raise HTTPException(401, "ops token required (loopback only)")
        actor = req.headers.get("x-ops-actor", "ops")[:80]
        if not _rate(cls):
            audit(actor, action, None, "RATE_LIMITED")
            raise HTTPException(429, f"ops rate limit ({cls})")
        return actor

    def execute(action: str, p: dict[str, Any], actor: str) -> dict[str, Any]:
        from forge.core import state as tstate
        if action == "stop_trading":
            return {"trading_state": tstate.stop_all(db, forge.audit, actor=f"ops:{actor}",
                                                     reason=str(p.get("reason") or "OPS Commander STOP ALL")[:200])}
        if action == "resume_trading":
            return {"trading_state": tstate.resume(db, forge.audit, actor=f"ops:{actor}", confirm="RESUME TRADING")}
        if action == "research_focus":
            iv = int(p.get("interval_s") or 3600)
            focus = str(p.get("focus") or "")[:500]
            if iv not in (300, 3600) or not focus:
                raise ValueError("params: focus (text), interval_s 300|3600")
            db.kv_set("brain.research_focus", {"interval_s": iv, "focus": focus, "by": f"ops:{actor}", "ts": time.time()})
            return {"research_focus": focus, "interval_s": iv}
        if action == "compute_boost":
            hrs = max(0.0, min(6.0, float(p.get("hours") or 1)))
            db.kv_set("ops.compute_boost", {"until": time.time() + hrs * 3600, "by": f"ops:{actor}"})
            comp = getattr(forge, "compute", None)
            return {"boost_until_utc": time.strftime("%H:%M", time.gmtime(time.time() + hrs * 3600)),
                    "modal": comp.summary() if comp else "Modal disabled"}
        if action in ("kalshi_live_off", "kalshi_live_on"):
            db.kv_set("ops.kalshi_live", "off" if action.endswith("off") else "on")
            return {"kalshi_live": db.kv_get("ops.kalshi_live")}
        if action == "cancel_directive":
            db.execute("UPDATE ops_directives SET status = 'CANCELLED', done_ts = ? WHERE id = ? AND status = 'OPEN'",
                       (time.time(), int(p.get("id") or 0)))
            return {"cancelled": int(p.get("id") or 0)}
        raise ValueError(f"unknown action {action}")

    @app.get("/api/ops/status")
    async def ops_status(request: Request) -> Any:
        actor = check(request, "read", "status")
        out = status(forge)
        audit(actor, "status", None, "OK")
        return out

    @app.get("/api/ops/tools")
    async def ops_tools(request: Request) -> Any:
        check(request, "read", "tools")
        from forge.brain.tools import TOOLS
        return {"tools": [t for t in TOOLS if t["function"]["name"] in READ_TOOLS],
                "actions": {k: {"class": c, "description": d} for k, (c, d) in ACTIONS.items()}, "roles": ROLES}

    @app.post("/api/ops/tool")
    async def ops_tool(request: Request) -> Any:
        actor = check(request, "read", "tool")
        b = await request.json()
        name = str(b.get("name", ""))
        if name not in READ_TOOLS:
            audit(actor, f"tool:{name}", b.get("args"), "DENIED")
            raise HTTPException(403, f"tool {name} not in the OPS read set")
        from forge.brain.tools import ToolRouter
        out = await ToolRouter(forge, f"ops:{actor}", "hermes_ops").dispatch(name, json.dumps(b.get("args") or {}))
        audit(actor, f"tool:{name}", b.get("args"), "OK")
        return json.loads(out)

    @app.post("/api/ops/directive")
    async def ops_directive(request: Request) -> Any:
        actor = check(request, "write", "directive")
        b = await request.json()
        role, instr = str(b.get("role") or ""), str(b.get("instruction") or "").strip()
        if role not in ROLES or not instr:
            raise HTTPException(400, f"role must be one of {ROLES}; instruction required")
        did = db.insert_id("ops_directives", {"ts": time.time(), "role": role, "instruction": instr[:3000],
                                              "priority": "high" if str(b.get("priority")) == "high" else "normal",
                                              "status": "OPEN", "requested_by": actor})
        audit(actor, "directive", {"role": role, "instruction": instr[:300]}, "OK", {"id": did})
        return {"id": did, "role": role, "status": "OPEN",
                "note": "delivered in the role's next brief (Hermes cron); the role reports back against this id"}

    @app.get("/api/ops/directives")
    async def ops_directives(request: Request, status_: str = "ALL", limit: int = 20) -> Any:
        check(request, "read", "directives")
        q = "SELECT * FROM ops_directives" + ("" if status_ == "ALL" else " WHERE status = ?") + " ORDER BY id DESC LIMIT ?"
        return db.query(q, ((status_, min(limit, 100)) if status_ != "ALL" else (min(limit, 100),)))

    @app.post("/api/ops/action")
    async def ops_action(request: Request) -> Any:
        actor = check(request, "write", "action")
        b = await request.json()
        action, p = str(b.get("action", "")), b.get("params") or {}
        if action not in ACTIONS:
            audit(actor, action, p, "DENIED", "unknown action")
            raise HTTPException(403, f"unknown action; allowed: {sorted(ACTIONS)}")
        cls = ACTIONS[action][0]
        if cls == "CONFIRM":
            code = f"{secrets.randbelow(10**6):06d}"
            pid = secrets.token_hex(4)
            db.insert("ops_pending", {"id": pid, "ts": time.time(), "action": action, "params": json.dumps(p),
                                      "code_hash": hashlib.sha256(f"{pid}:{code}".encode()).hexdigest(),
                                      "expires_ts": time.time() + 600, "status": "PENDING"})
            audit(actor, action, p, "PENDING_CONFIRMATION", {"pending_id": pid})
            return {"status": "CONFIRMATION_REQUIRED", "pending_id": pid, "expires_in_s": 600,
                    "description": ACTIONS[action][1], "owner_code": code}      # stripped by the OPS plugin
        try:
            res = execute(action, p, actor)
        except Exception as e:
            audit(actor, action, p, "ERROR", str(e)[:300])
            raise HTTPException(400, str(e)[:300]) from e
        audit(actor, action, p, "OK", res)
        return {"status": "DONE", "action": action, "result": res}

    @app.post("/api/ops/confirm")
    async def ops_confirm(request: Request) -> Any:
        actor = check(request, "confirm", "confirm")
        b = await request.json()
        pid, code = str(b.get("pending_id", "")), str(b.get("code", "")).strip()
        row = db.query_one("SELECT * FROM ops_pending WHERE id = ?", (pid,))
        if not row or row["status"] != "PENDING":
            raise HTTPException(404, "no pending action with that id")
        if time.time() > row["expires_ts"] or row["attempts"] >= 3:
            db.execute("UPDATE ops_pending SET status = 'EXPIRED', decided_ts = ? WHERE id = ?", (time.time(), pid))
            audit(actor, f"confirm:{row['action']}", {"pending_id": pid}, "DENIED", "expired / too many attempts")
            raise HTTPException(410, "confirmation expired or too many attempts — request the action again")
        ok = hmac.compare_digest(hashlib.sha256(f"{pid}:{code}".encode()).hexdigest(), row["code_hash"])
        if not ok:
            db.execute("UPDATE ops_pending SET attempts = attempts + 1 WHERE id = ?", (pid,))
            audit(actor, f"confirm:{row['action']}", {"pending_id": pid}, "DENIED", "wrong code")
            raise HTTPException(403, "wrong confirmation code")
        try:
            res = execute(row["action"], json.loads(row["params"] or "{}"), actor)
        except Exception as e:
            db.execute("UPDATE ops_pending SET status = 'REJECTED', decided_ts = ?, result = ? WHERE id = ?",
                       (time.time(), str(e)[:300], pid))
            audit(actor, f"confirm:{row['action']}", {"pending_id": pid}, "ERROR", str(e)[:300])
            raise HTTPException(400, str(e)[:300]) from e
        db.execute("UPDATE ops_pending SET status = 'EXECUTED', decided_ts = ?, result = ? WHERE id = ?",
                   (time.time(), json.dumps(res, default=str)[:2000], pid))
        audit(actor, f"confirm:{row['action']}", {"pending_id": pid}, "OK", res)
        return {"status": "DONE", "action": row["action"], "result": res}

    @app.post("/api/ops/audit")
    async def ops_audit_post(request: Request) -> Any:
        actor = check(request, "read", "audit")
        b = await request.json()
        audit(actor, str(b.get("action", "host"))[:80], b.get("args"), str(b.get("outcome", "OK"))[:24], b.get("detail"),
              channel=str(b.get("channel", "ops-host"))[:40])
        return {"ok": True}

    @app.get("/api/ops/audit")
    async def ops_audit_get(request: Request, limit: int = 30) -> Any:
        check(request, "read", "audit_read")
        return db.query("SELECT id, ts, actor, channel, action, substr(args, 1, 300) args, outcome, substr(detail, 1, 300) detail "
                        "FROM ops_audit ORDER BY id DESC LIMIT ?", (min(limit, 200),))

    @app.post("/api/ops/usage")
    async def ops_usage(request: Request) -> Any:
        check(request, "read", "usage")
        from forge.api.agent_api import record_usage
        return record_usage(forge, await request.json(), role_override="ops")
