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
    "launch_objective": ("SAFE", "executive objective → coordinated multi-role campaign: params {kind: grow_profit | "
                                 "integrate_platform | fix | custom, objective}"),
    "file_ticket": ("SAFE", "engineering ticket for code changes / new adapters: params {title, spec, credential_needed}"),
    "release_ticket": ("SAFE", "release a HOLD engineering ticket to the engineer: params {ticket_id}"),
    "approve_deploy": ("CONFIRM", "approve deploying an engineering change that touches a PROTECTED area: params {ticket_id}"),
    "lockdown": ("SAFE", "FREEZE remote control: only status reads and stop_trading work until unlocked"),
    "unlock": ("CONFIRM", "lift a lockdown"),
}
ALWAYS_ALLOWED_WHEN_LOCKED = {"stop_trading", "lockdown"}
LOOPBACK = {"127.0.0.1", "::1", "localhost"}
READ_AUDIT_SKIP_MIRROR = {"guardian", "eng_next", "eng_ticket", "eng_queue", "capabilities", "status", "tool", "econ", "debrief", "directives_read", "objectives_read", "audit_read"}
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


def _guardian_summary(db: Any) -> dict[str, Any]:
    g = db.kv_get("guardian.state") or {}
    last = float(g.get("last_run") or 0)
    return {"alive": time.time() - last < 180, "last_check_s_ago": round(time.time() - last) if last else None,
            "open_incidents": {k: v.get("text") for k, v in (g.get("open_incidents") or {}).items()},
            "recent_repairs": [f"{time.strftime('%H:%M', time.gmtime(r['ts']))} {r['text']}" for r in (g.get("recent_repairs") or [])[-5:]]}


def status(forge: Any) -> dict[str, Any]:
    """One-call live operational + economic status (what the owner asks for most)."""
    from forge.core import state as tstate
    db = forge.db
    t = getattr(forge, "treasury", {}) or {}
    v = db.kv_get("velocity") or {}
    loops = forge.sup.snapshot() if hasattr(forge.sup, "snapshot") else []
    stale = [x["loop"] for x in loops if not x["alive"] or (x["limit_s"] is not None and x["silent_s"] > x["limit_s"])]
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
        "health": {"score": h.score() if h else None, "loops": len(loops), "stale_loops": stale, "recent_warnings": warn,
                   "guardian": _guardian_summary(db)},
        "compute": comp.summary() if comp else None, "deepseek_spend_24h_usd": intel_24h,
        "hermes_roles_24h": roles,
        "open_directives": db.query("SELECT id, role, priority, substr(instruction, 1, 120) instruction, ts FROM ops_directives "
                                    "WHERE status = 'OPEN' ORDER BY id"),
    }


ENG_PATHS = ("/api/ops/tool", "/api/ops/tools", "/api/ops/tickets", "/api/ops/eng/next", "/api/ops/eng/claim",
             "/api/ops/eng/update", "/api/ops/eng/ticket")


def eng_token(home: Path) -> str:
    p = Path(home) / "run" / "eng_token"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(secrets.token_urlsafe(32))
        os.chmod(p, 0o600)
    return p.read_text().strip()


def mount_ops(app: FastAPI, forge: Any, token: str, etoken: str | None = None) -> None:
    db = forge.db

    from forge.ops import totp

    def audit(actor: str, action: str, args: Any, outcome: str, detail: Any = None, channel: str = "ops") -> None:
        db.insert("ops_audit", {"ts": time.time(), "actor": actor[:80], "channel": channel[:40], "action": action[:80],
                                "args": json.dumps(args, default=str)[:4000], "outcome": outcome,
                                "detail": json.dumps(detail, default=str)[:4000] if detail is not None else None})
        if action not in READ_AUDIT_SKIP_MIRROR or outcome not in ("OK",):
            try:      # tamper-evident mirror: hash-chained audit journal (forge verify-audit)
                forge.audit.append("OPS", {"actor": actor, "channel": channel, "action": action, "outcome": outcome,
                                           "args": json.dumps(args, default=str)[:600]}, actor=f"ops:{actor}"[:60])
            except Exception:
                pass

    def locked() -> bool:
        return bool((db.kv_get("ops.locked") or {}).get("locked"))

    def second_factor(code: str, pending: dict[str, Any] | None) -> tuple[bool, str]:
        """TOTP when configured (strong, channel-independent); else the one-time out-of-band code of the pending action."""
        home = forge.s.home
        if totp.configured(home):
            return totp.verify(home, db, code)
        if pending is None:
            return False, "authenticator (2FA) not configured — run forge-exec-2fa on the server"
        ok = hmac.compare_digest(hashlib.sha256(f"{pending['id']}:{code}".encode()).hexdigest(), pending["code_hash"])
        return ok, "ok" if ok else "wrong confirmation code"

    def check(req: Request, cls: str, action: str) -> str:
        host = req.client.host if req.client else ""
        a = req.headers.get("authorization", "")
        if "cf-connecting-ip" in req.headers or "x-forwarded-for" in req.headers:
            raise HTTPException(404, "not found")                     # never reachable through the portal tunnel
        presented = a[7:].strip() if a.startswith("Bearer ") else ""
        is_ops = bool(presented) and hmac.compare_digest(presented, token)
        is_eng = bool(presented and etoken) and hmac.compare_digest(presented, etoken or "~")
        if host not in LOOPBACK or not (is_ops or is_eng):
            raise HTTPException(401, "ops token required (loopback only)")
        if is_eng and not is_ops and req.url.path not in ENG_PATHS:
            raise HTTPException(403, "engineer scope: read tools + ticket workflow only")
        actor = ("engineer" if is_eng and not is_ops else req.headers.get("x-ops-actor", "ops"))[:80]
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
        if action == "launch_objective":
            from forge.ops.executive import launch_objective
            return launch_objective(db, str(p.get("kind") or "grow_profit"), str(p.get("objective") or ""), f"ops:{actor}")
        if action == "file_ticket":
            from forge.ops.executive import file_ticket
            return file_ticket(db, str(p.get("title") or "untitled"), str(p.get("spec") or ""), p.get("credential_needed"),
                               f"ops:{actor}", str(p.get("priority") or "normal"), bool(p.get("hold")))
        if action == "release_ticket":
            db.execute("UPDATE eng_tickets SET status = 'OPEN' WHERE id = ? AND status = 'HOLD'", (int(p.get("ticket_id") or 0),))
            return {"ticket": int(p.get("ticket_id") or 0), "status": db.scalar("SELECT status FROM eng_tickets WHERE id = ?",
                                                                                 (int(p.get("ticket_id") or 0),))}
        if action == "approve_deploy":
            tid = int(p.get("ticket_id") or 0)
            db.execute("UPDATE eng_tickets SET deploy_status = 'APPROVED', approved_ts = ? WHERE id = ? AND "
                       "deploy_status = 'AWAITING_OWNER'", (time.time(), tid))
            return {"ticket": tid, "deploy_status": db.scalar("SELECT deploy_status FROM eng_tickets WHERE id = ?", (tid,))}
        if action == "lockdown":
            db.kv_set("ops.locked", {"locked": True, "ts": time.time(), "by": actor})
            return {"locked": True, "note": "remote control frozen: reads + stop_trading only; unlock needs 2FA"}
        if action == "unlock":
            db.kv_set("ops.locked", {"locked": False, "ts": time.time(), "by": actor})
            return {"locked": False}
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
        if locked() and action not in ALWAYS_ALLOWED_WHEN_LOCKED and action != "unlock":
            audit(actor, action, p, "DENIED", "lockdown active")
            raise HTTPException(423, "FORGE remote control is in LOCKDOWN — only status and stop_trading; unlock needs 2FA")
        if cls == "CONFIRM":
            code = f"{secrets.randbelow(10**6):06d}"
            pid = secrets.token_hex(4)
            db.insert("ops_pending", {"id": pid, "ts": time.time(), "action": action, "params": json.dumps(p),
                                      "code_hash": hashlib.sha256(f"{pid}:{code}".encode()).hexdigest(),
                                      "expires_ts": time.time() + 600, "status": "PENDING"})
            audit(actor, action, p, "PENDING_CONFIRMATION", {"pending_id": pid})
            if totp.configured(forge.s.home):
                return {"status": "CONFIRMATION_REQUIRED", "pending_id": pid, "expires_in_s": 600, "factor": "authenticator",
                        "description": ACTIONS[action][1],
                        "instructions": f"Owner replies: CONFIRM {pid} <6-digit code from the FORGE authenticator entry>"}
            return {"status": "CONFIRMATION_REQUIRED", "pending_id": pid, "expires_in_s": 600, "factor": "out_of_band_code",
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
        if locked() and row["action"] != "unlock":
            raise HTTPException(423, "LOCKDOWN — only 'unlock' can be confirmed")
        if time.time() > row["expires_ts"] or row["attempts"] >= 3:
            db.execute("UPDATE ops_pending SET status = 'EXPIRED', decided_ts = ? WHERE id = ?", (time.time(), pid))
            audit(actor, f"confirm:{row['action']}", {"pending_id": pid}, "DENIED", "expired / too many attempts")
            raise HTTPException(410, "confirmation expired or too many attempts — request the action again")
        ok, why = second_factor(code, row)
        if not ok:
            db.execute("UPDATE ops_pending SET attempts = attempts + 1 WHERE id = ?", (pid,))
            audit(actor, f"confirm:{row['action']}", {"pending_id": pid}, "DENIED", why)
            raise HTTPException(403, why)
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

    # ------------------------------------------------------------------ Engineering Cell
    @app.get("/api/ops/eng/next")
    async def eng_next(request: Request) -> Any:
        check(request, "read", "eng_next")
        t = db.query_one("SELECT * FROM eng_tickets WHERE status IN ('OPEN', 'IN_PROGRESS') OR deploy_status IN "
                         "('TESTS_FAILED', 'REBASE_REQUIRED', 'REJECTED', 'ROLLED_BACK') AND status = 'SUBMITTED' "
                         "ORDER BY priority = 'high' DESC, id LIMIT 1")
        return {"ticket": t}

    @app.get("/api/ops/eng/ticket")
    async def eng_ticket(request: Request, id: int) -> Any:
        check(request, "read", "eng_ticket")
        t = db.query_one("SELECT * FROM eng_tickets WHERE id = ?", (id,))
        if not t:
            raise HTTPException(404, "no such ticket")
        obj = db.query_one("SELECT * FROM ops_objectives WHERE ticket_id = ?", (id,))
        if obj:
            ids = json.loads(obj.get("directive_ids") or "[]")
            t["objective"] = {"objective": obj["objective"], "research": db.query(
                f"SELECT role, status, substr(result, 1, 3000) result FROM ops_directives WHERE id IN "  # noqa: S608
                f"({','.join('?' * len(ids))})", ids) if ids else []}
        return t

    @app.post("/api/ops/eng/claim")
    async def eng_claim(request: Request) -> Any:
        actor = check(request, "write", "eng_claim")
        tid = int((await request.json()).get("id") or 0)
        db.execute("UPDATE eng_tickets SET status = 'IN_PROGRESS', claimed_ts = ? WHERE id = ? AND status IN ('OPEN','IN_PROGRESS',"
                   "'SUBMITTED')", (time.time(), tid))
        audit(actor, "eng_claim", {"id": tid}, "OK")
        return {"id": tid, "status": db.scalar("SELECT status FROM eng_tickets WHERE id = ?", (tid,))}

    @app.post("/api/ops/eng/update")
    async def eng_update(request: Request) -> Any:
        """Engineer reports progress. SUBMITTED (with commit_sha) queues the change for the root deployer — the engineer
        never deploys. DONE = no code needed (investigation answered). BLOCKED = needs the owner/ops."""
        actor = check(request, "write", "eng_update")
        b = await request.json()
        tid, st = int(b.get("id") or 0), str(b.get("status") or "").upper()
        if st not in ("IN_PROGRESS", "SUBMITTED", "DONE", "BLOCKED"):
            raise HTTPException(400, "status: IN_PROGRESS | SUBMITTED | DONE | BLOCKED")
        note = str(b.get("note") or "")[:6000]
        if st == "SUBMITTED":
            sha = str(b.get("commit_sha") or "")
            if not (7 <= len(sha) <= 40 and all(ch in "0123456789abcdef" for ch in sha)):
                raise HTTPException(400, "SUBMITTED requires the full commit_sha of the change in the engineer repo")
            db.execute("UPDATE eng_tickets SET status = 'SUBMITTED', commit_sha = ?, branch = ?, deploy_status = 'QUEUED', "
                       "deploy_log = NULL, notes = ? WHERE id = ?", (sha, str(b.get("branch") or "")[:100], note, tid))
        else:
            db.execute("UPDATE eng_tickets SET status = ?, notes = ?, resolution = CASE WHEN ? IN ('DONE','BLOCKED') THEN ? "
                       "ELSE resolution END, done_ts = CASE WHEN ? = 'DONE' THEN ? ELSE done_ts END WHERE id = ?",
                       (st, note, st, note, st, time.time(), tid))
        audit(actor, "eng_update", {"id": tid, "status": st}, "OK", {"note": note[:300]})
        return {"id": tid, "status": st}

    @app.get("/api/ops/eng/queue")
    async def eng_queue(request: Request) -> Any:
        check(request, "read", "eng_queue")
        return db.query("SELECT id, title, commit_sha, branch, deploy_status, deploy_class, approved_ts FROM eng_tickets "
                        "WHERE deploy_status IN ('QUEUED', 'APPROVED') ORDER BY id")

    @app.post("/api/ops/eng/deploy_result")
    async def eng_deploy_result(request: Request) -> Any:
        actor = check(request, "write", "eng_deploy_result")
        b = await request.json()
        tid, ds = int(b.get("id") or 0), str(b.get("deploy_status") or "")
        status = {"DEPLOYED": "DONE"}.get(ds, "SUBMITTED")
        db.execute("UPDATE eng_tickets SET deploy_status = ?, deploy_class = COALESCE(?, deploy_class), deploy_log = ?, "
                   "status = ?, done_ts = CASE WHEN ? = 'DEPLOYED' THEN ? ELSE done_ts END WHERE id = ?",
                   (ds, b.get("deploy_class"), str(b.get("log") or "")[:8000], status, ds, time.time(), tid))
        audit(actor, "eng_deploy_result", {"id": tid, "deploy_status": ds}, "OK", {"class": b.get("deploy_class")})
        return {"id": tid, "deploy_status": ds}

    @app.post("/api/ops/guardian")
    async def guardian_post(request: Request) -> Any:
        check(request, "read", "guardian")
        db.kv_set("guardian.state", {**(await request.json()), "received": time.time()})
        return {"ok": True}

    @app.get("/api/ops/capabilities")
    async def ops_capabilities(request: Request) -> Any:
        """Live roster: every agent, service, loop, rail, budget and power the EXECUTIVE OPS agent commands."""
        actor = check(request, "read", "capabilities")
        from forge.agents.roles import ROLES as ROLE_GENOMES
        loops = forge.sup.snapshot() if hasattr(forge.sup, "snapshot") else []
        roster = []
        for role in [r for r in ROLES if r != "all"]:
            last = db.query_one("SELECT MAX(ts) ts, COUNT(*) n FROM role_reports WHERE role = ? AND ts >= ?",
                                (role, time.time() - 86400)) or {}
            g = db.query_one("SELECT version, status FROM prompt_genomes WHERE role = ? AND status = 'CHAMPION' "
                             "ORDER BY version DESC LIMIT 1", (role,)) or {}
            spec = (ROLE_GENOMES.get(role) or {}) if isinstance(ROLE_GENOMES, dict) else {}
            roster.append({"role": role, "mission": str(spec.get("mission", ""))[:220], "reports_24h": last.get("n"),
                           "last_report_utc": time.strftime("%H:%M", time.gmtime(last["ts"])) if last.get("ts") else None,
                           "genome_version": g.get("version"),
                           "open_directives": db.scalar("SELECT COUNT(*) FROM ops_directives WHERE status='OPEN' AND role=?",
                                                        (role,))})
        comp = getattr(forge, "compute", None)
        v = db.kv_get("velocity") or {}
        out = {
            "prime_directive": "Keep FORGE succeeding and operating at all times; grow true-net income and the treasury "
                               "as fast as evidence allows (exponential, compounding); delegate to the right specialist.",
            "hermes_specialists": roster,
            "forge_services": {"forge": "trading engine + API + all loops", "forge-hermes": "7 specialist agents (scheduled)",
                               "forge-tunnel": "portal", "forge-ops": "you (EXECUTIVE OPS)",
                               "forge-eng": "FORGE ENGINEER (sandboxed coding agent)",
                               "forge-deployer": "root deployer (scan → sandboxed tests → deploy → watch → rollback)",
                               "forge-guardian": "root watchdog every 60 s: restarts anything down/stalled, alerts owner once"},
            "guardian": _guardian_summary(db),
            "engine_loops": {"count": len(loops), "names": sorted(x["loop"] for x in loops),
                             "unhealthy": [x["loop"] for x in loops if not x["alive"]]},
            "earning_streams": [{"id": s["id"], "live": s.get("live"), "tier": s.get("tier"), "n": s.get("n")}
                                for s in v.get("streams", [])],
            "rails": db.query("SELECT id, status, executable FROM rail_registry ORDER BY executable DESC, id"),
            "budgets": {"modal": comp.summary() if comp else None, "deepseek": db.kv_get("deepseek.sentinel"),
                        "hermes_mode": db.kv_get("hermes.mode")},
            "your_actions": {k: {"class": c, "description": d} for k, (c, d) in ACTIONS.items()},
            "your_tools": ["ops_status", "ops_debrief", "ops_econ", "ops_capabilities", "ops_objective", "ops_objectives",
                           "ops_assign", "ops_directives", "ops_action", "ops_confirm", "ops_restart", "ops_logs", "ops_host",
                           "ops_engineer", "ops_tickets", "ops_transfer_preview", "ops_transfer_confirm", "ops_audit"]
                          + [f"ops_{t}" for t in READ_TOOLS],
            "engineering": {"open_tickets": db.scalar("SELECT COUNT(*) FROM eng_tickets WHERE status IN ('OPEN','IN_PROGRESS','SUBMITTED')"),
                            "awaiting_owner": db.scalar("SELECT COUNT(*) FROM eng_tickets WHERE deploy_status = 'AWAITING_OWNER'"),
                            "engineer": "FORGE ENGINEER (Hermes, Opus 5.5 xhigh, sandboxed): writes code + tests from ops_engineer "
                                        "tickets; root deployer scans, tests, deploys, watches, rolls back"},
            "treasury": v.get("treasury"), "regime": (v.get("regime") or {}).get("regime"),
            "target_usd_per_h": v.get("target_usd_per_h"),
        }
        audit(actor, "capabilities", None, "OK")
        return out

    @app.get("/api/ops/econ")
    async def ops_econ(request: Request, window: str = "1h") -> Any:
        actor = check(request, "read", "econ")
        from forge.ops.econ import window as econ_window
        try:
            out = econ_window(forge, window)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        audit(actor, "econ", {"window": window}, "OK")
        return out

    @app.get("/api/ops/debrief")
    async def ops_debrief(request: Request) -> Any:
        actor = check(request, "read", "debrief")
        from forge.ops.executive import debrief
        out = debrief(forge)
        audit(actor, "debrief", None, "OK")
        return out

    @app.get("/api/ops/objectives")
    async def ops_objectives(request: Request, status_: str = "ALL") -> Any:
        check(request, "read", "objectives_read")
        from forge.ops.executive import objectives
        return objectives(db, status_)

    @app.get("/api/ops/tickets")
    async def ops_tickets(request: Request) -> Any:
        check(request, "read", "tickets")
        return db.query("SELECT * FROM eng_tickets ORDER BY id DESC LIMIT 20")

    @app.post("/api/ops/transfer/preview")
    async def ops_transfer_preview(request: Request) -> Any:
        actor = check(request, "write", "transfer_preview")
        if locked():
            raise HTTPException(423, "LOCKDOWN — transfers disabled")
        b = await request.json()
        from forge.ops.executive import transfer_preview
        out = await transfer_preview(forge, float(b.get("amount_usd") or 0))
        audit(actor, "transfer_preview", {"amount_usd": b.get("amount_usd")}, out["status"], out)
        return out

    @app.post("/api/ops/transfer/confirm")
    async def ops_transfer_confirm(request: Request) -> Any:
        """Owner's final confirmation: exact phrase 'CONFIRM TRANSFER $<amount>' + authenticator code (2FA mandatory)."""
        import re as _re
        actor = check(request, "confirm", "transfer_confirm")
        if locked():
            raise HTTPException(423, "LOCKDOWN — transfers disabled")
        b = await request.json()
        tid, phrase, code = str(b.get("transfer_id", "")), str(b.get("phrase", "")), str(b.get("code", ""))
        t = db.query_one("SELECT * FROM ops_transfers WHERE id = ?", (tid,))
        if not t or t["status"] != "PREVIEWED":
            raise HTTPException(404, "no previewed transfer with that id")
        m = _re.fullmatch(r"\s*CONFIRM TRANSFER \$?([0-9]+(?:\.[0-9]{1,2})?)\s*", phrase, flags=_re.I)
        if not m or abs(float(m.group(1)) - float(t["amount_usd"])) > 0.004:
            audit(actor, "transfer_confirm", {"transfer_id": tid}, "DENIED", "phrase mismatch")
            raise HTTPException(403, f"confirmation phrase must be exactly: CONFIRM TRANSFER ${float(t['amount_usd']):.2f}")
        if not totp.configured(forge.s.home):
            raise HTTPException(403, "transfers require the authenticator second factor (server: forge-exec-2fa)")
        ok, why = totp.verify(forge.s.home, db, code)
        if not ok:
            audit(actor, "transfer_confirm", {"transfer_id": tid}, "DENIED", why)
            raise HTTPException(403, why)
        from forge.ops.executive import transfer_execute
        try:
            out = await transfer_execute(forge, tid)
        except Exception as e:
            audit(actor, "transfer_execute", {"transfer_id": tid}, "ERROR", str(e)[:300])
            raise HTTPException(400, str(e)[:300]) from e
        audit(actor, "transfer_execute", {"transfer_id": tid, "amount_usd": t["amount_usd"]}, "OK", out)
        return out

    @app.get("/api/ops/transfers")
    async def ops_transfers(request: Request) -> Any:
        check(request, "read", "transfers")
        return db.query("SELECT id, ts, amount_usd, destination, status, treasury_before, treasury_after FROM ops_transfers "
                        "ORDER BY ts DESC LIMIT 20")

    @app.post("/api/ops/usage")
    async def ops_usage(request: Request) -> Any:
        check(request, "read", "usage")
        from forge.api.agent_api import record_usage
        return record_usage(forge, await request.json(), role_override="ops")
