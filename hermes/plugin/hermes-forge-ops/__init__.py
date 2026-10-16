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
    def h_research_results(params, session_id=None, **kw):
        return _out(_call("GET", "/api/v1/research/results", actor=_actor(session_id)))
    ctx.register_tool(name="ops_research_results", toolset="forge_ops", handler=h_research_results,
                      schema=_schema("ops_research_results", "[FORGE OPS] Where research money went: calls by role, "
                                     "jobs, artifacts, decisions, outstanding costs and paper curriculum. "
                                     "Report unresolved expenditure honestly; forecasts are not earned cash.", {}))
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

    def h_caps(params, session_id=None, **kw):
        return _out(_call("GET", "/api/ops/capabilities", actor=_actor(session_id)))
    ctx.register_tool(name="ops_capabilities", toolset="forge_ops", handler=h_caps, schema=_schema(
        "ops_capabilities", "[FORGE EXEC] Your live command roster: every Hermes specialist (mission, activity, open "
        "directives), FORGE services and engine loops, earning streams and rails, budgets (Modal, DeepSeek, Hermes "
        "mode), your actions and tools, engineering queue, treasury and target. Call it before planning any multi-step "
        "objective so you delegate to the right specialist.", {}))

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

    def h_treasury(params, session_id=None, **kw):
        _audit("treasury", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/treasury", actor=_actor(session_id)))
    ctx.register_tool(name="ops_treasury", toolset="forge_ops", handler=h_treasury, schema=_schema(
        "ops_treasury",
        "[FORGE EXEC] Treasury Truth: investment NAV, deployed/locked, RED ZONE, reconciliation, "
        "mode label, and safe-to-spend advisory (technical vs recommended). Use for 'how much can I spend?', "
        "'where is our money?', 'treasury status'.", {}))

    def h_spend(params, session_id=None, **kw):
        _audit("spend_advisory", params, "OK", session_id=session_id)
        truth = _call("GET", "/api/v1/treasury", actor=_actor(session_id))
        adv = (truth or {}).get("safe_to_withdraw_estimate") or {}
        return _out({
            "question": "how_much_can_I_spend",
            "mode_label": truth.get("mode_label"),
            "treasury_nav": truth.get("treasury_nav"),
            "red_zone": truth.get("red_zone"),
            "technical_usd": adv.get("technical_usd"),
            "recommended_usd": adv.get("recommended_usd"),
            "reason": adv.get("reason"),
            "note": "Advisory only. Transfers require founder confirmation flow. can_transfer may be false.",
            "account_flags": truth.get("account_flags"),
        })
    ctx.register_tool(name="ops_spend_advisory", toolset="forge_ops", handler=h_spend, schema=_schema(
        "ops_spend_advisory",
        "[FORGE EXEC] Answer 'how much can I move to spending?' with technical vs recommended amounts, "
        "RED ZONE status, and effect framing. Never invent balances — uses Treasury Truth.", {}))

    def h_trial(params, session_id=None, **kw):
        _audit("trial", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/trial/current", actor=_actor(session_id)))
    ctx.register_tool(name="ops_trial", toolset="forge_ops", handler=h_trial, schema=_schema(
        "ops_trial",
        "[FORGE EXEC] Current PAPER trial / 8h full-dress scorecard vs $1/h TRUE-NET target.", {}))

    def h_evidence(params, session_id=None, **kw):
        _audit("evidence", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/lab/evidence", actor=_actor(session_id)))
    ctx.register_tool(name="ops_evidence", toolset="forge_ops", handler=h_evidence, schema=_schema(
        "ops_evidence",
        "[FORGE EXEC] What WORKS / DOESN'T / inconclusive on PAPER (+ shadow rails). "
        "Use when founder asks 'what is working?', 'what should we kill?', 'show me the lab results'.", {}))

    def h_paper_lab(params, session_id=None, **kw):
        _audit("paper_lab", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/lab/paper", actor=_actor(session_id)))
    
    def h_vigil(params, session_id=None, **kw):
        _audit("vigil", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/lab/vigil", actor=_actor(session_id)))
    
    def h_dispatch(params, session_id=None, **kw):
        _audit("dispatch", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/lab/dispatch", actor=_actor(session_id)))
    ctx.register_tool(name="ops_dispatch", toolset="forge_ops", handler=h_dispatch, schema=_schema(
        "ops_dispatch",
        "[FORGE EXEC] Officer Dispatch: event-wakes titled Hermes roles on justified events "
        "(local regen first; LLM only with cooldowns). 24/7 goals without 24/7 inference.", {}))

    def h_intel(params, session_id=None, **kw):
        _audit("intel_feeds", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/intel/feeds", actor=_actor(session_id)))
    ctx.register_tool(name="ops_intel_feeds", toolset="forge_ops", handler=h_intel, schema=_schema(
        "ops_intel_feeds",
        "[FORGE EXEC] External SaaS/public intel board: EDGAR, Twelve Data, Odds API status + signup links.", {}))

    
    def h_econ(params, session_id=None, **kw):
        _audit("econ_tournament", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/econ/tournament", actor=_actor(session_id)))
    
    def h_esc(params, session_id=None, **kw):
        _audit("earnings_escalator", params, "OK", session_id=session_id)
        d=_call("GET", "/api/v1/econ/tournament", actor=_actor(session_id))
        return _out({k: (d or {}).get(k) for k in ("earnings_escalator","membership_recommendation","board","trial","prefer_rails","paper_bets")})
    ctx.register_tool(name="ops_earnings_escalator", toolset="forge_ops", handler=h_esc, schema=_schema(
        "ops_earnings_escalator",
        "[FORGE EXEC] Earnings Escalator: unacceptable $/h response — actionable levers, implementations, membership CANCEL.", {}))
    ctx.register_tool(name="ops_econ_tournament", toolset="forge_ops", handler=h_econ, schema=_schema(
        "ops_econ_tournament",
        "[FORGE EXEC] 8h PAPER economic tournament scoreboard: treasury board, realloc, edge decay, "
        "paper bets, Modal research, proven $/h, constraints to $1/h. Use for 'how are we doing economically'.", {}))

    def h_paper_bets(params, session_id=None, **kw):
        _audit("paper_bets", params, "OK", session_id=session_id)
        return _out(_call("GET", "/api/v1/lab/paper_bets", actor=_actor(session_id)))
    ctx.register_tool(name="ops_paper_bets", toolset="forge_ops", handler=h_paper_bets, schema=_schema(
        "ops_paper_bets",
        "[FORGE EXEC] PAPER event-bet desk (Odds intelligence, fake money): open bets, edges, bankroll, settlements.", {}))

    ctx.register_tool(name="ops_vigil", toolset="forge_ops", handler=h_vigil, schema=_schema(
        "ops_vigil",
        "[FORGE EXEC] Position Vigil: stuck/losing cuts, hibernations, challenger demands. "
        "Use when founder asks why capital is stuck or what the desk cut automatically.", {}))

    ctx.register_tool(name="ops_paper_lab", toolset="forge_ops", handler=h_paper_lab, schema=_schema(
        "ops_paper_lab",
        "[FORGE EXEC] Aggressive PAPER lab status: diversity actions, stable bridges, promotions, aggression settings.", {}))



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
    ctx.register_tool(name="ops_engineer", toolset="forge_ops", handler=h_ticket, schema=_schema(
        "ops_engineer", "[FORGE EXEC] Give the FORGE ENGINEER (sandboxed coding agent, DeepSeek V4.1 Flash, high reasoning) a code task: "
        "upgrade/debug/advance an algorithm or engine, build a platform adapter, fix a bug, add telemetry. Write a precise "
        "spec: goal, evidence, acceptance criteria, expected $/h effect. It picks it up within ~10 min, writes code + "
        "tests, submits; the root deployer policy-scans, tests in a sandbox, deploys, watches health 10 min and rolls back "
        "on degradation. Protected areas (risk, live execution, venues, money movement, security, deps) wait for owner "
        "approval (ops_action approve_deploy). Track with ops_tickets.",
        {"title": {"type": "string"}, "spec": {"type": "string"}, "priority": {"type": "string", "enum": ["normal", "high"]},
         "credential_needed": {"type": "string"}}, ["title", "spec"]))

    def h_tickets(params, session_id=None, **kw):
        return _out(_call("GET", "/api/ops/tickets", actor=_actor(session_id)))
    ctx.register_tool(name="ops_tickets", toolset="forge_ops", handler=h_tickets, schema=_schema(
        "ops_tickets", "[FORGE EXEC] Engineering tickets: status (OPEN/IN_PROGRESS/SUBMITTED/DONE/BLOCKED/HOLD), deploy "
        "status (QUEUED/AWAITING_OWNER/DEPLOYED/ROLLED_BACK/TESTS_FAILED/REJECTED), engineer notes and deploy log.", {}))

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

    # ---------------------------------------------------------------- insight tools (OP-026)
    def _get(path, session_id):
        return _out(_call("GET", path, actor=_actor(session_id)))

    ctx.register_tool(name="ops_leaderboard", toolset="forge_ops", schema=_schema(
        "ops_leaderboard", "[FORGE EXEC] Who makes / loses the money: evolved strategies ranked by net $ (paper book, with "
        "forward evidence) and every income stream ranked by evidence (tier, mean per unit, P>0, potential $/h). Use for "
        "'which strategy is best/worst', 'what's working', 'what should we scale or kill'.",
        {"window": {"type": "string", "description": "30m … 7d, today, lifetime (default 7d)"}, "limit": {"type": "integer"}}),
        handler=lambda p, session_id=None, **kw: _get(
            f"/api/ops/leaderboard?window={urllib.parse.quote(str(p.get('window', '7d')))}&limit={int(p.get('limit', 10))}",
            session_id))

    ctx.register_tool(name="ops_trades", toolset="forge_ops", schema=_schema(
        "ops_trades", "[FORGE EXEC] Trades and positions: open now, recent closes with net P&L and exit reason (paper/live), "
        "Kalshi signals (shadow) and Kalshi live orders. Use for 'what did we trade', 'what's open', 'show recent bets'.",
        {"window": {"type": "string"}, "book": {"type": "string", "enum": ["all", "paper", "live", "shadow", "kalshi"]},
         "limit": {"type": "integer"}}),
        handler=lambda p, session_id=None, **kw: _get(
            f"/api/ops/trades?window={urllib.parse.quote(str(p.get('window', '24h')))}&book={p.get('book', 'all')}"
            f"&limit={int(p.get('limit', 25))}", session_id))

    ctx.register_tool(name="ops_changes", toolset="forge_ops", schema=_schema(
        "ops_changes", "[FORGE EXEC] What changed since a time: deployments, strategy promotions/kills, completed directives "
        "and objectives, owner/agent actions, guardian repairs, new listings, warnings. Use for 'what happened while I was "
        "away', 'what changed today', 'catch me up'.", {"since": {"type": "string", "description": "e.g. 2h, today, 24h"}}),
        handler=lambda p, session_id=None, **kw: _get(f"/api/ops/changes?since={urllib.parse.quote(str(p.get('since', 'today')))}",
                                                     session_id))

    def h_chart(params, session_id=None, **kw):
        metric, window = str(params.get("metric", "treasury")), str(params.get("window", "24h"))
        d = _call("GET", f"/api/ops/series?metric={urllib.parse.quote(metric)}&window={urllib.parse.quote(window)}",
                  actor=_actor(session_id))
        if d.get("error"):
            return _out(d)
        try:
            path = _render_chart(d)
        except Exception as e:  # noqa: BLE001
            return _out({"error": f"chart render failed: {e}"})
        return (f"Chart ready. To send it to the owner, put this exact line in your reply on its own line:\nMEDIA:{path}\n"
                f"Summary data: {json.dumps(_chart_summary(d))[:1500]}")
    ctx.register_tool(name="ops_chart", toolset="forge_ops", handler=h_chart, schema=_schema(
        "ops_chart", "[FORGE EXEC] Make a chart image and send it in the chat: treasury (live $), paper_equity, usd_per_hour "
        "(realized vs potential vs target), stream_pnl (bar: P&L by income stream). Use whenever the owner says show / "
        "chart / graph / visualize, or when a picture explains a trend faster.",
        {"metric": {"type": "string", "enum": ["treasury", "paper_equity", "usd_per_hour", "stream_pnl"]},
         "window": {"type": "string", "description": "1h, 4h, today, 24h, 7d"}}, ["metric"]))

    def h_alert(params, session_id=None, **kw):
        return _out(_call("POST", "/api/ops/alerts", params, _actor(session_id)))
    ctx.register_tool(name="ops_alert", toolset="forge_ops", handler=h_alert, schema=_schema(
        "ops_alert", "[FORGE EXEC] Instant rule alerts to the owner's Telegram (checked every 30 s, no AI cost): create / "
        "list / delete. Metrics: treasury_usd, live_usd_per_h_1h, live_net_today_usd, paper_equity_usd, health_score, "
        "open_incidents, potential_usd_per_h, settled_signals_1h, stream_tier (arg = stream id, e.g. kalshi.SETTLE_WINDOW; "
        "threshold e.g. MEDIUM). Use for 'tell me when / if …', 'alert me', 'let me know'.",
        {"action": {"type": "string", "enum": ["create", "list", "delete"]}, "metric": {"type": "string"},
         "arg": {"type": "string"}, "op": {"type": "string", "enum": ["<", "<=", ">", ">=", "==", "!="]},
         "threshold": {"type": "string"}, "note": {"type": "string"}, "once": {"type": "boolean"}, "id": {"type": "integer"}},
        ["action"]))

    def h_cred(params, session_id=None, **kw):
        return _out(_call("POST", "/api/ops/credential_request", params, _actor(session_id)))
    ctx.register_tool(name="ops_credential_request", toolset="forge_ops", handler=h_cred, schema=_schema(
        "ops_credential_request", "[FORGE EXEC] When a platform needs an API key/secret: create a one-time secure link "
        "(30 min) the owner opens on their phone (portal login) to paste it; it is installed server-side and FORGE restarts "
        "to load it. kind=env for single-line values (UPPER_SNAKE name, e.g. KALSHI_API_KEY_ID), kind=pem for key files "
        "(lowercase name, e.g. kalshi_private_key). Send the owner the link; never ask for secrets in chat.",
        {"name": {"type": "string"}, "kind": {"type": "string", "enum": ["env", "pem"]}, "purpose": {"type": "string"}},
        ["name", "purpose"]))

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
                "model": model or "deepseek-flash", "session_id": session_id, "purpose": f"ops_{kind}",
                "latency_ms": int(float(api_duration or 0) * 1000)}
        threading.Thread(target=lambda: _call("POST", "/api/ops/usage", body, "ops-usage", 10), daemon=True).start()

    ctx.register_hook("post_api_request", lambda **kw: _usage("api", **kw))
    ctx.register_hook("post_auxiliary_call", lambda **kw: None if kw.get("error") else _usage("aux", **kw))


# ---------------------------------------------------------------------------------------------- chart rendering (Pillow)
def _chart_summary(d):
    if d.get("kind") == "bar":
        return {"bars": d.get("bars", [])[:12]}
    lines = d.get("lines") or {d.get("metric", "value"): d.get("points", [])}
    out = {}
    for k, pts in lines.items():
        vals = [v for _, v in pts if v is not None]
        if vals:
            out[k] = {"first": round(vals[0], 4), "last": round(vals[-1], 4), "min": round(min(vals), 4),
                      "max": round(max(vals), 4), "n": len(vals)}
    return out


def _render_chart(d):
    from datetime import datetime, timezone

    from PIL import Image, ImageDraw, ImageFont
    W, H, L, R, T, B = 1000, 560, 90, 30, 60, 70
    img = Image.new("RGB", (W, H), (17, 20, 27))
    g = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=18)
        small = ImageFont.load_default(size=14)
    except TypeError:
        font = small = ImageFont.load_default()
    title = f"FORGE · {d.get('metric')} · {d.get('window')}"
    g.text((L, 18), title, fill=(235, 235, 240), font=font)
    colors = [(56, 189, 248), (250, 204, 21), (239, 68, 68), (34, 197, 94), (168, 85, 247)]
    pw, ph = W - L - R, H - T - B
    g.rectangle([L, T, L + pw, T + ph], outline=(60, 66, 80))
    if d.get("kind") == "bar":
        bars = d.get("bars", [])[:14] or [["(no data)", 0.0]]
        vals = [v for _, v in bars]
        lo, hi = min(0.0, min(vals)), max(0.0, max(vals))
        span = (hi - lo) or 1.0
        y0 = T + ph * (hi / span)
        g.line([L, y0, L + pw, y0], fill=(120, 120, 130))
        bw = pw / len(bars)
        for i, (lab, v) in enumerate(bars):
            x0, x1 = L + i * bw + 6, L + (i + 1) * bw - 6
            y = T + ph * ((hi - v) / span)
            g.rectangle([x0, min(y, y0), x1, max(y, y0)], fill=(34, 197, 94) if v >= 0 else (239, 68, 68))
            g.text((x0, T + ph + 6), str(lab)[-14:], fill=(200, 200, 210), font=small)
            g.text((x0, min(y, y0) - 18), f"{v:+.3f}", fill=(220, 220, 225), font=small)
    else:
        lines = d.get("lines") or {d.get("metric", "value"): d.get("points", [])}
        allpts = [p for pts in lines.values() for p in pts if p[1] is not None]
        if not allpts:
            g.text((L + 20, T + 20), "no data yet for this window", fill=(200, 200, 210), font=font)
        else:
            x_lo, x_hi = min(p[0] for p in allpts), max(p[0] for p in allpts)
            y_lo, y_hi = min(p[1] for p in allpts), max(p[1] for p in allpts)
            if y_hi - y_lo < 1e-9:
                y_lo, y_hi = y_lo - 1, y_hi + 1
            pad = (y_hi - y_lo) * 0.08
            y_lo, y_hi = y_lo - pad, y_hi + pad
            fx = lambda x: L + pw * ((x - x_lo) / ((x_hi - x_lo) or 1))  # noqa: E731
            fy = lambda y: T + ph * (1 - (y - y_lo) / (y_hi - y_lo))      # noqa: E731
            for k in range(5):
                yv = y_lo + (y_hi - y_lo) * k / 4
                g.line([L, fy(yv), L + pw, fy(yv)], fill=(40, 45, 56))
                g.text((8, fy(yv) - 8), f"{yv:,.4g}", fill=(170, 170, 180), font=small)
            for k in range(5):
                xv = x_lo + (x_hi - x_lo) * k / 4
                g.text((fx(xv) - 20, T + ph + 8), datetime.fromtimestamp(xv, timezone.utc).strftime("%m-%d %H:%M"),
                       fill=(170, 170, 180), font=small)
            for i, (name, pts) in enumerate(lines.items()):
                xy = [(fx(x), fy(y)) for x, y in pts if y is not None]
                if len(xy) >= 2:
                    g.line(xy, fill=colors[i % len(colors)], width=3)
                elif xy:
                    g.ellipse([xy[0][0] - 3, xy[0][1] - 3, xy[0][0] + 3, xy[0][1] + 3], fill=colors[i % len(colors)])
                g.text((L + 10 + i * 230, T + ph + 40), f"■ {name}", fill=colors[i % len(colors)], font=small)
    out = Path(os.environ.get("FORGE_CHART_DIR", "/srv/forge/runtime/ops/work/charts"))
    out.mkdir(parents=True, exist_ok=True)
    for old in sorted(out.glob("*.png"))[:-30]:
        old.unlink(missing_ok=True)
    path = out / f"{d.get('metric')}_{int(time.time())}.png"
    img.save(path, "PNG")
    return str(path)

