"""hermes-forge — the FORGE tool surface inside Hermes (Hermes dossier §4).

Tools are the SAME tools FORGE's own brain uses (fetched from FORGE's agent API at load; static fallback), proxied to
http://127.0.0.1:8470/api/agent/tool. No exchange keys, no orders. Roles: every cron prompt starts with
"[forge-role:<role>]" → the pre_llm_call hook maps session → role; tool calls and token usage are attributed per role, so
FORGE measures each Hermes role's value-per-$ and throttles roles that do not pay for themselves.
"""

import json
import os
import re
import threading
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
API = os.environ.get("FORGE_API", "http://127.0.0.1:8470")
ROLE_RE = re.compile(r"\[forge-role:([a-z_]+)\]")
_roles: dict[str, str] = {}
_lock = threading.Lock()


def _token() -> str:
    return (HOME / "forge" / "agent_token").read_text().strip()


def _call(method: str, path: str, body: dict | None = None, timeout: float = 30.0) -> dict:
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def _role(session_id: str | None) -> str:
    with _lock:
        return _roles.get(session_id or "", "governor")


def _schemas() -> list[dict]:
    try:
        return [t["function"] for t in _call("GET", "/api/agent/tools").get("tools", [])]
    except Exception:
        return [{"name": "get_system_state", "description": "FORGE treasury, regime, fees, population.",
                 "parameters": {"type": "object", "properties": {}}}]


def register(ctx):
    for fn in _schemas():
        name = fn["name"]
        schema = {"name": f"forge_{name}", "description": "[FORGE] " + fn.get("description", ""),
                  "parameters": fn.get("parameters") or {"type": "object", "properties": {}}}

        def handler(params, session_id=None, _n=name, **kwargs):
            try:
                out = _call("POST", "/api/agent/tool", {"name": _n, "args": params or {}, "role": _role(session_id),
                                                        "session_id": session_id or "na"})
            except Exception as e:
                out = {"error": f"FORGE unreachable: {type(e).__name__}: {str(e)[:120]}"}
            return json.dumps(out, default=str)[:24000]

        ctx.register_tool(name=f"forge_{name}", toolset="forge", schema=schema, handler=handler)

    JOB_ROLE = {
        "forge-governor": "governor", "forge-alpha-inventor": "alpha_inventor",
        "forge-adversary": "adversary", "forge-critic": "critic", "forge-doctor": "doctor",
        "forge-rail-hunter": "rail_hunter", "forge-scout": "scout", "forge-architect": "architect",
        "forge-prediction": "prediction", "forge-execution": "execution",
        "forge-treasury": "treasury", "forge-intelligence": "intelligence",
        "forge-daily-report": "ops",
    }

    def on_pre_llm(session_id=None, user_message=None, **kwargs):
        msg = str(user_message or "")
        role = None
        m = ROLE_RE.search(msg)
        if m:
            role = m.group(1)
        if not role:
            for job, r in JOB_ROLE.items():
                if job in msg:
                    role = r
                    break
        # Explicit Tess/scout identity — never collapse to rail_hunter
        if role == "rail_hunter" and ("Callsign:** Tess" in msg or "Director of Strategic Opportunity" in msg):
            role = "scout"
        if role and session_id:
            with _lock:
                _roles[session_id] = role
        return None

    def _usage(kind, session_id=None, usage=None, model=None, api_request_id=None, api_duration=None, **kwargs):
        if not usage:
            return
        if isinstance(usage, dict):
            u = usage
        elif hasattr(usage, "model_dump"):
            u = usage.model_dump()
        elif hasattr(usage, "__dataclass_fields__"):
            import dataclasses
            u = dataclasses.asdict(usage)
        else:
            u = {k: getattr(usage, k) for k in dir(usage) if k.endswith("tokens") and not k.startswith("_")}
        uid = f"{kind}_{session_id}_{api_request_id}_{kwargs.get('api_call_count')}_{os.urandom(4).hex()}"
        body = {"api_request_id": uid[:120], "role": _role(session_id),
                "model": model or "deepseek-flash", "usage": u, "session_id": session_id,
                "latency_ms": int(float(api_duration or 0) * 1000), "purpose": kind}
        threading.Thread(target=lambda: _safe_post(body), daemon=True).start()

    def on_post_api(**kw):
        _usage("api", **kw)

    def on_post_aux(**kw):
        if kw.get("error"):
            return
        _usage("aux", **kw)

    ctx.register_hook("pre_llm_call", on_pre_llm)
    ctx.register_hook("post_api_request", on_post_api)
    ctx.register_hook("post_auxiliary_call", on_post_aux)


def _safe_post(body: dict) -> None:
    try:
        _call("POST", "/api/agent/usage", body, timeout=10)
    except Exception:
        pass
