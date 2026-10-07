"""hermes-forge-eng — the FORGE Engineer's FORGE-facing tools (OP-025). Code work itself uses Hermes' terminal/file tools
inside the engineer sandbox (repo: /srv/forge/runtime/eng/repo). Deploys are done ONLY by the root deployer."""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
API = os.environ.get("FORGE_API", "http://127.0.0.1:8470")


def _call(method, path, body=None, timeout=30.0):
    tok = (HOME / "forge" / "eng_token").read_text().strip()
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode()[:400]}


def _s(name, desc, props, req=None):
    return {"name": name, "description": desc, "parameters": {"type": "object", "properties": props, "required": req or []}}


def register(ctx):
    def h_next(p, **kw):
        return json.dumps(_call("GET", "/api/ops/eng/next"), default=str)[:20000]
    ctx.register_tool(name="eng_next_ticket", toolset="forge_eng", handler=h_next, schema=_s(
        "eng_next_ticket", "Next engineering ticket to work on (highest priority, oldest; includes tickets whose deploy "
        "failed and need a fix).", {}))

    def h_ticket(p, **kw):
        return json.dumps(_call("GET", f"/api/ops/eng/ticket?id={int(p.get('id', 0))}"), default=str)[:30000]
    ctx.register_tool(name="eng_ticket", toolset="forge_eng", handler=h_ticket, schema=_s(
        "eng_ticket", "Full ticket incl. spec, deploy log of the last attempt and (for platform integrations) the research "
        "findings of rail_hunter / critic / governor.", {"id": {"type": "integer"}}, ["id"]))

    def h_claim(p, **kw):
        return json.dumps(_call("POST", "/api/ops/eng/claim", {"id": p.get("id")}))
    ctx.register_tool(name="eng_claim", toolset="forge_eng", handler=h_claim, schema=_s(
        "eng_claim", "Claim a ticket (marks IN_PROGRESS).", {"id": {"type": "integer"}}, ["id"]))

    def h_update(p, **kw):
        return json.dumps(_call("POST", "/api/ops/eng/update", p))
    ctx.register_tool(name="eng_update", toolset="forge_eng", handler=h_update, schema=_s(
        "eng_update", "Report on a ticket. status=SUBMITTED with commit_sha (full sha of your commit in the engineer repo, "
        "based on prod HEAD, all tests passing) queues it for the root deployer. DONE = resolved without code (answer in "
        "note). BLOCKED = needs owner/ops (say exactly what). IN_PROGRESS = progress note.",
        {"id": {"type": "integer"}, "status": {"type": "string", "enum": ["IN_PROGRESS", "SUBMITTED", "DONE", "BLOCKED"]},
         "commit_sha": {"type": "string"}, "branch": {"type": "string"}, "note": {"type": "string"}}, ["id", "status"]))

    try:
        tools = _call("GET", "/api/ops/tools").get("tools", [])
    except Exception:
        tools = []
    for t in tools:
        fn = t["function"]

        def handler(p, _n=fn["name"], **kw):
            return json.dumps(_call("POST", "/api/ops/tool", {"name": _n, "args": p or {}}), default=str)[:24000]
        ctx.register_tool(name=f"forge_{fn['name']}", toolset="forge_eng", handler=handler, schema=_s(
            f"forge_{fn['name']}", "[FORGE read] " + fn.get("description", ""), (fn.get("parameters") or {}).get("properties", {}),
            (fn.get("parameters") or {}).get("required")))
