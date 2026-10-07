"""hermes-forge-ops — the FORGE OPS COMMANDER's entire tool surface (OP-023).

Scope: FORGE only. Talks to FORGE's loopback OPS API with its own token, reads journald for forge* units, restarts
forge* units through a narrow polkit rule. No shell, no file access, no secrets, nothing outside FORGE.
Confirmation-class actions: FORGE returns a one-time code; this plugin sends it straight to the owner's Telegram (Bot API)
and REMOVES it from what the model sees — so neither the model nor injected text can approve a risky action; only the
human typing the code can.
"""

import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
API = os.environ.get("FORGE_API", "http://127.0.0.1:8470")
UNITS = {"forge": "forge.service", "forge-hermes": "forge-hermes.service", "forge-tunnel": "forge-tunnel.service"}
LOG_UNITS = {**UNITS, "forge-ops": "forge-ops.service"}
SECRET_RES = [re.compile(p) for p in (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
    r"(?i)\bbearer\s+\S+",
    r"(?i)\b(token|secret|password|api[_-]?key|authorization)\b\s*[:=]\s*\S+",
    r"\bsk-[A-Za-z0-9_\-]{16,}", r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}\b",             # Telegram bot tokens
    r"\b[A-Za-z0-9_\-]{40,}\b")]
_session_actor: dict[str, str] = {}


def redact(text: str) -> str:
    for r in SECRET_RES:
        text = r.sub("[REDACTED]", text)
    return text


def _token() -> str:
    return (HOME / "forge" / "ops_token").read_text().strip()


def _call(method: str, path: str, body: dict | None = None, actor: str = "ops", timeout: float = 30.0) -> dict:
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json",
                                          "X-Ops-Actor": actor})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode()).get("detail")
        except Exception:
            detail = str(e)
        return {"error": f"HTTP {e.code}", "detail": detail}


def _out(obj) -> str:
    return redact(json.dumps(obj, default=str))[:24000]


def _actor(session_id) -> str:
    return f"ops-commander:{(session_id or 'na')[:24]}"


def _audit(action: str, args, outcome: str, detail=None, session_id=None) -> None:
    body = {"action": action, "args": args, "outcome": outcome, "detail": detail, "channel": "ops-host"}
    threading.Thread(target=lambda: _call("POST", "/api/ops/audit", body, _actor(session_id), 10), daemon=True).start()


def _owners() -> list[str]:
    return [u.strip() for u in os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip().isdigit()]


def _send_owner(text: str) -> bool:
    """Out-of-band delivery to the owner's Telegram DM (never through the model)."""
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    owners = _owners()
    if not tok or not owners:
        return False
    ok = False
    for chat in owners:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        try:
            with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=15) as r:
                ok = ok or json.loads(r.read().decode()).get("ok", False)
        except Exception:
            pass
    return ok


def _systemctl(*args: str, timeout: float = 90) -> tuple[int, str]:
    p = subprocess.run(["systemctl", *args], capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


def _health_wait(seconds: int = 120) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urllib.request.urlopen(API + "/health", timeout=4) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(4)
    return False


def _schema(name, desc, props, required=None):
    return {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required or []}}


def register(ctx):
    # ---------------------------------------------------------------- live status + FORGE read tools
    def h_status(params, session_id=None, **kw):
        return _out(_call("GET", "/api/ops/status", actor=_actor(session_id)))
    ctx.register_tool(name="ops_status", toolset="forge_ops", handler=h_status, schema=_schema(
        "ops_status", "[FORGE OPS] One-call live status: version, uptime, trading state, treasury + regime, realized and "
        "expected $/h vs target, today's paper/Kalshi-shadow P&L, open positions, health + stale loops, recent warnings, "
        "Modal + DeepSeek spend, Hermes role activity, open directives. Start here for 'what's happening?'.", {}))

    try:
        meta = _call("GET", "/api/ops/tools")
    except Exception:
        meta = {}
    for t in meta.get("tools", []):
        fn = t["function"]
        name = fn["name"]

        def handler(params, session_id=None, _n=name, **kw):
            return _out(_call("POST", "/api/ops/tool", {"name": _n, "args": params or {}}, _actor(session_id)))
        ctx.register_tool(name=f"ops_{name}", toolset="forge_ops", handler=handler, schema=_schema(
            f"ops_{name}", "[FORGE read] " + fn.get("description", ""), (fn.get("parameters") or {}).get("properties", {}),
            (fn.get("parameters") or {}).get("required")))

    # ---------------------------------------------------------------- delegation to the Hermes research organisation
    roles = meta.get("roles") or ["governor", "alpha_inventor", "adversary", "critic", "doctor", "rail_hunter", "architect", "all"]

    def h_directive(params, session_id=None, **kw):
        return _out(_call("POST", "/api/ops/directive", {"role": params.get("role"), "instruction": params.get("instruction"),
                                                         "priority": params.get("priority", "normal")}, _actor(session_id)))
    ctx.register_tool(name="ops_assign", toolset="forge_ops", handler=h_directive, schema=_schema(
        "ops_assign", "[FORGE OPS] Delegate a task to a Hermes role. governor=CIO/allocation, alpha_inventor=new strategy "
        "ideas, adversary=falsify/kill weak ideas, critic=red-team decisions, doctor=SRE/health fixes, rail_hunter=new "
        "income rails/markets, architect=prompt/agent improvements, all=broadcast. Delivered in the role's next scheduled "
        "run; it reports back against the directive id (check with ops_directives).",
        {"role": {"type": "string", "enum": roles}, "instruction": {"type": "string"},
         "priority": {"type": "string", "enum": ["normal", "high"]}}, ["role", "instruction"]))

    def h_directives(params, session_id=None, **kw):
        st = params.get("status", "ALL")
        return _out(_call("GET", f"/api/ops/directives?status_={urllib.parse.quote(st)}&limit={int(params.get('limit', 20))}",
                          actor=_actor(session_id)))
    ctx.register_tool(name="ops_directives", toolset="forge_ops", handler=h_directives, schema=_schema(
        "ops_directives", "[FORGE OPS] Delegated tasks and their results (OPEN / DONE / CANCELLED).",
        {"status": {"type": "string", "enum": ["ALL", "OPEN", "DONE", "CANCELLED"]}, "limit": {"type": "integer"}}))

    # ---------------------------------------------------------------- whitelisted actions (+ out-of-band confirmation)
    acts = meta.get("actions") or {}

    def h_action(params, session_id=None, **kw):
        r = _call("POST", "/api/ops/action", {"action": params.get("action"), "params": params.get("params") or {}},
                  _actor(session_id))
        code = r.pop("owner_code", None)
        if r.get("status") == "CONFIRMATION_REQUIRED":
            sent = _send_owner(f"FORGE OPS confirmation\nAction: {params.get('action')} — {r.get('description')}\n"
                               f"Params: {json.dumps(params.get('params') or {})[:300]}\n"
                               f"Reply in the chat:  CONFIRM {r.get('pending_id')} {code}\n(valid 10 min; ignore to cancel)")
            r["owner_notified_out_of_band"] = sent
            r["instructions"] = ("A one-time code was sent to the owner directly (you cannot see it). Ask the owner to reply "
                                 "'CONFIRM <pending_id> <code>'; then call ops_confirm with exactly what they typed."
                                 if sent else "Out-of-band channel unavailable (Telegram not configured) — confirmation-class "
                                              "actions are disabled; tell the owner.")
        return _out(r)
    ctx.register_tool(name="ops_action", toolset="forge_ops", handler=h_action, schema=_schema(
        "ops_action", "[FORGE OPS] Execute a whitelisted FORGE action. SAFE actions run immediately; CONFIRM actions send "
        "the owner a one-time code out-of-band. Available: " + "; ".join(f"{k} ({v['class']}): {v['description']}"
                                                                          for k, v in acts.items()),
        {"action": {"type": "string", "enum": sorted(acts) or ["stop_trading"]}, "params": {"type": "object"}}, ["action"]))

    def h_confirm(params, session_id=None, **kw):
        return _out(_call("POST", "/api/ops/confirm", {"pending_id": params.get("pending_id"), "code": params.get("code")},
                          _actor(session_id)))
    ctx.register_tool(name="ops_confirm", toolset="forge_ops", handler=h_confirm, schema=_schema(
        "ops_confirm", "[FORGE OPS] Complete a CONFIRM-class action with the pending_id and the code THE OWNER TYPED in this "
        "chat. Never guess or reuse codes.", {"pending_id": {"type": "string"}, "code": {"type": "string"}},
        ["pending_id", "code"]))

    # ---------------------------------------------------------------- executive economics + campaigns + transfers
    def h_econ(params, session_id=None, **kw):
        w = urllib.parse.quote(str(params.get("window", "1h")))
        return _out(_call("GET", f"/api/ops/econ?window={w}", actor=_actor(session_id)))
    ctx.register_tool(name="ops_econ", toolset="forge_ops", handler=h_econ, schema=_schema(
        "ops_econ", "[FORGE EXEC] Money for ANY window: 30s, 1m, 15m, 1h, 4h, today, 24h, 7d, lifetime (or 90s / 3h / "
        "2d). Returns LIVE true net + $/h (real wallets), PAPER realized/unrealized, costs (fees, inference, compute), "
        "deployed capital, by strategy and by rail. Use for 'how much did we make in the last X', 'total balance'.",
        {"window": {"type": "string"}}))

    def h_debrief(params, session_id=None, **kw):
        return _out(_call("GET", "/api/ops/debrief", actor=_actor(session_id)))
    ctx.register_tool(name="ops_debrief", toolset="forge_ops", handler=h_debrief, schema=_schema(
        "ops_debrief", "[FORGE EXEC] Everything needed for 'Debrief me': FORGE TODAY numbers, what worked, what didn't, "
        "what FORGE is doing (objectives, focus, diagnosis), next best levers. Format it as the executive debrief.", {}))

    def h_objective(params, session_id=None, **kw):
        return _out(_call("POST", "/api/ops/action", {"action": "launch_objective", "params": {
            "kind": params.get("kind", "grow_profit"), "objective": params.get("objective", "")}}, _actor(session_id)))
    ctx.register_tool(name="ops_objective", toolset="forge_ops", handler=h_objective, schema=_schema(
        "ops_objective", "[FORGE EXEC] Turn an owner goal into a coordinated campaign across the specialist roles: "
        "grow_profit ('make more money', 're-strategize', 'upgrade the algorithms'), integrate_platform ('add <platform>'), "
        "fix ('fix what's broken'), custom. Combine with ops_action compute_boost / research_focus when justified.",
        {"kind": {"type": "string", "enum": ["grow_profit", "integrate_platform", "fix", "custom"]},
         "objective": {"type": "string"}}, ["kind", "objective"]))

    def h_objectives(params, session_id=None, **kw):
        return _out(_call("GET", f"/api/ops/objectives?status_={urllib.parse.quote(params.get('status', 'ALL'))}",
                          actor=_actor(session_id)))
    ctx.register_tool(name="ops_objectives", toolset="forge_ops", handler=h_objectives, schema=_schema(
        "ops_objectives", "[FORGE EXEC] Executive objectives with per-role progress and results.",
        {"status": {"type": "string", "enum": ["ALL", "ACTIVE", "COMPLETE"]}}))

    def h_ticket(params, session_id=None, **kw):
        return _out(_call("POST", "/api/ops/action", {"action": "file_ticket", "params": params}, _actor(session_id)))
    ctx.register_tool(name="ops_ticket", toolset="forge_ops", handler=h_ticket, schema=_schema(
        "ops_ticket", "[FORGE EXEC] File an engineering ticket when a goal needs code (new platform adapter, algorithm "
        "change, bug fix). Include the credential type needed, if any.",
        {"title": {"type": "string"}, "spec": {"type": "string"}, "credential_needed": {"type": "string"}}, ["title"]))

    def h_tickets(params, session_id=None, **kw):
        return _out(_call("GET", "/api/ops/tickets", actor=_actor(session_id)))
    ctx.register_tool(name="ops_tickets", toolset="forge_ops", handler=h_tickets, schema=_schema(
        "ops_tickets", "[FORGE EXEC] Engineering tickets and their status.", {}))

    def h_transfer(params, session_id=None, **kw):
        return _out(_call("POST", "/api/ops/transfer/preview", {"amount_usd": params.get("amount_usd")}, _actor(session_id)))
    ctx.register_tool(name="ops_transfer_preview", toolset="forge_ops", handler=h_transfer, schema=_schema(
        "ops_transfer_preview", "[FORGE EXEC] Step 1 of 'transfer $X to me': preview amount, destination (owner's own "
        "pre-registered Coinbase portfolio), fee, treasury before/after and blockers. Show it to the owner verbatim.",
        {"amount_usd": {"type": "number"}}, ["amount_usd"]))

    def h_transfer_confirm(params, session_id=None, **kw):
        return _out(_call("POST", "/api/ops/transfer/confirm", {"transfer_id": params.get("transfer_id"),
                                                                "phrase": params.get("phrase"), "code": params.get("code")},
                          _actor(session_id)))
    ctx.register_tool(name="ops_transfer_confirm", toolset="forge_ops", handler=h_transfer_confirm, schema=_schema(
        "ops_transfer_confirm", "[FORGE EXEC] Step 2: ONLY after the owner typed 'CONFIRM TRANSFER $<amount> <6-digit "
        "authenticator code>'. Pass the phrase part and the code exactly as typed. Never fill these in yourself.",
        {"transfer_id": {"type": "string"}, "phrase": {"type": "string"}, "code": {"type": "string"}},
        ["transfer_id", "phrase", "code"]))

    # ---------------------------------------------------------------- host operations (FORGE units only)
    def h_restart(params, session_id=None, **kw):
        unit = UNITS.get(str(params.get("unit", "")))
        if not unit:
            return _out({"error": f"unit must be one of {sorted(UNITS)}"})
        rc, msg = _systemctl("restart", unit)
        healthy = _health_wait() if unit == "forge.service" and rc == 0 else None
        rc2, state = _systemctl("is-active", unit, timeout=10)
        res = {"unit": unit, "restart_rc": rc, "message": msg[:300], "state": state, "api_healthy": healthy}
        _audit("restart", {"unit": unit, "reason": params.get("reason")}, "OK" if rc == 0 else "ERROR", res, session_id)
        return _out(res)
    ctx.register_tool(name="ops_restart", toolset="forge_ops", handler=h_restart, schema=_schema(
        "ops_restart", "[FORGE OPS] Restart a FORGE service (forge = trading engine + API, forge-hermes = research agents, "
        "forge-tunnel = portal tunnel) and verify it came back healthy. Use for unhealthy/stale services; ~30-60 s.",
        {"unit": {"type": "string", "enum": sorted(UNITS)}, "reason": {"type": "string"}}, ["unit"]))

    def h_logs(params, session_id=None, **kw):
        unit = LOG_UNITS.get(str(params.get("unit", "forge")))
        if not unit:
            return _out({"error": f"unit must be one of {sorted(LOG_UNITS)}"})
        n = max(10, min(300, int(params.get("lines", 80))))
        since = str(params.get("since", "")).strip()
        cmd = ["journalctl", "-u", unit, "--no-pager", "-o", "short-iso", "-n", str(n)]
        if re.fullmatch(r"-?\d+\s?(min|h|m|s)|today|yesterday", since or "x"):
            cmd += ["--since", since if not since[0].isdigit() and not since.startswith("-") else f"-{since.lstrip('-')}"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = p.stdout.splitlines()
        pat = str(params.get("contains", "")).strip()
        if pat:
            lines = [ln for ln in lines if pat.lower() in ln.lower()]
        _audit("logs", {"unit": unit, "lines": n, "contains": pat}, "OK", None, session_id)
        return redact("\n".join(lines[-n:]))[:20000] or "(no matching lines)"
    ctx.register_tool(name="ops_logs", toolset="forge_ops", handler=h_logs, schema=_schema(
        "ops_logs", "[FORGE OPS] Recent journal lines of a FORGE service (secrets redacted). Filter with contains "
        "(e.g. 'error', 'Traceback', '401').", {"unit": {"type": "string", "enum": sorted(LOG_UNITS)},
                                                "lines": {"type": "integer"}, "contains": {"type": "string"},
                                                "since": {"type": "string", "description": "e.g. 30min, 2h, today"}}))

    def h_host(params, session_id=None, **kw):
        units = {u: _systemctl("is-active", f, timeout=10)[1] for u, f in LOG_UNITS.items()}
        restarts = {u: _systemctl("show", f, "-p", "NRestarts", "--value", timeout=10)[1] for u, f in LOG_UNITS.items()}
        mem = Path("/proc/meminfo").read_text().splitlines()[:3]
        psi = Path("/proc/pressure/memory").read_text().splitlines()[0] if Path("/proc/pressure/memory").exists() else ""
        st = os.statvfs("/srv/forge")
        return _out({"units": units, "restarts_since_boot": restarts, "loadavg": os.getloadavg(), "meminfo": mem,
                     "memory_pressure": psi, "disk_free_gb": round(st.f_bavail * st.f_frsize / 1e9, 1),
                     "uptime_h": round(float(Path("/proc/uptime").read_text().split()[0]) / 3600, 1)})
    ctx.register_tool(name="ops_host", toolset="forge_ops", handler=h_host, schema=_schema(
        "ops_host", "[FORGE OPS] Host diagnostics: FORGE unit states and restart counts, load, memory + pressure, disk, "
        "uptime.", {}))

    def h_audit(params, session_id=None, **kw):
        return _out(_call("GET", f"/api/ops/audit?limit={int(params.get('limit', 30))}", actor=_actor(session_id)))
    ctx.register_tool(name="ops_audit", toolset="forge_ops", handler=h_audit, schema=_schema(
        "ops_audit", "[FORGE OPS] Audit trail of every OPS command and action (who, what, outcome).",
        {"limit": {"type": "integer"}}))

    # ---------------------------------------------------------------- token accounting (attributed to role 'ops')
    def _usage(kind, session_id=None, usage=None, model=None, api_request_id=None, api_duration=None, **kwargs):
        if not usage:
            return
        u = usage if isinstance(usage, dict) else (usage.model_dump() if hasattr(usage, "model_dump") else
                                                   {k: getattr(usage, k) for k in dir(usage)
                                                    if k.endswith("tokens") and not k.startswith("_")})
        body = {"api_request_id": f"ops_{kind}_{session_id}_{api_request_id}_{os.urandom(4).hex()}"[:120], "usage": u,
                "model": model or "claude-opus-5-5", "session_id": session_id, "purpose": f"ops_{kind}",
                "latency_ms": int(float(api_duration or 0) * 1000)}
        threading.Thread(target=lambda: _call("POST", "/api/ops/usage", body, "ops-usage", 10), daemon=True).start()

    ctx.register_hook("post_api_request", lambda **kw: _usage("api", **kw))
    ctx.register_hook("post_auxiliary_call", lambda **kw: None if kw.get("error") else _usage("aux", **kw))
